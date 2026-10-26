"""CLI Entrypoint for airlock-demo."""

import sys
from airlock_demo.textkit import slugify, word_count


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("--help", "-h"):
        print("Usage: airlock-demo [slugify|count] <text>")
        return 0

    cmd = sys.argv[1]
    text = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else ""

    if cmd == "slugify":
        print(slugify(text))
    elif cmd == "count":
        print(word_count(text))
    else:
        print(f"Unknown command: {cmd}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
