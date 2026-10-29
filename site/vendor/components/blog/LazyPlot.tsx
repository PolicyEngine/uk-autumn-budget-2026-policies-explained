// Stands in for the site's Plotly chart (loaded through Next.js). This hands
// its props on as JSON; explainers.py reads every string in them as text the
// chart could show, the way Plotly reads it (chart_pieces).
export function LazyPlot(props: Record<string, unknown>) {
  return <pre data-chart="plotly">{JSON.stringify(props)}</pre>;
}
