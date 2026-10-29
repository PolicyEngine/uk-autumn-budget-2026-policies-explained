"""key_points() quotes a whole bullet list, or stops the build.

Invariants:
- Every list item comes out whole, however the post wraps or spaces it.
- Nothing after the list comes out unless the template asks for paragraphs.
- The build stops unless the post's source mentions "Key results/figures/
  findings" exactly once, in any case or spacing, with entities decoded,
  invisible characters dropped and compatibility forms folded, and with any
  run of tags, comments, link destinations or Markdown marks inside a word or
  between the two. A second mention stops it wherever it sits: in prose,
  code, a comment, an attribute, a caption, a footnote or a highlighted
  block, shown or not. That is fail-safe by design: the build never has to
  decide what the site would show, and a person decides what to do with such
  a post.
- Any spelling of the words built from that markup counts exactly once
  (a property test), and the count stays quick on unclosed markup.
- It also stops unless the model of what the page shows (_parse) finds exactly
  one opening line, and unless that line is a top-level paragraph of its own
  with a bullet list straight after it.
- The guard targets accidents in posts we write ourselves, not deliberate
  disguise such as look-alike letters from another script.
"""

import time
from html import unescape

import pytest
from hypothesis import assume, given
from hypothesis import strategies as st

import explainers
from explainers import OPENING, _markdown, _parse, key_points, shown_lines, source_mentions, visible

POSTS = [
    ("budget-2026-energy-bills", 0),
    ("fuel-duty-cut-extension", 0),
    ("pension-tax-allowance", 0),
    ("carers-allowance-taper", 0),
    ("uk-autumn-budget-2026-property-income-tax", 1),
    ("uk-autumn-budget-2026-trading-allowance", 0),
]


def quote(monkeypatch, text, extra=0):
    monkeypatch.setattr(explainers, "_text", lambda slug: text)
    return key_points("test-post", extra)


def test_wrapped_items_come_out_whole(monkeypatch):
    out = quote(monkeypatch, "Intro.\n\nKey figures for 2027-28:\n\n- one\n  wrapped\n- two\nlazily continued\n- three\n\nAfter.\n")
    assert out == "Key figures for 2027-28:\n\n- one\n  wrapped\n- two\nlazily continued\n- three"


def test_items_apart_by_blank_lines_stay_one_list(monkeypatch):
    out = quote(monkeypatch, "Key results:\n\n- one\n\n- two\n\n  second paragraph of two\n\n- three\n\n## Next\n")
    assert out == "Key results:\n\n- one\n\n- two\n\n  second paragraph of two\n\n- three"


@pytest.mark.parametrize("indent", [" ", "  ", "   "])
def test_indented_opening_is_still_an_opening(monkeypatch, indent):
    assert quote(monkeypatch, f"{indent}Key results:\n\n- one\n") == "Key results:\n\n- one"


@pytest.mark.parametrize("indent", [" ", "  ", "   "])
def test_indented_second_opening_stops_the_build(monkeypatch, indent):
    # Sol review r2: Markdown reads both as openings, so the build must too
    with pytest.raises(SystemExit, match="found 2"):
        quote(monkeypatch, f"Key results:\n\n- first\n\n## Split\n\n{indent}Key figures:\n\n- second\n")


@pytest.mark.parametrize("second", [
    "Example syntax:\n\n    Key figures:\n",  # an indented code block (intended since r6; r3 had it pass)
    "```text\nKey figures:\n```\n",  # a fence
    "## More\n\n- An item\n\n  ```\n  Key figures:\n  ```\n",  # a fence inside a list item
    "Example: `\nKey figures:\n`\n",  # inline code over three lines
    "<pre>\nKey figures:\n</pre>\n",  # raw HTML code
    "<!--\nKey figures:\n-->\n",  # an HTML comment
    "Inline <code>Key figures:</code>\n",  # inline HTML code
    "<template>\n\nKey figures:\n\n</template>\n",  # a template
    "```text\nKey figures:\n&&&\nx\n```\n",  # a fence of another language
    '<img alt="Key figures:">\n',  # an image the site drops, since it has no source (Sol review r7)
    "[ ] Key figures:\n",  # a literal marker outside a list (Sol review r7)
    "[^9]: Key figures:\n",  # a footnote nothing references (Sol review r7)
    "Text.[^1]\n\n[^1]: First paragraph\n\n    Key [figures](/x):\n\n    More prose.\n",  # linked words in a footnote (Sol review r9)
    "Key <code>figures</code>:\n",  # inline code inside the opening (Sol review r9)
    "~Key [figures](/x):~\n",  # a link inside strikethrough (Sol review r9)
    "```highlighted-block\n<template>\n&&&\nKey [figures](/x):\n```\n",  # a linked opening beside a broken pane (Sol review r9)
])
def test_a_second_mention_the_page_may_hide_still_stops_the_build(monkeypatch, second):
    # Fail-safe: the build doesn't decide whether the site shows these
    with pytest.raises(SystemExit, match="once in the source, found 2"):
        quote(monkeypatch, f"Key results:\n\n- actual\n\n{second}")


@pytest.mark.parametrize("second", [
    "- item\n\n  Key figures:\n\n  - nested\n",  # a paragraph inside a list item
    "- Key figures:\n",  # a list item itself (Sol review r4)
    "> Key figures:\n",  # a quote (Sol review r4)
    "**Key figures:**\n",  # formatting around it
    "<div>\nKey figures:\n</div>\n",  # an HTML block the page shows as text
    "| Key figures: |\n|---|\n| x |\n",  # a table cell
    "Key  figures:\n",  # two spaces, which a browser collapses (Sol review r5)
    "Key\tfigures:\n",  # a tab
    "Key\nfigures:\n",  # a soft break, which a browser shows as a space
    "Key&nbsp;figures:\n",  # a no-break space
    "![Key figures:](/chart.png)\n",  # the site shows alt text as a caption (Sol review r5)
    "```highlighted-block\nKey figures:\n\n- second\n&&&\nMore detail\n```\n",  # rendered as Markdown (Sol review r5)
    "```highlighted-block\nOne pane only\n\nKey figures:\n```\n",  # a malformed block renders as one pane
    "~~Key figures:~~\n",  # GFM strikethrough still shows the words
    "Text.[^1]\n\n[^1]: Key figures:\n",  # a GFM footnote shows its text
    "- [ ] Key figures:\n",  # a GFM task item shows a checkbox, then the words
    "```highlighted-block\n<template>\n&&&\nKey figures:\n```\n",  # each pane renders on its own (Sol review r7)
    "<div><pre>not closed</div>\n\nKey figures:\n",  # after broken HTML (Sol review r7)
    "```highlighted-block caption\nKey figures:\n```\n",  # the language is the info string's first word (Sol review r7)
    '<code class="language-highlighted-block">Key figures:</code>\n',  # the site renders this class as prose (Sol review r7)
    "~Key figures:~\n",  # GFM's single-tilde strikethrough (Sol review r7)
    "Text.[^1]\n\n[^1]: First paragraph\n\n    Key figures:\n",  # a footnote's second paragraph (Sol review r7)
    "<dl>\n<dt>Other</dt>\n<dd>Key figures:</dd>\n</dl>\n",  # a definition (Sol review r7)
    "<figure>\nText\n<figcaption>Key figures:</figcaption>\n</figure>\n",  # a figure caption (Sol review r7)
    "&#75;ey figures:\n",  # an entity
    "K*ey* figures:\n",  # emphasis inside a word
    "K<b>ey</b> figures:\n",  # a tag inside a word
    "K&shy;ey figures:\n",  # invisible characters inside a word (Sol review r9)
    "K\u00adey figures:\n",
    "K\u200bey figures:\n",
    "K\u2060ey figures:\n",
    "K\ufeffey figures:\n",
    "K&#8203;ey figures:\n",
    "K&#x2060;ey figures:\n",
    "_Key figures:_\n",  # underscores for italics
    "Ｋｅｙ ｆｉｇｕｒｅｓ:\n",  # full-width letters
    "Key ﬁgures:\n",  # a ligature
    "![KEY&nbsp;FINdi  \nngs:](/x.png)\n",  # an image's alt text drops a hard line break (site-renderer check)
])
def test_a_second_opening_anywhere_in_the_prose_stops_the_build(monkeypatch, second):
    with pytest.raises(SystemExit, match="found 2"):
        quote(monkeypatch, f"Key results:\n\n- actual\n\n## More\n\n{second}")


def rendered_count(text):
    """Openings in the page model alone, without the source count."""
    return sum(bool(OPENING.match(line.strip())) for _, line in _parse(text)[1])


@pytest.mark.parametrize("text", [
    "<dl>\n<dt>Other</dt>\n<dd>Key figures:</dd>\n</dl>\n",  # a regression in e4ff293 (Sol review r7)
    "<figure>\nText\n<figcaption>Key figures:</figcaption>\n</figure>\n",
    "K<b>ey</b> figures:\n",
    "![Key figures:](/chart.png)\n",  # the site shows alt text as a caption
    "```highlighted-block caption\nKey figures:\n```\n",
    "K&shy;ey figures:\n",  # the page model drops invisible characters too (Sol review r9)
    "K\u200bey figures:\n",
    "K&#xFEFF;ey figures:\n",
    "Ｋｅｙ ｆｉｇｕｒｅｓ:\n",
    "Key ﬁgures:\n",
])
def test_the_page_model_shows_an_opening_on_a_line_of_its_own(text):
    assert rendered_count(text) == 1


@pytest.mark.parametrize("text", ['<img alt="Key figures:">\n', '<img src="" alt="Key figures:">\n', "```text\nKey figures:\n```\n"])
def test_the_page_model_hides_what_the_site_hides(text):
    assert rendered_count(text) == 0


@pytest.mark.parametrize("text", [
    "Key figures", "KEY FIGURES", "key results", "Key\tfindings", "Key\nfigures", "&#75;ey figures", "K*ey* figures",
    "Key_ _figures", "`Key` figures", "Key \\figures", "_Key figures_", "__Key__ figures",
    "Key [figures](/x)", "K[ey](/x(y)) figures", "K[ey][1] figures", "Key <code>figures</code>", "Key</b> <b>figures",
    "K<!-- -->ey figures", "K<!-- a -> b -->ey figures", "K&shy;ey figures", "K\u00adey figures", "K\u200bey figures", "K\u2060ey figures",
    "K\ufeffey figures", "K&#8203;ey figures", "K&#x200B;ey figures", "K&zwj;ey figures", "Key\u00a0figures",
    "Ｋｅｙ ｆｉｇｕｒｅｓ", "Key ﬁgures", "Key findi  \nngs", "Key fig\\\nures",
])
def test_the_source_count_sees_any_spelling_of_the_words(text):
    assert source_mentions(text) == 1


@pytest.mark.parametrize("text", ["Keyfigures", "Key figure", "Monkey figures", "Key resultsx", "AKey figures", "Key figures2"])
def test_the_source_count_ignores_other_words(text):
    assert source_mentions(text) == 0


@pytest.mark.parametrize("text", ["K<!-- Key figures -->ey figures", '<b title="Key figures">Key figures</b>',
                                  'K<b title="Key figures">ey figures'])
def test_a_mention_inside_markup_another_mention_spans_counts_too(text):
    assert source_mentions(text) == 2


# Markup that can sit inside or between the words, as a post might write it
MARKS = ["*", "_", "~", "`", "\\", "[", "]", "<b>", "</span>", '<a href="/x">', "<!-- note -->", "](/x)", "](/x(y))",
         "][1]", "  \n", "\\\n", "\u00ad", "\u200b", "\u2060", "\ufeff", "&shy;", "&#8203;", "&#x2060;", "&zwj;"]
SPACES = [" ", "\t", "\n", "&nbsp;", "\u00a0", "\u2003"]
# What can part the two words: an invisible character alone shows them as one word
GAPS = SPACES + [m for m in MARKS if visible(unescape(m))]


@st.composite
def disguised(draw):
    """The opening's words in any case, with marks inside each word, around them, and in a gap between them."""
    def marks(options, **size):
        return "".join(draw(st.lists(st.sampled_from(options), **size)))

    def spell(word):
        return marks(MARKS, max_size=2).join(draw(st.sampled_from([c.lower(), c.upper()])) for c in word)

    second = draw(st.sampled_from(["results", "figures", "findings"]))
    gap = marks(MARKS, max_size=1) + draw(st.sampled_from(GAPS)) + marks(SPACES + MARKS, max_size=2)
    return marks(MARKS, max_size=2) + spell("key") + gap + spell(second) + marks(MARKS, max_size=2)


@given(disguised())
def test_any_spelling_built_from_markup_counts_once(words):
    # A lone "]" then "[" opens a reference link's label, which hides the
    # letters it holds or shows them in brackets: either way not the words
    assume("][" not in words.replace("][1]", ""))
    assert source_mentions(f"Some prose. {words} More prose.") == 1


@pytest.mark.parametrize("text", ["k<!--" * 20000, "key <!--" * 20000, "k](x" * 20000, "k][x" * 20000,
                                  "k" + "<!---->" * 20000 + "x", "k" + "[" * 20000 + "x", "key" + " *" * 20000 + "x"])
def test_the_source_count_stays_quick_on_unclosed_markup(text):
    start = time.perf_counter()
    assert source_mentions(text) == 0
    assert time.perf_counter() - start < 5


@pytest.mark.parametrize("text", ["~~Key figures:~~\n", "Key&nbsp;figures:\n", "Key  figures:\n",
                                  "Key &nbsp;figures:\n"])  # a browser keeps both spaces of the last
def test_the_page_model_reads_gfm_and_spacing_as_shown(text):
    assert rendered_count(text) == 1


def test_both_nets_see_a_word_split_by_a_tag(monkeypatch):
    text = "Key results:\n\n- actual\n\nK<b>ey</b> figures:\n"
    assert source_mentions(text) == 2 and rendered_count(text) == 2
    with pytest.raises(SystemExit, match="once in the source, found 2"):
        quote(monkeypatch, text)


def test_the_page_model_count_stops_a_post_whose_one_mention_isnt_a_line_of_its_own(monkeypatch):
    # The source count passes this; only the page model sees that no line opens with the words
    text = "Some words before\nKey results:\n\n- one\n"
    assert source_mentions(text) == 1
    with pytest.raises(SystemExit, match="line, found 0"):
        quote(monkeypatch, text)


@pytest.mark.parametrize("text", ["- Key results:\n\n  - one\n", "> Key results:\n>\n> - one\n"])
def test_a_sole_opening_inside_a_container_stops_the_build(monkeypatch, text):
    with pytest.raises(SystemExit, match="paragraph of its own"):
        quote(monkeypatch, text)


def test_list_straight_after_the_opening_line(monkeypatch):
    assert quote(monkeypatch, "Key findings:\n- one\n- two\n") == "Key findings:\n\n- one\n- two"


def test_extra_paragraph(monkeypatch):
    text = "Key results:\n\n- one\n\nA paragraph\nover two lines.\n\nAnother.\n"
    assert quote(monkeypatch, text, 1) == "Key results:\n\n- one\n\nA paragraph\nover two lines."


@pytest.mark.parametrize("after", ["## Heading", "```chart\n{}\n```", "[A link](/x) opening a caption", "![image](/x.png)"])
def test_extra_paragraph_must_be_prose(monkeypatch, after):
    with pytest.raises(SystemExit, match="no plain paragraph"):
        quote(monkeypatch, f"Key results:\n\n- one\n\n{after}\n", 1)


@pytest.mark.parametrize("text, message", [
    ("No opening here.\n\n- one\n", "found 0"),
    ("Key results:\n\n- one\n\nKey figures for 2028:\n\n- two\n", "found 2"),
    ("Some words before\nKey results:\n\n- one\n", "found 0"),  # a browser shows it as one line
    ("Some words before  \nKey results:\n\n- one\n", "paragraph of its own"),  # a hard break
    ("Key results:\n\nA paragraph first.\n\n- one\n", "no bullet list"),
    ("Key results:\n\n1. numbered\n", "no bullet list"),
    ("Key results:\n", "no bullet list"),
])
def test_ambiguous_or_missing_structure_stops_the_build(monkeypatch, text, message):
    with pytest.raises(SystemExit, match=message):
        quote(monkeypatch, text)


@pytest.mark.parametrize("slug, extra", POSTS)
def test_saved_posts_quote_a_whole_list(slug, extra):
    assert source_mentions(explainers._text(slug)) == 1
    out = key_points(slug, extra)
    lines = out.split("\n")
    assert explainers.OPENING.match(lines[0]) and lines[1] == "" and lines[2].startswith("- ")
    assert "](/" not in out and "](#" not in out  # every link absolute


# Fragments a post might hold, each an opening or a near miss in some context
FRAGMENTS = [
    "Key results:", "Key figures for 2027-28:", "Key findings: and more", "Some prose.", "## A heading",
    "- one", "- Key figures:", "  - Key figures:", "1. Key figures:", "  continued", "> Key figures:",
    "   Key figures:", "    Key figures:", "**Key figures:**", "[Key figures:](/x)", "<span>Key figures:</span>",
    "<code>Key figures:</code>", "<em>Key figures:</em>", "Inline <code>Key figures:</code>",
    "```\nKey figures:\n```", "~~~\nKey figures:\n~~~", "`\nKey figures:\n`",
    "| Key figures: |\n|---|\n| x |", "![Key figures:](/c.png)", "",
    "Key  figures:", "Key\tfigures:", "Key\nfigures:", "Key&nbsp;figures:", "~~Key figures:~~",
    "```highlighted-block\nKey figures:\n&&&\nx\n```", "```highlighted-block\n- Key figures:\n```",
    "[^1]: Key figures:", "- [x] Key figures:",
]
# Raw HTML split over lines stands in a block of its own: a table or list that
# absorbed it would leave its tags unbalanced inside a cell or item, where what
# shows depends on browsers' repair rules, and posts don't do that
FRAGMENTS += [f"\n{html}\n" for html in [
    "<code>\nKey figures:\n</code>", "<pre>\nKey figures:\n</pre>", "<div>\nKey figures:\n</div>",
    "<div><pre>\nKey figures:\n</pre></div>", "<!--\nKey figures:\n-->",
]]


def rendered_openings(text):
    """Reference count: render the whole post to HTML, then read what the page shows."""
    return sum(bool(OPENING.match(line.strip())) for line in shown_lines(_markdown().render(text)))


@given(st.lists(st.tuples(st.sampled_from(FRAGMENTS), st.sampled_from(["\n", "\n\n"])), max_size=8))
def test_opening_count_matches_the_rendered_page(parts):
    # Differential: the block-by-block count key_points uses agrees with
    # rendering the whole post and counting what a browser shows
    text = "".join(f + sep for f, sep in parts)
    _, prose = _parse(text)
    assert sum(bool(OPENING.match(line.strip())) for _, line in prose) == rendered_openings(text)
