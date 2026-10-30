# Sources

We saved here everything the briefing's figures and claims rest on: the artifacts on 30 October 2026, the rest on 28 October. The digest is the first 16 hex characters of each file's sha256.

| File | What it is | Where it came from | sha256 |
|:--|:--|:--|:--|
| `policy-555e7f74.xlsx` | The OBR's detailed forecast table 1.1 (policy measures by line), October 2026. Sheet `1.1` | The OBR's detailed forecast tables, as dashboard PR [#300](https://github.com/PolicyEngine/uk-autumn-budget-dashboard-2026/pull/300) (open) saved them at 555e7f74; `build_figures.py` refuses any other digest | `cdcc2a06b100241b` |
| `Table_6.1_and_6.2_Budget_2026_Policy_Decisions.xlsx` | HM Treasury, Budget 2026, Tables 6.1 (policy decisions) and 6.2 | The [Budget 2026 publication](https://www.gov.uk/government/publications/budget-2026-document/budget-2026-html) on GOV.UK | `359958df6b1ab974` |
| `efo-oct-2026.txt` | Text of the OBR's [Economic and fiscal outlook, October 2026](https://obr.uk/efo/economic-and-fiscal-outlook-october-2026/), for checking reasons | pdftotext of the OBR PDF | `0d449b8015fec840` |
| `manifest-rev17.json` | The dashboard's publication manifest, production revision 17 (2026-10-28 19:24 UTC). `scripts/build.sh` builds on it unless you pass `--latest` | [policyengine.org/uk/autumn-budget-2026/data/manifest.json](https://www.policyengine.org/uk/autumn-budget-2026/data/manifest.json) | `9685adc1bcd8c5eb` |
| `notes-prod-rev17.json` | The dashboard's per-measure notes as production rendered them at revision 17 | We captured it from the live page and matched its hash against the page | `e98d885574fbc77c` |
| `comparables-rev17.md` | Each estimate beside its OBR line and Table 6.1 total, with the gap and its reason | The post-Budget briefing article's comparables review | `2ff7744b9f1560de` |
| `article-6a14eb17.md` | The post-Budget briefing article, whose comparison section the cards follow | [policyengine-app-v2#1469](https://github.com/PolicyEngine/policyengine-app-v2/pull/1469) at 6a14eb17 (a draft, so the PDF doesn't link it) | `063533e327027e32` |
| `whats-improving-note.md` | The "What we're improving" section, which the briefing quotes word for word | The Budget coordinator's note | `bbf13048d3b848cc` |
| `pr1466-state.json` | The savings explainer's PR state when we built: open, so the PDF doesn't link it | [policyengine-app-v2#1466](https://github.com/PolicyEngine/policyengine-app-v2/pull/1466) | `8f558929c85345c8` |
| `posts/*.md` | The live explainers the cards cite and link | policyengine-app-v2 `main` at the commit in `posts/APP_V2_MAIN_SHA` | see below |
| `posts/meta.json` | Each post's title and description, which the article page shows above the post; the key points check counts them as page text | `app/src/data/posts/posts.json` in policyengine-app-v2 at the same commit (blob `93845310`), only the fields the page shows as text | `1ec57ecdc9dcf72b` |

| Post | sha256 |
|:--|:--|
| `budget-2026-energy-bills.md` | `08d97fbe57e8d7ac` |
| `carers-allowance-taper.md` | `fe9e66d17d86b482` |
| `fuel-duty-cut-extension.md` | `ccc7ddd081d8175e` |
| `pension-tax-allowance.md` | `87d63b808fc82081` |
| `uk-autumn-budget-2026-property-income-tax.md` | `36525e4368a49cee` |
| `uk-autumn-budget-2026-trading-allowance.md` | `bef16a328e7ec9d6` |
| `uk-triple-lock-budget-2026.md` | `901ee28ee7a12ec7` |

`artifacts-rev17/` holds the dashboard's artifacts at revision 17: a folder for each of the seven measures and one for the combined run, each with its CSVs and receipt. We copied them on 30 October from our last build's download, because the dashboard no longer serves them: all eight returned 404 that day, at revision 60. `scripts/build_figures.py` checks each receipt against the digest in `manifest-rev17.json` and each file against its receipt. `scripts/fetch_artifacts.py` downloads the artifacts of the live revision for `scripts/build.sh --latest`.
