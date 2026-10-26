"""Tests for CI guardrail tools in tools/."""

import json
import os
import tempfile
import pytest

from tools.policy_gate import evaluate_policy, PROTECTED, CONTROL_PLANE_LABEL, SIZE_LABEL
from tools.sast_gate import scan_reports
from tools.scorecard import build_scorecard


def test_policy_gate_blocks_control_plane_without_label():
    files = ['.gitlab-ci.yml', 'airlock_demo/textkit.py']
    deleted = []
    lines = 15
    labels = []

    violations, hits = evaluate_policy(files, deleted, lines, labels)
    assert len(violations) == 1
    assert hits == ['.gitlab-ci.yml']
    assert CONTROL_PLANE_LABEL in violations[0]


def test_policy_gate_allows_control_plane_with_label():
    files = ['.gitlab-ci.yml']
    deleted = []
    lines = 10
    labels = [CONTROL_PLANE_LABEL]

    violations, hits = evaluate_policy(files, deleted, lines, labels)
    assert len(violations) == 0
    assert hits == ['.gitlab-ci.yml']


def test_policy_gate_blocks_deleted_tests():
    files = ['airlock_demo/textkit.py']
    deleted = ['tests/test_textkit.py']
    lines = 50
    labels = []

    violations, _ = evaluate_policy(files, deleted, lines, labels)
    assert any("Test files deleted" in v for v in violations)


def test_policy_gate_enforces_size_limits():
    # 12 files > 10 file limit
    files = [f"file_{i}.py" for i in range(12)]
    deleted = []
    lines = 50
    labels = []

    violations, _ = evaluate_policy(files, deleted, lines, labels)
    assert any("limit: 10" in v for v in violations)

    # With size-approved label
    violations_approved, _ = evaluate_policy(files, deleted, lines, [SIZE_LABEL])
    assert len(violations_approved) == 0


def test_sast_gate_blocks_high_and_critical():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "gl-sast-report.json")
        sample_report = {
            "vulnerabilities": [
                {"name": "Hardcoded Secret", "severity": "Critical", "location": {"file": "auth.py"}},
                {"name": "SQL Injection", "severity": "High", "location": {"file": "db.py"}},
                {"name": "Info disclosure", "severity": "Low", "location": {"file": "info.py"}}
            ]
        }
        with open(report_path, "w") as f:
            json.dump(sample_report, f)

        bad, files = scan_reports(os.path.join(tmpdir, "gl-*report.json"))
        assert len(files) == 1
        assert len(bad) == 2  # Only Critical and High


def test_sast_gate_passes_clean_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "gl-sast-report.json")
        sample_report = {"vulnerabilities": []}
        with open(report_path, "w") as f:
            json.dump(sample_report, f)

        bad, files = scan_reports(os.path.join(tmpdir, "gl-*report.json"))
        assert len(files) == 1
        assert len(bad) == 0


def test_scorecard_generation():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = os.path.join(tmpdir, "ledger")
        os.makedirs(ledger_dir)

        with open(os.path.join(ledger_dir, "unit-tests.json"), "w") as f:
            json.dump({"job": "unit-tests", "status": "success"}, f)
        with open(os.path.join(ledger_dir, "policy-gate.json"), "w") as f:
            json.dump({"job": "policy-gate", "status": "success"}, f)

        out_file = os.path.join(tmpdir, "scorecard.md")
        build_scorecard(ledger_dir=ledger_dir, output_file=out_file)

        assert os.path.exists(out_file)
        content = open(out_file).read()
        assert "| unit-tests | success | PASSED |" in content
        assert "| policy-gate | success | PASSED |" in content
