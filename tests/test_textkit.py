"""Tests for airlock_demo.textkit."""

import pytest
from airlock_demo.textkit import slugify, word_count


def test_slugify_basic():
    assert slugify("Hello World") == "hello-world"


def test_slugify_special_characters():
    assert slugify("GitLab & AI: The Future!") == "gitlab-ai-the-future"


def test_slugify_whitespace_and_hyphens():
    assert slugify("  multiple   spaces --- and dashes  ") == "multiple-spaces-and-dashes"


def test_word_count_simple():
    assert word_count("hello world") == 2


def test_word_count_empty():
    assert word_count("") == 0


def test_word_count_multiple_spaces():
    # Exposes the seeded bug: split(' ') vs split()
    assert word_count("hello    world") == 2
