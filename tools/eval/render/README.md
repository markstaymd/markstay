# Render / formatter survival matrix

Does a markstay `stay:` marker survive the Markdown toolchain an adopter actually
pushes their `.md` through, a formatter, a static-site renderer, an HTML sanitizer?
This eval turns SPEC §3.1's *assertion* ("invisible in GitHub render, preserved in
raw source") into a **measured** per-tool matrix, and tests where the §3.2 MDX
profile is the required escape hatch.

`MATRIX.md` is the table; `FINDINGS.md` is the narrative (read that first). Distinct
from the attachment eval (`../attachment/`), which tests whether an id stays on the
*right block* after an edit; this tests whether the marker survives *foreign tools*
at all.

## Two axes, two oracles

1. **Source round-trip** (md → md): the load-bearing axis. Oracle = the reference
   linter's `lint_diff` (`DROPPED` / `RELOCATED` / `DUPLICATED`) plus a
   marker-cleanliness check, and for a marker that entered inside a table row, a
   row-association check (`ROW_ESCAPED`: a table is one block, so a marker that slid
   off its row is still "on the right block"). A §8 hash drift on reflow is
   **expected and not a failure**. Catches pandoc's `<!-- ... -->`{=html} code-span
   mangle, which a grep would miss.
2. **Render-emit** (md → HTML): the visibility axis. Oracle = is the marker visible
   in the rendered text (bad), is the comment retained in the HTML source (info), and,
   for `rehype-stay`'s `id=` emit, does the anchor survive a sanitizer.

## Run

```bash
./.venv/bin/python test_render.py     # the classifier self-tests (the acceptance gate)
./.venv/bin/python run.py             # write results.json + MATRIX.md + versions.json
./.venv/bin/python run.py --print     # also print the matrix
```

`run.py` runs the self-tests first and refuses to build the matrix if they fail. It
re-execs into `.venv` automatically if started with a bare `python` that cannot import
the in-process renderers.

## Setup (one-time, needs network; the measurement itself is offline)

```bash
python3 -m venv --system-site-packages .venv
./.venv/bin/pip install mdformat cmarkgfm        # python renderers; python-markdown + markdown-it-py come from system site-packages
( cd js && npm install )                          # pinned JS renderers (markdown-it, marked, remark*, @mdx-js/mdx, rehype-sanitize, dompurify)
```

`pandoc` and `prettier` are expected on `PATH`. A tool that is not installable
headless is dropped from v1 and logged in `FINDINGS.md`, not allowed to block the
matrix.

## Files

| File | Role |
|------|------|
| `run.py` | harness: table-driven over the pinned tool set, writes the matrix + results + versions |
| `classify.py` | the per-axis oracles (`roundtrip_verdict` / `render_verdict` / `mdx_verdict` / `sanitizer_verdict`) |
| `test_render.py` | classifier self-tests on hand-labelled survived/leaked/stripped/relocated/mangled cases (proven before the matrix is trusted) |
| `js/render.mjs` | the JS-side renderers, driven over stdin/stdout by `run.py` |
| `js/package.json` | pins the JS renderer versions |
| `fixtures/*.md` | the corpus: one stay per block kind, marker-only vs trailing placement, a hash-bearing marker, the §3.2 MDX form, and the in-cell table-row carrier (`rows.md`, the §14 gate) |
| `MATRIX.md` | the deliverable: the survival verdict per tool, both axes |
| `FINDINGS.md` | the narrative: what survives, what degrades, what is deferred |
| `versions.json` | the pinned versions a re-run re-measures against |

## Headline

Every mainstream formatter (`prettier`, `mdformat`, `remark`, `pandoc gfm`) preserves
the marker clean. The one round-trip degradation is pandoc's *native `markdown`
writer* mangling a *trailing inline* marker into a code span (avoid by keeping markers
on their own line, or using the `gfm` writer). On render, the marker is invisible by
default everywhere except `markdown-it`'s `html: false` default (escapes to visible
text) and MDX (HTML comments are invalid → use the §3.2 form). `rehype-stay`'s anchor
`id=` survives `DOMPurify` verbatim and `rehype-sanitize` renamed (`user-content-`).
The **table-row carrier** (a marker inside the last cell of a one-line row, the
placement §14 gates row identity on) survives every formatter but pandoc's native
`markdown` writer, which re-tables the row across lines and strands the marker on one
of its own. See `FINDINGS.md`.
