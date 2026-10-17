# Djot carrier: findings

Measured 2026-10-17 over 36 fixtures and 38 stays with djot.js 0.3.2, djot.js `main`
at `3b3a9f5`, jotdown 0.10.0 and pandoc 3.12 (`MATRIX.md`, `results.json`). The
question was where a `{stay=…}` block attribute lands, so a Djot profile could state
only what the readers agree on.

**Outcome: the profile is parked, on the format's release state, not on this
evidence.** The carrier works inside an agreement subset that is easy to state. What
it lacks is a target: the last tagged Djot syntax release is 0.2.0 (2023-01-03), the
reference implementation's last npm release is 0.3.2 (2024-12-19) with 56 commits
unreleased on `main`, and one of those commits changes block-attribute behaviour this
eval depends on. A profile would have to cite either a version nearly four years old or
an untagged branch.

## What works

- **Block placement agrees on 31 of 38 stays across all four readers, and 33 across
  the current three** (djot.js 0.3.2 is superseded by `main`). Paragraphs, lists,
  tables, code blocks, blockquotes, divs, footnote bodies and thematic breaks all take a
  stay on the line before them and every reader puts it on that block, inside
  containers too.
- **A key-value stay survives every Djot writer.** All 68 block-placed observations
  land on the same block after djot.js 0.3.2's, djot.js `main`'s and pandoc's own Djot
  round-trip (jotdown has no writer). Values come back quoted (`stay="ID"`).
- **It is invisible.** No block stay's id appears in any reader's rendered HTML text;
  it becomes an HTML attribute.
- **Headings keep their anchors** with a key-value stay (`02`: `id="Install"` in every
  renderer), and lose them to `#id` (`03`: `id="head0002"`). Djot's own `#id` is the
  wrong slot, as predicted.
- **Values carry what `quote=` needs.** `}`, `%` and an escaped `"` inside a quoted
  value parse to the same string in all four (`28`).
- **Fences hold.** A stay-shaped line inside a code block is content in all four, at top
  level, in a list item, indented four spaces, and after a fence its blockquote closed
  (`16`, `18`, `19`, `20`).
- **There is a list-item carrier, which the plan said there was not.** `- {stay=X}`
  then the text on the next line puts the stay on the item's paragraph in all four
  (`10`). It is the paragraph, not the item, so it is item identity only where an item is
  one paragraph.

## Where the readers disagree (the agreement subset's edges)

| fixture | shape | djot.js | jotdown | pandoc | consequence for a profile |
|---|---|---|---|---|---|
| `02` | stay before a heading | heading | **section** | **section** | an AST reader must map a section's stay to its heading |
| `27` | specifier over two lines | para | **inline, unattached** | para | writer emits one line |
| `29` | two stacked specifiers, two stays | last wins | both | last wins | writer never stacks two stays; source-level reading is normative |
| `32` | `stay` twice in one specifier | last wins | both | last wins | same |
| `34` | `{% stay:… %}` comment | dropped | kept | dropped | a comment is not a carrier |

## Hazards that hold everywhere

- **A Markdown-habit trailing marker never lands on its block.** On the line after a
  paragraph (`06`) or an item (`12`) it becomes inline content of that block; on its own
  line (`07`) or at the end of the document (`08`) it attaches to nothing. No current
  reader puts it on the following block.
- **djot.js 0.3.2 is the exception, and it is what npm installs.** It carries a
  specifier across a blank line (`05`, `07`), so there `07`'s trailing marker lands on
  the next paragraph. `main` stopped that on 2025-12-18 ("Reset block attributes on
  blank lines"), unreleased. Anything built on the npm package inherits the misattaching
  behaviour.
- **One bad character turns the stay into visible text.** An unquoted value outside
  `[A-Za-z0-9_:-]` (`33`, `a/b`) makes the whole specifier literal text in all four,
  shown on the page. A writer must quote every value it cannot prove bare.
- **The Markdown row carrier destroys the row.** A specifier after a row's last pipe
  (`14`) turns that row into a paragraph in all four. Djot has no row slot.
- **markstay's Markdown marker is literal text in Djot** (`35`): visible, never a marker.

## Corrections to what was believed before this run

The plan's "already known" list came from one djot.js 0.3.2 probe. Two of its four
points were 0.3.2 behaviour or wrong: attachment does not run forward across a blank
line in any current reader, and there is a list-item paragraph carrier. The other two
(key-value not `#id`, not a `%` comment) hold in every reader.

## Carve (added 2026-10-17)

Carve is a Djot-derived markup created 2026-05-13 that releases weekly, found by the
2026-10-17 new-formats scan as the candidate that fixes Djot's release problem. It was
run as a fifth reader over the same fixtures (`@markup-carve/carve` 0.1.9, 2026-09-30,
the newest release at least two weeks old), in its own matrix columns and outside the
Djot agreement counts, since it is a different language that happens to read most of
these fixtures the same way.

**What is better than Djot.**

- **Most fixtures as intended:** 26 of 38 stays, against djot.js `main`'s 24.
- **A heading keeps its stay on the heading**, whether a key-value or an explicit `#id`
  (`02` to `04`), where jotdown and pandoc move it to the section. Carve's HTML gives
  headings no auto-id at all, so there is no anchor for a stay to take over.
- **Every block-placed stay survives Carve's canonical formatter**: 25 of 25.
- **A multi-line specifier works** (`27`), and an unquoted `a/b` value is accepted
  (`33`) rather than turned into visible text.

**What is worse, and it is the hazard that matters.** Carve documents that a specifier
"floats forward across blank lines to the next block, matching djot". That is the
djot.js 0.3.2 rule `main` dropped on 2025-12-18, and Carve applies it more widely than
0.3.2 did:

- **A trailing marker lands on the next block, silently, and the formatter writes it
  there.** On the line straight after a paragraph (`06`), where every Djot reader keeps it
  inline, Carve breaks the paragraph and gives the stay to the *next* paragraph. On its own
  line (`07`) the same. Its canonical output then writes `{stay=…}` above the second
  paragraph, so the misattachment is fixed into the source. An agent with Markdown habits
  produces exactly this shape.
- **The formatter can turn content into a marker.** A fence indented four spaces (`20`)
  reads as code content, but Carve's formatter rewrites it as inline code across three
  lines, and on re-read the stay-shaped line inside it is a real stay on a paragraph. An
  odd input, but it is the §3.3 failure class (content becoming markup) produced by the
  tool's own formatter.
- **Some placements become visible text**: a specifier after a table row (`14`), inside a
  cell (`15`) and inside an indented footnote body (`25`, where Carve's footnote syntax
  differs from Djot's and the formatter escapes the line as `\{stay=…}`).
- `* * *` is a list in Carve, not a thematic break (`36`): a syntax difference, not a
  carrier finding.
- A `{% … %}` comment is a block node of its own in Carve (`34`), attached to nothing.

**Verdict.** Carve is a better host than Djot on headings, values and formatter
round-trips, and a worse one on the failure markstay exists to prevent: a stay sitting
on the wrong block with nothing to say so. A Carve profile would need a mandatory lint
for a stay specifier that follows a block without a blank line or sits behind one, and
it would be pinning a 0.1 language whose versioning doc allows behaviour changes in a
minor release. Same standing as Djot: measured, not built.

## Limits

- Fixtures and their intended placements are hand-written; the matrix measures reader
  behaviour against intent, not against the Djot spec.
- djot.lua was not run. pandoc's reader is a separate Haskell implementation, so the
  four are three codebases plus two versions of one.
- Not reviewed externally: the plan was parked at Phase 0 before its review gate ran.
