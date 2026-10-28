#!/usr/bin/env bash
# Build the PDF from template.md.
#
#   scripts/build.sh           build on the pinned manifest, sources/manifest-rev17.json
#   scripts/build.sh --latest  download the live production manifest first and build on that
#
# Writes document/proposal.md and document/figures.json (both committed, so a
# PR's diff shows every printed figure that moved), then the PDF, HTML and DOCX
# in document/ (not committed; CI uploads the PDF). Posts nothing.
set -euo pipefail
cd "$(dirname "$0")/.."

BASE=https://www.policyengine.org/uk/autumn-budget-2026/data
MANIFEST=sources/manifest-rev17.json
ART=.cache/artifacts

rm -rf "$ART"
if [[ "${1:-}" == "--latest" ]]; then
  MANIFEST=.cache/manifest-latest.json
  mkdir -p .cache
  uv run --frozen python -I scripts/fetch_artifacts.py \
    --manifest-url "$BASE/manifest.json" --manifest-out "$MANIFEST" --out "$ART"
else
  uv run --frozen python -I scripts/fetch_artifacts.py \
    --manifest "$MANIFEST" --base-url "$BASE" --out "$ART"
fi

uv run --frozen python -I scripts/build_figures.py \
  --manifest "$MANIFEST" --manifest-url "$BASE/manifest.json" --source production \
  --artifacts "$ART" \
  --xlsx sources/Table_6.1_and_6.2_Budget_2026_Policy_Decisions.xlsx \
  --obr sources/policy-555e7f74.xlsx \
  --template template.md \
  --out document/proposal.md --figures document/figures.json

uv run --frozen pe-doc build document
uv run --frozen pe-doc check document
