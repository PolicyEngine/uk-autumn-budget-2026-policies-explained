"""key_points() quotes a whole bullet list, or stops the build.

Invariants:
- Every list item comes out whole, however the post wraps or spaces it.
- Nothing after the list comes out unless the template asks for paragraphs.
- The build stops if the opening line is missing, repeated anywhere the site
  shows prose (indented or not, however its whitespace runs, in an image
  caption, a highlighted block, a footnote or a task item), inside another
  paragraph, or not followed straight away by a bullet list. A line in code,
  a comment or a <template> is never an opening.

The expected outcomes here come from what the site's renderer
(policyengine-app-v2 MarkdownFormatter.tsx at 85571f7a3: react-markdown,
remark-gfm, rehype-raw, an image caption from the alt text, highlighted-block
fences rendered as Markdown) and a browser show, written out by hand.
"""

import pytest
from hypothesis import given
from hypothesis import strategies as st

import explainers
from explainers import OPENING, _markdown, _parse, key_points, shown_lines

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


@pytest.mark.parametrize("example", [
    "Example syntax:\n\n    Key figures:\n",  # indented code block (Sol review r3)
    "```text\nKey figures:\n```\n",  # fenced code
    "## More\n\n- An item\n\n  ```\n  Key figures:\n  ```\n",  # fence inside a later list's item
])
def test_an_opening_inside_code_is_not_an_opening(monkeypatch, example):
    out = quote(monkeypatch, f"Key results:\n\n- actual\n\n{example}")
    assert out == "Key results:\n\n- actual"


@pytest.mark.parametrize("example", [
    "Example: `\nKey figures:\n`\n",  # inline code over three lines (Sol review r4)
    "<pre>\nKey figures:\n</pre>\n",  # raw HTML code
    "<!--\nKey figures:\n-->\n",  # HTML comment, which the page doesn't show
    "Inline <code>Key figures:</code>\n",  # inline HTML code
    "<code>Key figures:</code>\n",  # inline HTML code that is the whole line
    "<code>\nKey figures:\n</code>\n",  # the same over three lines, an HTML block
    "<div><pre>\nKey figures:\n</pre></div>\n",  # code inside an HTML block
    "<template>\n\nKey figures:\n\n</template>\n",  # a paragraph a template holds (Sol review r5)
    "```text\nKey figures:\n&&&\nx\n```\n",  # only highlighted-block fences render as Markdown
])
def test_an_opening_the_page_shows_as_code_or_hides_is_not_an_opening(monkeypatch, example):
    assert quote(monkeypatch, f"Key results:\n\n- actual\n\n{example}") == "Key results:\n\n- actual"


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
])
def test_a_second_opening_anywhere_in_the_prose_stops_the_build(monkeypatch, second):
    with pytest.raises(SystemExit, match="found 2"):
        quote(monkeypatch, f"Key results:\n\n- actual\n\n## More\n\n{second}")


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
    "<template>\n\nKey figures:\n\n</template>",
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
