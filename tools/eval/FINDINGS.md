# LLM marker-survival: findings

Question: does the markstay marker survive when an LLM processes the document,
and does the choice of syntax change the answer? This is open question #5 in
`../SPEC_DECISIONS.md` and the one assumption the AI use case rests on.

Method: 8 candidate marker syntaxes inserted after every block of 2 documents,
each run through 4 perturbations (rewrite, cleanup, translate, edit) on 3 models
(Claude Haiku 4.5, Claude Sonnet 4.6, GPT-4o-mini), with and without an explicit
"preserve the markers" instruction. 384 cells, 0 failures. Metric: percent of
block markers that survive *intact* (full marker + its id present in the output).
Harness and raw results: `run_eval.py`, `results.json`, `results.md`.

## What the data says

**1. Syntax choice barely matters.** Every inline syntax (HTML comment, Pandoc
`{#id}`, kramdown IAL, Obsidian `^id`, visible `[id]` tag, MDX comment) scores
~50% naive and 100% instructed. The HTML comment is marginally best in the naive
case (54% vs 50%) but the gap is within noise. There is no LLM-durability reason
to prefer a visible or attribute syntax over the HTML comment.

**2. The task is the real variable, not the syntax.**

| Task | naive survival | instructed |
|------|---------------:|-----------:|
| translate | ~100% | 100% |
| edit (targeted) | ~100% | 100% |
| rewrite | near 0-16% | 100% |
| cleanup | near 0-16% | 100% |

Structure-preserving operations (translate, targeted edit) keep markers whether
or not the model is told. Full-document regeneration (rewrite, "clean up")
destroys almost all markers when the model is not told: a spot check of a naive
cleanup stripped 0 of 10 HTML comments. Told to preserve them, the same model
keeps 10 of 10.

**3. Out-of-band does not help; it hurts.** Putting ids in a YAML frontmatter map
instead of inline scores *worse* (25% naive / 75% instructed): models rewrite or
drop the frontmatter block. Keeping identity out of the prose does not protect it.

**4. Model tier is a minor effect.** gpt4o-mini 68% / haiku 73% / sonnet 77%
overall. Better models preserve a little more, but the instruction dominates the
model.

## Conclusions for the spec

- **Keep the HTML comment as the primary syntax.** It is validated, ties or
  marginally wins, and brings the rendering/GitHub advantages on top.
- **The AI-regeneration failure mode is real and severe**, not theoretical. A
  regenerating agent that does not know about markstay will silently delete
  nearly all markers. This makes two things mandatory rather than optional:
  1. An explicit preservation instruction injected into any agent that edits a
     markstay document ("preserve every `<!-- stay:... -->` marker exactly").
  2. A post-edit linter that detects dropped, duplicated, or relocated ids and
     flags drift, so silent loss becomes a caught error.
- **Do not pursue frontmatter / sidecar placement for durability.** It is worse.
- Generated, non-semantic ids remain preferable: nothing to tempt a model into
  "improving" them.

This resolves open question #5: the marker survives reliably *only* under an
explicit preservation contract, and that contract, not the syntax, is what the
spec has to standardize for agent workflows.
