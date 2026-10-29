"""Read the live explainers saved in sources/posts/ (policyengine-app-v2 main at
the commit in sources/posts/APP_V2_MAIN_SHA).

key_points() returns a post's key points word for word: the line that opens
them ("Key figures for 2027-28:") and the bullet list after it, with relative
links turned absolute so they work in a PDF. chart_specs() returns the post's
```chart blocks, the JSON that policyengine-app-v2 draws.
"""

import json
import re
from html import unescape
from html.parser import HTMLParser
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


OPENING = re.compile(r"Key\s+(results|figures|findings)\b.*:\s*$")
# The opening's words anywhere in a post's source, in any case and spacing
MENTION = re.compile(r"\bkey\s+(results|figures|findings)\b", re.I)
# A browser collapses each run of HTML whitespace, line breaks included, to one space
WHITESPACE = re.compile(r"[ \t\n\r\f]+")


def source_mentions(text):
    """How often the post's source mentions the opening's words, shown or not.

    HTML entities are decoded and Markdown's emphasis, strikethrough, code
    and escape marks dropped first, so "K*ey* figures" and "&#75;ey figures"
    count. Mentions in code, comments, captions, footnotes and highlighted
    blocks count too: the build quotes only from a post that mentions the
    words once, so it never has to work out whether the site shows them.
    """
    return len(MENTION.findall(re.sub(r"[*_~`\\]", "", unescape(text))))


class _ShownText(HTMLParser):
    """The text a browser shows as prose: everything outside code-like elements
    and comments, with whitespace collapsed and a line break at each block
    boundary. Like the site, it shows an image's alt text as a caption when the
    image has a source."""

    HIDDEN = {"code", "pre", "script", "style", "textarea", "template"}
    BREAKS = {"br", "p", "div", "li", "ul", "ol", "dl", "dt", "dd", "blockquote", "table", "tr", "td", "th",
              "caption", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "section", "article", "aside", "nav",
              "header", "footer", "main", "address", "figure", "figcaption", "fieldset", "legend",
              "details", "summary", "dialog", "hgroup", "menu", "search"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden, self.parts = 0, []

    def handle_starttag(self, tag, attrs):
        self.hidden += tag in self.HIDDEN
        if tag in self.BREAKS:
            self.parts.append("\n")
        attrs = dict(attrs)
        if tag == "img" and attrs.get("src") and attrs.get("alt") and not self.hidden:
            self.parts.append("\n" + WHITESPACE.sub(" ", attrs["alt"]) + "\n")

    def handle_endtag(self, tag):
        if tag in self.HIDDEN and self.hidden:
            self.hidden -= 1
        if tag in self.BREAKS:
            self.parts.append("\n")

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(WHITESPACE.sub(" ", data))


def shown_lines(html):
    """The lines of prose a browser shows for some HTML (see _ShownText)."""
    parser = _ShownText()
    parser.feed(html)
    parser.close()
    return "".join(parser.parts).split("\n")


def _highlighted_block(self, tokens, idx, options, env):
    """The site renders a fence whose language is highlighted-block as Markdown
    in two panes split at "&&&" (one pane if the split doesn't give two)."""
    t = tokens[idx]
    if t.info.split()[:1] != ["highlighted-block"]:
        return self.fence_code(tokens, idx, options, env)
    parts = t.content.split("&&&")
    return "".join(f"<div>{self.md.render(part)}</div>" for part in (parts if len(parts) == 2 else [t.content]))


def _markdown():
    # The site renders posts with react-markdown and remark-gfm: CommonMark
    # with GFM's tables and strikethrough, plus its own highlighted-block fence
    md = MarkdownIt("commonmark").enable(["table", "strikethrough"])
    md.renderer.md = md
    md.renderer.fence_code = md.renderer.rules["fence"]
    md.add_render_rule("fence", _highlighted_block)
    return md


def _parse(text):
    """The post's top-level Markdown blocks as (kind, first line, end line), end
    exclusive, and (first line of its block, text) for each line of prose.

    markdown-it follows CommonMark, so a list block holds every item whole:
    wrapped and lazy continuation lines, and items set apart by blank lines.
    Prose is a model of what the page shows outside code, block by block:
    the text of every paragraph, heading and table cell at any depth (inside
    lists and quotes too), of HTML blocks, of image captions and of
    highlighted blocks, but not code spans, code blocks, other fences, <pre>,
    comments or what a <template> in the same block holds.
    """
    md = _markdown()
    tokens = md.parse(text)
    blocks = [(t.type.removesuffix("_open"), *t.map) for t in tokens if t.level == 0 and t.nesting >= 0 and t.map]
    prose = []
    for i, t in enumerate(tokens):
        if t.type == "inline":
            html = md.renderer.renderInline(t.children or [], md.options, {})
        elif t.type == "html_block":
            html = t.content
        elif t.type == "fence" and t.info.split()[:1] == ["highlighted-block"]:
            html = md.renderer.rules["fence"](tokens, i, md.options, {})
        else:
            continue
        prose += [(t.map[0], line) for line in shown_lines(html)]
    return blocks, prose


def key_points(slug, extra_paragraphs=0):
    """The opening line, the bullet list, and `extra_paragraphs` paragraphs after them.

    The build stops unless two counts both come to one: the opening's words
    anywhere in the post's source (source_mentions), and opening lines in the
    model of what the page shows (_parse), which also catches markup that
    splits the words. That line must stand as a top-level paragraph of its
    own with a bullet list straight after it.
    """
    text = _text(slug)
    lines = text.split("\n")
    mentions = source_mentions(text)
    if mentions != 1:
        raise SystemExit(f"{slug}: expected the words 'Key results/figures/findings' once in the source, found {mentions}")
    blocks, prose = _parse(text)
    starts = [first for first, line in prose if OPENING.match(line.strip())]
    if len(starts) != 1:
        raise SystemExit(f"{slug}: expected one 'Key results/figures/findings ...:' line, found {len(starts)}")
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
