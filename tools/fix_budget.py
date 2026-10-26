import json
import os
import subprocess
import sys

DEFAULT_CONFIG = {
    "max_agent_fix_attempts": 3,
    "agent_commit_prefix": "agent-fix:",
    "agent_author_patterns": ["GitLab Duo", "agent", "bot", "duo-developer"],
}


def load_fix_budget_config(config_path="policy/policy.json"):
    trusted_path = os.path.join(".trusted_tools", "policy.json")
    for path in (trusted_path, config_path):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return {
                        "max_agent_fix_attempts": data.get("max_agent_fix_attempts", 3),
                        "agent_commit_prefix": data.get("agent_commit_prefix", "agent-fix:"),
                        "agent_author_patterns": data.get(
                            "agent_author_patterns",
                            DEFAULT_CONFIG["agent_author_patterns"]
                        ),
                    }
            except Exception as e:
                print(f"Warning: Failed to load config from {path} ({e}); using defaults.")
    return dict(DEFAULT_CONFIG)


def get_mr_commits(base=None, head="HEAD"):
    """Get list of (author_name, author_email, subject) for commits in the MR."""
    if not base:
        base = os.environ.get("CI_MERGE_REQUEST_DIFF_BASE_SHA")
        if not base:
            target = os.environ.get("CI_MERGE_REQUEST_TARGET_BRANCH_NAME", "main")
            base = f"origin/{target}"

    try:
        out = subprocess.run(
            ["git", "log", "--format=%an\t%ae\t%s", f"{base}..{head}"],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception as e:
        print(f"Warning: git log failed ({e}); checking mock env.")
        out = os.environ.get("COMMITS_MOCK", "")

    commits = []
    for line in out.strip().splitlines():
        parts = line.split("\t")
        if len(parts) >= 3:
            commits.append({
                "author_name": parts[0].strip(),
                "author_email": parts[1].strip(),
                "subject": parts[2].strip(),
            })
    return commits


def evaluate_fix_budget(commits, config=None):
    """Count agent fix commits and determine whether budget is exceeded."""
    if config is None:
        config = load_fix_budget_config()

    max_attempts = config.get("max_agent_fix_attempts", 3)
    prefix = config.get("agent_commit_prefix", "agent-fix:").lower()
    patterns = [p.lower() for p in config.get("agent_author_patterns", [])]

    agent_commits = []
    for c in commits:
        sub = c.get("subject", "").lower()
        an = c.get("author_name", "").lower()
        ae = c.get("author_email", "").lower()

        # Match prefix or author patterns
        is_agent = False
        if prefix and sub.startswith(prefix):
            is_agent = True
        elif any(p in an or p in ae for p in patterns):
            is_agent = True

        if is_agent:
            agent_commits.append(c)

    exceeded = len(agent_commits) > max_attempts
    return exceeded, len(agent_commits), max_attempts, agent_commits


def main():
    config = load_fix_budget_config()
    commits = get_mr_commits()
    exceeded, count, limit, agent_commits = evaluate_fix_budget(commits, config=config)

    print(f"Total MR commits: {len(commits)}")
    print(f"Agent-fix commits detected: {count} (limit: {limit})")
    for ac in agent_commits:
        print(f"  - [{ac['author_name']}] {ac['subject']}")

    if exceeded:
        print(f"FIX BUDGET EXCEEDED: Detected {count} agent fix commits, exceeding cap of {limit}.")
        print("ESCALATE TO HUMAN: Autonomous fix attempts capped to prevent runaway loops. A human maintainer must review and resolve.")
        sys.exit(1)

    print("Fix budget gate passed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
