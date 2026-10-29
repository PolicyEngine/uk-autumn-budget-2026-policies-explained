// Stands in for the site's chart (Recharts, loaded through Next.js). It shows
// the chart's JSON as text, so the count sees every title, label and note the
// chart could show.
export function LazyBlogChart({ data }: { data: string }) {
  return <pre>{data}</pre>;
}
