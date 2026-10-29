"""Read the live explainers saved in sources/posts/ (policyengine-app-v2 main at
the commit in sources/posts/APP_V2_MAIN_SHA).

key_points() returns a post's key points word for word: the line that opens
them ("Key figures for 2027-28:") and the bullet list after it, with relative
links turned absolute so they work in a PDF. chart_specs() returns the post's
```chart blocks, the JSON that policyengine-app-v2 draws.
"""

import json
import re
from pathlib import Path

from markdown_it import MarkdownIt

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


OPENING = re.compile(r"Key (results|figures|findings)\b.*:\s*$")


def _blocks(text):
    """The post's top-level Markdown blocks as (kind, first line, end line), end exclusive.

    markdown-it follows CommonMark, as the site's renderer does, so a list
    block holds every item whole: wrapped and lazy continuation lines, and
    items set apart by blank lines.
    """
    tokens = MarkdownIt("commonmark").enable("table").parse(text)
    return [(t.type.removesuffix("_open"), *t.map) for t in tokens if t.level == 0 and t.nesting >= 0 and t.map]


def key_points(slug, extra_paragraphs=0):
    """The opening line, the bullet list, and `extra_paragraphs` paragraphs after them.

    The build stops unless the post has exactly one opening line, standing as
    a paragraph of its own, with a bullet list straight after it. Markdown
    lets a paragraph start with up to three spaces, so the search ignores
    indentation, and any indented copy counts as a second opening.
    """
    text = _text(slug)
    lines = text.split("\n")
    starts = [i for i, x in enumerate(lines) if OPENING.match(x.strip())]
    if len(starts) != 1:
        raise SystemExit(f"{slug}: expected one 'Key results/figures/findings ...:' line, found {len(starts)}")
    blocks = _blocks(text)
    k = next((j for j, (_, a, _b) in enumerate(blocks) if a == starts[0]), None)
    if k is None or blocks[k][0] != "paragraph" or blocks[k][2] - blocks[k][1] != 1:
        raise SystemExit(f"{slug}: the line '{lines[starts[0]]}' isn't a paragraph of its own")
    if k + 1 == len(blocks) or blocks[k + 1][0] != "bullet_list":
        raise SystemExit(f"{slug}: no bullet list straight after '{lines[starts[0]]}'")

    def block_lines(j):
        _, a, b = blocks[j]
        part = lines[a:b]
        while part and not part[-1].strip():
            part.pop()
        return part

    out = [lines[starts[0]].strip(), "", *block_lines(k + 1)]
    for j in range(k + 2, k + 2 + extra_paragraphs):
        # A paragraph that opens with a link or image is a caption or a chart's source, not prose
        if j >= len(blocks) or blocks[j][0] != "paragraph" or lines[blocks[j][1]].lstrip().startswith(("_[", "[", "!")):
            raise SystemExit(f"{slug}: no plain paragraph {j - k - 1} after the key points")
        out += ["", *block_lines(j)]
    return adapt(_absolute_links("\n".join(out), slug), slug)


def chart_specs(slug):
    return [json.loads(m.group(1)) for m in re.finditer(r"```chart\n(.*?)\n```", _text(slug), re.S)]
