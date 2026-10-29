# The site's renderer

To find an explainer's key points, the build renders the post the way policyengine.org renders it and reads the page that results ([`scripts/explainers.py`](../scripts/explainers.py)). This folder holds that renderer: policyengine-app-v2's own `MarkdownFormatter`, which `render.tsx` runs under [Bun](https://bun.sh) 1.3.12.

```bash
cd site && bun install --frozen-lockfile
bun render.tsx in.json out.json
```

`render.tsx` documents its input and output. The build starts it once with `--serve` and sends it every post and variant it needs.

## Copied files

`vendor/` mirrors `website/src/` in policyengine-app-v2 at 85571f7a3, the commit in [`sources/posts/APP_V2_MAIN_SHA`](../sources/posts/APP_V2_MAIN_SHA). `tsconfig.json` maps the app's `@/` imports to `vendor/`. Each blob id below equals `git rev-parse 85571f7a3:website/src/<path>` in policyengine-app-v2, and `tests/test_site.py` checks each file against it.

| File | Blob |
|:--|:--|
| `vendor/app/[countryId]/research/[slug]/ArticleClient.tsx` | `fd8f682214753e7e474d2e1fe1fd36a0084650da` |
| `vendor/components/blog/MarkdownFormatter.tsx` | `dd3166afc7f0a59e17b933a6e926fc6a89fe9990` |
| `vendor/components/blog/blogStyles.ts` | `1b4aff3464078751871b406d773c0af900c48a6b` |
| `vendor/components/blog/safeHref.ts` | `56de20d894f8256852663f9ceb1aee2769f3746a` |
| `vendor/components/blog/useDisplayCategory.ts` | `97e1be713771d7d215a5e36c3e6953b536f7d34e` |
| `vendor/hooks/useMediaQuery.ts` | `74d79deba0b3b72e1fd1b35345c9926eb5088f45` |

`render.tsx` doesn't run `ArticleClient.tsx`, which needs Next.js. It copies the few lines that turn the post's `##` lines into the contents sidebar, and a test checks that they still match.

## Stand-ins

| File | Stands in for | What it does |
|:--|:--|:--|
| `vendor/components/blog/LazyBlogChart.tsx` | The site's charts (BlogChart: Recharts, through Next.js) | Hands on the chart's JSON as written, in `<pre data-chart="chart">`; the build reads every string in it as text the chart could show |
| `vendor/components/blog/LazyPlot.tsx` | Plotly | Hands on its props as JSON, in `<pre data-chart="plotly">`; the build reads their strings the way Plotly does |
| `vendor/designTokens/index.ts` | The design tokens | Reads every token as "0"; tokens set colours, fonts and spacing, never text |
| `record-markdown.tsx` | react-markdown, as the formatter imports it | Passes every prop to the real react-markdown and notes each Markdown string, so the build can check the HTML in a highlighted block's panes, which the formatter renders with a formatter of their own |

## Packages

`package.json` pins each package, and through `overrides` each transitive one, to the version in policyengine-app-v2's `bun.lock` at 85571f7a3, so all 115 packages in `bun.lock` here match. After moving the commit, check again:

```bash
python3 site/compare_lock.py ~/PolicyEngine/policyengine-app-v2 <commit>
```

## What the page text leaves out

The site's own stylesheet, which can hide, move or add text, and fonts that draw look-alike letters. `explainers.py` stops the build on any post whose HTML could do the same: styles, classes beyond GFM's, the `hidden` attribute, `dir`, `<template>`, forms and media.
