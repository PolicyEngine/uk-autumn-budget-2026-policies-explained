# Autumn Budget 2026: the policies explained

PolicyEngine's post-Budget briefing. It says what the Budget of 28 October 2026 did, measure by measure, and for the seven measures in the [Budget dashboard](https://www.policyengine.org/uk/autumn-budget-2026) sets our estimate beside the matching line of the OBR's costing.

The PDF opens with a cover for outside readers: it links the dashboard and our [post-Budget briefing](https://www.policyengine.org/uk/research/uk-autumn-budget-2026-briefing) and credits the Nuffield Foundation, which funds our UK Budget work. `template.md` defines the cover, the contents page and the back page in fenced divs because `pe-doc` has none of them. `document/extra.css` sets the A4 layout: the teal cover under `pe-doc`'s letterhead, running headers and footers with page numbers, the measure cards, numbered figures and the teal back page. The logos in `document/assets/` come from the Budget dashboard.

`scripts/build.sh` builds the PDF from [`template.md`](template.md). [`scripts/build_figures.py`](scripts/build_figures.py) fills in the costing tables and gaps: our estimates from the artifacts the dashboard publishes, the official ones from the OBR's and the Treasury's workbooks. [`document/figures.json`](document/figures.json) traces each of those figures to its file, row and column. Each explainer page quotes its post's key points word for word from [`sources/posts/`](sources/posts). The build finds them by rendering each post with the site's own code ([`site/`](site)) and reading the page that results. [`scripts/build_charts.py`](scripts/build_charts.py) redraws one chart from each post's chart data, checking every income decile bar against the dashboard. We type the other numbers in the text (rates, thresholds, figures we quote from our posts or official documents) into the template and cite them there.

## What has gone out

| Version | Where | Folder |
|:--|:--|:--|
| Production manifest revision 17, beside the OBR's matching lines | Slack: #core-team (follow-up, 28 Oct 22:44 UTC) and #uk-autumn-budget-2026 | [`published/2026-10-28-rev17`](published/2026-10-28-rev17) |
| Draft adding a page for each of our six explainers (PR #1 at 7bbcdcb) | Slack: reply in the #uk-autumn-budget-2026 thread (29 Oct 01:27 UTC) | [`published/2026-10-29-explainers-draft`](published/2026-10-29-explainers-draft) |
| Outward version with a cover (PR #1 at 942e628) | Slack: reply in the #uk-autumn-budget-2026 thread (29 Oct 02:58 UTC); email to the 12 people who registered for the webinar (29 Oct 03:15 UTC) | [`published/2026-10-29-outward`](published/2026-10-29-outward) |
| Corrected version, after Pavel's review (PR #1 at 2291504) | Slack: reply in the #uk-autumn-budget-2026 thread (29 Oct 05:11 UTC) | [`published/2026-10-29-corrected`](published/2026-10-29-corrected) |
| Reader version, without notes on how we made it, under the corrected version's file name (PR #3 at 9e6760c) | Slack: reply in the #uk-autumn-budget-2026 thread (29 Oct 13:59 UTC) | [`published/2026-10-29-reader`](published/2026-10-29-reader) |

Commit b56b14c builds revision 17's PDF byte for byte, and 7bbcdcb the explainers draft. Commits 942e628 through 3f48787 build the outward version, 2291504 through b4f92fb the corrected one, and 9e6760c and 8b2c3dc, the merge of PR #3, the reader version. An earlier version went to #core-team at 19:07 UTC. We built it on the test manifest, and it quoted a triple lock figure we have since withdrawn, so we don't keep it here.

## Build

You need [uv](https://docs.astral.sh/uv/), [Bun](https://bun.sh) 1.3.12, pandoc 3, and read access to [PolicyEngine/document-templates](https://github.com/PolicyEngine/document-templates), which every PolicyEngine org member has. `uv sync` installs `pe-doc` from there, and `uv.lock` pins it to the commit that built the PDFs we posted.

```bash
(cd site && bun install --frozen-lockfile)
scripts/build.sh
```

This reads the artifacts we saved in [`sources/artifacts-rev17/`](sources/artifacts-rev17) for the pinned manifest ([`sources/manifest-rev17.json`](sources/manifest-rev17.json)), and checks each receipt against the manifest and each file against its receipt. It then writes `document/proposal.md`, `document/figures.json` and the charts in `document/charts/`, and builds the PDF with `pe-doc build` and `pe-doc check`. The PDF lands in `document/`, and git ignores it.

`uv run pytest` runs the tests of the build scripts; CI runs them before every build. `uv run python tests/mutations.py` breaks each rule the tests claim, one at a time in a copy of the repo, and checks that some test fails each time.

`scripts/build.sh --latest` builds on the live manifest instead. Use it to see what a new dashboard revision would change, then pin that revision in a PR if we adopt it.

## How to contribute

1. Branch from `main` and open a draft PR early.
2. Edit [`template.md`](template.md), not `document/proposal.md`. The build generates the proposal, and CI fails if the copy in the repo is stale. Costings and gaps go in as placeholders (the top of [`scripts/build_figures.py`](scripts/build_figures.py) lists them), not as numbers you type. Cite a source for anything else you type.
3. Run `scripts/build.sh` and commit `template.md` with the `document/proposal.md`, `document/figures.json` and `document/charts/` it writes. The PR diff then shows every figure and chart in the PDF that moved.
4. CI builds the PDF on every PR and attaches it to the run as the `policies-explained-pdf` artifact.

PRs from forks can't build, because CI reads the private template repo with an org secret. Push a branch to this repo instead.

## Rules the text follows

- Every figure comes from the dashboard, a live PolicyEngine post or an official document, and the source section cites it.
- Official comparisons use the line in the OBR's detailed forecast table 1.1 that matches what we model. Table 6.1's total, which the Treasury rounds to the nearest £5 million, is context only.
  - Name it as "the government's costing, which the OBR certifies", and its lines as "the official … line", not "the OBR's": the Treasury makes the costing.
  - The exception is fuel duty: "the government's estimate, which the OBR used but could not certify".
  - A gap over 25% needs a reason we have verified; otherwise state the gap without one.
- No claim about how a model works unless the dashboard notes, a post or the code supports it. Label inferences. Where the dashboard's description of a measure and its code differ, follow the code: the Carer's Allowance limit is £228 and £234 in the years we cost (`carers_allowance_earnings_taper.py` at 4de166f0), not the description's £212.
- No link to a post that hasn't merged. No small cells or single-record values. No poverty or people-affected figures until the dashboard publishes them, apart from any inside an explainer's key points, which we quote word for word (Max, 29 Oct: keep the energy post's 19.7 million households verbatim).
- Write for readers outside PolicyEngine: no notes to the team, no internal status, and no comparison with what we expected the Budget to do.
- Say what the reader gets and what we found, never how or why we made it (Max, 29 Oct): no production choices, checks, reviews, build machinery or plans for later updates. Keep method that changes how a number reads, such as assumptions, sources and scope limits, and state each limitation in the present tense.
- Sentence case and no emoji. Active voice: name who acts, with no passives, including reduced ones ("certified by", "not modelled"). Write "exceeds", not "is above". Use whole pounds in tables, with pence only where a formula spells them out or for a statutory rate.

## Sources

[`sources/README.md`](sources/README.md) lists each file, where it came from and its digest.
