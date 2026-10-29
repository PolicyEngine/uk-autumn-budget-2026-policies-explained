"""Read the live explainers saved in sources/posts/ (policyengine-app-v2 main at
the commit in sources/posts/APP_V2_MAIN_SHA).

key_points() returns a post's key points word for word: the line that opens
them ("Key figures for 2027-28:") and the bullet list after it, with relative
links turned absolute so they work in a PDF. chart_specs() returns the post's
```chart blocks, the JSON that policyengine-app-v2 draws.

To find the key points, the build renders the post with the site's own code
(site/render.tsx) and reads the page that results; see key_points().
"""

import atexit
import html
import json
import re
import select
import shutil
import subprocess
import tempfile
import unicodedata
from html.parser import HTMLParser
from pathlib import Path

import regex

ROOT = Path(__file__).resolve().parent.parent
POSTS = ROOT / "sources" / "posts"
RENDERER = ROOT / "site"
SITE = "https://www.policyengine.org"


def post_url(slug):
    return f"{SITE}/uk/research/{slug}"


def _text(slug):
    path = POSTS / f"{slug}.md"
    if not path.exists():
        raise SystemExit(f"no saved post {path}")
    return path.read_text()


def _header(slug):
    """The text the article page shows above the post: its title and description."""
    meta = json.loads((POSTS / "meta.json").read_text())
    if slug not in meta:
        raise SystemExit(f"no title or description for {slug} in {POSTS / 'meta.json'}")
    return list(meta[slug].values())


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


# micromark, inside react-markdown, slows quadratically on some input (a run of
# unclosed comments: 4,000 take 1.4 seconds, 40,000 over five minutes), and the
# site would too. A call that takes longer than this stops the build instead.
RENDER_SECONDS = 120


class _Renderer:
    """One `bun site/render.tsx --serve`, restarted if it stops."""

    def __init__(self):
        if not shutil.which("bun"):
            raise SystemExit("the build renders posts with bun; install it (site/README.md)")
        self.dir = Path(tempfile.mkdtemp())
        self.proc = subprocess.Popen(["bun", "render.tsx", "--serve"], cwd=RENDERER,
                                     stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        atexit.register(self.close)

    def __call__(self, posts, display=None):
        source, result = self.dir / "in.json", self.dir / "out.json"
        source.write_text(json.dumps({"posts": posts, "displayCategory": display}))
        self.proc.stdin.write(f"{source}\t{result}\n")
        self.proc.stdin.flush()
        if not select.select([self.proc.stdout], [], [], RENDER_SECONDS)[0]:
            self.proc.kill()
            self.proc.wait()
            raise SystemExit(f"site/render.tsx took over {RENDER_SECONDS} seconds to render, so the build stops")
        if self.proc.stdout.readline() != "done\n":
            raise SystemExit(f"site/render.tsx stopped (exit {self.proc.poll()})")
        return json.loads(result.read_text())

    def close(self):
        self.proc.stdin.close()
        self.proc.wait()
        shutil.rmtree(self.dir, ignore_errors=True)


_renderer = None
_rendered = {}


def render(posts, display=None):
    """For each Markdown string, what site/render.tsx gives: html (or error),
    blocks, contents and elements. `display` renders for a "mobile" or
    "tablet" screen instead of the desktop layout."""
    global _renderer
    todo = [p for p in dict.fromkeys(posts) if (display, p) not in _rendered]
    if todo:
        if _renderer is None or _renderer.proc.poll() is not None:
            _renderer = _Renderer()
        _rendered.update(((display, p), r) for p, r in zip(todo, _renderer(todo, display)))
    return [_rendered[display, p] for p in posts]


# The post's own HTML may use these tags and properties (hast names) and no
# others, nor may Markdown produce others. Styles, classes, the hidden
# attribute, dir, <bdo>, <template>, <style>, forms and media can hide, move
# or draw text in ways the page text below doesn't follow, so a post that
# uses them stops the build.
TAGS = {"a", "abbr", "b", "blockquote", "br", "caption", "cite", "code", "dd", "del", "details", "div", "dl",
        "dt", "em", "figcaption", "figure", "h1", "h2", "h3", "h4", "h5", "h6", "hr", "i", "img", "input",
        "ins", "kbd", "li", "mark", "ol", "p", "pre", "q", "s", "section", "small", "span", "strong", "sub",
        "summary", "sup", "table", "tbody", "td", "tfoot", "th", "thead", "tr", "u", "ul"}
PROPERTIES = {
    "*": {"id", "title", "className"},
    "a": {"href", "dataFootnoteRef", "dataFootnoteBackref", "ariaDescribedBy", "ariaLabel"},
    "img": {"src", "alt"},
    "ol": {"start"},
    "td": {"align", "colSpan", "rowSpan"},
    "th": {"align", "colSpan", "rowSpan"},
    "input": {"type", "checked", "disabled"},  # GFM's task list checkboxes
    "section": {"dataFootnotes"},
    "details": {"open"},
}
# GFM's own classes; a fence's language becomes language-<word> on <code>
CLASSES = {"contains-task-list", "task-list-item", "footnotes", "sr-only", "data-footnote-backref"}


def _unreadable(elements):
    """The first element whose tag, properties or classes the page text can't follow, if any."""
    for e in elements:
        extra = set(e["props"]) - PROPERTIES["*"] - PROPERTIES.get(e["tag"], set())
        classes = [c for c in e["classes"] if c not in CLASSES and not c.startswith("language-")]
        if e["tag"] not in TAGS or extra or classes:
            return f"<{e['tag']}> with {sorted(extra) + classes}" if extra or classes else f"<{e['tag']}>"
    return None


# Characters that make a browser draw letters in another order
BIDI = re.compile("[\u202a-\u202e\u2066-\u2069]")
# Characters a browser draws as nothing, such as a soft hyphen or a zero-width space
IGNORABLE = regex.compile(r"\p{Default_Ignorable_Code_Point}")
# Control characters other than whitespace, which a browser doesn't draw as letters
CONTROL = regex.compile(r"(?![\t\n\v\f\r\x1c-\x1f\x85])\p{Cc}")


def visible(text):
    """Text as a reader sees its letters: NFKC folds compatibility forms
    ("Ｋｅｙ" to "Key", "ﬁ" to "fi"), and invisible and control characters go."""
    return CONTROL.sub("", IGNORABLE.sub("", unicodedata.normalize("NFKC", text)))


# The page text is a string of segments, one per text node or attribute value
# a browser can show as text, with a boundary mark wherever a tag sits. A
# shown segment sits between SHOWN and END; one the browser may or may not
# draw, between MAYBE and MAYBE_END: those attribute values (an image's alt
# text shows if the image fails, a title on hover, an aria-label to a screen
# reader), and all text inside <details> (closed, it hides all but its
# summary), inside an element with class sr-only, or inside one the formatter
# styles as invisible (its heading anchors).
#
# Some layout sets two pieces of text side by side in the opposite order to
# the HTML's, or with other text between them in the HTML: a table (a caption
# shows on top and a footer at the bottom wherever they sit, and a cell that
# spans rows sits beside later cells), <details> (its summary shows first), a
# chart (it places its strings itself), and what the formatter lays out in a
# row or takes out of the flow (a highlighted block's two panes). The page
# text gives each such region's text twice, every segment as MAYBE, so the
# count sees any two of its pieces side by side, in either order.
BOUNDARY, SHOWN, END, MAYBE, MAYBE_END = "\x00", "\x01", "\x02", "\x03", "\x04"
TEXT_ATTRIBUTES = {"alt", "title", "aria-label", "value", "placeholder", "label"}
VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}
HIDING_STYLE = re.compile(r"opacity:0(?![.\d])|display:none|visibility:hidden")
FREE_TAGS = {"table", "details"}
FREE_STYLE = re.compile(r"display:(?:inline-)?(?:flex|grid)|position:(?:absolute|fixed|sticky)|float:(?!none)|"
                        r"columns?(?:-count)?:|order:|direction:|writing-mode:|transform:")
_AS_MAYBE = str.maketrans({SHOWN: MAYBE, END: MAYBE_END})
# What Plotly reads in a string (plotly.js 3.4.0, the site's version): tags
# (SPLIT_TAGS in src/lib/svg_text_utils.js) and template placeholders it fills
# from the data (TEMPLATE_STRING_REGEX in src/lib/index.js). It decodes
# entities in the text between them.
PLOTLY_MARKUP = re.compile(r"(<[^<>]*>|%\{[^\s%{}:]*(?:[:|][^}]*)?\})")


def _may_hide(tag, attrs):
    """Whether a browser may not draw the text inside this element."""
    return (tag == "details" or "sr-only" in (attrs.get("class") or "").split()
            or bool(HIDING_STYLE.search(attrs.get("style") or "")))


def _segment(text, maybe):
    if BIDI.search(text):
        raise SystemExit(f"text with a bidirectional override, which reorders the letters a reader sees: {text[:80]!r}")
    text = visible(text)
    return (MAYBE + text + MAYBE_END if maybe else SHOWN + text + END) if text else ""


def _anywhere(region):
    """A region's page text, twice, with every segment one the browser may or may not draw."""
    region = region.translate(_AS_MAYBE)
    return region + BOUNDARY + region


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, (dict, list)):
        for item in value.values() if isinstance(value, dict) else value:
            yield from _strings(item)


def chart_pieces(kind, spec):
    """The text a chart could show: each string in its JSON (a title, a series
    name, a category), which the site parses before it draws. Plotly reads tags,
    placeholders and entities in a string, so a Plotly string comes apart at its
    tags and placeholders, each piece as written and with entities decoded. A
    spec that doesn't parse counts as written, though the site draws nothing."""
    try:
        strings = list(_strings(json.loads(spec)))
    except (ValueError, RecursionError):
        strings = [spec]
    if kind == "plotly":
        strings = [q for s in strings for p in PLOTLY_MARKUP.split(s) for q in dict.fromkeys([p, html.unescape(p)])]
    return [s for s in strings if s.strip()]


class _PageText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.text, self.maybe = [], [], [False]
        self.regions = [None]  # for each open element, where its page text starts if it's a region
        self.chart = None  # a chart's kind and its JSON, while reading it

    def flush(self):
        self.parts.append(_segment("".join(self.text), self.maybe[-1]))
        self.text = []

    def handle_starttag(self, tag, attrs):
        self.flush()
        start = len(self.parts)
        self.parts.append(BOUNDARY)
        self.parts += [_segment(value, True) + BOUNDARY for name, value in attrs if name in TEXT_ATTRIBUTES and value]
        if tag not in VOID:
            attrs = dict(attrs)
            self.maybe.append(self.maybe[-1] or _may_hide(tag, attrs))
            if tag == "pre" and attrs.get("data-chart"):
                self.chart = (attrs["data-chart"], [])
            region = tag in FREE_TAGS or self.chart is not None or FREE_STYLE.search(attrs.get("style") or "")
            self.regions.append(start if region else None)

    def handle_endtag(self, tag):
        if self.chart is not None:
            kind, spec = self.chart
            self.chart = None
            self.parts.append(BOUNDARY.join(_segment(p, False) for p in chart_pieces(kind, "".join(spec))))
        self.flush()
        self.parts.append(BOUNDARY)
        if tag not in VOID and len(self.maybe) > 1:
            self.maybe.pop()
            start = self.regions.pop()
            # The outermost region takes in any inside it
            if start is not None and not any(s is not None for s in self.regions):
                self.parts[start:] = [_anywhere("".join(self.parts[start:]))]

    def handle_data(self, data):
        (self.chart[1] if self.chart is not None else self.text).append(data)


def page_text(page, header=()):
    """The page text (see above) of a rendered post, after the article page's
    header and its contents sidebar, each a shown segment of its own."""
    parser = _PageText()
    parser.feed(page["html"])
    parser.close()
    parser.flush()
    return BOUNDARY.join([_segment(t, False) for t in [*header, *page["contents"]]] + ["".join(parser.parts)])


# The opening's words in the page text, in any case. Inside a word or between
# the two, a match may HOP out of one segment and into a later one, across
# boundaries and segments the browser may not draw; between the two it also
# takes any whitespace. Each boundary may show as a line break or as nothing,
# and each MAYBE segment as its text or as nothing, so this counts every place
# a reader could see the words, under every way of drawing the page: no
# letter or digit of the same segment may touch them.
_SKIP = rf"{MAYBE}[^{MAYBE_END}]*{MAYBE_END}"
_HOP = rf"[{END}{MAYBE_END}](?:{BOUNDARY}|{_SKIP})*?[{SHOWN}{MAYBE}]"
WORDS = ("results", "figures", "findings")


def _spelled(word):
    return f"(?:{_HOP})?".join(word)


MENTION = regex.compile(
    rf"(?<![^\W_]){_spelled('key')}(?:\s|{_HOP})+(?:{'|'.join(_spelled(w) for w in WORDS)})(?![^\W_])", regex.I)


def mentions(text):
    """How many places in some page text could show the opening's words."""
    try:
        return len(MENTION.findall(text, overlapped=True, timeout=10))
    except TimeoutError:
        raise SystemExit("the page took over 10 seconds to read, so the build can't count the opening's words")


OPENING = re.compile(r"Key\s+(results|figures|findings)\b.*:\s*$")
# A browser draws each run of HTML whitespace, line breaks included, as one space
WHITESPACE = re.compile(r"[ \t\n\r\f]+")


class _ShownLines(HTMLParser):
    """The lines a browser shows for some HTML: shown text only, with a line
    break at each tag that isn't phrasing content or that the formatter styles
    as a block."""

    PHRASING = {"a", "abbr", "b", "cite", "code", "del", "em", "i", "img", "input", "ins", "kbd", "mark", "q",
                "s", "small", "span", "strong", "sub", "sup", "u"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.maybe = [], [False]

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag not in self.PHRASING or re.search(r"display:(?!inline)", attrs.get("style") or ""):
            self.parts.append("\n")
        if tag not in VOID:
            self.maybe.append(self.maybe[-1] or _may_hide(tag, attrs))

    def handle_endtag(self, tag):
        self.parts.append("\n" if tag not in self.PHRASING else "")
        if tag not in VOID and len(self.maybe) > 1:
            self.maybe.pop()

    def handle_data(self, data):
        if not self.maybe[-1]:
            self.parts.append(WHITESPACE.sub(" ", data))


def shown_lines(html):
    parser = _ShownLines()
    parser.feed(html)
    parser.close()
    lines = (" ".join(visible(line).split()) for line in "".join(parser.parts).split("\n"))
    return [line for line in lines if line]


def key_points(slug, extra_paragraphs=0):
    """The opening line, the bullet list, and `extra_paragraphs` paragraphs after them.

    The build renders the post with the site's own code and stops unless:
    - the post uses only the HTML in TAGS, PROPERTIES and CLASSES;
    - its page, header and contents sidebar included, could show the opening's
      words in exactly one place (mentions());
    - exactly one top-level block holds them, so that blanking that block's
      lines leaves none on the page;
    - that block is a one-line paragraph that shows as "Key results/figures/
      findings ...:" on its own, with a bullet list straight after it.
    """
    text = _text(slug)
    lines = text.split("\n")
    header = _header(slug)
    page = render([text])[0]
    if "error" in page:
        raise SystemExit(f"{slug}: the site's formatter can't render the post: {page['error']}")
    if problem := _unreadable(page["elements"]):
        raise SystemExit(f"{slug}: the post uses {problem}, which can hide or move text, so the build can't read the page")
    found = mentions(page_text(page, header))
    if found != 1:
        raise SystemExit(f"{slug}: expected the words 'Key results/figures/findings' in one place on the page, found {found}")
    blocks = page["blocks"]
    blanked = render(["\n".join("" if b["start"] <= n <= b["end"] else line for n, line in enumerate(lines, 1))
                      for b in blocks])
    holders = [j for j, p in enumerate(blanked) if "error" in p or mentions(page_text(p, header)) == 0]
    if len(holders) != 1 or "error" in blanked[holders[0]]:
        raise SystemExit(f"{slug}: expected one block of the post to hold the words, found {len(holders)}")
    k = holders[0]
    first, last = blocks[k]["start"], blocks[k]["end"]
    if blocks[k]["type"] != "paragraph" or first != last:
        raise SystemExit(f"{slug}: the words sit in a {blocks[k]['type']} on lines {first}-{last}, not a paragraph of their own")
    line = lines[first - 1].strip()
    shown = shown_lines(render([line])[0].get("html", ""))
    if len(shown) != 1 or not OPENING.match(shown[0]):
        raise SystemExit(f"{slug}: line {first} shows {shown}, not one line that opens 'Key results/figures/findings ...:'")
    if k + 1 == len(blocks) or blocks[k + 1]["type"] != "list" or blocks[k + 1]["ordered"]:
        raise SystemExit(f"{slug}: no bullet list straight after '{line}'")

    def block_lines(j):
        return lines[blocks[j]["start"] - 1:blocks[j]["end"]]

    out = [line, "", *block_lines(k + 1)]
    for j in range(k + 2, k + 2 + extra_paragraphs):
        # A paragraph that opens with a link or image is a caption or a chart's source, not prose
        if j >= len(blocks) or blocks[j]["type"] != "paragraph" or lines[blocks[j]["start"] - 1].lstrip().startswith(("_[", "[", "!")):
            raise SystemExit(f"{slug}: no plain paragraph {j - k - 1} after the key points")
        out += ["", *block_lines(j)]
    return adapt(_absolute_links("\n".join(out), slug), slug)


def chart_specs(slug):
    return [json.loads(m.group(1)) for m in re.finditer(r"```chart\n(.*?)\n```", _text(slug), re.S)]
