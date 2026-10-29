# Document folder

The `pe-doc` folder for the briefing: [`proposal.md`](proposal.md) (`scripts/build.sh` generates it from [`../template.md`](../template.md); don't edit it here), [`extra.css`](extra.css) for the cards and explainer pages, [`figures.json`](figures.json), which traces each costing, gap and combined total to its file, row and column, and [`charts/`](charts), which `scripts/build_charts.py` draws from the explainers' chart data.

Build from the repo root with `scripts/build.sh`. Git ignores the PDF, HTML and DOCX it writes here.
