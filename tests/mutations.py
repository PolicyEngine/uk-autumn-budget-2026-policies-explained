"""Mutation check for the build scripts' tests.

Each mutation below breaks one rule the tests claim to hold. The script applies
each in a fresh copy of the repo, runs the tests there with a fixed Hypothesis
seed, and prints how many tests fail. Every mutation must fail at least one
test; the script exits 1 if any survives or no longer applies.

    uv run python tests/mutations.py

pytest doesn't collect this file, since its name doesn't start with test_.
"""

import re
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CHARTS = "scripts/build_charts.py"
EXPLAINERS = "scripts/explainers.py"
RENDER = "site/render.tsx"
CHART = "site/vendor/components/blog/LazyBlogChart.tsx"
PLOT = "site/vendor/components/blog/LazyPlot.tsx"

# (what the mutation breaks, file, [(text, replacement), ...]); each text must occur once
MUTATIONS = [
    ("A flat £0.50 tolerance, the old check's floor", CHARTS,
     [("return (0.5 * 10 ** -decimals if decimals is not None else 0) + EPSILON", "return 0.5 + EPSILON")]),
    ("No font filter", CHARTS,
     [('manager.ttflist = [f for f in manager.ttflist if f.name.casefold() != "inter"]', "manager.ttflist = list(manager.ttflist)")]),
    ("A case-sensitive font filter", CHARTS, [('f.name.casefold() != "inter"', 'f.name != "Inter"')]),
    # What the build reads
    ("No HTML allowlist", EXPLAINERS, [('if problem := _unreadable(page["elements"]):', "if problem := None:")]),
    ("The allowlist ignores tags", EXPLAINERS, [('if e["tag"] not in TAGS or extra or classes:', "if extra or classes:")]),
    ("The allowlist ignores properties", EXPLAINERS,
     [('extra = set(e["props"]) - PROPERTIES["*"] - PROPERTIES.get(e["tag"], set())', "extra = set()")]),
    ("The allowlist ignores classes", EXPLAINERS,
     [('classes = [c for c in e["classes"] if c not in CLASSES and not c.startswith("language-")]', "classes = []")]),
    ("Nested panes left out of the allowlist", RENDER, [("elements: seen.flatMap(elements) }", "elements: elements(markdown) }")]),
    ("No contents sidebar", RENDER, [("return { html, blocks, contents: contents(markdown),", "return { html, blocks, contents: [],")]),
    ("No bidirectional override check", EXPLAINERS, [("    if BIDI.search(text):\n", "    if False:\n")]),
    ("Page text without visible()", EXPLAINERS, [("    text = visible(text)\n", "    pass\n")]),
    ("visible() keeping invisible characters", EXPLAINERS,
     [('return CONTROL.sub("", IGNORABLE.sub("", unicodedata.normalize("NFKC", text)))', 'return CONTROL.sub("", unicodedata.normalize("NFKC", text))')]),
    ("visible() without NFKC", EXPLAINERS,
     [('return CONTROL.sub("", IGNORABLE.sub("", unicodedata.normalize("NFKC", text)))', 'return CONTROL.sub("", IGNORABLE.sub("", text))')]),
    ("visible() keeping control characters", EXPLAINERS,
     [('return CONTROL.sub("", IGNORABLE.sub("", unicodedata.normalize("NFKC", text)))', 'return IGNORABLE.sub("", unicodedata.normalize("NFKC", text))')]),
    # The page text
    ("No attribute values", EXPLAINERS, [("if name in TEXT_ATTRIBUTES and value]", "if False]")]),
    ("Every attribute value", EXPLAINERS, [("if name in TEXT_ATTRIBUTES and value]", "if value]")]),
    ("Attribute values always shown", EXPLAINERS, [("[_segment(value, True) + BOUNDARY", "[_segment(value, False) + BOUNDARY")]),
    ("Text a browser may hide left out", EXPLAINERS,
     [("else self.text).append(data)", "else self.text).extend([] if self.maybe[-1] else [data])")]),
    ("<details> text always shown", EXPLAINERS, [('return (tag == "details" or ', 'return (tag == "nothing" or ')]),
    ("sr-only text always shown", EXPLAINERS, [('"sr-only" in (attrs.get("class") or "").split()', "False")]),
    ("Text the formatter styles invisible always shown", EXPLAINERS,
     [('bool(HIDING_STYLE.search(attrs.get("style") or ""))', "False")]),
    # Layout that can set text side by side in another order (Sol review r11)
    ("A table keeps the HTML's order", EXPLAINERS, [('FREE_TAGS = {"table", "details"}', 'FREE_TAGS = {"details"}')]),
    ("<details> keeps the HTML's order", EXPLAINERS, [('FREE_TAGS = {"table", "details"}', 'FREE_TAGS = {"table"}')]),
    ("The formatter's layout keeps the HTML's order", EXPLAINERS,
     [(' or FREE_STYLE.search(attrs.get("style") or "")', "")]),
    ("A chart keeps its JSON's order", EXPLAINERS, [("region = tag in FREE_TAGS or self.chart is not None or ", "region = tag in FREE_TAGS or ")]),
    ("A region's text once", EXPLAINERS, [("    return BOUNDARY.join([region] * COPIES)\n", "    return region\n")]),
    ("A region's text only twice", EXPLAINERS, [('COPIES = len("key") + max(map(len, WORDS))', "COPIES = 2")]),
    ("A region's text stays shown", EXPLAINERS, [("    region = region.translate(_AS_MAYBE)\n", "    pass\n")]),
    ("A chart's JSON read as written", EXPLAINERS, [("    strings = list(_strings(parsed))\n", "    strings = [spec]\n")]),
    ("A chart whose JSON Python can't read counts as written", EXPLAINERS,
     [("        raise SystemExit(f\"a ```{kind} block whose JSON", "        parsed = spec\n        (f\"a ```{kind} block whose JSON")]),
    ("A chart's JSON walked recursively", EXPLAINERS,
     [("    stack = [value]\n    while stack:\n        value = stack.pop()\n        if isinstance(value, str):\n            yield value\n"
       "        elif isinstance(value, (dict, list)):\n"
       "            stack += reversed(list(value.values()) if isinstance(value, dict) else value)\n",
       "    if isinstance(value, str):\n        yield value\n    elif isinstance(value, (dict, list)):\n"
       "        for item in value.values() if isinstance(value, dict) else value:\n            yield from _strings(item)\n")]),
    ("Plotly strings kept whole", EXPLAINERS, [("for p in PLOTLY_MARKUP.split(s) ", "for p in [s] ")]),
    ("Plotly entities left encoded", EXPLAINERS, [("dict.fromkeys([p, html.unescape(p)])", "dict.fromkeys([p])")]),
    ("Plotly placeholders kept in their string", EXPLAINERS, [("|%\\{[^\\s%{}:]*(?:[:|][^}]*)?\\})", ")")]),
    ("The chart stand-in drops its marker", CHART, [('<pre data-chart="chart">', "<pre>")]),
    ("The chart stand-in drops its JSON", CHART, [('<pre data-chart="chart">{data}</pre>', '<pre data-chart="chart"></pre>')]),
    ("The Plotly stand-in drops its marker", PLOT, [('<pre data-chart="plotly">', "<pre>")]),
    ("The Plotly stand-in drops its props", PLOT, [("{JSON.stringify(props)}</pre>", "</pre>")]),
    ("No page header", EXPLAINERS, [('[*header, *page["contents"]]', '[*page["contents"]]')]),
    ("No contents sidebar in the page text", EXPLAINERS, [('[*header, *page["contents"]]', "[*header]")]),
    ("An empty page header", EXPLAINERS, [("    return list(meta[slug].values())", "    return []")]),
    # The count
    ("No page count", EXPLAINERS, [("    if found != 1:\n", "    if False:\n")]),
    ("No hop inside a word", EXPLAINERS, [('return f"(?:{_HOP})?".join(word)', "return word")]),
    ("Hops can't skip what a browser may hide", EXPLAINERS, [("(?:{BOUNDARY}|{_SKIP})*?", "(?:{BOUNDARY})*?")]),
    ("No whitespace between the words", EXPLAINERS, [("(?:\\s|{_HOP})+", "(?:{_HOP})+")]),
    ("A case-sensitive count", EXPLAINERS, [('(?![^\\W_])", regex.I)', '(?![^\\W_])")')]),
    ("A word boundary where only letters and digits may not touch", EXPLAINERS, [('rf"(?<![^\\W_]){_spelled', 'rf"\\b{_spelled')]),
    ("Nothing stops a letter touching the first word", EXPLAINERS, [('rf"(?<![^\\W_]){_spelled', 'rf"{_spelled')]),
    ("Nothing stops a letter touching the second word", EXPLAINERS, [('(?![^\\W_])", regex.I)', '", regex.I)')]),
    ("Overlapping mentions counted once", EXPLAINERS, [("overlapped=True", "overlapped=False")]),
    ("No time limit on the renderer", EXPLAINERS,
     [("if not select.select([self.proc.stdout], [], [], RENDER_SECONDS)[0]:", "if False:")]),
    ("A stopped renderer never restarts", EXPLAINERS,
     [("if _renderer is None or _renderer.proc.poll() is not None:", "if _renderer is None:")]),
    # Finding the opening
    ("Blanking keeps the block", EXPLAINERS, [('"" if b["start"] <= n <= b["end"] else line', "line")]),
    ("Any number of blocks may hold the words", EXPLAINERS,
     [('if len(holders) != 1 or "error" in blanked[holders[0]]:', "if not holders:")]),
    ("A multi-line paragraph counts as one of its own", EXPLAINERS,
     [('if blocks[k]["type"] != "paragraph" or first != last:', 'if blocks[k]["type"] != "paragraph":')]),
    ("Any one-line block counts as a paragraph", EXPLAINERS,
     [('if blocks[k]["type"] != "paragraph" or first != last:', "if first != last:")]),
    ("No check of the line the page shows", EXPLAINERS,
     [("if len(shown) != 1 or not OPENING.match(shown[0]):", "if not shown:")]),
    ("An opening that needn't end in a colon", EXPLAINERS, [('\\b.*:\\s*$")', '\\b.*$")')]),
    ("An ordered list counts as a bullet list", EXPLAINERS, [(' or blocks[k + 1]["ordered"]:', ":")]),
    ("Shown lines show text a browser may hide", EXPLAINERS,
     [("        if not self.maybe[-1]:\n            self.parts.append(WHITESPACE", "        if True:\n            self.parts.append(WHITESPACE")]),
    ("Shown lines break at every tag", EXPLAINERS, [("if tag not in self.PHRASING or re.search", "if True or re.search")]),
    ("Shown lines keep line breaks in text", EXPLAINERS, [('self.parts.append(WHITESPACE.sub(" ", data))', "self.parts.append(data)")]),
    ("Relative links left relative", EXPLAINERS,
     [('return adapt(_absolute_links("\\n".join(out), slug), slug)', 'return adapt("\\n".join(out), slug)')]),
]


def failures(swaps=(), path=None, timeout=300):
    """Tests that fail in a copy of the repo with the swaps applied, or a reason they didn't run."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__", ".hypothesis", "*.pdf",
                                                                   "node_modules"))
        (copy / "site" / "node_modules").symlink_to(ROOT / "site" / "node_modules")
        if swaps:
            file = copy / path
            text = file.read_text()
            for old, new in swaps:
                if text.count(old) != 1:
                    return f"no longer applies: {old!r} occurs {text.count(old)} times"
                text = text.replace(old, new)
            file.write_text(text)
        try:
            run = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--hypothesis-seed=0", "tests"],
                                 cwd=copy, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            return f"hangs (stopped after {timeout} s)"
        found = re.search(r"(\d+) failed", run.stdout)
        if not found and run.returncode not in (0, 1):
            return f"pytest exited {run.returncode}: {run.stdout[-300:]}{run.stderr[-300:]}"
        return int(found.group(1)) if found else 0


def main():
    baseline = failures()
    if baseline != 0:
        sys.exit(f"the unmutated tests don't all pass: {baseline}")
    with ThreadPoolExecutor(4) as pool:
        results = list(pool.map(lambda m: failures(m[2], m[1], timeout=300), MUTATIONS))
    print("| Mutation | Tests that fail |\n|:--|--:|")
    for (label, _, _), result in zip(MUTATIONS, results):
        print(f"| {label} | {result} |")
    caught = [isinstance(r, int) and r > 0 or str(r).startswith("hangs") for r in results]
    sys.exit(0 if all(caught) else 1)


if __name__ == "__main__":
    main()
