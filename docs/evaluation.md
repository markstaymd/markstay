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
- **3 models** across two families: Claude Haiku 4.5, Claude Sonnet 4.6, and
 GPT-4o-mini.
- **Two conditions**: with and without an explicit "preserve the markers"
 instruction.

That is 384 cells, run with 0 harness failures. The metric is the percentage of block
markers that survive *intact* (the full marker plus its id present in the output).

The harness and every per-cell result ship with the site repo:
[`tools/eval/`](https://github.com/markstaymd/markstay/tree/master/tools/eval)
(`run_eval.py`, fixtures, and `results.json`), so the numbers below are reproducible
without re-running the models.

## What the data says

**1. Syntax choice barely matters.** Every inline syntax scores about 50% naive and
100% instructed. The HTML comment is marginally best in the naive case (54% vs 50%),
but the gap is within noise. There is no LLM-durability reason to prefer a visible or
attribute syntax over the HTML comment.

**2. The task is the real variable, not the syntax.**

| Task | Naive survival | Instructed |
|------|---------------:|-----------:|
| translate | ~100% | 100% |
| edit (targeted) | ~100% | 100% |
| rewrite | near 0-16% | 100% |
| cleanup | near 0-16% | 100% |

Structure-preserving operations (translate, targeted edit) keep markers whether or not
the model is told. Full-document regeneration (rewrite, "clean up") destroys almost all
markers when the model is not told: a spot check of a naive cleanup stripped 0 of 10
HTML comments. Told to preserve them, the same model kept 10 of 10.

**3. Out-of-band placement does not help; it hurts.** Putting ids in a YAML
frontmatter map instead of inline scores *worse* (about 25% naive / 75% instructed):
models rewrite or drop the frontmatter block. Keeping identity out of the prose does
not protect it.

**4. Model tier is a minor effect.** Overall survival was roughly GPT-4o-mini 68% /
Haiku 73% / Sonnet 77%. Better models preserve a little more, but the instruction
dominates the model.

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
