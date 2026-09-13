# Renderer / formatter compatibility

markstay records a block's identity as a trailing HTML comment
(`<!-- stay:id -->`). Renderers can hide, retain, escape, or reject that comment,
depending on their configuration and the source around it. The tables below
measure marker survival and visibility on a fixed set of fixtures; they do not
guarantee identical rendering for arbitrary Markdown.

This page is the measured answer: does a `stay:` marker survive the Markdown tools an
adopter actually pushes their `.md` through, a formatter, a static-site renderer, an
HTML sanitizer? Check the measured configuration and the insertion limits below
before you stamp a repo.

!!! question "The question"
    When my `.md` passes through a formatter (it reflows the doc) or a renderer (it
    emits HTML), does the marker survive, stay on the right block, and stay invisible,
    or does some stage silently eat it?

The harness, fixtures, and every per-tool result ship with the site repo:
[`tools/eval/render/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/render)
(`run.py`, `MATRIX.md`, `FINDINGS.md`, `versions.json`). It is offline and
deterministic, and the classifier is proven on hand-labelled cases before the matrix
is trusted, so the verdicts below reproduce without re-running anything.

Legend: ✅ survives · ⚠️ survives but degraded (named in the note) · ❌ lost.

## Source round-trip (md → md), the one that matters

markstay's whole value is *edit survival*, so the load-bearing question is whether a
formatter preserves the marker, on the right block, when it reflows the document. A
content hash drift on reflow is expected and is **not** a failure (it is the correct
"same block, body changed" signal).

| Formatter | Verdict | Notes |
|-----------|---------|-------|
| `prettier` | ✅ survives | clean across every block kind; hash drifts on reflow (expected) |
| `mdformat` | ✅ survives | clean; normalizes bullet style, which drifts the hash (expected) |
| `remark` + `remark-stringify` | ✅ survives | clean, no drift |
| `pandoc` (`gfm` → `gfm`) | ✅ survives | clean in every placement |
| `remark-mdx` (MDX round-trip) | ✅ survives | preserves the [§3.2](spec.md#3-marker-syntax) `{/* stay:id */}` form |
| `pandoc` (native `markdown` writer) | ⚠️ degraded | a **trailing inline** marker is rewritten to a `` `<!-- ... -->`{=html} `` code span. **→** keep markers on their own line (a marker-only chunk, which `markstay stamp` already emits), or use the `gfm` writer. Both avoid it. |

In these block fixtures, **every tested formatter preserves separate-line markers**.
The measured degradation is pandoc's *native* `markdown` writer turning a marker that rides the end
of a paragraph or list item into an inline code span; it does not happen with the
`gfm` writer, and not at all when the marker sits on its own line.

## Render-emit (md → HTML), the visibility axis

This arm checks whether each fixture's marker is hidden or leaks as visible text.

| Renderer | Verdict | Notes |
|----------|---------|-------|
| GitHub (`cmark-gfm`) | ✅ invisible | the comment is omitted from the rendered HTML; confirms the spec's §3.1 claim |
| `markdown-it` (`html: true`) | ✅ invisible | comment retained in the HTML source, not shown to the reader |
| `marked` | ✅ invisible | comment retained, not shown |
| `python-markdown` (MkDocs) | ✅ invisible | comment retained; this is the engine behind this very site |
| `markdown-it` (default, `html: false`) | ❌ leaks | the default config HTML-escapes the comment to **visible** `<!-- stay:… -->` text. **→** set `html: true`, or rely on the consumer detecting a missing expected marker |
| MDX (`@mdx-js/mdx`) | ✅ invisible (§3.2 only) | an HTML comment is **invalid MDX** and is rejected at compile. **→** target MDX with the [§3.2](spec.md#3-marker-syntax) `{/* stay:id */}` form, which compiles away invisibly |

The two traps are both well-known once named: `markdown-it`'s default escapes embedded
HTML (so the comment becomes visible text), and MDX forbids HTML comments outright,
which is the entire reason the spec carries the §3.2 comment-expression profile.

## Table-row carrier

Row-level identity is [specified](spec.md#56-child-block-identity-table-rows-v16), and
this measurement is what it rests on: until version 1.6 the spec deferred rows "until
that carrier is shown to survive real renderers", and the run below is that
demonstration. A GFM row is one line, so a row marker has one position available to it,
inside the **last cell**, before the closing pipe. Nothing else in this matrix covered
that placement, because the table fixture puts its marker on its own line after the
table.

```md
| fruit  | crates | note                                                 |
|--------|--------|------------------------------------------------------|
| apples | 3      | picked early <!-- stay:rw1 subhash=sha256:1a2b -->    |
```

| Tool | Axis | Verdict | Notes |
|------|------|---------|-------|
| `prettier` | round-trip | ✅ survives | re-aligns the column, keeps the marker on its row |
| `mdformat` | round-trip | ✅ survives | strips the padding, keeps the marker on its row |
| `remark` + `remark-stringify` | round-trip | ✅ survives | clean |
| `pandoc` (`gfm` → `gfm`) | round-trip | ✅ survives | clean |
| `pandoc` (native `markdown` writer) | round-trip | ❌ leaves its row | re-tables into a multi-line simple table and strands the marker on a continuation line carrying none of its row's cells. **→** the same remediation as above: use the `gfm` writer |
| GitHub (`cmark-gfm`) | render | ✅ invisible | dropped from the rendered HTML, as at block placement |
| `markdown-it` (`html: true`), `marked`, `python-markdown` | render | ✅ invisible | comment retained in the HTML source, inside the cell |
| `markdown-it` (default, `html: false`) | render | ❌ leaks | the same default-config trap as everywhere else, here inside a table cell |

A cell that is the marker and nothing else survives everywhere the populated one does;
nothing collapses the empty-looking cell or drops the row.

**Seeing the one failure needed a new oracle**, which is worth knowing if you build a
check of your own: a table is a single block to every segmenter, so a marker that slides
off its row still passes a "was it dropped, was it relocated to the wrong block" test.
The matrix now also asserts that a marker which entered on a row comes out on a line
still carrying that row's other cells.

**One design note the run produced, and §5.6 took it.** A row's drift evidence has to
be computed over the cell's **trimmed content** rather than its source slice:
[§8](spec.md#8-hash-normalization) strips trailing whitespace per line but does not
collapse interior whitespace, and every table formatter re-pads cells, so a
source-slice hash would drift on a `prettier` run that changed nothing. The row body in
§5.6 is therefore the row's cells trimmed, reversibly escaped, and joined, which also
keeps cell boundaries from colliding.

## Marker insertion and rendering (v1.8)

Preserving an existing comment through a formatter is different from inserting a
new one. A marker written inside an unclosed HTML construct, after a backslash,
or against certain emphasis delimiters can change what the document displays.
[§3.4](spec.md#34-a-marker-that-shares-a-line-with-content-v18) constrains insertion:

- New block markers go on their own line. Existing same-line block markers remain
  readable and can have their digest or duplicate id refreshed in place.
- List-item and row carriers are refused when the container's raw source prefix
  contains `<` or a backslash, or `{` in MDX. Existing plain markers are masked;
  other comments and markers carrying extra evidence remain part of the check.
- At a list-item carrier only, the content of a **closed** inline code span is
  masked as well (v1.8), so `` `<repo>` `` in an earlier item no longer refuses a
  later one. The scan reads one line at a time and **stops at the first line whose
  backtick runs do not pair evenly**, so a stray backtick earlier in the container
  still refuses every carrier after it. An unclosed run masks nothing, and a row
  carrier keeps the full rule, because GFM splits cells before inline parsing.
- A row's flush carrier also refuses a prefix ending in `*`, `_`, or `~` after
  masking. New same-line markers carry only an id and optional digest fields.

The prefix is read from the document as the write began, across the whole
container up to the carrier. A character in a table header or an earlier list
item therefore can refuse a later carrier. These are lexical presence checks:
an otherwise harmless `<` in `a < b` refuses the position, and so does one in an
unclosed code span, or in any code span at a row carrier. A refused child
receives no new stay; other children and the container remain eligible.
The Python writer reports refused carriers through the CLI and
`StampResult.refused_carriers`.

This rule **does not guarantee unchanged rendering for arbitrary Markdown**.
The reference measurement covers 2417 npm documentation files. It finds 2168
refused positions out of 40508 under tree segmentation (5.35%), and 1906 of
30799 under blank-line segmentation (6.19%). Before v1.8's code-span mask the
same corpus refused 3186 (7.87%) and 2716 (8.82%); the 1018 and 810 recovered
positions are all list children, and rows are unmoved at 688 of 2762. The rule
refuses all 39 measured capture and delimiter cases. These measurements are
described in [§3.4](spec.md#34-a-marker-that-shares-a-line-with-content-v18).

With the optional parser installed, Python's [linter](linter.md) emits
`OUTSIDE_SUBSET` for documents where blank-line and CommonMark-tree segmentation
disagree. This is an informational risk signal; being inside the agreement
subset is not a rendering guarantee. Successful writes may normalize line
endings to LF. A whole-operation refusal returns the original input unchanged.

Only Python implements child carriers. The JavaScript and Rust cores write
block markers on separate lines; `remark-stay` and `rehype-stay` do not write
marker comments; `plate-stay` writes separate-line block markers and rejects
list-item and table wrappers. Their exact scopes are listed under
[implementations](implementations.md#write-safety-in-version-18).

## Anchor after a sanitizer (`rehype-stay`'s `id=`)

[`rehype-stay`](implementations.md) emits an HTML `id=` per stay so a
`doc.md#stay-id` deep link resolves in a browser. HTML sanitizers are where an `id`
attribute is most likely to be stripped or rewritten:

| Sanitizer | Verdict | Notes |
|-----------|---------|-------|
| `DOMPurify` | ✅ id kept | preserved verbatim; the deep link resolves |
| `rehype-sanitize` | ⚠️ id renamed | GitHub's schema clobbers `id` to `user-content-<id>` (the same prefix it gives heading anchors). **→** the anchor survives, but a `#stay-id` link must target the prefixed id |

No sanitizer in the set strips the anchor outright.

## What this means for an adopter

- **The tested formatters preserve these fixtures.** If you use `pandoc`, prefer
  its `gfm` writer for child markers; separate-line block markers also avoid the
  measured native-writer degradation.
- **The tested HTML-enabled renderers hide these fixture markers**, including
  GitHub and MkDocs. `markdown-it` with HTML disabled exposes them as text.
- **MDX needs the §3.2 form.** That is what the profile is for.
- **Check insertion separately from survival.** §3.4 refuses known unsafe
  placements, while the [failure-mode table](spec.md#13-failure-modes-and-how-the-spec-answers-them)
  covers toolchain configuration and consumers detecting a missing marker.

Tools left out of this first pass (Hugo/Goldmark, Jekyll/kramdown, Eleventy, and a
live cross-renderer CI gate) are listed in
[`FINDINGS.md`](https://github.com/markstaymd/markstay/tree/master/tools/eval/render),
not silently omitted. The matrix re-measures on a tool version bump rather than
trusting an old verdict; the versions it was last run against are pinned in
`versions.json`.
