"""Read the live explainers saved in sources/posts/ (policyengine-app-v2 main at
the commit in sources/posts/APP_V2_MAIN_SHA).

key_points() returns a post's key points exactly as published: the line that
opens them ("Key figures for 2027-28:") and the bullet list after it, with
relative links made absolute so they work in a PDF. chart_specs() returns the
post's ```chart blocks, the JSON that policyengine-app-v2 draws.
"""

import json
import re
from pathlib import Path

POSTS = Path(__file__).resolve().parent.parent / "sources" / "posts"
SITE = "https://www.policyengine.org"


def post_url(slug):
    return f"{SITE}/uk/research/{slug}"


def _text(slug):
    path = POSTS / f"{slug}.md"
    if not path.exists():
        raise SystemExit(f"no saved post {path}")
    return path.read_text()


# Words in a post that point elsewhere in the post ("below") have nothing to
# point at in the PDF. Each is replaced in square brackets, the usual mark of an
# editor's words in a quotation; the build stops if one no longer matches once.
ADAPTATIONS = {
    "carers-allowance-taper": [("as we explain below", "as [the explainer sets out]")],
    "uk-autumn-budget-2026-trading-allowance": [("in the example below", "in [the explainer's] example")],
}


def adapt(text, slug, pairs=None):
    for old, new in ADAPTATIONS.get(slug, []) if pairs is None else pairs:
        if text.count(old) != 1:
            raise SystemExit(f"{slug}: expected '{old}' once, found it {text.count(old)} times")
        text = text.replace(old, new)
    return text


def _absolute_links(md, slug):
    md = re.sub(r"\]\(/", f"]({SITE}/", md)
    return re.sub(r"\]\(#", f"]({post_url(slug)}#", md)


def key_points(slug, extra_paragraphs=0):
    """The opening line, the bullets, and `extra_paragraphs` paragraphs after them."""
    lines = _text(slug).split("\n")
    start = next((i for i, x in enumerate(lines) if re.match(r"Key (results|figures|findings)\b.*:\s*$", x)), None)
    if start is None:
        raise SystemExit(f"{slug}: no 'Key results/figures/findings ...:' line")
    out = [lines[start], ""]
    i = start + 1
    while i < len(lines) and not lines[i].strip():
        i += 1
    if i == len(lines) or not lines[i].startswith("- "):
        raise SystemExit(f"{slug}: no bullet list after line {start + 1}")
    while i < len(lines) and lines[i].startswith("- "):
        out.append(lines[i])
        i += 1
    for _ in range(extra_paragraphs):
        while i < len(lines) and not lines[i].strip():
            i += 1
        para = []
        while i < len(lines) and lines[i].strip():
            para.append(lines[i])
            i += 1
        if not para or para[0].startswith(("#", "```", "|", "_[", "[")):
            raise SystemExit(f"{slug}: no plain paragraph after the key points")
        out += ["", *para]
    return adapt(_absolute_links("\n".join(out), slug), slug)


def chart_specs(slug):
    return [json.loads(m.group(1)) for m in re.finditer(r"```chart\n(.*?)\n```", _text(slug), re.S)]
