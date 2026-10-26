"""Comprehensive tests for CI guardrail tools in tools/."""

import json
import os
import tempfile
import pytest

from tools.policy_gate import (
    DEFAULT_POLICY,
    evaluate_policy,
    filter_human_labels,
    is_human_applied,
    load_policy,
)
from tools.sast_gate import (
    REQUIRED_REPORTS,
    load_blocked_severities,
    missing_reports,
    scan_reports,
    main as sast_main,
)
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


def test_policy_gate_blocks_renamed_protected_file():
    # With --no-renames, renaming .gitlab-ci.yml -> ci_backup.yml generates:
    # D: .gitlab-ci.yml, A: ci_backup.yml
    files = ['.gitlab-ci.yml', 'ci_backup.yml']
    deleted = ['.gitlab-ci.yml']
    violations, hits = evaluate_policy(files, deleted, 25, [])
    assert len(violations) >= 1
    assert any("Control-plane files modified" in v for v in violations)
    assert '.gitlab-ci.yml' in hits


def test_policy_gate_blocks_renamed_test_file():
    # With --no-renames, renaming tests/test_gates.py -> old_tests.py emits:
    # D: tests/test_gates.py, A: old_tests.py
    files = ['tests/test_gates.py', 'old_tests.py']
    deleted = ['tests/test_gates.py']
    violations, _ = evaluate_policy(files, deleted, 25, [])
    assert any("Test files deleted without 'control-plane-approved'" in v for v in violations)


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


def test_sast_gate_fails_with_no_reports():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Directory is completely empty - must fail closed
        missing = missing_reports(directory=tmpdir)
        assert "gl-sast-report.json" in missing
        with pytest.raises(SystemExit) as exc:
            sast_main(directory=tmpdir)
        assert exc.value.code == 1


def test_sast_gate_fails_with_only_secret_detection_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Only secret-detection report present, required gl-sast-report.json missing
        secret_report = os.path.join(tmpdir, "gl-secret-detection-report.json")
        with open(secret_report, "w") as f:
            json.dump({"vulnerabilities": []}, f)

        missing = missing_reports(directory=tmpdir)
        assert "gl-sast-report.json" in missing
        with pytest.raises(SystemExit) as exc:
            sast_main(directory=tmpdir)
        assert exc.value.code == 1


def test_sast_gate_passes_main_on_clean_report():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "gl-sast-report.json")
        with open(report_path, "w") as f:
            json.dump({"vulnerabilities": []}, f)

        ret = sast_main(directory=tmpdir)
        assert ret == 0


def test_sast_gate_ignores_medium_fails_on_high():
    with tempfile.TemporaryDirectory() as tmpdir:
        report_path = os.path.join(tmpdir, "gl-sast-report.json")
        # Report with Medium severity only
        with open(report_path, "w") as f:
            json.dump({
                "vulnerabilities": [
                    {"name": "Weak Hash", "severity": "Medium", "location": {"file": "crypto.py"}}
                ]
            }, f)

        # Ignores Medium and passes cleanly
        ret = sast_main(directory=tmpdir)
        assert ret == 0

        # Now add High severity vulnerability
        with open(report_path, "w") as f:
            json.dump({
                "vulnerabilities": [
                    {"name": "Weak Hash", "severity": "Medium", "location": {"file": "crypto.py"}},
                    {"name": "Command Injection", "severity": "High", "location": {"file": "exec.py"}}
                ]
            }, f)

        # Fails on High
        with pytest.raises(SystemExit) as exc:
            sast_main(directory=tmpdir)
        assert exc.value.code == 1


def test_is_human_applied_agent_applied():
    agent_list = ["gitlab-duo", "agent-bot"]
    events = [
        {
            "id": 1,
            "action": "add",
            "created_at": "2026-10-26T10:00:00Z",
            "label": {"name": "control-plane-approved"},
            "user": {"username": "gitlab-duo"}
        }
    ]
    # Agent applied -> not human
    assert not is_human_applied("control-plane-approved", events, agent_list)


def test_is_human_applied_removed_label():
    agent_list = ["gitlab-duo"]
    events = [
        {
            "id": 1,
            "action": "add",
            "created_at": "2026-10-26T10:00:00Z",
            "label": {"name": "control-plane-approved"},
            "user": {"username": "alice_human"}
        },
        {
            "id": 2,
            "action": "remove",
            "created_at": "2026-10-26T10:05:00Z",
            "label": {"name": "control-plane-approved"},
            "user": {"username": "alice_human"}
        }
    ]
    # Latest action was remove -> label is not active/valid
    assert not is_human_applied("control-plane-approved", events, agent_list)


def test_is_human_applied_out_of_order_events():
    agent_list = ["agent-bot"]
    # Even if events are provided in reverse chronological order:
    events = [
        {
            "id": 2,
            "action": "add",
            "created_at": "2026-10-26T11:00:00Z",
            "label": {"name": "control-plane-approved"},
            "user": {"username": "lead_maintainer"}
        },
        {
            "id": 1,
            "action": "add",
            "created_at": "2026-10-26T10:00:00Z",
            "label": {"name": "control-plane-approved"},
            "user": {"username": "agent-bot"}
        }
    ]
    # Chronologically, the human's add (11:00) overrides the agent's earlier add (10:00)
    assert is_human_applied("control-plane-approved", events, agent_list)


def test_filter_human_labels_fail_closed_without_token(monkeypatch):
    monkeypatch.delenv("AIRLOCK_API_TOKEN", raising=False)
    agent_list = ["agent-bot"]
    labels = ["control-plane-approved", "agent-task", "size-approved"]
    filtered = filter_human_labels(labels, agent_list, events=None)
    # When token is missing and events is None, fail closed: strip approval labels
    assert "control-plane-approved" not in filtered
    assert "size-approved" not in filtered
    assert "agent-task" in filtered


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
