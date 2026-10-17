// Reads source on stdin; prints the parser's AST, its HTML, and its own canonical
// rendering (the round-trip ../run.py re-parses) as one JSON object.
// `node dump.mjs` uses djot.js 0.3.2; `main` the pinned djot.js main commit;
// `carve` Carve, which reads the same fixtures as its own Djot-derived syntax.
const which = process.argv[2] ?? "";

let src = "";
for await (const chunk of process.stdin) src += chunk;

let out;
if (which === "carve") {
  const { parse, renderHtml, renderCarve } = await import("@markup-carve/carve");
  const ast = parse(src);
  out = { ast, html: renderHtml(ast), djot: renderCarve(ast) };
} else {
  const pkg = which === "main" ? "djot-main" : "@djot/djot";
  const { parse, renderHTML, renderDjot } = await import(pkg);
  const ast = parse(src, { sourcePositions: true });
  out = { ast, html: renderHTML(ast), djot: renderDjot(ast) };
}
process.stdout.write(JSON.stringify(out) + "\n");
