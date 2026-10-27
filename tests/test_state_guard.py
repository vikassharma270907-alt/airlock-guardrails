"""Unit tests for Gate 5: State & Readiness Integrity Guardrail (ReturnReady Engine)."""

import time
import pytest
from tools.state_guard import (
    ChecklistItem,
    ReturnTaskItem,
    PendingAction,
    StateGuardEngine,
    PreconditionFailedError,
    StateLockedError,
    VersionConflictError,
    ActionExpiredError,
    run_self_test,
)


@pytest.fixture
def sample_items():
    return [
        ReturnTaskItem(
            id="item-incomplete",
            name="Wireless Headphones",
            merchant="Demo Electronics",
            amount_inr=4999.0,
            purchase_date="2026-10-13",
            return_deadline="2026-10-28",
            status="preparing",
            version=1,
            checklist=[
                ChecklistItem("c1", "Unit", True),
                ChecklistItem("c2", "Cable", False),
            ],
        ),
        ReturnTaskItem(
            id="item-ready",
            name="Running Shoes",
            merchant="Demo Sports",
            amount_inr=2799.0,
            purchase_date="2026-10-14",
            return_deadline="2026-10-30",
            status="preparing",
            version=2,
            checklist=[
                ChecklistItem("c3", "Shoes", True),
                ChecklistItem("c4", "Box", True),
            ],
        ),
        ReturnTaskItem(
            id="item-terminal",
            name="Travel Backpack",
            merchant="Demo Outdoors",
            amount_inr=1999.0,
            purchase_date="2026-10-10",
            return_deadline="2026-10-22",
            status="dropped_off",
            version=3,
            checklist=[
                ChecklistItem("c5", "Emptied", True),
            ],
        ),
        ReturnTaskItem(
            id="item-empty-checklist",
            name="Desk Lamp",
            merchant="Demo Living",
            amount_inr=1299.0,
            purchase_date="2026-10-15",
            return_deadline="2026-11-01",
            status="planning",
            version=1,
            checklist=[],
        ),
    ]


def test_readiness_derivation_and_blocking_incomplete(sample_items):
    engine = StateGuardEngine()
    item = sample_items[0]
    assert not item.is_ready
    assert item.derived_status == "preparing"

    with pytest.raises(PreconditionFailedError) as exc_info:
        engine.validate_transition(item, "dropped_off")
    assert "incomplete verification checks" in str(exc_info.value)


def test_readiness_derivation_complete(sample_items):
    engine = StateGuardEngine()
    item = sample_items[1]
    assert item.is_ready
    assert item.derived_status == "ready"
    assert engine.validate_transition(item, "dropped_off") is True


def test_zero_checklist_readiness_blocked(sample_items):
    engine = StateGuardEngine()
    item = sample_items[3]
    assert not item.is_ready

    with pytest.raises(PreconditionFailedError) as exc_info:
        engine.validate_transition(item, "ready")
    assert "no checklist verification criteria defined" in str(exc_info.value)


def test_terminal_state_locking_blocks_mutation(sample_items):
    engine = StateGuardEngine()
    item = sample_items[2]
    assert item.is_locked

    action = PendingAction(
        kind="assign",
        item_id=item.id,
        item_name=item.name,
        expected_version=item.version,
        created_at_ms=int(time.time() * 1000),
    )
    with pytest.raises(StateLockedError) as exc_info:
        engine.validate_action(item, action)
    assert "Cannot execute 'assign' on locked terminal item" in str(exc_info.value)


def test_optimistic_concurrency_version_mismatch(sample_items):
    engine = StateGuardEngine()
    item = sample_items[1]  # version 2

    stale_action = PendingAction(
        kind="dropoff",
        item_id=item.id,
        item_name=item.name,
        expected_version=1,  # Stale!
        created_at_ms=int(time.time() * 1000),
    )
    with pytest.raises(VersionConflictError) as exc_info:
        engine.validate_action(item, stale_action)
    assert "Optimistic Concurrency Conflict" in str(exc_info.value)


def test_action_token_ttl_expiration(sample_items):
    engine = StateGuardEngine(ttl_ms=1000)
    item = sample_items[1]

    old_time = int(time.time() * 1000) - 2000
    expired_action = PendingAction(
        kind="dropoff",
        item_id=item.id,
        item_name=item.name,
        expected_version=item.version,
        created_at_ms=old_time,
    )
    with pytest.raises(ActionExpiredError) as exc_info:
        engine.validate_action(item, expired_action)
    assert "Pending Action Expired" in str(exc_info.value)


def test_intent_router_due_and_ready_filters(sample_items):
    engine = StateGuardEngine()
    due_res = engine.route_intent("what is due soon", sample_items)
    assert due_res["intent"] == "list_due"
    assert len(due_res["items"]) == 3  # All except terminal dropped_off

    ready_res = engine.route_intent("what is ready", sample_items)
    assert ready_res["intent"] == "list_ready"
    assert len(ready_res["items"]) == 1
    assert ready_res["items"][0]["name"] == "Running Shoes"


def test_intent_router_ambiguous_mutation_blocked(sample_items):
    engine = StateGuardEngine()
    res = engine.route_intent("drop off", sample_items)
    assert res["status"] == "BLOCKED"
    assert "No matching purchase identified" in res["error"]


def test_intent_router_dropoff_valid_proposes_action(sample_items):
    engine = StateGuardEngine()
    res = engine.route_intent("drop off running shoes", sample_items)
    assert res["status"] == "PENDING_CONFIRMATION"
    assert res["pending_action"]["kind"] == "dropoff"
    assert res["pending_action"]["expected_version"] == 2


def test_cli_self_test_exit_code_zero():
    assert run_self_test() == 0
