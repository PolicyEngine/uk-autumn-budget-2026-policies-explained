"""The sentence after the combined figure reads as a sentence whether or not both have signed."""

import re
from pathlib import Path

import pytest

from build_figures import signoff

TEMPLATE = (Path(__file__).resolve().parent.parent / "template.md").read_text()
PROVISIONAL = " The combined figure is provisional and may change."


def test_a_signed_run_adds_nothing():
    assert signoff({"checker": "first", "second": "second"}) == ""


@pytest.mark.parametrize("attestation", [
    None,
    {},
    {"checker": "first"},
    {"checker": "first", "second": ""},
    {"checker": "first", "second": None},
    {"checker": "PREVIEW ONLY", "second": "second"},
    {"checker": "first", "second": "PREVIEW ONLY: not signed"},
])
def test_an_unsigned_run_says_the_figure_may_change(attestation):
    assert signoff(attestation) == PROVISIONAL


def test_the_template_puts_the_placeholder_straight_after_a_full_stop():
    places = re.findall(r"(.)\{\{signoff:", TEMPLATE)
    assert places == ["."]


@pytest.mark.parametrize("attestation, sentence", [
    ({"checker": "first", "second": "second"}, "still in force."),
    ({}, "still in force. The combined figure is provisional and may change."),
])
def test_the_filled_line_reads_as_sentences(attestation, sentence):
    line = next(line for line in TEMPLATE.splitlines() if "{{signoff:" in line)
    filled = re.sub(r"\{\{signoff:[^}]+\}\}", signoff(attestation), line)
    assert filled.endswith(sentence)


def test_the_briefing_compares_the_budget_with_nothing_we_expected():
    assert not re.search(r"\bour list\b|\bon the list\b|pre-Budget list|\bodds\b|we had (expected|listed)|\.badge|\.prev\b", TEMPLATE, re.I)
