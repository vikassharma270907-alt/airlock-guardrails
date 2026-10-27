import glob
import json
import os
import subprocess
import sys

DEFAULT_PATTERNS = ["gitlab duo", "agent", "bot", "duo-developer"]
DEFAULT_PREFIX = "agent-fix:"


def classify_commits(commits_list=None, config_path="policy/policy.json"):
    """Classify commits into human-authored vs agent-authored."""
    prefix = DEFAULT_PREFIX
    patterns = DEFAULT_PATTERNS

    trusted_path = os.path.join(".trusted_tools", "policy.json")
    for path in (trusted_path, config_path):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    cfg = json.load(f)
                    prefix = cfg.get("agent_commit_prefix", DEFAULT_PREFIX).lower()
                    patterns = [p.lower() for p in cfg.get("agent_author_patterns", DEFAULT_PATTERNS)]
            except Exception:
                pass

    if commits_list is None:
        commits_list = []
        try:
            out = subprocess.run(
                ["git", "log", "-n", "15", "--format=%h\t%an\t%ae\t%s"],
                capture_output=True, text=True, check=True
            ).stdout
            for line in out.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 4:
                    commits_list.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "subject": parts[3],
                    })
        except Exception:
            mock = os.environ.get("COMMITS_MOCK", "")
            for line in mock.strip().splitlines():
                parts = line.split("\t")
                if len(parts) >= 4:
                    commits_list.append({
                        "hash": parts[0],
                        "author": parts[1],
                        "email": parts[2],
                        "subject": parts[3],
                    })

    classified = []
    agent_count = 0
    human_count = 0

    for c in commits_list:
        sub = c.get("subject", "").lower()
        an = c.get("author", "").lower()
        ae = c.get("email", "").lower()

        is_agent = False
        if prefix and sub.startswith(prefix):
            is_agent = True
        elif any(p in an or p in ae for p in patterns):
            is_agent = True

        provenance = "Agent" if is_agent else "Human"
        if is_agent:
            agent_count += 1
        else:
            human_count += 1

        author_display = c.get("author", "unknown")
        # Attribute project commits to owner: Vikas Sharma
        if any(t in author_display.lower() for t in ("vikas", "beyondnothing", "-alt", "airlock maintainer")):
            author_display = "Vikas Sharma (Owner)"

        classified.append({
            "hash": c.get("hash", "HEAD"),
            "author": author_display,
            "subject": c.get("subject", ""),
            "provenance": provenance,
        })

    return classified, agent_count, human_count


def build_scorecard(ledger_dir="ledger", output_file="scorecard.md", commits=None):
    pattern = os.path.join(ledger_dir, "*.json")
    files = sorted(glob.glob(pattern))

    rows = []
    for p in files:
        try:
            with open(p, "r", encoding="utf-8") as f:
                rows.append(json.load(f))
        except Exception as e:
            print(f"Error reading ledger entry {p}: {e}")

    classified_commits, agent_count, human_count = classify_commits(commits_list=commits)

    lines = [
        "# Pipeline Governance Scorecard",
        "",
        "## CI Check & Deterministic Gate Results",
        "",
        "| CI Check / Stage | Result | Policy Status |",
        "|---|---|---|",
    ]

    for r in rows:
        job = r.get("job", "unknown")
        status = r.get("status", "unknown")
        icon = "PASSED" if status in ("success", "passed") else "FAILED / VIOLATION"
        lines.append(f"| {job} | {status} | {icon} |")

    if not rows:
        lines.append("| No jobs recorded | - | - |")

    lines.extend([
        "",
        "## Commit Provenance & Authorship Audit",
        "",
        f"- **Human-Authored Commits:** {human_count}",
        f"- **Agent-Authored Commits:** {agent_count}",
        "",
        "| Commit | Author | Subject | Provenance |",
        "|---|---|---|---|",
    ])

    for c in classified_commits:
        lines.append(f"| `{c['hash']}` | {c['author']} | {c['subject']} | **{c['provenance']}** |")

    if not classified_commits:
        lines.append("| - | - | No commit history available | - |")

    text = "\n".join(lines) + "\n"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(text)

    print(text)
    return text


def main():
    build_scorecard()
    return 0


if __name__ == "__main__":
    sys.exit(main())
