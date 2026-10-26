import sys
from pathlib import Path

# Add project root and tools to sys.path so tests can import airlock_demo and tools
root = Path(__file__).resolve().parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))
