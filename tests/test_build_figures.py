"""The sentence after the combined figure reads as a sentence, and the saved artifacts match the manifest."""

import hashlib
import json
import re
import shutil
from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st

from build_figures import canonical, load_dashboard, signoff

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = (ROOT / "template.md").read_text()
MANIFEST = ROOT / "sources" / "manifest-rev17.json"
ARTIFACTS = ROOT / "sources" / "artifacts-rev17"
KEY = "trading_allowance_raise"
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


def json_values():
    leaves = st.none() | st.booleans() | st.integers(-(2**53) + 1, 2**53 - 1) | st.text()
    return st.recursive(leaves, lambda v: st.lists(v, max_size=4) | st.dictionaries(st.text(), v, max_size=4), max_leaves=12)


def without_null_members(value):
    if isinstance(value, dict):
        return {k: without_null_members(v) for k, v in value.items() if v is not None}
    if isinstance(value, list):
        return [without_null_members(v) for v in value]
    return value


@given(json_values())
def test_canonical_json_reads_back_without_null_members(value):
    assert json.loads(canonical(value)) == without_null_members(value)


@given(st.dictionaries(st.text(), st.integers(-(2**53) + 1, 2**53 - 1), max_size=6))
def test_canonical_json_ignores_key_order(value):
    assert canonical(dict(reversed(value.items()))) == canonical(value)


@pytest.mark.parametrize("number", [0.5, 1.0, 2**53, -(2**53)])
def test_canonical_json_stops_on_numbers_it_cannot_write(number):
    with pytest.raises(SystemExit, match="canonical"):
        canonical({"a": [number]})


def test_canonical_json_sorts_keys_as_rfc_8785_does():
    keys = ["\u20ac", "\r", "\ufb33", "1", "\U0001f600", "\u0080", "\u00f6"]
    written = json.loads(canonical({key: 0 for key in keys}))
    assert list(written) == ["\r", "1", "\u0080", "\u00f6", "\u20ac", "\U0001f600", "\ufb33"]


def test_every_saved_artifact_matches_the_manifest():
    _, loaded = load_dashboard(MANIFEST, ARTIFACTS)
    assert len(loaded) == 8


@pytest.fixture
def saved(tmp_path):
    """One saved artifact, its copy free to change, and a manifest that lists only it."""
    shutil.copytree(ARTIFACTS / KEY, tmp_path / KEY)
    manifest = {"measures": {KEY: json.loads(MANIFEST.read_text())["measures"][KEY]}, "combined": {}}
    (tmp_path / "manifest.json").write_text(json.dumps(manifest))
    return tmp_path


def test_a_changed_file_stops_the_build(saved):
    with open(saved / KEY / "budgetary_impact.csv", "a") as f:
        f.write("\n")
    with pytest.raises(SystemExit, match="digest"):
        load_dashboard(saved / "manifest.json", saved)


def test_a_changed_file_stops_the_build_when_its_receipt_agrees(saved):
    table = saved / KEY / "budgetary_impact.csv"
    with open(table, "a") as f:
        f.write("\n")
    receipt = json.loads((saved / KEY / "receipt.json").read_text())
    receipt["dashboard"]["files"][table.name] = hashlib.sha256(table.read_bytes()).hexdigest()
    (saved / KEY / "receipt.json").write_text(json.dumps(receipt))
    with pytest.raises(SystemExit, match="manifest"):
        load_dashboard(saved / "manifest.json", saved)
