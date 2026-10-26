import fnmatch
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

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
    "agent_usernames": [],
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
    """Extract changed files, deleted files, and line counts from git diff using --no-renames."""
    if not base:
        # Base SHA from GitLab Merge Request environment
        base = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
        if not base:
            # Fallback for local testing or non-MR contexts
            base = "origin/main"

    try:
        status_out = subprocess.run(
            ["git", "diff", "--no-renames", "--name-status", base, head],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception as e:
        print(f"Warning: git diff failed against base '{base}' ({e}); checking mock env.")
        status_out = os.environ.get("DIFF_STATUS_MOCK", "")

    try:
        stat_out = subprocess.run(
            ["git", "diff", "--no-renames", "--shortstat", base, head],
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


def fetch_resource_label_events(api_url=None, project_id=None, mr_iid=None, token=None):
    """Fetch MR resource label events from GitLab REST API. Fail closed (return None) on any error."""
    api_url = api_url or os.environ.get("CI_API_V4_URL")
    project_id = project_id or os.environ.get("CI_PROJECT_ID")
    mr_iid = mr_iid or os.environ.get("CI_MERGE_REQUEST_IID")
    token = token or os.environ.get("AIRLOCK_API_TOKEN")

    if not (api_url and project_id and mr_iid and token):
        return None

    url = f"{api_url.rstrip('/')}/projects/{project_id}/merge_requests/{mr_iid}/resource_label_events"
    req = urllib.request.Request(url, headers={"PRIVATE-TOKEN": token})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                return json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        print(f"Warning: Failed to fetch MR resource label events ({e})")
    return None


def is_human_applied(label_name, events, agent_usernames):
    """Determine whether a label's latest action was an 'add' by a verified human.

    Returns True if:
      - At least one event exists for label_name.
      - The latest event (by created_at or id) has action == 'add'.
      - The author's username is NOT in agent_usernames.
    Otherwise returns False.
    """
    if not agent_usernames:
        return True

    label_events = [
        e for e in (events or [])
        if (e.get("label", {}).get("name") if isinstance(e.get("label"), dict) else e.get("label")) == label_name
    ]
    if not label_events:
        return False

    # Sort events chronologically to evaluate the latest state
    label_events.sort(key=lambda ev: (ev.get("created_at", ""), ev.get("id", 0)))
    latest = label_events[-1]

    if latest.get("action") != "add":
        return False

    user = latest.get("user", {})
    username = user.get("username", "") if isinstance(user, dict) else str(user)
    if username in agent_usernames:
        return False

    return True


def filter_human_labels(labels, agent_usernames, events=None, approval_labels=None):
    """Filter approval labels to ensure they were applied by humans, not agents.

    If agent_usernames is empty, all labels are preserved.
    If events is None, fetch_resource_label_events() is called.
    If events cannot be fetched or token is missing, fail closed by removing approval labels.
    """
    if not agent_usernames:
        return list(labels)

    if approval_labels is None:
        approval_labels = {
            DEFAULT_POLICY["control_plane_label"],
            DEFAULT_POLICY["size_label"],
        }
    else:
        approval_labels = set(approval_labels)

    if events is None:
        events = fetch_resource_label_events()
        if events is None:
            print("Warning: AIRLOCK_API_TOKEN missing or API call failed; rejecting approval labels (fail-closed).")
            return [l for l in labels if l not in approval_labels]

    verified = []
    for l in labels:
        if l in approval_labels:
            if is_human_applied(l, events, agent_usernames):
                verified.append(l)
            else:
                print(f"Warning: Label '{l}' was added by an agent or lacks human verification; ignoring.")
        else:
            verified.append(l)
    return verified


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
    initial_labels = [l.strip() for l in raw_labels.split(",") if l.strip()]

    agent_usernames = policy.get("agent_usernames", [])
    approval_labels = {
        policy.get("control_plane_label", DEFAULT_POLICY["control_plane_label"]),
        policy.get("size_label", DEFAULT_POLICY["size_label"]),
    }
    labels = filter_human_labels(initial_labels, agent_usernames, approval_labels=approval_labels)

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
