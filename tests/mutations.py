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

# (what the mutation breaks, file, [(text, replacement), ...]); each text must occur once
MUTATIONS = [
    ("A flat £0.50 tolerance, the old check's floor", CHARTS,
     [("return (0.5 * 10 ** -decimals if decimals is not None else 0) + EPSILON", "return 0.5 + EPSILON")]),
    ("No font filter", CHARTS,
     [('manager.ttflist = [f for f in manager.ttflist if f.name.casefold() != "inter"]', "manager.ttflist = list(manager.ttflist)")]),
    ("A case-sensitive font filter", CHARTS, [('f.name.casefold() != "inter"', 'f.name != "Inter"')]),
    # The source count
    ("No source count", EXPLAINERS, [("    if mentions != 1:\n", "    if False:\n")]),
    ("Source count without entity decoding", EXPLAINERS, [("visible(unescape(text))", "visible(text)")]),
    ("Source count without visible()", EXPLAINERS, [("MENTION.findall(visible(unescape(text))", "MENTION.findall(unescape(text)")]),
    ("visible() keeping invisible characters", EXPLAINERS,
     [('return IGNORABLE.sub("", unicodedata.normalize("NFKC", text))', 'return unicodedata.normalize("NFKC", text)')]),
    ("visible() without NFKC", EXPLAINERS,
     [('return IGNORABLE.sub("", unicodedata.normalize("NFKC", text))', 'return IGNORABLE.sub("", text)')]),
    ("No comments among the marks", EXPLAINERS, [("(?:<!--.*?-->|<[^<>]*>|", "(?:<[^<>]*>|")]),
    ("No tags among the marks", EXPLAINERS, [("<!--.*?-->|<[^<>]*>|", "<!--.*?-->|")]),
    ("No link destinations among the marks", EXPLAINERS, [(r"|\]\((?:[^()]|\([^()]*\))*\)", "")]),
    ("Link destinations without parentheses inside", EXPLAINERS, [(r"\]\((?:[^()]|\([^()]*\))*\)", r"\]\([^()]*\)")]),
    ("No reference links among the marks", EXPLAINERS, [(r"|\]\[[^\[\]]*\]", "")]),
    ("No Markdown marks among the marks", EXPLAINERS, [(r"|[*_~`\\\[\]])", ")")]),
    ("Marks only between the two words, not inside one", EXPLAINERS, [('return f"{_MARK}*+".join(word)', "return word")]),
    ("Backtracking marks instead of possessive ones", EXPLAINERS,
     [('return f"{_MARK}*+".join(word)', 'return f"{_MARK}*".join(word)'), ("(?:\\s|{_MARK})++", "(?:\\s|{_MARK})+")]),
    ("Case-sensitive source count (regex.I removed)", EXPLAINERS, [("    regex.I | regex.S,\n", "    regex.S,\n")]),
    ("A word boundary where only letters and digits may not touch", EXPLAINERS, [('rf"(?<![^\\W_]){_spelled', 'rf"\\b{_spelled')]),
    ("Nothing stops a letter touching the first word", EXPLAINERS, [('rf"(?<![^\\W_]){_spelled', 'rf"{_spelled')]),
    ("Nothing stops a letter touching the second word", EXPLAINERS, [("))})(?![^\\W_])\",", "))})\",")]),
    ("Overlapping mentions counted once", EXPLAINERS, [("overlapped=True", "overlapped=False")]),
    # The page model
    ("No page-model count", EXPLAINERS, [("    if len(starts) != 1:\n", "    if False:\n")]),
    ("Page model without visible()", EXPLAINERS,
     [('return visible("".join(parser.parts)).split("\\n")', 'return "".join(parser.parts).split("\\n")')]),
    ("Inline text unrendered", EXPLAINERS,
     [("html = md.renderer.renderInline(t.children or [], md.options, {})", "html = t.content")]),
    ("HTML blocks ignored", EXPLAINERS, [('elif t.type == "html_block":', "elif False:")]),
    ("Code and <pre> read as prose", EXPLAINERS,
     [('HIDDEN = {"code", "pre", "script", "style", "textarea", "template"}', 'HIDDEN = {"script", "style", "textarea", "template"}')]),
    ("No whitespace collapse", EXPLAINERS, [('self.parts.append(WHITESPACE.sub(" ", data))', "self.parts.append(data)")]),
    ("No image caption", EXPLAINERS, [('if tag == "img" and attrs.get("src") and attrs.get("alt") and not self.hidden:', "if False:")]),
    ("A caption for an image with no source", EXPLAINERS,
     [('if tag == "img" and attrs.get("src") and attrs.get("alt") and not self.hidden:', 'if tag == "img" and attrs.get("alt") and not self.hidden:')]),
    ("Highlighted blocks read as code", EXPLAINERS,
     [('elif t.type == "fence" and t.info.split()[:1] == ["highlighted-block"]:', "elif False:")]),
    ("Language from the whole info string", EXPLAINERS,
     [('elif t.type == "fence" and t.info.split()[:1] == ["highlighted-block"]:', 'elif t.type == "fence" and t.info == "highlighted-block":')]),
    ("No strikethrough", EXPLAINERS, [('.enable(["table", "strikethrough"])', '.enable(["table"])')]),
    ("No line breaks at dl, dt, dd, figure and figcaption", EXPLAINERS,
     [('"ol", "dl", "dt", "dd", ', '"ol", '), ('"address", "figure", "figcaption", ', '"address", ')]),
    ("An opening pattern that needs a single space", EXPLAINERS,
     [('OPENING = re.compile(r"Key\\s+(results', 'OPENING = re.compile(r"Key (results')]),
]


def failures(swaps=(), path=None, timeout=300):
    """Tests that fail in a copy of the repo with the swaps applied, or a reason they didn't run."""
    with tempfile.TemporaryDirectory() as tmp:
        copy = Path(tmp) / "repo"
        shutil.copytree(ROOT, copy, ignore=shutil.ignore_patterns(".venv", ".git", "__pycache__", ".hypothesis", "*.pdf"))
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
        results = list(pool.map(lambda m: failures(m[2], m[1], timeout=120), MUTATIONS))
    print("| Mutation | Tests that fail |\n|:--|--:|")
    for (label, _, _), result in zip(MUTATIONS, results):
        print(f"| {label} | {result} |")
    caught = [isinstance(r, int) and r > 0 or str(r).startswith("hangs") for r in results]
    sys.exit(0 if all(caught) else 1)


if __name__ == "__main__":
    main()
