import glob
import json
import sys

BLOCK = {'Critical', 'High'}


def scan_reports(pattern='gl-*report.json'):
    bad = []
    files_checked = glob.glob(pattern)
    for path in files_checked:
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            for v in data.get('vulnerabilities', []):
                sev = v.get('severity')
                if sev in BLOCK:
                    bad.append({
                        'severity': sev,
                        'name': v.get('name', 'Unknown'),
                        'file': v.get('location', {}).get('file', 'Unknown'),
                        'report': path
                    })
        except Exception as e:
            print(f"Error reading report {path}: {e}")
    return bad, files_checked


def main():
    bad, files = scan_reports('gl-*report.json')
    print(f"Scanned {len(files)} security report(s).")
    print(f"Blocking findings (High/Critical): {len(bad)}")
    for b in bad:
        print(f"  [{b['severity']}] {b['name']} in {b['file']} ({b['report']})")

    if bad:
        print("SAST GATE FAILED: High or Critical security findings present.")
        sys.exit(1)

    print("SAST gate passed cleanly.")
    return 0


if __name__ == '__main__':
    sys.exit(main())
