# Findings: do markers survive LLM editing?

The whole AI case for markstay rests on one assumption: that a marker placed in a
document survives when a language model reads and rewrites that document. If a routine
"clean this up" pass silently deletes the markers, every downstream reference breaks
and the idea is dead on arrival.

Rather than assume an answer, it was measured.

!!! question "The question"
 Does the markstay marker survive when an LLM processes the document, and does the
 choice of marker syntax change the answer?

## Method

- **8 candidate syntaxes** inserted after every block: the HTML comment, Pandoc
 `{#id}`, kramdown inline attribute list, Obsidian `^id`, a visible `[id]` tag, the
 MDX comment, a UUID variant, and an out-of-band YAML frontmatter map.
- **4 tasks** run over each document: full rewrite, "clean up", translate, and a
 targeted edit.
- **5 models** across three vendor families: Claude Haiku 4.5, Claude Sonnet 4.6,
 and Claude Opus 4.8 (Anthropic), GPT-4o-mini (OpenAI), and Kimi K2.6 (Moonshot).
- **Two conditions**: with and without an explicit "preserve the markers"
 instruction.

That is 640 cells, run with 0 harness failures. The metric is the percentage of block
markers that survive *intact* (the full marker plus its id present in the output).
(Kimi K2.6 is a reasoning model that spends completion tokens on hidden reasoning
before the visible answer, so the harness gives it an 8000-token ceiling and a 300s
timeout; a tighter cap truncates its output to empty and misreads as ~0% survival.)

The harness and every per-cell result ship with the site repo:
[`tools/eval/`](https://github.com/markstaymd/markstay/tree/master/tools/eval)
(`run_eval.py`, fixtures, and `results.json`), so the numbers below are reproducible
without re-running the models.

## What the data says

**1. Syntax choice barely matters.** Every inline syntax scores ~55-67% naive and
100% instructed. The HTML comment is marginally best in the naive case (67% vs 55%),
but the gap is within noise. There is no LLM-durability reason to prefer a visible or
attribute syntax over the HTML comment.

**2. The task is the real variable, not the syntax.**

| Task | Naive survival | Instructed |
|------|---------------:|-----------:|
| translate | ~95% | ~98% |
| edit (targeted) | ~96% | 100% |
| rewrite | ~37% | ~97% |
| cleanup | ~5% | ~96% |

Structure-preserving operations (translate, targeted edit) keep markers whether or not
the model is told. Full-document regeneration (rewrite, "clean up") destroys almost all
markers when the model is not told: a spot check of a naive cleanup stripped 0 of 10
HTML comments. Told to preserve them, the same model kept 10 of 10.

**3. Out-of-band placement does not help; it hurts.** Putting ids in a YAML
frontmatter map instead of inline scores *worse* (45% naive / 84% instructed): models
rewrite or drop the frontmatter block. Keeping identity out of the prose does not
protect it; it is the only syntax that fails to reach 100% even when instructed.

**4. Model tier is a minor effect, and the finding holds across vendors.** Overall
survival was roughly GPT-4o-mini 70% / Haiku 73% / Kimi 76% / Sonnet 82% / Opus 90%.
Better models preserve a little more, but the instruction dominates the model. Adding
a third vendor family (Moonshot's Kimi K2.6) corroborates the headline: 100% instructed
survival on every inline syntax, so the preservation-contract result is not specific to
Anthropic or OpenAI.

## Conclusions

- **Keep the HTML comment as the primary syntax.** It is validated, ties or marginally
 wins on durability, and brings the rendering and GitHub advantages on top.
- **The AI-regeneration failure mode is real and severe**, not theoretical. A
 regenerating agent that does not know about markstay will silently delete nearly all
 markers. That makes two things mandatory rather than optional:
 1. an explicit preservation instruction injected into any agent that edits a
 markstay document ("preserve every `<!-- stay:... -->` marker exactly"), which
 restores survival to 100%;
 2. a post-edit [linter](linter.md) that detects dropped, duplicated, or relocated
 ids, so silent loss becomes a caught error.
- **Do not pursue frontmatter or sidecar placement for durability.** It is worse.
- **Generated, non-semantic ids remain preferable**: there is nothing to tempt a model
 into "improving" them.

The headline result behind the [specification](spec.md): the marker survives reliably
*only* under an explicit preservation contract, and that contract, not the syntax, is
what the spec standardises for agent workflows (the AI editing contract).

## What this does not test

This measured whether the *id token* survives the round trip. It did not test whether
the marker stays attached to the *correct* block after content is split, merged, or
moved. That is the harder question, and the real test of the recovery model
(`hash` + `quote`).

That second study now exists as a separate, deterministic eval:
[`tools/eval/attachment/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/attachment)
(findings in `FINDINGS.md`). Headline: on lexically distinct prose the
marker->hash->quote ladder re-attaches 98% of ids correctly with zero false
attachment (the exact `hash` tier alone does 81%), but near-duplicate blocks are the
failure mode, content recovery binds to the wrong twin a few percent of the time even
with a margin guard. So content recovery is best-effort evidence, and keeping the id
token alive via the preservation contract remains the trustworthy path.

That deterministic eval has one blind spot: its edits are synthetic, so even its
most aggressive paraphrase keeps roughly 0.7 text similarity to the original. The
genuinely hard case for the recovery model is an agent rewording prose much further
than that. A third study now tests exactly that, with real LLM rewrites:
[`tools/eval/attachment/llm/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/attachment/llm)
(findings in `FINDINGS.md`). It has a model rewrite a document while preserving the
markers (so their placement is a checkable ground truth), then strips the markers and
asks the recovery model to re-find every block from `hash` + `quote` alone, scored by
the measured before/after similarity of each block. Across 336 ids and three models,
recovery degrades gracefully as the rewrite drifts (100% at high similarity down to
about a third at 0.3-0.5), but the false-attachment rate stays near zero in **every**
similarity band: when a rewrite is too aggressive to match confidently, the recovery
model surfaces the marker as detached rather than guessing. The single wrong
attachment in the whole run was again a near-duplicate twin. The takeaway confirms the
spec's recovery parameters hold under real rewrites: content recovery loses recall on
heavy edits but does not start binding to wrong blocks, because the commit rule turns
uncertainty into an explicit detached state.
