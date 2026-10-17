# Prior art

markstay is not a new idea so much as a recombination of existing ones. The closest
prior art is not a single system but a combination of three lineages:

- **Block-id tools** (Obsidian, Logseq, Roam, Notion) for stable identity below the
  document level.
- **Markdown attribute and anchor syntaxes** (Pandoc, kramdown, PHP Markdown Extra,
  MyST, Docusaurus, MkDocs, GitHub) for how an id is written next to content.
- **Annotation and review systems** (W3C Web Annotation, Google Docs, GitHub review
  comments, Figma, PDF) for how an anchor survives, or fails to survive, edits.

The strongest single conclusion across all of them: **separate identity from
anchoring.** A block id should be stable logical identity. Hashes, quotes, line
numbers, and positions should be evidence used to validate or recover that identity,
never the identity itself.

## Cross-cutting findings

1. Explicit ids are the only broadly proven way to survive arbitrary edits to a
   block's text.
2. Generated heading slugs are convenient but not stable. GitHub, MyST, Docusaurus,
   and MkDocs share the same limitation: change the heading text or the duplicate
   ordering and the anchor changes.
3. Human-readable ids are pleasant for authored landmarks; generated ids are better
   for dense automatic coverage.
4. Content hashes detect change, they do not establish identity. If a paragraph is
   edited, the hash should change while the block is still the same logical block.
5. Position anchors (line, character offset) are cheap and precise at one revision
   but fragile under insertion, deletion, and reflow.
6. Quote selectors recover better than positions but fail on repeated or heavily
   rewritten text.
7. HTML comments are the best Markdown degradation path found in this survey:
   invisible in GitHub-rendered Markdown, preserved across most source workflows, and
   requiring no attribute extension.
8. Attribute syntaxes such as `{#id}` are mature but fragmented. They are visible in
   tools that do not support them, and `{#id}` is awkward or invalid in MDX v2. In
   the formats where an attribute is native (Djot, Carve), it is a good place to put
   an id and a poor one to trust without a linter: see
   [native block attributes, measured](#native-block-attributes-measured).

## Identity approaches compared

| Approach | Example | Strengths | Weaknesses | Role in markstay |
|---|---|---|---|---|
| Human-readable id | `<!-- stay:install-step -->` | Reviewable, stable in links, easy to type | Naming burden, collisions, can leak semantics | Optional authored ids |
| Generated random id | `<!-- stay:8f24c9a1 -->` | Low collision risk, no naming burden, stable across text edits | Opaque, harder to debug by hand | Default for automatic coverage |
| UUID | `id:: 64f1f3d5-...` | Globally unique, common in block tools | Long, token-heavy, visually noisy | Optional long form |
| Content hash | `hash=sha256:7a9c...` | Detects drift, supports recovery | Changes with content, cannot tell duplicates apart | Secondary evidence, not identity |
| Positional anchor | `line=42`, `char=120:180` | Compact, precise within a revision | Breaks when text moves or earlier content changes | Fallback evidence only |
| Quote selector | `quote="Retries use backoff"` | Can re-find moved text, W3C precedent | Ambiguous on duplicates, fails after heavy rewrite | Recovery evidence |
| Prefix/suffix selector | `prefix="..." suffix="..."` | Disambiguates repeated text | Token cost, still text-dependent | Optional recovery evidence |
| Generated heading slug | `#installation` | Familiar, no source noise | Breaks on text and duplicate-order changes | Convenience link only |
| HTML custom anchor | `<a name="x"></a>` | Works on GitHub | Raw HTML can be stripped, heavier near blocks | Existing fallback, heavier than comments |
| Attribute extension | `{#x}` / `{: #x}` | Maps cleanly to AST ids where supported | Not CommonMark, visible if unsupported, MDX issues | Interop bridge, not primary syntax |

## How annotation systems anchor to mutable documents

These are annotation products, not identity primitives, but their anchoring choices
show what survives editing and what does not.

| System | Anchor shape | Strategy | Survives when | Fails when | Lesson |
|---|---|---|---|---|---|
| Google Docs | Opaque Drive `anchor` + internal ranges | Transformed range over an operational model | Edits happen around the range and the app transforms it | Target text deleted, exported, or read by a third party | Internal IDs plus transformed ranges work, but opaque anchors are not portable |
| PDF annotations | Page + rectangles/quads, optional name | Fixed-layout geometry | Page geometry stays fixed | Reflow, OCR fixes, regeneration, repagination | Right for final-form artifacts, wrong for editable source |
| GitHub review comments | `commit_id` + `path` + `line` + `side` | Revision-scoped line ranges | The diff can map the line through later commits | The line changes or the file is rewritten | Pair location with revision identity; accept an "outdated" state |
| Figma comments | File key + `client_meta` coords or node id | Coordinate or node-scoped anchor | The node persists | Node deleted, restructured, or moved frames | Stable object ids beat coordinates |
| Notion comments | Comment UUID + parent block/page UUID | Stable block-id parentage + thread | The parent block exists | Block deleted, copied without thread, or exported | Block-UUID parentage is the closest product analogue to markstay |
| Sidecar Markdown reviewers | A JSON file beside the `.md`: document hash and offsets, source *and* rendered quotes, heading path | A multi-tier recovery ladder over pure evidence, with nothing written into the source | One tier still matches, and the file keeps its name and location | The block is rewritten past the similarity threshold, moves to another file, or the sidecar is lost | Evidence-only anchoring is workable, and its cost is visible: several tiers, two quote forms, and a section filter to approximate what one stable id resolves directly |

The recurring pattern: mature systems lean on stable internal object identity wherever
they own the data model, keep positions and quotes only as recovery evidence, and mark
an anchor **outdated** rather than silently reattaching it to a nearby block. The
sidecar reviewers are the instructive exception, because they do not own the data
model and cannot write to it, so they must reconstruct identity from evidence alone on
every open. markstay is an attempt to make that same block-id idea source-native and
tool-neutral, so it lives in the Markdown text instead of a single application's
database.

## Block editors with CRDT identity

The richest production analogue is a class of block-based editors. AFFiNE, built on
the open-source BlockSuite engine, is the clearest example: every document and block
is a node with a stable id. That is strong evidence the problem is worth solving. An
editor at that scale needs durable sub-document identity for collaboration, comments,
and references, and it has it.

The difference is where the id lives. BlockSuite persists block ids in a YJS CRDT
store, so identity is a property of the editor's data model and is reachable only
through that runtime. markstay puts the id in the Markdown source itself, so identity
is a property of the text and survives outside any one editor or database.

That difference is sharpest at the export boundary. BlockSuite serialises content two
ways: a lossless snapshot (JSON) that carries every block id, and lossy adapters to
Markdown, HTML, and plain text. In its own words, "adapters may result in data loss
during the conversion process, as the target format might not support all the
structures present in the original data." The Markdown adapter builds an ordinary
CommonMark/GFM tree and stringifies it; that format has no slot for a block id and the
adapter writes none, so a block's id does not survive export to Markdown. Recovering
it means returning to the CRDT document, which is why a separate reader library exists
to walk the store and pull the ids back out.

This is the clearest statement of what markstay is for. A CRDT editor cannot hand you
a Markdown file whose blocks keep their identity, because the moment the content
becomes plain text the ids are gone. markstay is the layer that keeps the id in the
`.md`. The two are not really competitors: one owns identity inside an application,
the other carries it in portable text. markstay is what lets a block editor's identity
survive the trip out to a file.

## Markdown as the AI interchange format

Markdown has become the practical surface for model input and output: it is plain
text with just enough structure for headings, lists, tables, code fences, and quotes,
and it is the native format for repositories, issues, prompts, and agent responses. It
maps directly to Git, diffs line-by-line, and stays readable in raw form.

Its missing piece is identity below the heading. Heading anchors drift, line ranges
break, and quote matching is ambiguous, which is precisely the substrate an agent
needs when it edits a document and wants its references to survive. That is the gap
markstay probes.

## Native block attributes, measured

Markdown has no slot for a block id, which is why markstay uses an HTML comment.
Djot, John MacFarlane's redesign of Markdown, and Carve, a newer language derived
from it, both have one: a `{key=value}` line before any block attaches to that block
and renders as an HTML attribute rather than text. If the slot works, the contract
(stable ids, drift evidence, recovery, a linter) could ride on it instead of on a
comment. So it was measured rather than assumed: 36 fixtures, each a shape an author
or an agent will produce, through five readers. Those were djot.js 0.3.2 (the last npm
release), djot.js `main`, jotdown (Rust), pandoc 3.12's Djot reader and Carve 0.1.9.
Read 2026-10-17; the harness, matrix and findings are in
[`tools/eval/djot/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/djot).

**Where it works.** Inside an agreement subset the slot is a good carrier:

- A key-value attribute (`{stay=ID hash=…}`) before a paragraph, list, table, code
  block, blockquote, div or footnote body lands on that block in every reader, inside
  containers too.
- It survives each tool's own formatter: every block-placed stay came back on the same
  block after djot.js's, pandoc's and Carve's canonical rewrite.
- It is invisible in rendered HTML, and a stay-shaped line inside a code block stays
  content in every reader.
- `- {stay=ID}` on a list item lands on the item's paragraph in every reader, which
  gives item identity wherever an item is one paragraph.

**Where it does not.**

- **Djot's own `#id` is the wrong slot.** An explicit identifier replaces a heading's
  generated anchor, so stamping one breaks existing links. A key-value pair does not.
- **The readers disagree at the edges.** jotdown and pandoc put a heading's attribute
  on its section, djot.js on the heading. jotdown does not read a two-line attribute
  as a block attribute. When two attributes stack before one block, djot.js and pandoc
  keep only the last, jotdown keeps both. A writer has to stay inside the shapes all of
  them read the same way.
- **One character outside the bare-value set** (`a/b` unquoted) turns the whole
  attribute into visible text in every Djot reader.
- **A marker written Markdown-style, after its block, never lands on that block.**
  In current Djot readers it becomes inline text or attaches to nothing. In djot.js
  0.3.2, which is what `npm install` gives, and in Carve, which documents that an
  attribute "floats forward across blank lines", it lands silently on the *next* block.
  Carve's formatter then writes it there. This is the failure markstay exists to
  catch, produced by the carrier itself.

**Why markstay does not ship a profile for either.** Neither has a version to
target. Djot's syntax was last tagged 0.2.0 on 2023-01-03, and djot.js last shipped
0.3.2 on 2024-12-19, with the behaviour change above among the dozens of commits on
`main` since. Carve releases weekly, but it is at 0.1, and its versioning document
allows behaviour changes in a minor release. A native slot moves the id out of a
comment; it does not remove the need for the linter, because the most likely mistake
moves an id onto the wrong block without leaving anything visibly wrong.

## Newer work on the same problem (2025 to 2026)

A scan for tools with a release or dated specification since April 2025 (read
2026-10-17) found nothing that writes a content-independent id into Markdown source
together with per-block drift evidence and a recovery rule. It found more projects
than before taking one half of it:

| Project | What it does | Where identity lives | Evidence | What it shows |
|---|---|---|---|---|
| [GEML](https://github.com/geml-spec/geml) | A document language for agents, with an MCP server, so an agent reads and writes one block by id instead of rewriting a file | `{#id}` on headings and typed blocks in its own syntax | A hash per whole version; a block without an id is keyed by a hash of its content | The use case is real. Its Markdown export drops the ids ("block ids and table-bound charts don't survive it"), which is the gap a stay fills |
| [SilverBullet](https://github.com/silverbulletmd/silverbullet) `$anchor` | A notes app over plain Markdown, anchors since 2.7.0 (May 2026) | A visible inline token, `$name` | None | States markstay's claim in plain Markdown, that anchors "survive edits to the page (positions shift, anchors do not)". The token shows as text in any other renderer |
| [robot-notes](https://github.com/cedricziel/robot-notes) | Per-document block maps for agent notes | A sidecar file | A source hash per block, "never" used to identify one | The identity/evidence split, reached independently, outside the text |
| [AGD](https://github.com/Pinperepette/agd) | A line syntax for agent documents | `[#id]` in its own syntax | An optional hash that excludes the id | The same split, in a new syntax |
| [Dirac](https://github.com/dirac-run/dirac) | A coding agent | A stable line-anchor protocol in its edit tools, not in the file | Hash anchors per line, reconciled with a diff | The same split, at line level, inside one agent's tools |

Each one reaches the conclusion this page starts from, that identity and evidence are
different things, and each keeps the identity somewhere other than portable Markdown
text, or in a form other tools render visibly.

## What the research literature says

A sweep of 2023 to 2026 papers on editing fidelity, anchoring and structured editing
(read 2026-10-17) supports the identity/evidence split and says something sharper
about how much an instruction alone can do.

- **Models damage documents they are asked to edit, silently.** Over 20 rounds of
  delegated editing across 52 domains, frontier models corrupted about a quarter of
  the content, and agentic tool use did not prevent it
  ([Laban et al., 2026](https://arxiv.org/abs/2604.15597)).
- **A preservation instruction helps and does not finish the job.** Telling a model to
  keep an edit minimal reduced over-editing measurably without removing it
  ([Zhu et al., EMNLP 2026](https://arxiv.org/abs/2609.04061)). markstay's own
  [evaluation](evaluation.md) found its instruction lifts marker survival to 96-100%
  in a single edit. Together these papers say not to read that as holding across long
  multi-step sessions, which is why the post-edit linter, not the instruction, is the
  part of the contract that has to hold.
- **A lint gate inside the edit loop works.** SWE-agent's editor rejects an edit that
  fails a lint and lets the agent retry; removing the gate lowered its score
  ([Yang et al., 2024](https://arxiv.org/abs/2405.15793)). The same shape applies to a
  stay check run after every agent edit, not only at commit.
- **Block-level edits beat offsets.** Comparisons of edit formats find that line and
  offset addressing is the fragile part and that rewriting whole blocks keeps accuracy
  at lower cost ([Cheng et al., Findings of ACL 2026](https://arxiv.org/abs/2604.27296)).
- **Recovering identity from content alone has a cost.** Code-block tracking reaches
  high precision without any in-source id, but leans on syntax trees and refactoring
  semantics that prose does not have
  ([Hasan et al., IEEE TSE 2024](https://arxiv.org/abs/2409.16185)).

Two gaps are worth stating. No paper found measures whether a model keeps an
HTML-comment id through a rewrite, so markstay's own [evaluation](evaluation.md) is
still the only direct evidence. And nothing validates or refutes the thresholds of the
quote-recovery step (§9); a corpus of aligned real revisions such as Re3-Sci
([Ruan et al., ACL 2024](https://arxiv.org/abs/2406.00197)) is a ready way to measure
them.

## Closest existing standards

- **Recovery anchoring**: W3C Web Annotation Data Model selectors, especially
  `TextQuoteSelector`, `TextPositionSelector`, and `FragmentSelector`.
  <https://www.w3.org/TR/annotation-model/>
- **Markdown syntax lineage**: Pandoc / PHP Markdown Extra / kramdown attribute
  syntax (`{#id}` and inline attribute lists).
  <https://pandoc.org/MANUAL.html> ·
  <https://michelf.ca/projects/php-markdown/extra/> ·
  <https://kramdown.gettalong.org/syntax.html#inline-attribute-lists>
- **Native block attributes**: Djot and Carve, measured above.
  <https://djot.net/> ·
  <https://github.com/markup-carve/carve>
- **Open proposal on comments**: a native Markdown comment that parsers would strip
  from the output (CommonMark issue #844, opened 2026-10-05). If adopted, tools would
  drop such comments by design; HTML comments are a different construct and are not
  affected unless tools start treating them the same way.
  <https://github.com/commonmark/commonmark-spec/issues/844>
- **Markdown product precedent**: Obsidian block references (`^block-id`).
  <https://help.obsidian.md/links>
- **Block-database precedent**: Notion comments parented by block id, plus
  Logseq / Roam block references.
  <https://developers.notion.com/reference/comment-object>
- **Block editor with CRDT identity**: AFFiNE / BlockSuite, where every block has a
  stable id persisted in a YJS CRDT store, lost on export to Markdown.
  <https://blocksuite.io/guide/adapter.html>
- **Revision / stale-state precedent**: GitHub review comments, anchored by commit,
  path, side, and line, with an outdated state.
  <https://docs.github.com/en/rest/pulls/comments>
- **Markdown rendering and id generation**: CommonMark, MDX, Docusaurus heading ids,
  MkDocs.
  <https://spec.commonmark.org/> ·
  <https://mdxjs.com/docs/what-is-mdx/> ·
  <https://docusaurus.io/docs/markdown-features/toc> ·
  <https://www.mkdocs.org/>

## What the prior art does not settle

The survey supports the identity-versus-evidence split, generated-id defaults, and the
HTML-comment degradation path. It does not settle the exact attribute grammar, hash
normalisation rules, copy-versus-move behaviour at the boundaries, or the precise
block-attachment rules. The [specification](spec.md) settles those by decision and
measurement, beyond what the survey alone could.
