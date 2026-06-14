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
   tools that do not support them, and `{#id}` is awkward or invalid in MDX v2.

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

The recurring pattern: mature systems lean on stable internal object identity wherever
they own the data model, keep positions and quotes only as recovery evidence, and mark
an anchor **outdated** rather than silently reattaching it to a nearby block. markstay
is an attempt to make that same block-id idea source-native and tool-neutral, so it
lives in the Markdown text instead of a single application's database.

## Markdown as the AI interchange format

Markdown has become the practical surface for model input and output: it is plain
text with just enough structure for headings, lists, tables, code fences, and quotes,
and it is the native format for repositories, issues, prompts, and agent responses. It
maps directly to Git, diffs line-by-line, and stays readable in raw form.

Its missing piece is identity below the heading. Heading anchors drift, line ranges
break, and quote matching is ambiguous, which is precisely the substrate an agent
needs when it edits a document and wants its references to survive. That is the gap
markstay probes.

## Closest existing standards

- **Recovery anchoring**: W3C Web Annotation Data Model selectors, especially
  `TextQuoteSelector`, `TextPositionSelector`, and `FragmentSelector`.
  <https://www.w3.org/TR/annotation-model/>
- **Markdown syntax lineage**: Pandoc / PHP Markdown Extra / kramdown attribute
  syntax (`{#id}` and inline attribute lists).
  <https://pandoc.org/MANUAL.html> ·
  <https://michelf.ca/projects/php-markdown/extra/> ·
  <https://kramdown.gettalong.org/syntax.html#inline-attribute-lists>
- **Markdown product precedent**: Obsidian block references (`^block-id`).
  <https://help.obsidian.md/links>
- **Block-database precedent**: Notion comments parented by block id, plus
  Logseq / Roam block references.
  <https://developers.notion.com/reference/comment-object>
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
block-attachment rules. Those are carried into the [draft spec](spec.md) as open
questions.
