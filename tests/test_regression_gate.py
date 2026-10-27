import json
import hashlib
import pytest
from tools.regression_gate import (
    load_incidents,
    match_incidents,
    build_context_packet,
    validate_assessment,
    generate_test,
    classify_junit,
    REVIEWED_TEMPLATES,
)

SAMPLE_SHA = "a" * 40
SAMPLE_MR = 42
SAMPLE_CONTEXT = {
    "project_id": 88101823,
    "mr_iid": SAMPLE_MR,
    "head_sha": SAMPLE_SHA,
    "context_sha256": "placeholder",
}
# Compute valid context_sha256
packet_for_hash = {k: v for k, v in SAMPLE_CONTEXT.items() if k != "context_sha256"}
SAMPLE_CONTEXT["context_sha256"] = hashlib.sha256(
    json.dumps(packet_for_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
).hexdigest()


def test_load_incidents_returns_known_catalog():
    incidents = load_incidents()
    assert len(incidents) >= 2
    ids = [i["id"] for i in incidents]
    assert "INCIDENT-AUTH-001" in ids
    assert "INCIDENT-SEC-002" in ids


def test_match_incidents_by_path_and_symbol():
    changed_files = ["airlock_demo/legacy_runner.py", "airlock_demo/textkit.py"]
    added_code = "def execute_expression(user_input):\n    return eval(user_input)"
    matches = match_incidents(changed_files, added_code)
    assert len(matches) > 0
    matched_ids = [m["incident"]["id"] for m in matches]
    assert "INCIDENT-SEC-002" in matched_ids
    assert any("symbol:execute_expression" in r for m in matches for r in m["reasons"])


def test_build_context_packet_checksum_and_routes():
    diffs = [{
        "old_path": "airlock_demo/app.py",
        "new_path": "airlock_demo/app.py",
        "diff": '+@app.get("/notes/{note_id}/export")\ndef export_note(note_id: int):\n    return find_note(note_id)'
    }]
    packet = build_context_packet(
        project_id=88101823,
        mr_iid=SAMPLE_MR,
        head_sha=SAMPLE_SHA,
        mr_url="https://gitlab.com/group/proj/-/merge_requests/42",
        title="Feat: add export",
        diffs=diffs,
        changed_paths=["airlock_demo/app.py"],
        matches=[],
    )
    assert packet["head_sha"] == SAMPLE_SHA
    assert len(packet["context_sha256"]) == 64
    assert len(packet["routes"]) == 1
    assert packet["routes"][0]["route"] == "/notes/{note_id}/export"
    assert "export_note" in packet["symbols"]


def test_validate_assessment_accepts_valid_suspected():
    assessment = {
        "mr_iid": SAMPLE_MR,
        "head_sha": SAMPLE_SHA,
        "context_sha256": SAMPLE_CONTEXT["context_sha256"],
        "historical_failure_ids": ["INCIDENT-AUTH-001"],
        "confidence": 0.85,
        "state": "suspected",
        "test_spec": {
            "pattern": "notes_export_ownership",
            "target_path": "airlock_demo/app.py",
        },
    }
    assert validate_assessment(assessment, SAMPLE_CONTEXT) is True


def test_validate_assessment_rejects_sha_mismatch():
    assessment = {
        "mr_iid": SAMPLE_MR,
        "head_sha": "b" * 40,
        "context_sha256": SAMPLE_CONTEXT["context_sha256"],
        "historical_failure_ids": ["INCIDENT-AUTH-001"],
        "confidence": 0.85,
        "state": "suspected",
        "test_spec": {"pattern": "notes_export_ownership"},
    }
    with pytest.raises(ValueError, match="head_sha differs"):
        validate_assessment(assessment, SAMPLE_CONTEXT)


def test_validate_assessment_rejects_unknown_incident():
    assessment = {
        "mr_iid": SAMPLE_MR,
        "head_sha": SAMPLE_SHA,
        "context_sha256": SAMPLE_CONTEXT["context_sha256"],
        "historical_failure_ids": ["UNKNOWN-CVE-9999"],
        "confidence": 0.85,
        "state": "suspected",
        "test_spec": {"pattern": "notes_export_ownership"},
    }
    with pytest.raises(ValueError, match="unknown incident ID"):
        validate_assessment(assessment, SAMPLE_CONTEXT)


def test_validate_assessment_blocks_code_injection_in_spec():
    assessment = {
        "mr_iid": SAMPLE_MR,
        "head_sha": SAMPLE_SHA,
        "context_sha256": SAMPLE_CONTEXT["context_sha256"],
        "historical_failure_ids": ["INCIDENT-AUTH-001"],
        "confidence": 0.85,
        "state": "suspected",
        "test_spec": {
            "pattern": "notes_export_ownership",
            "code": "import os; os.system('rm -rf /')",
        },
    }
    with pytest.raises(ValueError, match="code execution injection is forbidden"):
        validate_assessment(assessment, SAMPLE_CONTEXT)


def test_generate_test_returns_reviewed_template_without_arbitrary_code():
    assessment = {
        "state": "suspected",
        "test_spec": {"pattern": "notes_export_ownership"},
    }
    source = generate_test(assessment, SAMPLE_CONTEXT)
    assert "test_tmci_cross_user_export_denied" in source
    assert "TMCI_AUTH_ASSERT" in source


def test_classify_junit_reproduced_for_authorization():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="1" name="pytest" skips="0" tests="1" time="0.1">
    <testcase classname="test_tmci_regression" name="test_tmci_cross_user_export_denied" time="0.05">
        <failure message="AssertionError: TMCI_AUTH_ASSERT status=200 body_exposed=True">Details</failure>
    </testcase>
</testsuite>"""
    verdict = classify_junit(xml, exit_code=1)
    assert verdict["state"] == "reproduced"
    assert verdict["gate_exit_code"] == 1
    assert "TMCI_AUTH_ASSERT status=200 body_exposed=True" in verdict["assertion_evidence"]


def test_classify_junit_cleared_for_passed_tests():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="0" failures="0" name="pytest" skips="0" tests="1" time="0.1">
    <testcase classname="test_tmci_regression" name="test_tmci_cross_user_export_denied" time="0.05" />
</testsuite>"""
    verdict = classify_junit(xml, exit_code=0)
    assert verdict["state"] == "cleared"
    assert verdict["gate_exit_code"] == 0


def test_classify_junit_inconclusive_on_setup_error():
    xml = """<?xml version="1.0" encoding="utf-8"?>
<testsuite errors="1" failures="0" name="pytest" skips="0" tests="1" time="0.1">
    <testcase classname="test_tmci_regression" name="test_tmci_cross_user_export_denied" time="0.05">
        <error message="ImportError: No module named demo_service">Traceback</error>
    </testcase>
</testsuite>"""
    verdict = classify_junit(xml, exit_code=1)
    assert verdict["state"] == "inconclusive"
    assert verdict["gate_exit_code"] == 0
