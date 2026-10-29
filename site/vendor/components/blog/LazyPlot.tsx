// Stands in for the site's Plotly chart (loaded through Next.js). It shows the
// chart's props as JSON text, so the count sees every string the chart could show.
export function LazyPlot(props: Record<string, unknown>) {
  return <pre>{JSON.stringify(props)}</pre>;
}
