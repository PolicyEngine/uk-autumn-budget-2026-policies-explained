# Sources

Everything the briefing's figures and claims rest on, saved on 28 October 2026. The digest is the first 16 hex characters of each file's sha256.

| File | What it is | Where it came from | sha256 |
|:--|:--|:--|:--|
| `policy-555e7f74.xlsx` | The OBR's detailed forecast table 1.1 (policy measures by line), October 2026. Sheet `1.1` | The OBR's detailed forecast tables, as saved in dashboard PR [#300](https://github.com/PolicyEngine/uk-autumn-budget-dashboard-2026/pull/300) (open) at 555e7f74; `build_figures.py` refuses any other digest | `cdcc2a06b100241b` |
| `Table_6.1_and_6.2_Budget_2026_Policy_Decisions.xlsx` | HM Treasury, Budget 2026, Tables 6.1 (policy decisions) and 6.2 | The [Budget 2026 publication](https://www.gov.uk/government/publications/budget-2026-document/budget-2026-html) on GOV.UK | `359958df6b1ab974` |
| `efo-oct-2026.txt` | Text of the OBR's [Economic and fiscal outlook, October 2026](https://obr.uk/efo/economic-and-fiscal-outlook-october-2026/), for checking reasons | pdftotext of the OBR PDF | `0d449b8015fec840` |
| `manifest-rev17.json` | The dashboard's publication manifest, production revision 17 (2026-10-28 19:24 UTC). The build is pinned to it | [policyengine.org/uk/autumn-budget-2026/data/manifest.json](https://www.policyengine.org/uk/autumn-budget-2026/data/manifest.json) | `9685adc1bcd8c5eb` |
| `notes-prod-rev17.json` | The dashboard's per-measure notes as rendered on production at revision 17 | Captured from the live page and hash-matched against it | `e98d885574fbc77c` |
| `comparables-rev17.md` | Each estimate beside its OBR line and Table 6.1 total, with the gap and its reason | The written briefing's comparables review | `2ff7744b9f1560de` |
| `article-6a14eb17.md` | The written post-Budget briefing, whose comparison section the cards follow | [policyengine-app-v2#1469](https://github.com/PolicyEngine/policyengine-app-v2/pull/1469) at 6a14eb17 (a draft, so not linked from the PDF) | `063533e327027e32` |
| `whats-improving-note.md` | The "What we're improving" section, quoted verbatim | The Budget coordinator's note | `bbf13048d3b848cc` |
| `pr1466-state.json` | The savings explainer's PR state when we built: open, so the PDF doesn't link it | [policyengine-app-v2#1466](https://github.com/PolicyEngine/policyengine-app-v2/pull/1466) | `8f558929c85345c8` |
| `posts/*.md` | The live explainers the cards cite and link | policyengine-app-v2 `main` at the commit in `posts/APP_V2_MAIN_SHA` | see below |

| Post | sha256 |
|:--|:--|
| `budget-2026-energy-bills.md` | `08d97fbe57e8d7ac` |
| `carers-allowance-taper.md` | `fe9e66d17d86b482` |
| `fuel-duty-cut-extension.md` | `ccc7ddd081d8175e` |
| `pension-tax-allowance.md` | `87d63b808fc82081` |
| `uk-autumn-budget-2026-property-income-tax.md` | `065217a115640c60` |
| `uk-autumn-budget-2026-trading-allowance.md` | `bef16a328e7ec9d6` |
| `uk-triple-lock-budget-2026.md` | `901ee28ee7a12ec7` |

The dashboard's artifacts (one folder of CSVs per measure) are not saved here. `scripts/fetch_artifacts.py` downloads the ones the pinned manifest lists and checks every file against its receipt's digest.
