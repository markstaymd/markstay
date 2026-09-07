# Render-survival findings

Does a `stay:` marker survive the Markdown toolchain an adopter actually pushes
their `.md` through? This eval measures it across a pinned set of formatters,
renderers, and HTML sanitizers (`MATRIX.md` is the table; `run.py` regenerates it;
`versions.json` pins what was measured). Two axes, two oracles, headline first.

## Headline: the marker survives every measured GFM-preserving formatter

The load-bearing axis is **source round-trip** (md → md): markstay's whole value is
edit-survival, so the question that matters is whether a formatter preserves the
marker, on the right block, when it reflows the doc. Across `prettier`, `mdformat`,
`remark`, and `pandoc`'s `gfm` writer, the answer is **yes, clean** for every block
kind (paragraph, heading, list, fence, blockquote, table) and for both placements
(marker-only chunk and trailing). The only round-trip side effect is a §8 hash drift
when a formatter rewrites a body (e.g. `mdformat` normalizes `*` bullets to `-`),
which is the correct "same block, content changed" signal, **not** a detach. The
"my formatter silently ate the marker" fear is unfounded for the measured
GFM-preserving paths. Pandoc's native non-GFM writer is the explicit exception below.

## The one round-trip degradation: pandoc's native `markdown` writer

The plan predicted pandoc would be the scary cell, and it is the only degrading one,
but the reality is narrower than "pandoc mangles":

- `pandoc -f gfm -t gfm` **preserves** the marker cleanly in every placement.
- `pandoc -f markdown -t markdown` (the native pandoc-Markdown writer) moves a
  **marker-only chunk** into a fenced raw-HTML block. Under §3.3 the marker-shaped text
  inside that fence is content, not a marker, so those stays are `DROPPED`.
- The same writer rewrites a **trailing inline** marker, one riding the last line of a
  paragraph or list item, into an inline raw-HTML code span:
  `` `<!-- stay:p2 -->`{=html} ``. Inline code is outside §3.3's mask, so the id still
  parses, but the marker is no longer a clean comment and is `MANGLED`.

The generated worst-across-fixtures verdict is `DROPPED`, the stronger failure.
Practical remediation (no spec change): use pandoc's `gfm` writer. Moving markers to
their own line does not help with the native writer because that is the placement it
turns into fenced content. This is an adopter warning, not a defect to chase upstream
(out of scope per the plan).

The 2026-09-01 regeneration corrected the earlier code-blind oracle: it now enumerates
markers through the document parser, so frontmatter and fenced code cannot vouch for
survival. Two consecutive `run.py` executions produced identical generated files. The
headline now reads `DROPPED`; the detailed `MANGLED` mechanism for inline placements
still explains those individual markers but no longer masks the lost block stays.

## Render-emit: invisible by default, with two real traps

On the visibility axis (md → HTML) the marker should be invisible in the render and
must not leak as visible text.

- **GitHub (`cmark-gfm`), `markdown-it` (`html: true`), `marked`, `python-markdown`
  (MkDocs)** all render the marker **invisible**. This confirms SPEC §3.1's headline
  claim ("invisible in GitHub-rendered Markdown") with evidence: GitHub's safe-mode
  `cmark-gfm` omits the comment from the rendered HTML entirely, so a reader never sees
  it. (Nuance: GitHub *drops* the comment from the rendered page source, while
  `markdown-it`/`marked`/`python-markdown` *retain* it as an invisible HTML comment in
  the source. Both are invisible to the reader; only the retention differs. `MkDocs` =
  `python-markdown` is markstay's own site renderer, and it retains.)
- **Trap 1, `markdown-it` in its default config (`html: false`)**: the default
  HTML-escapes the comment, so `<!-- stay:p1 -->` becomes visible `&lt;!-- stay:p1 --&gt;`
  text in a `<p>`. This is the single most likely "the reader sees the marker" failure,
  and it is a *default*, not an opt-in. Remediation: set `html: true`, or (the §13
  answer) have the consumer detect a missing expected marker.
- **Trap 2, MDX (`@mdx-js/mdx`)**: an HTML comment is **invalid MDX** and is rejected at
  compile (the compiler's own error literally says "to create a comment in MDX, use
  `{/* text */}`"). With the SPEC §3.2 comment-expression form `{/* stay:id */}` it
  compiles cleanly and the marker becomes an empty expression that renders to nothing,
  invisible. This is exactly why §3.2 exists, now demonstrated rather than asserted.
  Remediation: target MDX with the §3.2 form.

## The table-row carrier: the placement §14 originally gated row identity on

Before §5.6 settled row identity, `SPEC.md` §14 deferred it *"until that carrier is
shown to survive real renderers"*. A GFM row is one line, and §5.6 gives a writer one
canonical carrier: **inside the last cell, before the closing pipe**. A reader is
deliberately looser and accepts a `subhash` marker anywhere on an accepted body-row
source line. Until the `rows` fixture landed, no fixture here covered the canonical
writer carrier (`blocks.md` puts the table's marker on its own line *after* the table).
This measurement discharged that historical gate.

**The carrier survives the GFM round-trip tools, with the render axis's known HTML
trap.** `prettier`, `mdformat`, `remark` and pandoc's `gfm` writer all keep every row
marker inside the row it entered on. With HTML enabled, `markdown-it`, `marked` and
`python-markdown` retain the comment invisibly in the HTML source, while `cmark-gfm`
drops it for `<!-- raw HTML omitted -->` exactly as it does at block placement. The
default `markdown-it` configuration (`html: false`) instead escapes the comment into
visible cell text; its existing remediation is to enable HTML or have the consumer
detect the missing expected marker. The degenerate placement, a last cell that is the
marker and nothing else, keeps its row association everywhere the populated one does;
nothing collapses the empty-looking cell or drops the row. Pandoc's native writer is
the separate cleanliness failure below. What the formatters do change is **cell
padding**, which is a §8 hash drift on the container and nothing more.

**The one failing writer is pandoc's native `markdown` writer, and it fails on both
identity levels.** It moves each table's marker-only container stay into a fenced
raw-HTML block, where §3.3 makes it content, so `tbls`, `tblf`, and `tblc` are dropped. It also
mangles every row comment into a `` `<!-- ... -->`{=html} `` code span and re-tables
the document into pandoc's non-pipe simple-table style. Under §5.6 that output has no
accepted row candidates, so all nine row markers leave addressable rows. The six
populated rows additionally wrap the marker onto a **continuation line of its own**;
the three marker-only rows do not wrap, but non-pipe placement still addresses no child:

```
  apples   3        picked early
                    `<!-- stay:rs1 subhash=sha256:1a2b -->`{=html}
```

The fixture's generated verdict is `DROPPED` because loss of either container stay is
stronger than the row-specific failures. Looking below that precedence, the complete
§5.6 scan shows all nine row markers leaving accepted rows and their original selected
containers, and the cleanliness check shows all nine mangled into inline code spans.
Their marker bytes remain exact, so the separate exact-marker check reports them
unchanged. This deeper account is a direct diagnostic replay because the generated
verdict correctly short-circuits at the stronger dropped-container failure. The
populated-cell wrapping explains the emitted shape, not the verdict. The remediation
is the one already on this page: use the `gfm` writer.

**The shipped linter already reports a row marker rather than misreading it**, which
matters because row identity is not in any released version. Over this fixture with
`child_blocks=True` the reference emits `CHILD_UNADDRESSED` for all nine row markers
("addresses no list item; this segmenter emitted no child blocks for this block"), at
`warn` level, and in every mode it leaves the table's own `hash` bound to the table.
So a row-stamped document read by v1.3 tooling degrades into a report, not into a
wrong answer, which is what §5.5's `subhash` reservation was written to buy.

### Which placement inside the cell, measured 2026-08-29

The carrier run above answered *whether* a row marker survives. It did not ask *where
in the cell* it should sit, because until row identity was picked up nobody owed an
answer. Specifying §5.6 asks it, and the fixture now carries both placements on
tables with identical visible cells and matching source padding. The
marker ids must remain unique, so paired ids differ, but they have equal widths and
carry the same paired `subhash` values. Those identifier bytes are the only remaining
fixture difference beyond the carrier placement, and they do not change wrapping.

**On survival the two are indistinguishable, including where the carrier fails.** All
four passing round-trip tools keep all six paired markers on their rows and with their table
marker. Pandoc's native `markdown` writer drops both table markers into fenced content
and loses the row line for `rs1`, `rs2`, `rf1` and `rf2` alike: it re-tables into the
multi-line simple-table style and wraps the last cell, taking the marker onto a
continuation line carrying none of the row's other cells. Its blank lines also
separate all six paired row markers from their original container. Every effect is independent
of spaced versus flush placement. The `gfm`-writer remediation is unchanged.

*(An earlier reading of this run credited the flush placement with surviving pandoc's
native writer. That was the fixture's narrower cells, not the placement: paired against
identical short cells both placements survive, and against identical wrapping cells
both fail. The fixture was rebuilt to pair them properly.)*

**The compact marked case now reaches the oracle too.** The first two tables are
aligned to isolate the spaced/flush variable; they did not satisfy Phase 0's separate
requirement for compact marked input. The third table begins with no optional cell
padding and carries three flush row stays. All four GFM-preserving round-trip paths
keep those stays on accepted rows. `prettier` and pandoc's `gfm` writer align the table;
`mdformat` and `remark`, which have no table extension in this pinned setup, preserve
the compact source byte shape. Pandoc's native writer repeats its non-pipe failure.

**What the placement does decide is the container's hash**, and this is where the two
forms of sub-block identity stop behaving alike. §8 removes markers, then strips
trailing whitespace **per line**. A list-item marker sits at the end of its line, so
the strip is clean and stamping an item leaves its list's hash untouched. A row marker
sits before the closing pipe, so a space written in front of it survives as a double
space §8 never collapses, and **stamping a row drifts its table**. Writing the marker
flush against the cell content removes that space. When the last cell has no visible
content, the flush carrier begins immediately after the cell's opening delimiter,
`|<!-- stay:rid --> |`. In either form, the container's bytes come back byte-identical
unless a formatter re-pads them.

`carrier_hash.py` measures both populated rows and a marker-only row over the same
round-trip tools. Its insertion helper preserves whatever closing-pipe padding the
formatter supplied and asserts that flush insertion itself leaves the pre-format
container hash unchanged. The aggregate hashes below therefore include the empty-cell
carrier, not just the easier populated case:

| Formatter | Mechanism | unstamped | spaced carrier | flush carrier |
|---|---|---|---|---|
| `prettier` | parses, aligns cells | `e64ecf4fd7e0` | drifts | drifts |
| `mdformat` | no tables plugin: never a table | `1230d5216af8` | drifts | **holds** |
| `remark` | no `remark-gfm`: never a table | `1230d5216af8` | drifts | **holds** |
| `pandoc` (gfm) | parses, aligns cells | `8f6d6993bad5` | drifts | drifts |

The adjacency trace explains the marker-only result. `mdformat` and `remark` preserve
the marker immediately after the empty cell's opening delimiter. `prettier` and
pandoc's `gfm` writer insert a padding space there, even though both leave populated
carriers flush. Those aligning writers already drift in the aggregate hash table;
the two non-table text round-trippers hold the entire source, including the marker-only
row.

**Read the mechanism column before the result column.** The pinned venv has no
`mdformat-tables` plugin, so `mdformat` reads this source as a paragraph rather than a
table. `remark` likewise runs with no `remark-gfm` (`js/render.mjs:41`). Both holds are
text preservation rather than table formatting. Adding either table extension would
need a fresh measurement; the measured `remark-gfm` scratch run moved `remark` into
the aligning group and flipped its result.

So **neither measured tool that actually formats a table holds**. `prettier` and
pandoc's `gfm` writer pad every cell to its column's width, so a marker widens the whole
column and the container drifts on the next format run whatever the writer did. No
carrier can hold the hash there. A hash rule that knew what a table was could, which is
exactly the coupling §8 has never had and should not acquire for this.

**So the flush placement is never worse and is sometimes exactly right**, which is
enough to specify it, and §5.6 now imposes a container-refresh obligation beside §5.5's
existing "mint the container's stay in the same pass". The practical consequence for
§9.2: tier 2 is gated on the container's hash matching, so it is weaker for rows than
for list items on any prettier-managed document, and tiers 3 and 4 carry the load.

**One design input for whoever writes the row spec, free from this run.** §8 strips
*trailing* whitespace per line but never collapses interior whitespace, and every
table formatter re-pads cells. A row hash defined over the cell's **source slice**
would therefore drift on a `prettier` run that changed nothing; defined over the
cell's **trimmed content** it does not. In this run all four surviving formatters
changed nothing in a cell but the padding around it. The executable oracle now
enforces that distinction: after fixing pipe boundaries with markers treated as
opaque tokens, it deletes the markers, trims only §5.6's named edge whitespace, and
compares the exact ordered cell strings. A text edit, empty-cell move, or
interior-whitespace change is `ROW_ESCAPED`; alignment padding alone is not.

## Anchor after sanitizer (gap 4, `rehype-stay`'s `id=` emit)

`rehype-stay` emits an HTML `id=` per stay so `doc.md#stay-id` resolves in a browser.
Through a sanitizer:

- **`DOMPurify`** keeps the `id` **verbatim**: the deep link resolves.
- **`rehype-sanitize`** (GitHub's schema) keeps the `id` but **clobbers it to
  `user-content-<id>`**, the same prefix GitHub applies to heading anchors. The anchor
  survives, but a `#stay-id` link must target the prefixed id (or the consumer
  re-derives it). Not a strip, but a rename the on-ramp must call out.

No sanitizer in the set strips the `id` outright.

## §13 cross-check

Every red/amber cell maps to a remediation SPEC §13 already offers, no new spec
artifact:

| Cell | Verdict | §13 remediation |
|------|---------|-----------------|
| pandoc `markdown` writer, marker-only or trailing marker | DROPPED / MANGLED | the `gfm` writer; consumer detects the missing expected marker |
| markdown-it default (`html: false`) | LEAKED | `html: true`, or consumer detects the missing expected marker |
| MDX, HTML-comment form | ERROR | the §3.2 MDX/comment-expression profile |
| pandoc `markdown` writer, table and in-cell row markers | DROPPED, plus row loss | the `gfm` writer, which preserves the container and keeps each row addressable |
| rehype-sanitize | ID renamed | target the `user-content-` id (the GitHub-anchor convention) |

None needed a "§4 side-index": §4's side-index sentence covers quote/prefix/suffix
*recovery evidence*, not marker storage, so it is correctly not offered here.

## Deferred (logged, not silently dropped)

Out of v1, per the plan's representative-not-exhaustive scope:

- **Static-site generators**: Hugo/Goldmark, Jekyll/kramdown, Eleventy. The render-emit
  result is expected to track their underlying CommonMark engine (Goldmark, kramdown),
  but unmeasured here. Follow-up.
- **A live cross-renderer CI gate.** v1 is a one-shot measured matrix plus a re-runnable
  offline harness; wiring it into a renderer's own CI is a separate follow-up.
- **MDX serialize-to-Markdown round-trip beyond `remark-mdx`.** `remark-mdx` preserves
  the §3.2 form; other MDX toolchains are unmeasured.
- **markdown-it/marked plugin configurations** beyond the stock `html` toggle.

## Method note

- Round-trip verdicts are parser-verified by the reference linter's `lint_diff`
  (`DROPPED` / `RELOCATED` / `DUPLICATED`) plus a marker-cleanliness check and, for
  a marker that entered inside a table row, a row-association check (`ROW_ESCAPED`),
  **not** grepped; `HASH_DRIFT` is explicitly not a failure. Render/sanitizer verdicts come from
  HTML inspection (visible-text extraction, comment retention, `id=` survival). The
  classifier is proven on hand-labelled survived/leaked/stripped/relocated/mangled cases
  in `test_render.py` (120/120, including twenty-nine round-trip cases with a carried
  input row, twenty-one direct row-line cases, and twenty-nine complete candidate-scan
  cases) before the matrix is trusted. Exact parsed `subhash` key presence is retained
  separately from a valid digest, so `subhash=bogus` and a quoted value still route as
  child evidence while `x-subhash=...` does not; the same distinction keeps invalid-valued
  child markers out of bare selected-container evidence. A marker becomes an opaque token
  or row-stay evidence only after its whole
  §4 body parses: malformed attributes, whitespace around `=`, invalid quoted escapes,
  and bytes after a host comment closer remain table text. HTML scanning stops at the
  earlier of `-->` and `--!>` and accepts only the former; MDX scanning stops at the
  first `*/` and accepts it only when `}` follows immediately. A rejected opener does
  not consume a later opener. Marker quotes do not escape host comment syntax.
  Recognition uses a normalized-LF copy, but exact marker comparison maps every span
  back to the original source, so changing CRLF or CR inside a multiline marker is
  `MANGLED` rather than silently accepted as verbatim.
  Document-level marker enumeration excludes frontmatter and fenced code,
  judging a multiline span by its opener line so a real marker crossing into a fence is
  retained while marker-shaped content crossing out of one stays content. The same
  opener-owned span set drives overlap and multiline row refusal.
  round-trip cleanliness rejects markers parsed inside CommonMark code spans including
  padded spans. HTML visibility uses a context-aware parser, so marker syntax inside
  RCDATA such as `textarea` is visible data rather than a discarded comment. Visible
  leakage requires a marker form rather than a naked `stay:id` mention. After a `--!>`
  close, the parser arms leakage only when the bytes before it are a valid but
  incomplete marker prefix, then promotes that id only if the browser emits immediate
  visible data. A complete body followed by ordinary prose stays invisible as marker
  evidence, an unrelated later comment closer proves nothing, and a visible tail does
  not need a later `-->`. The prematurely closed form is not itself a valid §4 marker.
- Parser mode is pinned to `blank-line` for the whole matrix (decision 4), so a
  "relocated" verdict reflects the tool under test, not a segmenter mismatch.
- The row-association check runs the complete §5.6 candidate scan on both input and
  output, then compares exact normalized cell signatures and selected-container
  evidence. A bare selected-container id is required to prove that association; when
  the input container has none, the oracle fails closed even if table shape and
  occurrence are unchanged. A review counterexample moved the sole table between two
  different unstamped containers while preserving both of those weaker signals, so
  the earlier claim that they independently identified a container is withdrawn.
  Only a parsed marker carrying `subhash` on an accepted body row enters the oracle:
  headers, delimiters, standalone row-shaped lines, refused candidates, fenced source,
  and bare container markers do not. A non-pipe output is no longer a §5.6 row and
  therefore reports `ROW_ESCAPED`, even when its visible text resembles the original
  row. Parsed marker bytes are compared exactly by id as a separate §4 check, so a
  changed `subhash` or extension attribute reports `MANGLED` even when row association
  holds. Two limits remain: an input GFM row without outer pipes is not tracked because
  §5.6 refuses it, and identical rows inside one selected container remain
  indistinguishable. The paired fixture's identical rows are in different containers,
  whose table markers make a cross-table swap observable.
- Everything runs offline over vendored fixtures; a re-run on a version bump
  re-measures rather than trusting the old verdict.
