# Render-survival findings

Does a `stay:` marker survive the Markdown toolchain an adopter actually pushes
their `.md` through? This eval measures it across a pinned set of formatters,
renderers, and HTML sanitizers (`MATRIX.md` is the table; `run.py` regenerates it;
`versions.json` pins what was measured). Two axes, two oracles, headline first.

## Headline: the marker survives every mainstream formatter

The load-bearing axis is **source round-trip** (md → md): markstay's whole value is
edit-survival, so the question that matters is whether a formatter preserves the
marker, on the right block, when it reflows the doc. Across `prettier`, `mdformat`,
`remark`, and `pandoc`'s `gfm` writer, the answer is **yes, clean** for every block
kind (paragraph, heading, list, fence, blockquote, table) and for both placements
(marker-only chunk and trailing). The only round-trip side effect is a §8 hash drift
when a formatter rewrites a body (e.g. `mdformat` normalizes `*` bullets to `-`),
which is the correct "same block, content changed" signal, **not** a detach. The
"my formatter silently ate the marker" fear is unfounded for the common formatters.

## The one round-trip degradation: pandoc's native `markdown` writer

The plan predicted pandoc would be the scary cell, and it is the only degrading one,
but the reality is narrower than "pandoc mangles":

- `pandoc -f gfm -t gfm` **preserves** the marker cleanly in every placement.
- `pandoc -f markdown -t markdown` (the native pandoc-Markdown writer) preserves a
  **marker-only chunk** (a comment on its own line) but rewrites a **trailing inline**
  marker, one riding the last line of a paragraph or list item, into an inline raw-HTML
  code span: `` `<!-- stay:p2 -->`{=html} ``. The id token still parses, so attachment
  is not lost, but the marker is no longer a clean comment: it would render as visible
  `<!-- stay:p2 -->` text, and the `{=html}` is pandoc-specific noise. The classifier
  reports this as `MANGLED`, distinct from both `SURVIVES` and `DROPPED`.

Practical remediation (no spec change): keep markers on their own line (the
marker-only-chunk placement markstay's own stamper already emits), or use pandoc's
`gfm` writer. Both fully avoid the mangle. This is an adopter warning, not a defect to
chase upstream (out of scope per the plan).

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
| pandoc `markdown` writer, trailing marker | MANGLED | placement (marker-only chunk) or the `gfm` writer; consumer detects the missing expected marker |
| markdown-it default (`html: false`) | LEAKED | `html: true`, or consumer detects the missing expected marker |
| MDX, HTML-comment form | ERROR | the §3.2 MDX/comment-expression profile |
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
  (`DROPPED` / `RELOCATED` / `DUPLICATED`) plus a marker-cleanliness check, **not**
  grepped; `HASH_DRIFT` is explicitly not a failure. Render/sanitizer verdicts come from
  HTML inspection (visible-text extraction, comment retention, `id=` survival). The
  classifier is proven on hand-labelled survived/leaked/stripped/relocated/mangled cases
  in `test_render.py` (15/15) before the matrix is trusted.
- Parser mode is pinned to `blank-line` for the whole matrix (decision 4), so a
  "relocated" verdict reflects the tool under test, not a segmenter mismatch.
- Everything runs offline over vendored fixtures; a re-run on a version bump
  re-measures rather than trusting the old verdict.
