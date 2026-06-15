# LLM marker-survival: findings

Question: does the markstay marker survive when an LLM processes the document,
and does the choice of syntax change the answer? This measurement backs the AI
editing contract (`../SPEC.md` §11), the one assumption the AI use case rests on.

Method: 8 candidate marker syntaxes inserted after every block of 2 documents,
each run through 4 perturbations (rewrite, cleanup, translate, edit) on 5 models
spanning 3 vendor families , Claude Haiku 4.5 / Sonnet 4.6 / Opus 4.8 (Anthropic),
GPT-4o-mini (OpenAI), Kimi K2.6 (Moonshot) , with and without an explicit
"preserve the markers" instruction. 640 cells, 0 failures. Metric: percent of
block markers that survive *intact* (full marker + its id present in the output).
Harness and raw results: `run_eval.py`, `results.json`, `results.md`.

Reasoning-model caveat (measurement, not a finding): Kimi K2.6 spends completion
tokens on hidden `reasoning_content` before the visible answer, so a tight
`max_tokens` cap truncates its output to empty and reads as ~0% survival. The
harness uses an 8000-token ceiling and a 300s client timeout so reasoning models
get the headroom; non-reasoning models stop well under both.

## What the data says

**1. Syntax choice barely matters.** Every inline syntax (HTML comment, Pandoc
`{#id}`, kramdown IAL, Obsidian `^id`, visible `[id]` tag, MDX comment) scores
~55-67% naive and 100% instructed. The HTML comment is marginally best in the
naive case (67% vs 55%) but the gap is within noise. There is no LLM-durability
reason to prefer a visible or attribute syntax over the HTML comment.

**2. The task is the real variable, not the syntax.**

| Task | naive survival | instructed |
|------|---------------:|-----------:|
| translate | ~95% | ~98% |
| edit (targeted) | ~96% | 100% |
| rewrite | ~37% | ~97% |
| cleanup | ~5% | ~96% |

Structure-preserving operations (translate, targeted edit) keep markers whether
or not the model is told. Full-document regeneration drops markers when the model
is not told , a "clean up" wipes nearly all of them (5% naive survival), a rewrite
most (37%). Told to preserve them, both recover to ~96-100%: a spot check of a
naive cleanup stripped 0 of 10 HTML comments, and the same model told to preserve
kept 10 of 10.

**3. Out-of-band does not help; it hurts.** Putting ids in a YAML frontmatter map
instead of inline scores *worse* (45% naive / 84% instructed): models rewrite or
drop the frontmatter block. Keeping identity out of the prose does not protect it.
It is the only syntax that fails to reach 100% even when instructed.

**4. Model tier is a minor effect, and the finding holds across vendors.**
gpt4o-mini 70% / haiku 73% / kimi 76% / sonnet 82% / opus 90% overall. Better
models preserve a little more, but the instruction dominates the model. Adding a
third vendor family (Moonshot's Kimi K2.6) corroborates the headline: 100%
instructed survival on every inline syntax, the out-of-band frontmatter again the
sole laggard. The preservation-contract result is not specific to Anthropic or
OpenAI.

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

This is why the spec standardizes the AI editing contract (`../SPEC.md` §11), not
a marker syntax: the marker survives reliably *only* under an explicit
preservation contract, and that contract, not the syntax, is the lever for agent
workflows.
