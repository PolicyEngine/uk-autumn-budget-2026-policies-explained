"""sources/README.md gives the right digest for every file it lists."""

import hashlib
import re
from pathlib import Path

import pytest

SOURCES = Path(__file__).resolve().parent.parent / "sources"
ROW = re.compile(r"^\| `([^`*]+)` \|(?:.*\|)? `([0-9a-f]{16})` \|$")


def listed():
    rows = [ROW.match(line) for line in (SOURCES / "README.md").read_text().splitlines()]
    return [m.groups() for m in rows if m]


def test_readme_lists_every_saved_file():
    names = {name for name, _ in listed()}
    saved = {p.name for p in SOURCES.iterdir() if p.is_file() and p.name != "README.md"}
    saved |= {p.name for p in (SOURCES / "posts").glob("*.md")}
    saved |= {f"posts/{p.name}" for p in (SOURCES / "posts").glob("*.json")}
    assert names == saved


@pytest.mark.parametrize("name, digest", listed())
def test_digest_matches_the_file(name, digest):
    path = SOURCES / name if (SOURCES / name).exists() else SOURCES / "posts" / name
    assert hashlib.sha256(path.read_bytes()).hexdigest()[:16] == digest
