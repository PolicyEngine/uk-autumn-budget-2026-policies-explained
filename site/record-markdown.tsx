// Stands in for "react-markdown" when the vendored formatter imports it
// (tsconfig.json maps the name here). It hands every prop to the real
// react-markdown unchanged and notes each Markdown string, so render.tsx can
// check the HTML in every pane the formatter renders, nested ones included.
import ReactMarkdown from "./node_modules/react-markdown/index.js";

export * from "./node_modules/react-markdown/index.js";

export const seen: string[] = [];

export default function RecordedMarkdown(props: any) {
  seen.push(props.children);
  return <ReactMarkdown {...props} />;
}
