// JS-side renderers/formatters for the markstay render-survival matrix.
//
//   node render.mjs <tool>      reads input on stdin, writes output on stdout.
//
// `tool` is one of the keys in TOOLS below. Round-trip tools take Markdown and
// emit Markdown; render tools take Markdown and emit HTML; sanitizer tools take
// HTML and emit HTML; `rehype-stay` takes Markdown and emits HTML with id=.
// The Python driver (run.py) owns classification; this script only runs the tool.
//
// A tool that throws (e.g. @mdx-js/mdx on an HTML comment, which is invalid MDX)
// exits non-zero with the error text on stderr, which the driver records as a
// verdict (ERROR / compile-rejected), not a harness crash.

import { unified } from "unified";
import remarkParse from "remark-parse";
import remarkStringify from "remark-stringify";
import remarkMdx from "remark-mdx";
import remarkRehype from "remark-rehype";
import rehypeParse from "rehype-parse";
import rehypeStringify from "rehype-stringify";
import rehypeSanitize from "rehype-sanitize";
import MarkdownIt from "markdown-it";
import { marked } from "marked";
import { compile as mdxCompile } from "@mdx-js/mdx";
import createDOMPurify from "dompurify";
import { JSDOM } from "jsdom";
import rehypeStay from "rehype-stay";

function readStdin() {
  return new Promise((resolve, reject) => {
    let data = "";
    process.stdin.setEncoding("utf8");
    process.stdin.on("data", (c) => (data += c));
    process.stdin.on("end", () => resolve(data));
    process.stdin.on("error", reject);
  });
}

// --- round-trip (md -> md) ------------------------------------------------

async function remarkRoundtrip(md) {
  const out = await unified().use(remarkParse).use(remarkStringify).process(md);
  return String(out);
}

async function remarkMdxRoundtrip(md) {
  // MDX-aware parse + stringify: the only md->md tool that should preserve the
  // §3.2 `{/* ... */}` comment-expression form.
  const out = await unified()
    .use(remarkParse)
    .use(remarkMdx)
    .use(remarkStringify)
    .process(md);
  return String(out);
}

// --- render-emit (md -> HTML) ---------------------------------------------

// html:true treats `<!-- ... -->` as an HTML block (passed through to the HTML
// source, invisible in the render). This is the "renders embedded HTML" config.
function markdownItHtml(md) {
  return new MarkdownIt({ html: true }).render(md);
}

// Default markdown-it (html:false) ESCAPES embedded HTML, so the comment becomes
// visible `&lt;!-- stay --&gt;` text. The most common config, and a real leak.
function markdownItDefault(md) {
  return new MarkdownIt().render(md);
}

function markedRender(md) {
  return marked.parse(md);
}

async function mdxRender(md) {
  // Returns the compiled JS module source. Throws on invalid MDX (e.g. an HTML
  // comment), which the driver records as a compile rejection.
  const compiled = await mdxCompile(md, { jsx: true });
  return String(compiled);
}

// --- HTML emit with id= (gap 4, rehype-stay) ------------------------------

async function rehypeStayEmit(md) {
  const out = await unified()
    .use(remarkParse)
    .use(rehypeStay)
    .use(remarkRehype)
    .use(rehypeStringify)
    .process(md);
  return String(out);
}

// --- sanitizers (HTML -> HTML) --------------------------------------------

async function rehypeSanitizeHtml(html) {
  // Default schema = GitHub's. It clobbers `id`/`name` with a `user-content-`
  // prefix, so this is where an emitted anchor id gets renamed (or dropped).
  const out = await unified()
    .use(rehypeParse, { fragment: true })
    .use(rehypeSanitize)
    .use(rehypeStringify)
    .process(html);
  return String(out);
}

function dompurifyHtml(html) {
  const DOMPurify = createDOMPurify(new JSDOM("").window);
  return DOMPurify.sanitize(html);
}

const TOOLS = {
  remark: { axis: "roundtrip", run: remarkRoundtrip },
  "remark-mdx": { axis: "roundtrip", run: remarkMdxRoundtrip },
  "markdown-it": { axis: "render", run: markdownItHtml },
  "markdown-it-default": { axis: "render", run: markdownItDefault },
  marked: { axis: "render", run: markedRender },
  mdx: { axis: "render", run: mdxRender },
  "rehype-stay": { axis: "emit", run: rehypeStayEmit },
  "rehype-sanitize": { axis: "sanitize", run: rehypeSanitizeHtml },
  dompurify: { axis: "sanitize", run: dompurifyHtml },
};

async function main() {
  const tool = process.argv[2];
  if (!tool || !(tool in TOOLS)) {
    process.stderr.write(
      `unknown tool: ${tool}\nknown: ${Object.keys(TOOLS).join(", ")}\n`
    );
    process.exit(2);
  }
  const input = await readStdin();
  const out = await TOOLS[tool].run(input);
  process.stdout.write(out);
}

main().catch((err) => {
  process.stderr.write(String(err && err.stack ? err.stack : err) + "\n");
  process.exit(1);
});
