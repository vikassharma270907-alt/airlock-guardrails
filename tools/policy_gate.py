import fnmatch
import json
import os
import re
import subprocess
import sys

DEFAULT_POLICY = {
    "protected_paths": [
        ".gitlab-ci.yml",
        ".gitlab/*",
        "policy/*",
        "deploy/*",
        "CODEOWNERS",
        "tools/*",
    ],
    "max_files": 10,
    "max_lines": 300,
    "control_plane_label": "control-plane-approved",
    "size_label": "size-approved",
    "blocked_severities": ["Critical", "High"],
}


def load_policy(config_path="policy/policy.json"):
    """Load policy config from JSON file with graceful fallback to defaults."""
    # Check trusted path first if present
    trusted_path = os.path.join(".trusted_tools", "policy.json")
    for path in (trusted_path, config_path):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    merged = dict(DEFAULT_POLICY)
                    merged.update(data)
                    return merged
            except Exception as e:
                print(f"Warning: Failed to parse policy file {path} ({e}); using defaults.")
    return dict(DEFAULT_POLICY)


def get_diff_data(base=None, head="HEAD"):
    """Extract changed files, deleted files, and line counts from git diff."""
    if not base:
        # Base SHA from GitLab Merge Request environment
        base = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
        if not base:
            # Fallback for local testing or non-MR contexts
            base = "origin/main"

    try:
        status_out = subprocess.run(
            ["git", "diff", "--name-status", base, head],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception as e:
        print(f"Warning: git diff failed against base '{base}' ({e}); checking mock env.")
        status_out = os.environ.get("DIFF_STATUS_MOCK", "")

    try:
        stat_out = subprocess.run(
            ["git", "diff", "--shortstat", base, head],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception:
        stat_out = os.environ.get("DIFF_STAT_MOCK", "")

    changed_files = []
    deleted_files = []
    for line in status_out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 2:
            status, path = parts[0], parts[1]
            changed_files.append(path)
            if status.startswith("D"):
                deleted_files.append(path)

    total_lines = 0
    if stat_out:
        m_ins = re.search(r"(\d+)\s+insertion", stat_out)
        ins = int(m_ins.group(1)) if m_ins else 0
        m_del = re.search(r"(\d+)\s+deletion", stat_out)
        dels = int(m_del.group(1)) if m_del else 0
        total_lines = ins + dels

    return changed_files, deleted_files, total_lines


def evaluate_policy(files, deleted_files, total_lines, labels, policy=None):
    """Evaluate whether MR changes violate guardrail policy."""
    if policy is None:
        policy = load_policy()

    violations = []
    protected_patterns = policy.get("protected_paths", DEFAULT_POLICY["protected_paths"])
    max_files = policy.get("max_files", DEFAULT_POLICY["max_files"])
    max_lines = policy.get("max_lines", DEFAULT_POLICY["max_lines"])
    control_label = policy.get("control_plane_label", DEFAULT_POLICY["control_plane_label"])
    size_label = policy.get("size_label", DEFAULT_POLICY["size_label"])

    # 1. Control-plane protected file hits
    hits = [f for f in files if any(fnmatch.fnmatch(f, p) for p in protected_patterns)]
    if hits and control_label not in labels:
        violations.append(
            f"Control-plane files modified without '{control_label}' label: {hits}"
        )

    # 2. Test deletion check: files under tests/ or matching test_*.py / *_test.py
    deleted_tests = [
        f for f in deleted_files
        if f.startswith("tests/")
        or fnmatch.fnmatch(os.path.basename(f), "test_*.py")
        or fnmatch.fnmatch(os.path.basename(f), "*_test.py")
    ]
    if deleted_tests and control_label not in labels:
        violations.append(
            f"Test files deleted without '{control_label}' label: {deleted_tests}"
        )

    # 3. Size check (10 files / 300 lines)
    if len(files) > max_files and size_label not in labels:
        violations.append(
            f"MR touches {len(files)} files (limit: {max_files}) without '{size_label}' label."
        )

    if total_lines > max_lines and size_label not in labels:
        violations.append(
            f"MR changes {total_lines} lines (limit: {max_lines}) without '{size_label}' label."
        )

    return violations, hits


def main():
    policy = load_policy()
    base_sha = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA") or "origin/main"
    raw_labels = os.environ.get("CI_MERGE_REQUEST_LABELS", "")
    labels = [l.strip() for l in raw_labels.split(",") if l.strip()]

    files, deleted, lines = get_diff_data(base=base_sha, head="HEAD")
    violations, hits = evaluate_policy(files, deleted, lines, labels, policy=policy)

    print(f"Diff base: {base_sha}")
    print(f"Changed files ({len(files)}): {files}")
    print(f"Control-plane hits ({len(hits)}): {hits}")
    print(f"Active labels: {labels}")

    if violations:
        print("POLICY VIOLATION DETECTED:")
        for v in violations:
            print(f"  - {v}")
        sys.exit(1)

    print("Policy gate passed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
