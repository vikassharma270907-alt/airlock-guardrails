"""Comprehensive tests for CI guardrail tools in tools/."""

import json
import os
import tempfile
import pytest

from tools.policy_gate import evaluate_policy, load_policy, DEFAULT_POLICY
from tools.sast_gate import scan_reports, load_blocked_severities
from tools.fix_budget import evaluate_fix_budget, load_fix_budget_config
from tools.scorecard import build_scorecard, classify_commits


def test_policy_gate_loads_defaults_on_missing_file():
    policy = load_policy("nonexistent/policy.json")
    assert policy["max_files"] == 10
    assert policy["max_lines"] == 300
    assert ".gitlab-ci.yml" in policy["protected_paths"]


def test_policy_gate_blocks_control_plane_without_label():
    files = ['.gitlab-ci.yml', 'airlock_demo/textkit.py']
    deleted = []
    lines = 15
    labels = []

    violations, hits = evaluate_policy(files, deleted, lines, labels)
    assert len(violations) == 1
    assert hits == ['.gitlab-ci.yml']
    assert "control-plane-approved" in violations[0]


def test_policy_gate_allows_control_plane_with_label():
    files = ['.gitlab-ci.yml', 'tools/policy_gate.py']
    deleted = []
    lines = 10
    labels = ['control-plane-approved']

    violations, hits = evaluate_policy(files, deleted, lines, labels)
    assert len(violations) == 0
    assert set(hits) == {'.gitlab-ci.yml', 'tools/policy_gate.py'}


def test_policy_gate_blocks_deleted_tests_under_dir_and_pattern():
    # File under tests/
    violations1, _ = evaluate_policy(['app.py'], ['tests/test_sample.py'], 20, [])
    assert any("Test files deleted" in v for v in violations1)

    # File matching test_*.py in subfolder
    violations2, _ = evaluate_policy(['app.py'], ['custom/test_runner.py'], 20, [])
    assert any("Test files deleted" in v for v in violations2)

    # Allowed with control-plane-approved
    violations_approved, _ = evaluate_policy(['app.py'], ['tests/test_sample.py'], 20, ['control-plane-approved'])
    assert len(violations_approved) == 0


def test_policy_gate_enforces_size_limits():
    files = [f"file_{i}.py" for i in range(12)]  # 12 files > 10
    violations, _ = evaluate_policy(files, [], 50, [])
    assert any("limit: 10" in v for v in violations)

    # Line limit violation (350 lines > 300)
    violations_lines, _ = evaluate_policy(['app.py'], [], 350, [])
    assert any("limit: 300" in v for v in violations_lines)

    # With size-approved label
    violations_approved, _ = evaluate_policy(files, [], 350, ['size-approved'])
    assert len(violations_approved) == 0


def test_sast_gate_blocks_configured_severities():
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

        bad, files = scan_reports(os.path.join(tmpdir, "gl-*report.json"), blocked_severities={"Critical", "High"})
        assert len(files) == 1
        assert len(bad) == 2


def test_sast_gate_passes_clean_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "gl-sast-report.json")
        with open(report_path, "w") as f:
            json.dump({"vulnerabilities": []}, f)

        bad, files = scan_reports(os.path.join(tmpdir, "gl-*report.json"))
        assert len(files) == 1
        assert len(bad) == 0


def test_fix_budget_allows_under_limit():
    commits = [
        {"author_name": "Developer", "author_email": "dev@example.com", "subject": "feat: initial feature"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: repair unit test"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: second repair"},
    ]
    exceeded, count, limit, _ = evaluate_fix_budget(commits)
    assert not exceeded
    assert count == 2
    assert limit == 3


def test_fix_budget_fails_when_limit_exceeded():
    commits = [
        {"author_name": "Developer", "author_email": "dev@example.com", "subject": "feat: feature"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: repair 1"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: repair 2"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: repair 3"},
        {"author_name": "GitLab Duo", "author_email": "bot@gitlab.com", "subject": "agent-fix: repair 4"},
    ]
    exceeded, count, limit, agent_commits = evaluate_fix_budget(commits)
    assert exceeded
    assert count == 4
    assert len(agent_commits) == 4


def test_scorecard_with_commit_provenance():
    with tempfile.TemporaryDirectory() as tmpdir:
        ledger_dir = os.path.join(tmpdir, "ledger")
        os.makedirs(ledger_dir)

        with open(os.path.join(ledger_dir, "unit-tests.json"), "w") as f:
            json.dump({"job": "unit-tests", "status": "success"}, f)
        with open(os.path.join(ledger_dir, "policy-gate.json"), "w") as f:
            json.dump({"job": "policy-gate", "status": "success"}, f)

        mock_commits = [
            {"hash": "abc1234", "author": "Alice", "email": "alice@corp.com", "subject": "feat: new utility"},
            {"hash": "def5678", "author": "GitLab Duo", "email": "duo@gitlab.com", "subject": "agent-fix: fix typo"},
        ]

        out_file = os.path.join(tmpdir, "scorecard.md")
        build_scorecard(ledger_dir=ledger_dir, output_file=out_file, commits=mock_commits)

        assert os.path.exists(out_file)
        content = open(out_file).read()
        assert "| unit-tests | success | PASSED |" in content
        assert "Commit Provenance & Authorship Audit" in content
        assert "**Human-Authored Commits:** 1" in content
        assert "**Agent-Authored Commits:** 1" in content
        assert "| `abc1234` | Alice | feat: new utility | **Human** |" in content
        assert "| `def5678` | GitLab Duo | agent-fix: fix typo | **Agent** |" in content
