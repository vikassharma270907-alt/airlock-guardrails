import glob
import json
import os
import sys


def build_scorecard(ledger_dir='ledger', output_file='scorecard.md'):
    pattern = os.path.join(ledger_dir, '*.json')
    files = sorted(glob.glob(pattern))

    rows = []
    for p in files:
        try:
            with open(p, 'r', encoding='utf-8') as f:
                rows.append(json.load(f))
        except Exception as e:
            print(f"Error reading ledger entry {p}: {e}")

    lines = [
        "# Pipeline Governance Scorecard",
        "",
        "| CI Check / Stage | Result | Policy Status |",
        "|---|---|---|",
    ]

    for r in rows:
        job = r.get('job', 'unknown')
        status = r.get('status', 'unknown')
        icon = "PASSED" if status in ("success", "passed") else "FAILED / VIOLATION"
        lines.append(f"| {job} | {status} | {icon} |")

    if not rows:
        lines.append("| No jobs recorded | - | - |")

    text = "\n".join(lines) + "\n"
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    print(text)
    return text


def main():
    build_scorecard()
    return 0


if __name__ == '__main__':
    sys.exit(main())
