// Stands in for the site's chart (BlogChart: Recharts, loaded through Next.js),
// which parses the JSON and shows its strings as text. This hands the JSON on
// as written; explainers.py reads every string in it as text the chart could
// show (chart_pieces).
export function LazyBlogChart({ data }: { data: string }) {
  return <pre data-chart="chart">{data}</pre>;
}
