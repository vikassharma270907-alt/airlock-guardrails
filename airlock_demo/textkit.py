"""Text utilities for Airlock Demo."""

import re


def slugify(text: str) -> str:
    """Convert text to URL-friendly slug."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    text = re.sub(r"[\s_-]+", "-", text)
    return text.strip("-")


def word_count(text: str) -> int:
    """Count words in a text string.
    
    Seeded bug for demo: uses split(' ') instead of split(),
    which fails on multiple consecutive spaces or tabs.
    """
    if not text:
        return 0
    # Fix: split() without arguments strips and splits on any consecutive whitespace
    return len(text.split())
