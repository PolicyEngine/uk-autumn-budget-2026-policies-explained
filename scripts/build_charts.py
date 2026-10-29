"""Draw one chart from each explainer for the PDF, as SVG in document/charts/.

Each chart is the explainer's own published chart: the JSON spec in its
```chart block (sources/posts/), drawn here with matplotlib in the
PolicyEngine palette and pe-doc's Inter, with text as outlines so it looks the
same on every machine. Where a chart shows the dashboard's results (the income
decile charts), the build checks every bar against the dashboard artifact it
uses, and stops if one differs by more than the post's data rounds.

document/charts/charts.json records each chart's post, block and checks.

  build_charts.py --artifacts .cache/artifacts --out document/charts
"""

import argparse
import csv
import hashlib
import json
import sys
import textwrap
from decimal import Decimal
from pathlib import Path

import matplotlib

matplotlib.use("svg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402

import pe_doc  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))  # python -I leaves out the script's folder
from explainers import POSTS, adapt, chart_specs  # noqa: E402

# (output name, post slug, chart block index, data decimals, dashboard checks)
# A check is (series key, artifact key, year): the series' value for each
# decile must match that artifact's winners_losers.csv avg_change to the
# precision the post's data carries. Data decimals gives that precision: the
# post rounds its values to that many places, or None if it keeps them unrounded.
CHARTS = [
    ("energy-bills-deciles", "budget-2026-energy-bills", 0, 0,
     [("payment", "household_energy_payment_2026", 2026), ("vat", "domestic_electricity_zero_vat", 2026)]),
    ("fuel-duty-deciles", "fuel-duty-cut-extension", 2, 3,
     [("y2026", "fuel_duty_rise_deferral", 2026), ("y2027", "fuel_duty_rise_deferral", 2027)]),
    ("pension-tax-allowance-income-tax", "pension-tax-allowance", 1, None, []),
    ("carers-allowance-by-pay", "carers-allowance-taper", 0, None, []),
    ("property-income-deciles", "uk-autumn-budget-2026-property-income-tax", 0, None,
     [("y2027", "property_income_rates_up", 2027), ("y2031", "property_income_rates_up", 2031)]),
    ("trading-allowance-receipts", "uk-autumn-budget-2026-trading-allowance", 0, None, []),
]

# Room for binary floating point when two decimal strings name the same number
EPSILON = 1e-9

# The posts name colours by role; these are the PolicyEngine ui-kit values
COLOURS = {
    "primary": "#319795",  # teal-500
    "secondary": "#285E61",  # teal-700
    "tertiary": "#81E6D9",  # teal-200
    "quaternary": "#2C7A7B",  # teal-600
    "quinary": "#94A3B8",  # gray-400
    "negative": "#D97706",  # the dashboard's loss colour (chartTheme.js)
}
INK, MUTED, GRID, ZERO = "#101828", "#64748B", "#E2E8F0", "#475569"

# A chart's source that points further down its post, marked as explainers.ADAPTATIONS are
SOURCE_ADAPTATIONS = {
    "carers-allowance-taper": [("described below", "described [in the explainer]")],
}


def setup_fonts():
    """Draw with pe-doc's own Inter files, whatever fonts the machine has."""
    fonts = Path(pe_doc.__file__).parent / "template" / "fonts"
    files = {"normal": fonts / "Inter-Regular.ttf", "bold": fonts / "Inter-Bold.ttf"}
    # An installed Inter would tie with the bundled one on family name, and
    # matplotlib keeps the first of equal matches; drop it, so glyphs and
    # layout come out the same on every machine
    manager = font_manager.fontManager
    manager.ttflist = [f for f in manager.ttflist if f.name != "Inter"]
    for path in files.values():
        manager.addfont(str(path))  # also clears matplotlib's font lookup cache
    for weight, path in files.items():
        found = font_manager.findfont(font_manager.FontProperties(family="Inter", weight=weight), fallback_to_default=False)
        if Path(found).resolve() != path.resolve():
            raise SystemExit(f"Inter {weight} resolves to {found}, not pe-doc's {path}")
    plt.rcParams.update({
        "font.family": "Inter",
        "font.size": 8,
        "svg.fonttype": "path",
        "svg.hashsalt": "policies-explained",
        "axes.edgecolor": GRID,
        "axes.labelcolor": MUTED,
        "xtick.color": MUTED,
        "ytick.color": MUTED,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def money(fmt):
    prefix, decimals, sep = fmt.get("prefix", ""), fmt.get("decimals", 0), fmt.get("separator", False)

    def f(v, _pos=None):
        sign = "−" if v < 0 else ""
        body = f"{abs(v):,.{decimals}f}" if sep else f"{abs(v):.{decimals}f}"
        return f"{sign}{prefix}{body}"

    return f


def decile_label(d):
    return str(d).rstrip("stndrdth") or str(d)


def decimals_of(value):
    """Decimal places a number carries, trailing zeros aside (72.0 has none, 6.920 two)."""
    return max(0, -Decimal(str(value)).normalize().as_tuple().exponent)


def tolerance(decimals):
    """How far a posted value may sit from the artifact's: half its last digit, or none if unrounded."""
    return (0.5 * 10 ** -decimals if decimals is not None else 0) + EPSILON


def check_deciles(spec, checks, artifacts, decimals):
    """Check every bar of each checked series against the artifact; return what the check covered."""
    done = []
    for series, key, year in checks:
        rows = {r["decile"]: r["avg_change"] for r in csv.DictReader(open(Path(artifacts) / key / "winners_losers.csv")) if int(r["year"]) == year}
        for point in spec["data"]:
            d = decile_label(point[spec["xKey"]])
            posted, art = point[series], rows.get(d)
            if art in (None, ""):
                raise SystemExit(f"{key} {year} decile {d}: the artifact withholds it, the post shows {posted}")
            # A post that carries more places than CHARTS says would loosen the check
            if decimals is not None and decimals_of(posted) > decimals:
                raise SystemExit(f"{key} {year} decile {d}: post {posted} has more than the {decimals} decimals CHARTS gives")
            if abs(float(posted) - float(art)) > tolerance(decimals):
                raise SystemExit(f"{key} {year} decile {d}: post {posted} vs artifact {art}")
        done.append({"series": series, "artifact": f"{key}/winners_losers.csv", "year": year, "deciles": len(spec["data"]),
                     "precision": "unrounded" if decimals is None else f"{decimals} decimals"})
    return done


def draw(spec, path, slug):
    fmt, xfmt = spec.get("format", {}), spec.get("xFormat")
    src = None
    if spec.get("source"):
        src = adapt(spec["source"], slug, SOURCE_ADAPTATIONS.get(slug, []))
        src = textwrap.fill(src if src.startswith("Source") else f"Source: {src}", 150)
    fig, ax = plt.subplots(figsize=(6.7, 3.0))
    # Each extra line of source takes room from the plot
    fig.subplots_adjust(left=0.1, right=0.96, top=0.76, bottom=0.2 + 0.035 * (src.count("\n") if src else 0))
    series, data, xkey = spec["series"], spec["data"], spec["xKey"]

    if spec["type"] == "bar":
        n, width = len(series), 0.8 / len(series)
        xs = list(range(len(data)))
        labels = spec.get("valueLabels", True) is not False
        for j, s in enumerate(series):
            offs = [x - 0.4 + width * (j + 0.5) for x in xs]
            vals = [float(p[s["key"]]) for p in data]
            bars = ax.bar(offs, vals, width * 0.92, color=COLOURS[s.get("color", "primary")], label=s["name"], zorder=2)
            if labels:
                for b, v in zip(bars, vals):
                    ax.annotate(money(fmt)(v), (b.get_x() + b.get_width() / 2, v), xytext=(0, 2 if v >= 0 else -2),
                                textcoords="offset points", ha="center", va="bottom" if v >= 0 else "top", fontsize=6, color=INK)
        ax.set_xticks(xs, [decile_label(p[xkey]) for p in data])
        ax.set_xlabel(spec.get("xLabel", "Income decile (1 = lowest)"))
        ax.axhline(0, color=ZERO, linewidth=0.8, zorder=3)
        ax.tick_params(axis="x", length=0)
    else:
        xs = [p[xkey] for p in data]
        for s in series:
            ax.plot(xs, [p[s["key"]] for p in data], color=COLOURS[s.get("color", "primary")], linewidth=1.8, label=s["name"], zorder=3)
        if xfmt:
            ax.xaxis.set_major_formatter(FuncFormatter(money(xfmt)))
        ax.set_xlabel(spec.get("xLabel", ""))
        x0, x1 = min(xs), max(xs)
        ax.set_xlim(x0, x1)
        markers = spec.get("markers", [])
        if markers:
            # A band above the data for the marker labels
            lo, hi = ax.get_ylim()
            ax.set_ylim(lo, hi + 0.3 * (hi - lo))
        top = ax.get_ylim()[1]
        for k, m in enumerate(markers):
            ax.axvline(m["x"], color=COLOURS["quinary"], linewidth=0.8, linestyle=(0, (3, 2)), zorder=1)
            # Alternate heights so neighbouring labels don't overlap; a label
            # reads leftwards from its line only if it can't fit to the right
            pos = ax.get_position()
            room = ((x1 - m["x"]) / (x1 - x0) * pos.width + (1 - pos.x1)) * fig.get_figwidth() * 72
            right = len(m["label"]) * 6.5 * 0.55 + 3 > room
            ax.annotate(m["label"], (m["x"], top), xytext=(-3 if right else 3, -4 - 10 * (k % 2)), textcoords="offset points",
                        ha="right" if right else "left", va="top", fontsize=6.5, color=MUTED)

    ax.yaxis.set_major_formatter(FuncFormatter(money(fmt)))
    ax.set_ylabel(spec.get("yLabel", ""))
    ax.grid(axis="y", color=GRID, linewidth=0.6, zorder=0)
    ax.set_axisbelow(True)
    fig.text(0.01, 0.97, spec["title"], fontsize=9.5, fontweight="bold", color=INK, va="top")
    if spec.get("subtitle"):
        fig.text(0.01, 0.89, spec["subtitle"], fontsize=7.5, color=MUTED, va="top")
    if len(series) > 1:
        fig.legend(loc="upper right", bbox_to_anchor=(0.98, 0.9), ncol=len(series), frameon=False, fontsize=7, handlelength=1.2)
    if src:
        fig.text(0.01, 0.012, src, fontsize=6, color=MUTED, va="bottom", linespacing=1.3)
    fig.savefig(path, format="svg", metadata={"Date": None})
    plt.close(fig)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    setup_fonts()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    sha = (POSTS / "APP_V2_MAIN_SHA").read_text().strip()
    record = []
    for name, slug, index, decimals, checks in CHARTS:
        spec = chart_specs(slug)[index]
        checked = check_deciles(spec, checks, a.artifacts, decimals)
        draw(spec, out / f"{name}.svg", slug)
        record.append({
            "chart": f"{name}.svg", "post": f"{slug}.md", "app_v2_main": sha, "block": index, "title": spec["title"],
            "post_sha256": hashlib.sha256((POSTS / f"{slug}.md").read_bytes()).hexdigest()[:16],
            "dashboard_checks": checked,
        })
        print(f"{name}.svg: {slug} block {index}" + (f", {len(checked)} series checked against the dashboard" if checked else ""))
    (out / "charts.json").write_text(json.dumps(record, indent=1, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
