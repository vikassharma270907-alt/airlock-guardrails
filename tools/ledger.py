import json
import os
import sys

if len(sys.argv) < 3:
    print("Usage: python ledger.py <job_name> <job_status>")
    sys.exit(1)

name, status = sys.argv[1], sys.argv[2]
os.makedirs('ledger', exist_ok=True)
with open(os.path.join('ledger', f"{name}.json"), 'w') as f:
    json.dump({'job': name, 'status': status}, f, indent=2)
print(f"Recorded {name}: {status}")
