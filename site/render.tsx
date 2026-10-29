// Renders Markdown the way policyengine.org renders a research post: with the
// site's own MarkdownFormatter (copied into site/vendor/ from policyengine-app-v2),
// react-markdown, remark-gfm and rehype-raw, to static HTML. Only the charts and
// the design tokens are stand-ins; site/README.md lists which file is which.
//
//   bun site/render.tsx in.json out.json
//   bun site/render.tsx --serve
//
// in.json holds a JSON array of Markdown strings, or {"posts": [...],
// "displayCategory": "mobile"} to render as a phone would (the formatter
// otherwise takes the desktop layout, as it does on the server). out.json
// gets, for each:
// - html: what the formatter renders, or error if it throws;
// - blocks: the post's top-level blocks as remark parses them, with type,
//   first and last line (1-based), and whether a list is ordered;
// - contents: the text of each entry in the article page's contents sidebar;
// - elements: each HTML element react-markdown hands the formatter, as its tag
//   and property names, with class names listed (rehype-raw has parsed the
//   post's own HTML by then, as a browser would). This covers every Markdown
//   string the formatter renders: the post, and each pane of a highlighted
//   block, which it renders with a MarkdownFormatter of its own.
// With --serve, each line on stdin names an in.json and an out.json, separated
// by a tab; the script answers "done" on stdout once it has written out.json.
// Writing results to a file sidesteps Bun.write stalling on pipes past 64 KB.
const { createElement } = await import("react");
const { renderToStaticMarkup } = await import("react-dom/server");
const { unified } = await import("unified");
const { default: remarkParse } = await import("remark-parse");
const { default: remarkGfm } = await import("remark-gfm");
const { default: remarkRehype } = await import("remark-rehype");
const { default: rehypeRaw } = await import("rehype-raw");
const { MarkdownFormatter } = await import("./vendor/components/blog/MarkdownFormatter.tsx");
const { seen } = await import("./record-markdown.tsx");

// The formatter warns on stderr about some HTML (a highlighted block without
// two panes, a <textarea> with children); the build reads only out.json
console.warn = () => {};
console.error = () => {};

const parser = unified().use(remarkParse).use(remarkGfm);
// The pipeline react-markdown 10.1.0 builds (createProcessor in
// node_modules/react-markdown/lib/index.js) with the formatter's plugins
const pipeline = unified()
  .use(remarkParse)
  .use([remarkGfm])
  .use(remarkRehype, { allowDangerousHtml: true })
  .use([rehypeRaw]);

function elements(markdown: string) {
  const found: { tag: string; props: string[]; classes: string[] }[] = [];
  const walk = (node: any) => {
    if (node.type === "element") {
      const props = node.properties ?? {};
      found.push({ tag: node.tagName, props: Object.keys(props), classes: (props.className ?? []).map(String) });
    }
    // A <template>'s children sit in its content fragment
    for (const child of [...(node.children ?? []), ...(node.content ? [node.content] : [])]) walk(child);
  };
  walk(pipeline.runSync(pipeline.parse(markdown)));
  return found;
}

// The article page lists each line that starts with "##" in a contents
// sidebar (LeftContents in site/vendor/app/[countryId]/research/[slug]/
// ArticleClient.tsx). These lines copy its text logic word for word, and a
// test checks they still match that file.
function contents(markdown: string): string[] {
  const headers = markdown.split("\n").filter((line) => line.startsWith("##"));
  return headers.map((header) => {
    let text = header.split(" ").slice(1).join(" ");

    // Extract text from markdown links [text](url)
    if (text.includes("[")) {
      text = text.split("[").slice(1).join("[").split("]")[0];
    }
    return text;
  });
}

function render(markdown: string, displayCategory?: string) {
  const blocks = parser.parse(markdown).children.map((node: any) => ({
    type: node.type,
    start: node.position.start.line,
    end: node.position.end.line,
    ordered: node.ordered ?? null,
  }));
  seen.length = 0;
  try {
    const html = renderToStaticMarkup(createElement(MarkdownFormatter, { markdown, displayCategory }));
    return { html, blocks, contents: contents(markdown), elements: seen.flatMap(elements) };
  } catch (err) {
    return { error: String(err), blocks, contents: contents(markdown), elements: [markdown, ...seen].flatMap(elements) };
  }
}

async function run(input: string, output: string) {
  const request = JSON.parse(await Bun.file(input).text());
  const { posts, displayCategory } = Array.isArray(request) ? { posts: request, displayCategory: undefined } : request;
  await Bun.write(output, JSON.stringify(posts.map((markdown: string) => render(markdown, displayCategory))));
}

if (Bun.argv[2] === "--serve") {
  for await (const line of console) {
    if (!line) continue;
    const [input, output] = line.split("\t");
    await run(input, output);
    process.stdout.write("done\n");
  }
} else {
  await run(Bun.argv[2], Bun.argv[3]);
}
