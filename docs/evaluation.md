# Findings: do markers survive LLM editing?

The AI case for markstay rests on two assumptions: that a marker placed in a document
survives when a language model reads and rewrites that document, and that a surviving
id is worth more than matching the block's stored text. This page measures the first,
and [the last section](#ids-against-id-free-matching) reports what is known about the
second. If a routine "clean this up" pass silently deletes the markers, every reference
held on a marker falls back on stored evidence, and one with no evidence stored breaks.

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

**3. Frontmatter placement does not help; it hurts.** Putting ids in a YAML
frontmatter map instead of inline scores *worse* (45% naive / 84% instructed): models
rewrite or drop the frontmatter block. Moving identity out of the prose within the same
file does not protect it; it is the only syntax that fails to reach 100% even when
instructed.

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
- **Do not pursue frontmatter placement for durability.** It is worse. A separate sidecar
 file was not tested.
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
(findings in `FINDINGS.md`). Headline: with every marker stripped, on lexically distinct
prose, the hash and quote tiers re-attach 99% of ids correctly with zero false attachment
(the exact `hash` tier alone does 81%). Near-duplicate blocks are the failure mode: on
the resolver through version 1.10, content recovery binds to the wrong twin about 3% of
the time even with a margin guard. So content recovery is best-effort evidence, and a
surviving id token is the stronger signal where text cannot separate two blocks.

That deterministic eval has one blind spot: its edits are synthetic, so even its
most aggressive paraphrase keeps roughly 0.7 text similarity to the original. The
genuinely hard case for the recovery model is an agent rewording prose much further
than that. A third study now tests exactly that, with real LLM rewrites:
[`tools/eval/attachment/llm/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/attachment/llm)
(findings in `FINDINGS.md`). It has a model rewrite a document while preserving the
markers (so their placement is a checkable ground truth), then strips the markers and
asks the recovery model to re-find every block from `hash` + `quote` alone, scored by
the measured before/after similarity of each block. Across 336 ids and three models,
measured before the §9 stored-context window landed in 2026-08, recovery degrades
gracefully as the rewrite drifts (100% at high similarity down to about a third at
0.3-0.5), but the false-attachment rate stays near zero in **every**
similarity band: when a rewrite is too aggressive to match confidently, the recovery
model surfaces the marker as detached rather than guessing. The single wrong
attachment in the whole run was again a near-duplicate twin. The takeaway confirms the
spec's recovery parameters hold under real rewrites within one document: content recovery
loses recall on heavy edits but does not start binding to wrong blocks, because the commit
rule turns uncertainty into an explicit detached state.

## Ids against id-free matching

The studies above ask whether a marker survives and whether recovery finds the right
block. A separate question is what a surviving id adds over matching the block's stored
text. Within one document the answer so far is little, and it is inconclusive. Between
files there is no answer yet.

**Within one document.** A replay of one project's own Markdown history, 168 agent edits
of six documents under a linter that requires ids to be kept, compares markstay as
designed with the same ladder and no markers, 20 stamped revisions of a document apart:

| k = 20, repaired truth | misattached | missed |
|---|--:|--:|
| ids, with the ladder behind them | 0.53% | 0.00% |
| ladder, no ids | 0.51% | 0.59% |
| heading + quote, no ids | 0.43% | 0.87% |
| markers only | 0.23% | 1.17% |

The ids add 0.56 points of correct targets and no precision. Read that with its limits.
The rule fixed before the data was read takes the ids as truth, and on that truth they
pay. 109 of the ladder's 149 misattachments were the ids' own errors, and the repair that
removes them was written afterwards. The pooled repaired-truth calculation in the
published results calls this `ids-not-needed`, treating ids as independent. Among 20
subsamples with no shared edits, at most two pass both interval bars. They still share
boundary revisions and dependent blocks, and only four documents reach this gap, so
these intervals cannot certify a 1% bar. Agents here keep markers under a linter and
edit mostly in place, which is a friendly regime for both sides.

**Where ids beat the tested arms.** They separate byte-identical blocks and follow a list
split in two. The replay also records a paragraph rewritten so far that its author
assigned a new id, an explicit replacement judgment that similarity thresholds did not
make. Markers cost 7.40% of the bytes and 10.4% of the lines of the six documents.

**Between files.** One private store has 3,133 moves of an id to another document, and a
second has none. Scored on 369 draws, the call is `insufficient-evidence` at every window:
neither "ids pay for moves" nor "ids are not needed for moves" stands. The best id-free arm,
a hash lookup across the whole store, finds 95.08% [78.0, 97.7] and misattaches 0.00% [0.0,
17.7]. A search of the source document alone finds nothing. List items, 90% of the moves,
were moved verbatim by tooling, and the store-wide hash finds 309 of 310 draws. Block stays
are the doubtful half: the block the id names scores under 0.5 against the id's old text in
26 of 59 draws, so the ids may be the ones in error. How this call is computed changed after
an earlier call had been read.

These numbers come from private histories. Aggregate within-document results and the harness are in
[`tools/eval/replay/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/replay);
the source documents, findings report, hand judgments and case bodies are not.
The pinned replay and its history-dependent tests cannot be re-run from the public
repo. The cross-file harness accepts another repository, and its synthetic tests
run without the private histories.
