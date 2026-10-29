"""key_points() quotes a whole bullet list, or stops the build.

Invariants:
- Every list item comes out whole, however the post wraps or spaces it.
- Nothing after the list comes out unless the template asks for paragraphs.
- The build stops if the opening line is missing, repeated (indented or not),
  inside another paragraph, or not followed straight away by a bullet list.
"""

import pytest

import explainers
from explainers import key_points

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
    ("Some words before\nKey results:\n\n- one\n", "paragraph of its own"),
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
