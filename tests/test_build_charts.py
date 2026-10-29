"""The dashboard check on the explainer charts, and the fonts they draw with.

Invariants:
- A post value that rounds the artifact's to the post's precision always passes.
- A bar two or more of the post's last digits away from the artifact always fails;
  for unrounded data, any difference of 1e-6 or more fails.
- A withheld artifact value, or a post value with more decimals than CHARTS
  gives, fails.
- CHARTS gives each checked chart the precision its post's data carries.
- Inter resolves to pe-doc's own files even when the machine has another Inter.
"""

import csv
import tempfile
from pathlib import Path

import matplotlib
import pytest
from hypothesis import given
from hypothesis import strategies as st
from matplotlib import font_manager

import build_charts
from build_charts import CHARTS, check_deciles, decimals_of, setup_fonts
from explainers import chart_specs

DECILES = ["1st", "2nd", "3rd", "4th", "5th", "6th", "7th", "8th", "9th", "10th"]


def run(posted, artifact, decimals):
    """Check one posted series against artifact values (None = withheld), decile by decile."""
    spec = {"xKey": "decile", "data": [{"decile": d, "s": v} for d, v in zip(DECILES, posted)]}
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "m").mkdir()
        with open(Path(tmp) / "m" / "winners_losers.csv", "w", newline="") as f:
            w = csv.writer(f)
            w.writerow(["year", "decile", "avg_change"])
            for i, v in enumerate(artifact, start=1):
                w.writerow([2027, i, "" if v is None else repr(v)])
            w.writerow([2028, 1, "999"])  # another year's row, which the check must ignore
        return check_deciles(spec, [("s", "m", 2027)], tmp, decimals)


values = st.lists(st.floats(min_value=-500, max_value=500, allow_nan=False), min_size=10, max_size=10)
precision = st.sampled_from([0, 1, 2, 3])


@given(values, precision)
def test_true_rounding_always_passes(artifact, d):
    run([round(v, d) for v in artifact], artifact, d)


@given(values, precision, st.integers(0, 9), st.integers(2, 1000), st.sampled_from([-1, 1]))
def test_a_wrong_bar_always_fails(artifact, d, i, k, sign):
    posted = [round(v, d) for v in artifact]
    posted[i] = round(posted[i] + sign * k * 10 ** -d, d)
    with pytest.raises(SystemExit, match=f"decile {i + 1}"):
        run(posted, artifact, d)


@given(values)
def test_unrounded_data_must_match_exactly(artifact):
    run(list(artifact), artifact, None)


@given(values, st.integers(0, 9), st.floats(min_value=1e-6, max_value=100), st.sampled_from([-1, 1]))
def test_unrounded_data_fails_on_any_real_difference(artifact, i, delta, sign):
    posted = list(artifact)
    posted[i] += sign * delta
    with pytest.raises(SystemExit, match=f"decile {i + 1}"):
        run(posted, artifact, None)


def test_review_counterexample_fails():
    # Sol review r1: the property chart's 2031 top decile moved by £0.49 passed the old check
    artifact = [-2.0, -5.6, -6.3, -7.0, -8.0, -9.0, -10.0, -12.0, -20.0, -65.561265]
    posted = artifact[:9] + [-65.071265]
    with pytest.raises(SystemExit, match="decile 10"):
        run(posted, artifact, None)


def test_withheld_value_fails():
    with pytest.raises(SystemExit, match="withholds"):
        run([1] * 10, [1] * 9 + [None], 0)


def test_more_decimals_than_declared_fails():
    with pytest.raises(SystemExit, match="more than the 0 decimals"):
        run([1.4] + [1] * 9, [1.4] + [1] * 9, 0)


def test_decimals_of_ignores_trailing_zeros():
    assert [decimals_of(v) for v in (72, 72.0, 6.92, 6.920, 7.503, -0.849537805191413)] == [0, 0, 2, 2, 3, 15]


@pytest.mark.parametrize("name, slug, index, decimals, checks", [c for c in CHARTS if c[4]], ids=lambda c: c if isinstance(c, str) else None)
def test_charts_precision_matches_the_posts(name, slug, index, decimals, checks):
    data = chart_specs(slug)[index]["data"]
    seen = max(decimals_of(p[series]) for series, _, _ in checks for p in data)
    if decimals is None:
        assert seen > 3, f"{name}: CHARTS calls the data unrounded, but it has at most {seen} decimals"
    else:
        assert seen == decimals, f"{name}: CHARTS gives {decimals} decimals, the post's data has up to {seen}"


def test_bundled_inter_beats_an_installed_one(monkeypatch):
    # Two "Inter" entries ahead of the bundled ones, as an installed copy would be;
    # they point at DejaVu Sans so a wrong match is visible
    dejavu = str(Path(matplotlib.get_data_path()) / "fonts" / "ttf" / "DejaVuSans.ttf")
    impostors = [font_manager.FontEntry(fname=dejavu, name="Inter", weight=w, size="scalable") for w in (400, 700)]
    monkeypatch.setattr(font_manager.fontManager, "ttflist", impostors + list(font_manager.fontManager.ttflist))
    monkeypatch.setattr(matplotlib, "rcParams", matplotlib.rcParams.copy())
    setup_fonts()
    fonts = Path(build_charts.pe_doc.__file__).parent / "template" / "fonts"
    for weight, file in (("normal", "Inter-Regular.ttf"), ("bold", "Inter-Bold.ttf")):
        found = font_manager.findfont(font_manager.FontProperties(family="Inter", weight=weight), fallback_to_default=False)
        assert Path(found).resolve() == (fonts / file).resolve()
