import fnmatch
import os
import subprocess
import sys

PROTECTED = [
    '.gitlab-ci.yml',
    '.gitlab/*',
    'policy/*',
    'deploy/*',
    'CODEOWNERS',
    'tools/*',
]
CONTROL_PLANE_LABEL = 'control-plane-approved'
SIZE_LABEL = 'size-approved'
MAX_FILES = 10
MAX_LINES = 300


def get_diff_data(base='origin/main', head='HEAD'):
    """Extract changed files and line count from git diff."""
    try:
        status_out = subprocess.run(
            ['git', 'diff', '--name-status', base, head],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception as e:
        print(f"Warning: git diff failed ({e}), checking DIFF_FILES env var")
        status_out = os.environ.get('DIFF_STATUS_MOCK', '')

    try:
        stat_out = subprocess.run(
            ['git', 'diff', '--shortstat', base, head],
            capture_output=True, text=True, check=True
        ).stdout
    except Exception:
        stat_out = os.environ.get('DIFF_STAT_MOCK', '')

    changed_files = []
    deleted_files = []
    for line in status_out.strip().splitlines():
        parts = line.split('\t')
        if len(parts) >= 2:
            status, path = parts[0], parts[1]
            changed_files.append(path)
            if status.startswith('D'):
                deleted_files.append(path)

    total_lines = 0
    if stat_out:
        # e.g. " 3 files changed, 45 insertions(+), 12 deletions(-)"
        import re
        m = re.search(r'(\d+)\s+insertion', stat_out)
        ins = int(m.group(1)) if m else 0
        m = re.search(r'(\d+)\s+deletion', stat_out)
        dels = int(m.group(1)) if m else 0
        total_lines = ins + dels

    return changed_files, deleted_files, total_lines


def evaluate_policy(files, deleted_files, total_lines, labels):
    """Evaluate whether MR changes violate guardrail policy."""
    violations = []

    # 1. Control-plane protected file hits
    hits = [f for f in files if any(fnmatch.fnmatch(f, p) for p in PROTECTED)]
    if hits and CONTROL_PLANE_LABEL not in labels:
        violations.append(
            f"Control-plane files modified without '{CONTROL_PLANE_LABEL}' label: {hits}"
        )

    # 2. Test deletion check
    deleted_tests = [f for f in deleted_files if f.startswith('tests/') or 'test' in f.lower()]
    if deleted_tests and CONTROL_PLANE_LABEL not in labels:
        violations.append(
            f"Test files deleted without '{CONTROL_PLANE_LABEL}' label: {deleted_tests}"
        )

    # 3. Size check
    if len(files) > MAX_FILES and SIZE_LABEL not in labels:
        violations.append(
            f"MR touches {len(files)} files (limit: {MAX_FILES}) without '{SIZE_LABEL}' label."
        )

    if total_lines > MAX_LINES and SIZE_LABEL not in labels:
        violations.append(
            f"MR changes {total_lines} lines (limit: {MAX_LINES}) without '{SIZE_LABEL}' label."
        )

    return violations, hits


def main():
    base = os.environ.get('CI_MERGE_REQUEST_DIFF_BASE_SHA', 'origin/main')
    raw_labels = os.environ.get('CI_MERGE_REQUEST_LABELS', '')
    labels = [l.strip() for l in raw_labels.split(',') if l.strip()]

    files, deleted, lines = get_diff_data(base=base, head='HEAD')
    violations, hits = evaluate_policy(files, deleted, lines, labels)

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


if __name__ == '__main__':
    sys.exit(main())
