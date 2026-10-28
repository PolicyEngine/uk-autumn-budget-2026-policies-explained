# Autumn Budget 2026: the policies explained

PolicyEngine's post-Budget briefing. It takes the 20 measures on Vahid's pre-Budget list and says what the Budget of 28 October 2026 did with each, adds the measures the list missed, and for the seven measures in the [Budget dashboard](https://www.policyengine.org/uk/budgets/autumn-2026) sets our estimate beside the matching line of the OBR's costing.

The PDF is built from [`template.md`](template.md). The costing tables and gaps are filled in by [`scripts/build_figures.py`](scripts/build_figures.py): our estimates from the dashboard's published artifacts, the official ones from the OBR's and the Treasury's workbooks. [`document/figures.json`](document/figures.json) traces each of those figures to its file, row and column. The other numbers in the text (rates, thresholds, figures quoted from our posts or official documents) are typed into the template and cited there.

## What has gone out

| Version | Where | Folder |
|:--|:--|:--|
| Production manifest revision 17, compared with the OBR's matching lines | Slack: #core-team (follow-up, 28 Oct 22:44 UTC) and #uk-autumn-budget-2026 | [`published/2026-10-28-rev17`](published/2026-10-28-rev17) |

`main` builds it exactly: a clean build reproduces its PDF byte for byte. An earlier version went to #core-team at 19:07 UTC. It was built on the test manifest and quoted a triple lock figure we have since withdrawn, so it isn't kept here.

## Build

You need [uv](https://docs.astral.sh/uv/), pandoc 3, and read access to [PolicyEngine/document-templates](https://github.com/PolicyEngine/document-templates), which every PolicyEngine org member has. `uv sync` installs `pe-doc` from there, pinned to the commit the posted PDF was built with.

```bash
scripts/build.sh
```

This fetches the artifacts that the pinned manifest ([`sources/manifest-rev17.json`](sources/manifest-rev17.json)) lists from production and checks each against its receipt's digest. It then writes `document/proposal.md` and `document/figures.json`, and builds the PDF with `pe-doc build` and `pe-doc check`. The PDF lands in `document/`; it is not committed.

`scripts/build.sh --latest` builds on the live manifest instead. Use it to see what a new dashboard revision would change, then pin that revision in a PR if we adopt it.

## How to contribute

1. Branch from `main` and open a draft PR early.
2. Edit [`template.md`](template.md), not `document/proposal.md`. The proposal is generated; CI fails if the committed copy is stale. Costings and gaps go in as placeholders (listed at the top of [`scripts/build_figures.py`](scripts/build_figures.py)), not typed numbers. Anything else you type needs its source cited.
3. Run `scripts/build.sh` and commit `template.md` with the regenerated `document/proposal.md` and `document/figures.json`. The PR diff then shows every printed figure that moved.
4. CI builds the PDF on every PR and attaches it to the run as the `policies-explained-pdf` artifact.

PRs from forks can't build, because CI reads the private template repo with an org secret. Push a branch to this repo instead.

## Rules the text follows

- Every figure comes from the dashboard, a live PolicyEngine post or an official document, and the source section cites it.
- Official comparisons use the line in the OBR's detailed forecast table 1.1 that matches what we model. Table 6.1's rounded total is context only.
  - Name it as "the government's costing, certified by the OBR".
  - The exception is fuel duty: "the government's estimate, which the OBR used but could not certify".
  - A gap over 25% needs a verified reason, or must be stated without one.
- No claim about how a model works unless the dashboard notes, a post or the code supports it. Label inferences.
- No link to an unmerged post. No small cells or single-record values. No poverty or people-affected figures until the dashboard publishes them.
- Sentence case and no emoji. Write "exceeds", not "is above". Use whole pounds in tables, with pence only in a spelled-out formula or a statutory rate.

## Sources

[`sources/README.md`](sources/README.md) lists each file, where it came from and its digest.
