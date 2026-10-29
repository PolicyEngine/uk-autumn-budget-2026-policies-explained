"""site/ renders posts with policyengine-app-v2's own code.

Invariants:
- Each copied file matches the git blob id site/README.md gives, which is the
  file's blob in policyengine-app-v2 at the commit the README names, and the
  README accounts for every file under site/vendor/.
- render.tsx's contents() copies the contents sidebar's text logic from
  ArticleClient.tsx line for line.
- package.json pins exact versions.
- The display category changes only styles: each saved post renders the same
  HTML, style attributes aside, on desktop, tablet and phone.
- No source file holds an invisible or bidirectional control character, which
  can make code read differently from how it runs.
"""

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pytest

import explainers

ROOT = Path(__file__).resolve().parent.parent
SITE = ROOT / "site"
ROW = re.compile(r"^\| `(vendor/[^`]+)` \| `([0-9a-f]{40})` \|$")
STAND_INS = {"vendor/components/blog/LazyBlogChart.tsx", "vendor/components/blog/LazyPlot.tsx",
             "vendor/designTokens/index.ts"}


def copied():
    rows = [ROW.match(line) for line in (SITE / "README.md").read_text().splitlines()]
    return [m.groups() for m in rows if m]


def blob(path):
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def test_readme_accounts_for_every_vendored_file():
    files = {str(p.relative_to(SITE)) for p in (SITE / "vendor").rglob("*") if p.is_file()}
    assert {name for name, _ in copied()} | STAND_INS == files
    readme = (SITE / "README.md").read_text()
    assert all(f"`{name}`" in readme for name in STAND_INS)


@pytest.mark.parametrize("name, blob_id", copied())
def test_copied_file_matches_the_app(name, blob_id):
    assert blob(SITE / name) == blob_id


def test_contents_sidebar_logic_matches_the_article_page():
    page = (SITE / "vendor/app/[countryId]/research/[slug]/ArticleClient.tsx").read_text()
    sidebar = page[page.index("function LeftContents"):]
    ours = (SITE / "render.tsx").read_text()
    ours = ours[ours.index("function contents"):ours.index("function render")]
    lines = [
        'const headers = markdown.split("\\n").filter((line) => line.startsWith("##"));',
        'let text = header.split(" ").slice(1).join(" ");',
        "// Extract text from markdown links [text](url)",
        'if (text.includes("[")) {',
        'text = text.split("[").slice(1).join("[").split("]")[0];',
    ]
    for source in (sidebar, ours):
        stripped = [line.strip() for line in source.splitlines()]
        positions = [stripped.index(line) for line in lines]
        assert positions == sorted(positions)


def test_contents_sidebar_lists_each_double_hash_line():
    page = explainers.render(["## One\n\n### [Two](/x) more\n\n```\n## Three\n```\n#### Four\n"])[0]
    assert page["contents"] == ["One", "Two", "Three", "Four"]


def test_packages_pin_exact_versions():
    package = json.loads((SITE / "package.json").read_text())
    for version in [*package["dependencies"].values(), *package["overrides"].values()]:
        assert re.fullmatch(r"\d+\.\d+\.\d+", version)


@pytest.mark.parametrize("slug", sorted(p.stem for p in explainers.POSTS.glob("*.md")))
def test_display_category_changes_only_styles(slug):
    text = explainers._text(slug)
    unstyled = {re.sub(r' style="[^"]*"', "", explainers.render([text], display)[0]["html"])
                for display in (None, "tablet", "mobile")}
    assert len(unstyled) == 1


def test_no_source_file_holds_invisible_or_bidirectional_characters():
    files = [*ROOT.glob("scripts/*.py"), *ROOT.glob("tests/*.py"), *SITE.glob("*.ts*"), *SITE.glob("*.py"),
             *(SITE / "vendor").rglob("*.ts*")]
    for path in files:
        odd = {c for c in path.read_text() if unicodedata.category(c) in ("Cf", "Zl", "Zp")
               or unicodedata.bidirectional(c) in ("LRE", "RLE", "LRO", "RLO", "PDF", "LRI", "RLI", "FSI", "PDI")}
        assert not odd, f"{path.relative_to(ROOT)}: {sorted(map(hex, map(ord, odd)))}"
