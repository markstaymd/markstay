# Renderer / formatter compatibility

markstay records a block's identity as a trailing HTML comment
(`<!-- stay:id -->`). The [specification](spec.md#marker-syntax) asserts that comment
is invisible in a rendered document and preserved in the raw source. That is true for
GitHub specifically; for everyone else's toolchain it was an assumption, until it was
measured.

This page is the measured answer: does a `stay:` marker survive the Markdown tools an
adopter actually pushes their `.md` through, a formatter, a static-site renderer, an
HTML sanitizer? Check your formatter against the green list before you stamp a repo.

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
| `remark-mdx` (MDX round-trip) | ✅ survives | preserves the [§3.2](spec.md#marker-syntax) `{/* stay:id */}` form |
| `pandoc` (native `markdown` writer) | ⚠️ degraded | a **trailing inline** marker is rewritten to a `` `<!-- ... -->`{=html} `` code span. **→** keep markers on their own line (a marker-only chunk, which `markstay stamp` already emits), or use the `gfm` writer. Both avoid it. |

The headline: **every mainstream formatter preserves the marker clean.** The only
degradation is pandoc's *native* `markdown` writer turning a marker that rides the end
of a paragraph or list item into an inline code span; it does not happen with the
`gfm` writer, and not at all when the marker sits on its own line.

## Render-emit (md → HTML), the visibility axis

Here the marker should be invisible in the render (the good default for a comment) and
must never leak as visible text.

| Renderer | Verdict | Notes |
|----------|---------|-------|
| GitHub (`cmark-gfm`) | ✅ invisible | the comment is omitted from the rendered HTML; confirms the spec's §3.1 claim |
| `markdown-it` (`html: true`) | ✅ invisible | comment retained in the HTML source, not shown to the reader |
| `marked` | ✅ invisible | comment retained, not shown |
| `python-markdown` (MkDocs) | ✅ invisible | comment retained; this is the engine behind this very site |
| `markdown-it` (default, `html: false`) | ❌ leaks | the default config HTML-escapes the comment to **visible** `<!-- stay:… -->` text. **→** set `html: true`, or rely on the consumer detecting a missing expected marker |
| MDX (`@mdx-js/mdx`) | ✅ invisible (§3.2 only) | an HTML comment is **invalid MDX** and is rejected at compile. **→** target MDX with the [§3.2](spec.md#marker-syntax) `{/* stay:id */}` form, which compiles away invisibly |

The two traps are both well-known once named: `markdown-it`'s default escapes embedded
HTML (so the comment becomes visible text), and MDX forbids HTML comments outright,
which is the entire reason the spec carries the §3.2 comment-expression profile.

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

- **Formatters are safe.** Run `prettier`, `mdformat`, or `remark` over a stayed repo
  freely. If you use `pandoc`, prefer its `gfm` writer or keep markers on their own
  line.
- **Renders are invisible by default,** including on GitHub and on a MkDocs site. The
  one configuration to avoid is `markdown-it` with HTML disabled.
- **MDX needs the §3.2 form.** That is what the profile is for.
- Every degraded cell above maps to an answer the spec already gives in its
  [failure-mode table](spec.md#failure-modes-and-how-the-spec-answers-them) (the §3.2 profile, or a consumer that
  detects a missing expected marker). None of them need a change to the standard.

Tools left out of this first pass (Hugo/Goldmark, Jekyll/kramdown, Eleventy, and a
live cross-renderer CI gate) are listed in
[`FINDINGS.md`](https://github.com/markstaymd/markstay/tree/master/tools/eval/render),
not silently omitted. The matrix re-measures on a tool version bump rather than
trusting an old verdict; the versions it was last run against are pinned in
`versions.json`.
