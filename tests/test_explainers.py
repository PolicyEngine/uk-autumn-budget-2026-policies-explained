"""key_points() quotes a whole bullet list, or stops the build.

The build renders each post with the site's own code (site/render.tsx) and
reads the HTML that results as page text (explainers.page_text): a segment
for each text node and attribute value, a boundary mark at each tag.

Invariants:
- Every list item comes out whole, however the post wraps or spaces it.
- Nothing after the list comes out unless the template asks for paragraphs.
- mentions() counts every place a reader could see "Key results/figures/
  findings", under every way of drawing the page: each boundary as a line
  break or as nothing, and each segment a browser may not draw (alt, title
  and other attribute values it can show as text; text in <details>, in class
  sr-only or styled invisible) as its text or as nothing. On small page texts
  it finds exactly the places that drawing the page every such way and
  searching the plain text finds (a property test against brute force).
- page_text() keeps every text node a browser shows: on rendered posts, an
  independent reading of the HTML never finds more mentions (a property test).
- The build stops unless the page could show the words in exactly one place,
  unless exactly one top-level block holds them, and unless that block is a
  one-line paragraph that shows as "Key results/figures/findings ...:", with
  a bullet list straight after it. Mentions the page never shows (in a
  comment, an unreferenced footnote, an image without a source) don't count.
- A post whose HTML the page text can't follow (styles, classes outside
  GFM's, the hidden attribute, dir, <template>, forms, media), in any pane,
  stops the build, and so does a bidirectional override.
- Out of scope: the site's stylesheet, which can hide, move or add text, and
  look-alike letters from other scripts.
"""

import html
import itertools
import re
import time

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

import explainers
from explainers import (BOUNDARY, END, MAYBE, MAYBE_END, MENTION, OPENING, SHOWN, key_points, mentions, page_text,
                        render, shown_lines)

POSTS = [
    ("budget-2026-energy-bills", 0),
    ("fuel-duty-cut-extension", 0),
    ("pension-tax-allowance", 0),
    ("carers-allowance-taper", 0),
    ("uk-autumn-budget-2026-property-income-tax", 1),
    ("uk-autumn-budget-2026-trading-allowance", 0),
]


def quote(monkeypatch, text, extra=0, header=()):
    monkeypatch.setattr(explainers, "_text", lambda slug: text)
    monkeypatch.setattr(explainers, "_header", lambda slug: list(header))
    return key_points("test-post", extra)


def count(markdown):
    """Places the rendered page could show the words."""
    return mentions(page_text(render([markdown])[0]))


def test_wrapped_items_come_out_whole(monkeypatch):
    out = quote(monkeypatch, "Intro.\n\nKey figures for 2027-28:\n\n- one\n  wrapped\n- two\nlazily continued\n- three\n\nAfter.\n")
    assert out == "Key figures for 2027-28:\n\n- one\n  wrapped\n- two\nlazily continued\n- three"


def test_items_apart_by_blank_lines_stay_one_list(monkeypatch):
    out = quote(monkeypatch, "Key results:\n\n- one\n\n- two\n\n  second paragraph of two\n\n- three\n\n## Next\n")
    assert out == "Key results:\n\n- one\n\n- two\n\n  second paragraph of two\n\n- three"


@pytest.mark.parametrize("indent", [" ", "  ", "   "])
def test_indented_opening_is_still_an_opening(monkeypatch, indent):
    assert quote(monkeypatch, f"{indent}Key results:\n\n- one\n") == "Key results:\n\n- one"


@pytest.mark.parametrize("opening", ["**Key figures:**", "K<b>ey</b> figures:", "_Key figures for 2027-28:_",
                                     "Key [figures](https://x.org):", "K&shy;ey figures:", "Key&nbsp;figures:"])
def test_an_opening_in_markup_still_opens(monkeypatch, opening):
    assert quote(monkeypatch, f"Intro.\n\n{opening}\n\n- one\n") == f"{opening}\n\n- one"


@pytest.mark.parametrize("indent", [" ", "  ", "   "])
def test_indented_second_opening_stops_the_build(monkeypatch, indent):
    # Sol review r2: Markdown reads both as openings, so the build must too
    with pytest.raises(SystemExit, match="one place on the page, found 2"):
        quote(monkeypatch, f"Key results:\n\n- first\n\n## Split\n\n{indent}Key figures:\n\n- second\n")


# A second mention the page shows, where reviews r1-r10 looked for one
SHOWN_SECOND = [
    "Example syntax:\n\n    Key figures:\n",  # an indented code block
    "```text\nKey figures:\n```\n",  # a fence
    "- An item\n\n  ```\n  Key figures:\n  ```\n",  # a fence inside a list item
    "Example: `\nKey figures:\n`\n",  # inline code over three lines
    "<pre>\nKey figures:\n</pre>\n",  # raw HTML code
    "Inline <code>Key figures:</code>\n",
    "```text\nKey figures:\n&&&\nx\n```\n",  # a fence of another language
    "[ ] Key figures:\n",  # a literal marker outside a list (Sol review r7)
    "Text.[^1]\n\n[^1]: First paragraph\n\n    Key [figures](/x):\n\n    More prose.\n",  # (Sol review r9)
    "Key <code>figures</code>:\n",  # (Sol review r9)
    "~Key [figures](/x):~\n",  # (Sol review r9)
    "```highlighted-block\nOne pane\n&&&\nKey [figures](/x):\n```\n",  # (Sol review r9)
    "- item\n\n  Key figures:\n\n  - nested\n",  # a paragraph inside a list item
    "- Key figures:\n",  # a list item itself (Sol review r4)
    "> Key figures:\n",  # a quote (Sol review r4)
    "**Key figures:**\n",
    "<div>\nKey figures:\n</div>\n",
    "| Key figures: |\n|---|\n| x |\n",  # a table cell
    "Key  figures:\n", "Key\tfigures:\n", "Key\nfigures:\n", "Key&nbsp;figures:\n",  # (Sol review r5)
    "![Key figures:](/chart.png)\n",  # the site shows alt text as a caption (Sol review r5)
    "```highlighted-block\nKey figures:\n\n- second\n&&&\nMore detail\n```\n",  # (Sol review r5)
    "```highlighted-block\nOne pane only\n\nKey figures:\n```\n",  # a malformed block renders as one pane
    "~~Key figures:~~\n", "~Key figures:~\n",  # GFM strikethrough (Sol review r7)
    "Text.[^1]\n\n[^1]: Key figures:\n",  # a footnote
    "Text.[^1]\n\n[^1]: First paragraph\n\n    Key figures:\n",  # its second paragraph (Sol review r7)
    "- [ ] Key figures:\n",  # a task item
    "<div><pre>not closed</div>\n\nKey figures:\n",  # after broken HTML (Sol review r7)
    "```highlighted-block caption\nKey figures:\n```\n",  # (Sol review r7)
    '<code class="language-highlighted-block">Key figures:</code>\n',  # (Sol review r7)
    "<dl>\n<dt>Other</dt>\n<dd>Key figures:</dd>\n</dl>\n",  # (Sol review r7)
    "<figure>\nText\n<figcaption>Key figures:</figcaption>\n</figure>\n",  # (Sol review r7)
    "<details><summary>More</summary>Key figures:</details>\n",  # closed, it may hide them, or not
    '<abbr title="Key figures:">KF</abbr>\n',  # a title shows on hover
    "## Key figures for 2027\n",  # a heading and its entry in the contents sidebar
    "```text\n## Key figures\n```\n",  # the sidebar lists a "##" line even inside code
    "<!--\n## Key figures\n-->\n",  # and inside a comment, which only the sidebar shows
    "&#75;ey figures:\n", "K*ey* figures:\n", "K<b>ey</b> figures:\n", "_Key figures:_\n",
    "K&shy;ey figures:\n", "K\u00adey figures:\n", "K\u200bey figures:\n", "K\u2060ey figures:\n",  # (Sol review r9)
    "K\ufeffey figures:\n", "K&#8203;ey figures:\n", "K&#x2060;ey figures:\n",
    "Ｋｅｙ ｆｉｇｕｒｅｓ:\n", "Key ﬁgures:\n",
    '<span title="a &gt; b">K</span>ey figures:\n',  # an attribute holding ">" (Sol review r10)
    "K[ey](</x y>) figures:\n", "K[ey](/x\\)) figures:\n",  # link destinations (Sol review r10)
    "K<!-- Key figures -->ey figures:\n",  # the comment hides one; the page shows the other
]


@pytest.mark.parametrize("second", SHOWN_SECOND)
def test_a_second_mention_the_page_shows_stops_the_build(monkeypatch, second):
    with pytest.raises(SystemExit, match=r"one place on the page, found [2-9]"):
        quote(monkeypatch, f"Key results:\n\n- actual\n\n## More\n\n{second}")


@pytest.mark.parametrize("second", [
    "<!--\nKey figures:\n-->\n",  # a comment, which the site drops
    '<img alt="Key figures:">\n',  # an image without a source, which the formatter drops (Sol review r7)
    '<img src="" alt="Key figures:">\n',
    "[^9]: Key figures:\n",  # a footnote nothing references, which GFM drops (Sol review r7)
    '[link](/x "Key figures:")\n',  # the formatter's links drop their title
    "K<!-- x -->ey<!-- y -->\n",  # half the words
])
def test_a_second_mention_the_page_never_shows_leaves_the_quote_alone(monkeypatch, second):
    assert quote(monkeypatch, f"Key results:\n\n- actual\n\n## More\n\n{second}") == "Key results:\n\n- actual"


def test_the_words_in_the_page_header_count(monkeypatch):
    with pytest.raises(SystemExit, match="found 2"):
        quote(monkeypatch, "Key results:\n\n- actual\n", header=["Key figures from the Budget"])
    with pytest.raises(SystemExit, match="one block of the post to hold the words, found 0"):
        quote(monkeypatch, "Intro.\n\n- actual\n", header=["Our key results"])


@pytest.mark.parametrize("post", [
    "Key results:\n\n- one\n\n<template>x</template>\n",  # (Sol review r3)
    "Key results:\n\n- one\n\nK<span style=\"display:none\">x</span>ey figures\n",
    'Key results:\n\n- one\n\n<span class="hidden">Key figures</span>\n',
    "Key results:\n\n- one\n\n<b hidden>x</b>\n",
    'Key results:\n\n- one\n\n<p dir="rtl">serugif yeK</p>\n',
    "Key results:\n\n- one\n\n<bdo>x</bdo>\n",
    "Key results:\n\n- one\n\n<style>p{display:none}</style>\n",
    'Key results:\n\n- one\n\n<input value="Key figures">\n',
    "Key results:\n\n- one\n\n<select><option>Key figures</option></select>\n",
    "Key results:\n\n- one\n\n<font size=0>x</font>\n",
    "Key results:\n\n- one\n\n<svg><text>Key figures</text></svg>\n",
    # Raw HTML in a highlighted block's pane, which the formatter renders as a post of its own
    'Key results:\n\n- one\n\n```highlighted-block\nK<span style="display:none">x</span>ey figures\n&&&\nRight\n```\n',
])
def test_html_the_page_text_cant_follow_stops_the_build(monkeypatch, post):
    with pytest.raises(SystemExit, match="can hide or move text"):
        quote(monkeypatch, post)


@pytest.mark.parametrize("override", ["\u202e", "&#x202E;", "\u202d", "\u2066", "\u2069"])
def test_a_bidirectional_override_stops_the_build(monkeypatch, override):
    with pytest.raises(SystemExit, match="bidirectional override"):
        quote(monkeypatch, f"Key results:\n\n- one\n\nKey {override}serugif:\n")


@pytest.mark.parametrize("text", [
    "Key figures", "KEY FIGURES", "key results", "Key\tfindings", "Key\nfigures", "&#75;ey figures", "K*ey* figures",
    "`Key` figures", "_Key figures_", "__Key__ figures", "Key [figures](/x)", "K[ey](/x(y)) figures",
    "Key <code>figures</code>", "Key</b> <b>figures", "K<!-- -->ey figures", "K<!-- a -> b -->ey figures",
    "K&shy;ey figures", "K\u00adey figures", "K\u200bey figures", "K\u2060ey figures", "K\ufeffey figures",
    "K&#8203;ey figures", "K&#x200B;ey figures", "K&zwj;ey figures", "Key\u00a0figures", "Ｋｅｙ ｆｉｇｕｒｅｓ",
    "Key ﬁgures", "K\x01ey figures", '<span title="a &gt; b">K</span>ey figures', "K[ey](</x y>) figures",
])
def test_the_count_sees_any_spelling_the_page_shows_as_the_words(text):
    assert count(f"Some prose. {text} More prose.\n") == 1


@pytest.mark.parametrize("text", [
    "Keyfigures", "Key figure", "Monkey figures", "Key resultsx", "AKey figures", "Key figures2",
    "Key_ _figures", "Key \\figures", "K[ey][1] figures",  # the page shows the underscores, backslash and brackets
    "Key findi  \nngs", "Key fig\\\nures",  # a hard line break inside a word
])
def test_the_count_ignores_what_the_page_shows_as_other_words(text):
    assert count(f"Some prose. {text} More prose.\n") == 0


@pytest.mark.parametrize("text", ['<b title="Key figures">Key figures</b>', 'K<b title="Key figures">ey figures',
                                  "![Key figures](/x.png)"])  # the alt text and the caption
def test_the_words_in_an_attribute_count_as_well(text):
    assert count(text + "\n") == 2


@pytest.mark.parametrize("text", [
    "K<details>zz</details>ey figures",  # closed, <details> hides what it holds
    'K<span class="sr-only">zz</span>ey figures',
    "## Key\n\nfigures, more",  # the formatter's heading anchor "#" shows only on hover
])
def test_text_a_browser_may_hide_can_part_the_words(text):
    # The page may draw each pair as the words, so the count must see them
    assert count(text + "\n") == 1


# Inline markup that the page draws as nothing, between or inside the words
INVISIBLE = ["<b>{}</b>", "<span>{}</span>", "<em>{}</em>", "*{}*", "**{}**", "`{}`", "[{}](/x)", "~~{}~~"]
SPACES = [" ", "\n", "&nbsp;", "\u00a0", "\u2003", " <!-- note --> ", "\t"]
INSIDE = ["", "<!-- x -->", "&shy;", "\u200b", "&#8203;", "\ufeff", "&zwj;"]


@st.composite
def drawn_as_the_words(draw):
    """The words in any case, split anywhere into pieces, each wrapped in
    inline markup, with invisible characters between the pieces. Not before a
    word, since after a line break "<!--" opens an HTML block; and never two
    delimiter runs side by side, since "*k**ey*" merges them and shows them."""
    def spell(word):
        word = "".join(draw(st.sampled_from([c.lower(), c.upper()])) for c in word)
        cuts = sorted(draw(st.sets(st.integers(1, len(word) - 1), max_size=2)))
        pieces = [word[a:b] for a, b in zip([0, *cuts], [*cuts, len(word)])]
        out, before = [], "<"
        for i, piece in enumerate(pieces):
            gap = draw(st.sampled_from(INSIDE)) if i else ""
            wrap = draw(st.sampled_from(INVISIBLE))
            if not gap and before[0] in "*`~" and wrap[0] in "*`~":
                wrap = "<b>{}</b>"
            out.append(gap + wrap.format(piece))
            before = wrap
        return "".join(out)

    return spell("key") + draw(st.sampled_from(SPACES)) + spell(draw(st.sampled_from(["results", "figures", "findings"])))


@settings(max_examples=150, deadline=None)
@given(drawn_as_the_words())
def test_any_spelling_drawn_from_invisible_markup_counts_once(words):
    assert count(f"Some prose. {words} More prose.\n") == 1


def drawings(text):
    """Every way of drawing a page text, as (plain text, the page text index of
    each of its characters): each run of boundaries as a line break or as
    nothing, each MAYBE segment as its text or as nothing."""
    tokens = re.findall(f"{BOUNDARY}+|{SHOWN}[^{END}]*{END}|{MAYBE}[^{MAYBE_END}]*{MAYBE_END}", text)
    assert "".join(tokens) == text
    starts = list(itertools.accumulate([0] + [len(t) for t in tokens]))
    choices = [[True, False] if t[0] in BOUNDARY + MAYBE else [True] for t in tokens]
    for picks in itertools.product(*choices):
        plain, where = [], []
        for t, start, pick in zip(tokens, starts, picks):
            if t[0] == BOUNDARY:
                plain.append("\n" if pick else "")
                where += [start] if pick else []
            elif pick:
                plain.append(t[1:-1])
                where += range(start + 1, start + len(t) - 1)
        yield "".join(plain), where


PLAIN = re.compile(r"(?<![^\W_])key\s+(?:results|figures|findings)(?![^\W_])", re.I)
PIECES = ["k", "ke", "key", "Key", "KEY", "ey", "y", "e", " ", "\n", "fig", "ures", "figures", "Results", "res",
          "ults", "findings", "x", "a key", "key ", " figures", "s", "1", "_", "figuresx"]


@st.composite
def page_texts(draw):
    segments = draw(st.lists(st.tuples(st.lists(st.sampled_from(PIECES), min_size=1, max_size=2), st.booleans()),
                             min_size=1, max_size=6))
    parts = [(MAYBE + "".join(p) + MAYBE_END) if maybe else (SHOWN + "".join(p) + END) for p, maybe in segments]
    return BOUNDARY.join(parts)


@settings(max_examples=400, deadline=None)
@given(page_texts())
def test_mentions_finds_what_every_drawing_shows(text):
    # Differential: the pattern against drawing the page every way and searching each drawing
    found = {m.start() for m in MENTION.finditer(text, overlapped=True)}
    seen = {where[m.start()] for plain, where in drawings(text) for m in PLAIN.finditer(plain)}
    assert found == seen


# Fragments a post might hold, each a mention or a near miss in some context
FRAGMENTS = [
    "Key results:", "Key figures for 2027-28:", "Some prose.", "## A heading", "- one", "- Key figures:",
    "  - Key figures:", "1. Key figures:", "  continued", "> Key figures:", "    Key figures:", "**Key figures:**",
    "[Key figures:](/x)", "<span>Key figures:</span>", "<code>Key figures:</code>", "K<b>ey</b> figures",
    "```\nKey figures:\n```", "`\nKey figures:\n`", "| Key figures: |\n|---|\n| x |", "![Key figures:](/c.png)",
    "", "Key  figures:", "Key\nfigures:", "Key&nbsp;figures:", "~~Key figures:~~",
    "```highlighted-block\nKey figures:\n&&&\nx\n```", "[^1]: Key figures:", "Text.[^1]", "- [x] Key figures:",
    "Key", "figures:", "<b>Key</b>", "<i>figures</i>", "<details><summary>Key</summary>figures</details>",
    '<abbr title="Key">k</abbr>', "## Key", "Ke", "y figures",
]


def independent_reading(markup):
    """Plain text of some HTML read without page_text: split at tags with a
    regular expression, drop attribute values and text a browser may hide,
    and draw every tag as nothing or every tag as a line break."""
    hidden, depth, texts = [], 0, []
    for tag, text in re.findall(r"(<[^>]*>)|([^<]+)", markup):
        if tag:
            closing, name = tag.startswith("</"), re.match(r"</?([a-z0-9]+)", tag).group(1)
            void = tag.endswith("/>") or name in explainers.VOID
            if closing:
                depth -= 1
                if hidden and hidden[-1] == depth:
                    hidden.pop()
            elif not void:
                if not hidden and (name == "details" or "sr-only" in tag or "opacity:0" in tag):
                    hidden.append(depth)
                depth += 1
            texts.append(None)
        elif not hidden:
            texts.append(explainers.visible(html.unescape(text)))
    return ["".join(t or "" for t in texts), "".join("\n" if t is None else t for t in texts)]


@settings(max_examples=150, deadline=None)
@given(st.lists(st.tuples(st.sampled_from(FRAGMENTS), st.sampled_from(["\n", "\n\n", " "])), max_size=8))
def test_page_text_keeps_every_mention_an_independent_reading_finds(parts):
    page = render(["".join(f + sep for f, sep in parts)])[0]
    for plain in independent_reading(page["html"]):
        assert mentions(page_text(page)) >= len(PLAIN.findall(plain))


@pytest.mark.parametrize("text", [
    SHOWN + "a key" + END + (BOUNDARY + MAYBE + " " + MAYBE_END) * 30 + BOUNDARY + SHOWN + "x" + END,
    BOUNDARY.join([SHOWN + "k" + END] * 20000),
    SHOWN + "key" + END + BOUNDARY * 200000,
    SHOWN + "key" + END + (BOUNDARY + MAYBE + "abc" + MAYBE_END) * 50000 + BOUNDARY + SHOWN + "x" + END,
    BOUNDARY.join([SHOWN + "key " + END, MAYBE + " " + MAYBE_END] * 20000),
])
def test_the_count_stays_quick_on_long_page_texts(text):
    start = time.perf_counter()
    assert mentions(text) == 0
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize("line", [
    'Key <a href="/x" title="Household income &gt; £100,000">figures</a>:',
    "[Key](https://example.org/report_(2026_(revised))) figures:",
    "[Key](/x\\(a) figures:",
])
def test_a_second_opening_in_a_footnote_stops_the_build(monkeypatch, line):
    # Sol review r10's reproductions, word for word
    post = f"Key results:\n\n- actual\n\n## More\n\nText.[^1]\n\n[^1]: First paragraph\n\n    {line}\n\n    More prose.\n"
    with pytest.raises(SystemExit, match="one place on the page, found 2"):
        quote(monkeypatch, post)


def test_a_post_the_renderer_cant_finish_stops_the_build(monkeypatch):
    # Unclosed comments slow micromark quadratically (Sol review r10)
    monkeypatch.setattr(explainers, "RENDER_SECONDS", 1)
    start = time.perf_counter()
    with pytest.raises(SystemExit, match="took over 1 seconds"):
        quote(monkeypatch, "Key results:\n\n- one\n\n" + "k<!--" * 12000 + "\n")  # over 10 seconds unchecked
    assert time.perf_counter() - start < 10
    monkeypatch.undo()
    assert count("Key figures\n") == 1  # a fresh renderer takes over


@pytest.mark.parametrize("text, message", [
    ("Key\nresults:\n\n- one\n", "paragraph on lines 1-2"),
    ("Our key\n\nfigures, and so on.\n\n- one\n", "hold the words, found 2"),  # the words across two blocks
    ("Some words before\nKey results:\n\n- one\n", "paragraph on lines 1-2"),  # a browser shows it as one line
    ("Some words before  \nKey results:\n\n- one\n", "paragraph on lines 1-2"),  # a hard break
    ("Key results: and more\n\n- one\n", "not one line that opens"),
    ("Our key results:\n\n- one\n", "not one line that opens"),
    ("Key results:<br>more:\n\n- one\n", "not one line that opens"),
    # Rendered alone, a reference link loses its definition and shows its brackets
    ("[Key results][x]:\n\n- one\n\n[x]: /x\n", "not one line that opens"),
    ("- Key results:\n\n  - one\n", "list on lines 1-3"),
    ("> Key results:\n>\n> - one\n", "blockquote on lines 1-3"),
    ("# Key results:\n\n- one\n", "heading on lines 1-1"),  # one line, but a heading
    ("> Key results:\n\n- one\n", "blockquote on lines 1-1"),
    ("No opening here.\n\n- one\n", "one place on the page, found 0"),
    ("Key results:\n\n- one\n\nKey figures for 2028:\n\n- two\n", "found 2"),
    ("Key results:\n\nA paragraph first.\n\n- one\n", "no bullet list"),
    ("Key results:\n\n1. numbered\n", "no bullet list"),
    ("Key results:\n", "no bullet list"),
])
def test_ambiguous_or_missing_structure_stops_the_build(monkeypatch, text, message):
    with pytest.raises(SystemExit, match=message):
        quote(monkeypatch, text)


def test_a_post_the_formatter_cant_render_stops_the_build(monkeypatch):
    monkeypatch.setattr(explainers, "render", lambda posts, display=None: [{"error": "TypeError: boom"}] * len(posts))
    with pytest.raises(SystemExit, match="can't render the post: TypeError: boom"):
        quote(monkeypatch, "Key results:\n\n- one\n")


def test_list_straight_after_the_opening_line(monkeypatch):
    assert quote(monkeypatch, "Key findings:\n- one\n- two\n") == "Key findings:\n\n- one\n- two"


def test_extra_paragraph(monkeypatch):
    text = "Key results:\n\n- one\n\nA paragraph\nover two lines.\n\nAnother.\n"
    assert quote(monkeypatch, text, 1) == "Key results:\n\n- one\n\nA paragraph\nover two lines."


@pytest.mark.parametrize("after", ["## Heading", "```chart\n{}\n```", "[A link](/x) opening a caption", "![image](/x.png)"])
def test_extra_paragraph_must_be_prose(monkeypatch, after):
    with pytest.raises(SystemExit, match="no plain paragraph"):
        quote(monkeypatch, f"Key results:\n\n- one\n\n{after}\n", 1)


@pytest.mark.parametrize("markup, lines", [
    ("<p>Key <b>figures</b>:</p>", ["Key figures:"]),
    ('<p>Key<span style="display:block">figures</span></p>', ["Key", "figures"]),
    ("<p>Key<br/>figures</p>", ["Key", "figures"]),
    ('<h2>Head<a style="opacity:0">#</a></h2>', ["Head"]),
    ("<details><summary>S</summary>D</details><p>shown</p>", ["shown"]),
    ("<p>K&shy;ey  \n figures</p>", ["Key figures"]),
])
def test_shown_lines(markup, lines):
    assert shown_lines(markup) == lines


@pytest.mark.parametrize("slug, extra", POSTS)
def test_saved_posts_quote_a_whole_list(slug, extra):
    header = explainers._header(slug)
    assert len(header) == 2 and all(header)  # the title and description
    assert mentions(page_text(render([explainers._text(slug)])[0], header)) == 1
    out = key_points(slug, extra)
    lines = out.split("\n")
    assert OPENING.match(lines[0]) and lines[1] == "" and lines[2].startswith("- ")
    assert "](/" not in out and "](#" not in out  # every link absolute
