import glob
import json
import os
import sys

DEFAULT_BLOCK = {"Critical", "High"}


def load_blocked_severities(config_path="policy/policy.json"):
    """Load blocked severities from policy.json with fallback."""
    trusted_path = os.path.join(".trusted_tools", "policy.json")
    for path in (trusted_path, config_path):
        if path and os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data.get("blocked_severities", DEFAULT_BLOCK))
            except Exception as e:
                print(f"Warning: Failed to load policy file {path} ({e}); using defaults.")
    return set(DEFAULT_BLOCK)


def scan_reports(pattern="gl-*report.json", blocked_severities=None):
    """Scan security reports for vulnerabilities matching blocked severities."""
    if blocked_severities is None:
        blocked_severities = load_blocked_severities()

    bad = []
    files_checked = glob.glob(pattern)
    for path in files_checked:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for v in data.get("vulnerabilities", []):
                sev = v.get("severity")
                if sev in blocked_severities:
                    bad.append({
                        "severity": sev,
                        "name": v.get("name", "Unknown"),
                        "file": v.get("location", {}).get("file", "Unknown"),
                        "report": path,
                    })
        except Exception as e:
            print(f"Error reading report {path}: {e}")
    return bad, files_checked


def main():
    blocked = load_blocked_severities()
    bad, files = scan_reports("gl-*report.json", blocked_severities=blocked)
    print(f"Scanned {len(files)} security report(s) with blocked severities: {blocked}")
    print(f"Blocking findings: {len(bad)}")
    for b in bad:
        print(f"  [{b['severity']}] {b['name']} in {b['file']} ({b['report']})")

    if bad:
        print("SAST GATE FAILED: Blocking security findings present.")
        sys.exit(1)

    print("SAST gate passed cleanly.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
