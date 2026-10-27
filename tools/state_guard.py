"""State & Readiness Integrity Guardrail (ReturnReady Engine).

Enforces deterministic state progression, 100% checklist verification preconditions,
terminal state-locking (immutability), and version-bound optimistic concurrency for
autonomous and human-in-the-loop task operations.

Integrated from ReturnReady Guardian architecture.
Owner: Vikas Sharma <beyondnothing01@gmail.com>
"""

import argparse
import json
import re
import sys
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

PENDING_CONFIRMATION_TTL_MS = 5 * 60 * 1000  # 5 minutes


class StateGuardError(Exception):
    """Base exception for State Guard violations."""

    pass


class PreconditionFailedError(StateGuardError):
    """Raised when checklist verification criteria are not 100% satisfied."""

    pass


class StateLockedError(StateGuardError):
    """Raised when mutating an immutable or terminal state."""

    pass


class VersionConflictError(StateGuardError):
    """Raised when optimistic concurrency version mismatch is detected."""

    pass


class ActionExpiredError(StateGuardError):
    """Raised when action confirmation token has exceeded TTL."""

    pass


class AmbiguousIntentError(StateGuardError):
    """Raised when an intent cannot be mapped deterministically to a single entity."""

    pass


@dataclass
class ChecklistItem:
    id: str
    label: str
    checked: bool
    sort_order: int = 1


@dataclass
class ReturnTaskItem:
    id: str
    name: str
    merchant: str
    amount_inr: float
    purchase_date: str
    return_deadline: str
    status: str  # 'planning' | 'preparing' | 'dropped_off'
    version: int = 1
    assignee_name: Optional[str] = None
    checklist: List[ChecklistItem] = field(default_factory=list)
    dropped_off_at: Optional[str] = None

    @property
    def total_checks(self) -> int:
        return len(self.checklist)

    @property
    def completed_checks(self) -> int:
        return sum(1 for c in self.checklist if c.checked)

    @property
    def is_ready(self) -> bool:
        return self.status != "dropped_off" and self.total_checks > 0 and self.completed_checks == self.total_checks

    @property
    def derived_status(self) -> str:
        if self.status == "dropped_off":
            return "dropped_off"
        if self.is_ready:
            return "ready"
        return self.status

    @property
    def is_locked(self) -> bool:
        return self.status == "dropped_off"

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["total_checks"] = self.total_checks
        d["completed_checks"] = self.completed_checks
        d["is_ready"] = self.is_ready
        d["derived_status"] = self.derived_status
        d["is_locked"] = self.is_locked
        return d


@dataclass
class PendingAction:
    kind: str  # 'assign' | 'dropoff' | 'reopen' | 'status_change'
    item_id: str
    item_name: str
    expected_version: int
    created_at_ms: int
    payload: Dict[str, Any] = field(default_factory=dict)


PRODUCT_SYNONYMS: Dict[str, List[str]] = {
    "wireless headphones": ["headphones", "headphone", "headset", "earphones", "earbuds", "audio"],
    "running shoes": ["shoes", "shoe", "trainers", "sneakers", "footwear"],
    "desk lamp": ["lamp", "light", "desk light", "reading light", "study lamp"],
    "travel backpack": ["backpack", "rucksack", "travel bag", "daypack", "bag"],
    "coffee grinder": ["grinder", "coffee", "coffee mill", "burr grinder"],
}


def normalize_utterance(text: str) -> str:
    """Normalize utterance for deterministic matching."""
    cleaned = text.lower()
    cleaned = re.sub(r"['’]", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9\s]", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


class StateGuardEngine:
    """State & Readiness Integrity Guardrail Engine."""

    def __init__(self, ttl_ms: int = PENDING_CONFIRMATION_TTL_MS):
        self.ttl_ms = ttl_ms

    def validate_transition(self, item: ReturnTaskItem, target_status: str) -> bool:
        """Validate if item can transition to target_status."""
        # 1. Terminal state locking check
        if item.is_locked and target_status != "dropped_off":
            raise StateLockedError(
                f"State Lock Violation: '{item.name}' is in terminal state 'dropped_off' (immutably locked). "
                f"Requires explicit audited reopen workflow."
            )

        # 2. Checklist completeness check for ready / dropoff
        if target_status in ("ready", "dropped_off"):
            if item.total_checks == 0:
                raise PreconditionFailedError(
                    f"Readiness Precondition Failed: '{item.name}' has no checklist verification criteria defined."
                )
            if item.completed_checks < item.total_checks:
                incomplete = [c.label for c in item.checklist if not c.checked]
                raise PreconditionFailedError(
                    f"Readiness Precondition Failed: '{item.name}' has {len(incomplete)} incomplete verification checks: "
                    f"{', '.join(incomplete)}. Cannot transition to '{target_status}'."
                )

        return True

    def validate_action(
        self,
        item: ReturnTaskItem,
        action: PendingAction,
        current_time_ms: Optional[int] = None,
    ) -> bool:
        """Validate action against optimistic concurrency and state locks."""
        now = current_time_ms if current_time_ms is not None else int(time.time() * 1000)

        # 1. Concurrency Check (Version-Bound)
        if action.expected_version != item.version:
            raise VersionConflictError(
                f"Optimistic Concurrency Conflict on '{item.name}': "
                f"Action expected version {action.expected_version}, but resource is at version {item.version}. "
                f"Stale state mutation rejected."
            )

        # 2. TTL Expiry Check
        elapsed = now - action.created_at_ms
        if elapsed > self.ttl_ms:
            raise ActionExpiredError(
                f"Pending Action Expired: Action '{action.kind}' token elapsed {elapsed}ms (TTL limit {self.ttl_ms}ms). "
                f"Must re-propose action with active user intent."
            )

        # 3. Terminal State Lock Check
        if item.is_locked and action.kind != "reopen":
            raise StateLockedError(
                f"State Lock Violation: Cannot execute '{action.kind}' on locked terminal item '{item.name}'."
            )

        # 4. Action-specific Precondition checks
        if action.kind == "dropoff":
            self.validate_transition(item, "dropped_off")

        return True

    def match_item_in_text(self, text: str, items: List[ReturnTaskItem]) -> List[ReturnTaskItem]:
        """Find matching items from natural text using exact and synonym dictionary."""
        norm = normalize_utterance(text)
        if not norm:
            return []

        words = set(norm.split())
        matched = []

        for item in items:
            item_norm = normalize_utterance(item.name)
            if item_norm in norm:
                matched.append(item)
                continue

            synonyms = PRODUCT_SYNONYMS.get(item_norm, [])
            if any(syn in words or syn in norm for syn in synonyms):
                matched.append(item)

        return matched

    def route_intent(self, utterance: str, items: List[ReturnTaskItem]) -> Dict[str, Any]:
        """Classify and resolve conversational intent with strict ambiguity guardrails."""
        norm = normalize_utterance(utterance)
        matched = self.match_item_in_text(utterance, items)

        if not norm or norm in ("help", "what can you do"):
            return {
                "intent": "help",
                "message": "Supported commands: 'what is due', 'what is ready', 'drop off <item>', 'assign <item> to <name>'.",
            }

        if any(kw in norm for kw in ("what is due", "due soon", "list due", "pending returns")):
            due_items = [i for i in items if i.status != "dropped_off"]
            return {
                "intent": "list_due",
                "items": [i.to_dict() for i in due_items],
                "message": f"Found {len(due_items)} active returns in progress.",
            }

        if any(kw in norm for kw in ("what is ready", "ready items", "list ready")):
            ready_items = [i for i in items if i.is_ready]
            return {
                "intent": "list_ready",
                "items": [i.to_dict() for i in ready_items],
                "message": f"Found {len(ready_items)} returns 100% prepared and ready to drop off.",
            }

        if any(kw in norm for kw in ("drop off", "dropped off", "complete return")):
            if len(matched) == 0:
                return {
                    "intent": "ambiguous_mutation",
                    "error": "No matching purchase identified. Please specify which item to drop off.",
                    "status": "BLOCKED",
                }
            if len(matched) > 1:
                return {
                    "intent": "ambiguous_mutation",
                    "error": f"Ambiguous request matches multiple items: {', '.join(i.name for i in matched)}. Please clarify.",
                    "status": "BLOCKED",
                }

            target = matched[0]
            try:
                self.validate_transition(target, "dropped_off")
                action = PendingAction(
                    kind="dropoff",
                    item_id=target.id,
                    item_name=target.name,
                    expected_version=target.version,
                    created_at_ms=int(time.time() * 1000),
                )
                return {
                    "intent": "propose_dropoff",
                    "target": target.to_dict(),
                    "pending_action": asdict(action),
                    "message": f"Confirmed readiness: All {target.total_checks} packing checks verified. Ready to record drop-off.",
                    "status": "PENDING_CONFIRMATION",
                }
            except StateGuardError as e:
                return {
                    "intent": "blocked_dropoff",
                    "target": target.to_dict(),
                    "error": str(e),
                    "status": "BLOCKED",
                }

        return {
            "intent": "unknown",
            "message": f"Unrecognized intent: '{utterance}'. Rephrase or type 'help'.",
        }


def create_sample_dataset() -> List[ReturnTaskItem]:
    """Create benchmark dataset representing household return tasks."""
    return [
        ReturnTaskItem(
            id="ret-1",
            name="Wireless Headphones",
            merchant="Demo Electronics",
            amount_inr=4999.0,
            purchase_date="2026-10-13",
            return_deadline="2026-10-28",
            status="preparing",
            version=1,
            checklist=[
                ChecklistItem("c1", "Headphones unit", True),
                ChecklistItem("c2", "Charging cable & case", False),  # Incomplete!
            ],
        ),
        ReturnTaskItem(
            id="ret-2",
            name="Running Shoes",
            merchant="Demo Sports",
            amount_inr=2799.0,
            purchase_date="2026-10-14",
            return_deadline="2026-10-30",
            status="preparing",
            version=2,
            checklist=[
                ChecklistItem("c3", "Both shoes in clean condition", True),
                ChecklistItem("c4", "Original shoebox & tags", True),  # 100% complete!
            ],
        ),
        ReturnTaskItem(
            id="ret-3",
            name="Travel Backpack",
            merchant="Demo Outdoors",
            amount_inr=1999.0,
            purchase_date="2026-10-10",
            return_deadline="2026-10-22",
            status="dropped_off",
            version=3,
            dropped_off_at="2026-10-21T14:30:00Z",
            checklist=[
                ChecklistItem("c5", "Emptied all pockets", True),
                ChecklistItem("c6", "Return barcode affixed", True),
            ],
        ),
    ]


def run_self_test() -> int:
    """Execute complete automated self-test of State & Readiness Integrity Guardrail."""
    print("=" * 70)
    print("  AIRLOCK :: GATE 5: STATE & READINESS INTEGRITY GUARDRAIL (ReturnReady)")
    print("=" * 70)

    engine = StateGuardEngine()
    items = create_sample_dataset()
    failures = 0

    # Test 1: Incomplete checklist blocks 'ready' and 'dropped_off'
    headphones = next(i for i in items if i.id == "ret-1")
    print("\n[TEST 1] Incomplete checklist readiness check:")
    print(f"  Item: '{headphones.name}' ({headphones.completed_checks}/{headphones.total_checks} checked)")
    assert not headphones.is_ready, "Headphones should NOT be ready"
    try:
        engine.validate_transition(headphones, "dropped_off")
        print("  FAIL: Expected PreconditionFailedError not raised!")
        failures += 1
    except PreconditionFailedError as e:
        print(f"  PASS: Correctly blocked transition ({e})")

    # Test 2: Complete checklist derives ready and allows proposed dropoff
    shoes = next(i for i in items if i.id == "ret-2")
    print("\n[TEST 2] 100% complete checklist readiness check:")
    print(f"  Item: '{shoes.name}' ({shoes.completed_checks}/{shoes.total_checks} checked)")
    assert shoes.is_ready, "Shoes should be ready"
    assert shoes.derived_status == "ready", "Derived status should be 'ready'"
    try:
        engine.validate_transition(shoes, "dropped_off")
        print("  PASS: Validation succeeded for 100% complete checklist")
    except Exception as e:
        print(f"  FAIL: Unexpected error {e}")
        failures += 1

    # Test 3: Terminal state locking blocks mutation on dropped_off item
    backpack = next(i for i in items if i.id == "ret-3")
    print("\n[TEST 3] Terminal State Lock on 'dropped_off' item:")
    print(f"  Item: '{backpack.name}' (status: {backpack.status}, locked: {backpack.is_locked})")
    assert backpack.is_locked, "Backpack should be locked"
    try:
        action = PendingAction("assign", backpack.id, backpack.name, backpack.version, int(time.time() * 1000))
        engine.validate_action(backpack, action)
        print("  FAIL: Mutation allowed on locked state!")
        failures += 1
    except StateLockedError as e:
        print(f"  PASS: Correctly blocked mutation on locked item ({e})")

    # Test 4: Concurrency control blocks stale expected_version
    print("\n[TEST 4] Optimistic Concurrency version-bound verification:")
    stale_action = PendingAction(
        "dropoff",
        shoes.id,
        shoes.name,
        expected_version=1,  # Shoes is at version 2
        created_at_ms=int(time.time() * 1000),
    )
    try:
        engine.validate_action(shoes, stale_action)
        print("  FAIL: Stale version accepted!")
        failures += 1
    except VersionConflictError as e:
        print(f"  PASS: Correctly rejected stale version ({e})")

    # Test 5: Intent routing disambiguation and out-of-scope handling
    print("\n[TEST 5] Conversational Intent Routing & Guardrails:")
    res_due = engine.route_intent("what is due soon", items)
    assert res_due["intent"] == "list_due"
    print(f"  PASS: 'what is due soon' -> {res_due['intent']} ({len(res_due['items'])} items)")

    res_blocked = engine.route_intent("drop off headphones", items)
    assert res_blocked["status"] == "BLOCKED"
    print(f"  PASS: 'drop off headphones' -> BLOCKED ({res_blocked['error']})")

    res_shoes = engine.route_intent("drop off running shoes", items)
    assert res_shoes["status"] == "PENDING_CONFIRMATION"
    print(f"  PASS: 'drop off running shoes' -> PENDING_CONFIRMATION")

    res_ambiguous = engine.route_intent("drop off", items)
    assert res_ambiguous["status"] == "BLOCKED"
    print(f"  PASS: 'drop off' (no item specified) -> BLOCKED (Ambiguous mutation)")

    print("\n" + "=" * 70)
    if failures == 0:
        print("  ALL 5 STATE & READINESS INTEGRITY TESTS PASSED (0 FAILURES)")
        print("=" * 70)
        return 0
    else:
        print(f"  SELF-TEST FAILED WITH {failures} ERRORS")
        print("=" * 70)
        return 1


def main() -> int:
    parser = argparse.ArgumentParser(description="State & Readiness Integrity Guardrail")
    parser.add_argument("--self-test", action="store_true", help="Run automated self-tests")
    parser.add_argument("--json", action="store_true", help="Output results in JSON format")
    args = parser.parse_args()

    if args.self_test:
        return run_self_test()

    items = create_sample_dataset()
    if args.json:
        print(json.dumps([i.to_dict() for i in items], indent=2))
        return 0

    print(f"StateGuardEngine active. Tracking {len(items)} items.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
