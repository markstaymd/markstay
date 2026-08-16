# LLM-driven attachment-survival: findings

Question: does the resolution model in `../../SPEC.md` §9 hold up under **real**
low-similarity LLM rewrites? The deterministic attachment eval (`../FINDINGS.md`)
answered the structural cases (move / split / merge / delete) with exact ground
truth, but its hardest synthetic rewrite still kept ~0.7 text similarity. The
genuinely hard regime, an agent rewording prose down to 0.3-0.5 similarity, was
the one untested place v1 §9 could still break. This eval closes that gap.

## These numbers predate the §9 stored-context window (2026-08)

**Every number in this file was measured before the stored prefix/suffix was
windowed to §9's 48 characters, and it cannot be re-measured without paying for
the cells again.** `results.json` keeps per-id derived data only (category,
clamped score, target, gold) and not the rewritten Markdown, so there is nothing
on disk to replay a resolver change against. `demo_fixture.json` is one captured
before/after pair, which is a demonstration, not a sample.

Direction, not magnitude, is what can be said: the correction only ever *raises*
the context bonus, and on the deterministic corpora it improved both headline
numbers (recovery 95.6% -> 96.4%, false attachment 1.2% -> 0.8%). On the one
captured LLM pair it changes no decision at all. So these figures are most likely
a slight understatement of current behaviour rather than an overstatement, but
they are stale figures either way and should be cited with the date, not as the
current recovery rate.

## Method (judge-free ground truth from one generation)

For each (doc, rewrite task, model) cell:

1. Annotate a clean doc, every block gets a `stay:` marker.
2. Ask the model to rewrite the prose, with the §11 preservation instruction so
   it keeps every marker on the same block. An *instructed* rewrite keeps ~100% of
   markers (the marker-survival eval), so the preserved placement is a trustworthy
   gold label for where each block's content went.
3. Validate that label with the linter's `lint_diff`: any id the rewrite dropped,
   duplicated, or relocated is excluded (no clean ground truth).
4. **Strip those markers** from the same rewritten text. That stripped doc is the
   resolver's input, identical to what a naive rewrite (markers dropped, the real
   failure mode) would produce. The resolver must now recover every id from hash +
   quote alone.
5. Score recovery against the gold block, bucketed by the *measured* before/after
   text similarity of each block.

No judge, no human in the loop: ground truth is the model's own preserved-marker
placement, checked deterministically by the linter. Harness:
`run_llm_attach_eval.py`; raw data `results.{json,md}`; 29/29 offline self-tests in
`test_llm_attach.py` (the LLM is faked with controlled strings + the `perturb`
operators so the pipeline is verified without an API key).

Run: 3 models (sonnet, gpt4o, opus) × 2 distinct-prose docs + the near-duplicate
adversarial fixture × 4 rewrite intensities (copyedit → rewrite → restructure →
reword). 336 scored ids.

## What the data says

**1. v1 §9 holds: recovery degrades gracefully with similarity, and false
attachment does NOT climb in the low-similarity regime.** This is the headline and
the thing Phase 1 was built to test.

| before/after similarity | scored | recovery | false-attach |
|-------------------------|-------:|---------:|-------------:|
| 0.9-1.0 | 172 | 100% | 0% |
| 0.7-0.9 | 56 | 84% | 2% |
| 0.5-0.7 | 80 | 91% | 0% |
| 0.3-0.5 | 28 | 36% | **0%** |

As the rewrite drifts further from the original the quote tier recovers less (36%
at 0.3-0.5), but it converts the lost recall into **safe DETACHED states, not
wrong attachments**: 18 of the 28 ids in the 0.3-0.5 band resolve to a correct
`missed` (safe detach), zero to `wrong`. The §9 commit rule (score ≥ 0.5 AND a
margin ≥ 0.05 over the runner-up) is exactly what produces this: when the rewrite
is too aggressive to match confidently, the resolver surfaces the marker as
outdated (§10) rather than guessing. **The risk Phase 1 set out to find, that real
low-similarity rewrites would force a v1 §9 revision, did not materialize.**

**2. On distinct prose the model is safe; the only false attachment is the known
near-duplicate case.** Across 240 distinct-prose ids (doc1, doc2): **0 wrong.**
The entire run produced **one** false attachment, on the near-duplicate fixture, a
gpt4o rewrite at 0.84 similarity that the resolver committed with score 0.94, the
margin guard could not catch it because the pristine twin was an even closer match.
This is the exact "necessary but not sufficient" guard limit the deterministic eval
already documented; this eval reproduces it under real rewrites and finds nothing
new beyond it.

| document | scored | recovery | false-attach |
|----------|-------:|---------:|-------------:|
| doc1 | 120 | 96% | 0% |
| doc2 | 120 | 95% | 0% |
| near_dups | 96 | 76% | 1% |

**3. Under real rewrites the quote tier carries the majority of the work.** Tier
split: hash 39% / quote 51% / detached 10%. This inverts the deterministic eval
(hash 81% / quote 16%), because deterministic operators left many blocks byte-identical
(reorder, insert) whereas a real reword changes almost every block. So the quote
tier is not a rarely-exercised safety net here; it is the primary recovery path for
genuine edits, and it is precisely the tier these numbers stress-tested.

**4. The §11 AI-editing contract is honoured in practice.** 0 of 336 ids were
dropped, duplicated, or relocated by the instructed rewrites (excluded = 0). An
instructed rewrite preserves marker attachment essentially perfectly, corroborating
the marker-survival eval's "100% instructed" result from a second direction and
re-confirming that the durable deliverable is the preservation contract, not the
marker syntax.

## Conclusions for the spec

- **Keep v1 §9 as written.** 48-char context, threshold 0.5, margin 0.05 survive
  real LLM rewrites down to 0.3 similarity: recovery falls off but false attachment
  does not rise, because the commit rule turns low-confidence matches into safe
  detaches. No parameter change is justified by this data.
- **The hash + preservation-contract combination remains the trustworthy core.**
  Quote recovery is best-effort: it recovered ~84-91% in the mid bands and only 36%
  at 0.3-0.5. Where it cannot recover, it correctly detaches. The reliable signals
  are still the surviving id (kept via §11) and the exact hash (§8).
- **Near-duplicate blocks remain the one residual risk, unchanged.** The single
  false attachment is the documented twin case; the margin guard halves but does not
  eliminate it. The standing guidance holds: on repetitive documents (config
  references, retry tables, checklists) the preservation contract is mandatory, not
  advisory, because content recovery alone can confidently pick the wrong twin.

## Limitations and next

- Ground truth is the instructed rewrite's preserved-marker placement. It is
  validated by `lint_diff` (no drop/dup/relocate), but it inherits the model's own
  judgement of "same block". With 0 contract violations across 336 ids the label was
  clean here; on documents where models do split/merge under instruction, those ids
  would be excluded rather than mislabeled.
- Rewrites were constrained to keep blocks 1:1 (same set, same order) so the
  per-block similarity and id→block mapping stay clean. Structural rewrites (the
  model merging or splitting blocks) are the deterministic eval's domain; combining
  real low-similarity drift *with* real structural change is the untested corner.
- The 0.3-0.5 band has 28 ids; the sub-0.3 band did not populate (instructed,
  meaning-preserving rewrites rarely drift that far). Pushing into sub-0.3 would need
  rewrites that change meaning, at which point "correct attachment" stops being
  well-defined.

---

# Item granularity (experimental child blocks), 2026-08-14

Same judge-free method one level down, on a list-heavy corpus
(`list_tracker`, `list_readme`, `list_checklist`), run on **gpt4o**: a
deliberately cross-family choice, since a format claim is stronger when it holds
on a model the format was never designed against.

**256 scored resolutions, 92.2% recovery, 0.0% false attachment**, 95%
Clopper-Pearson upper bound **1.16%**. Zero exclusions: gpt4o preserved every
marker in all 12 cells, including the two most aggressive rewrite tasks, which is
a §11 preservation result at item granularity in its own right.

| measured similarity | scored | recovery | false-attach |
|---------------------|-------:|---------:|-------------:|
| 0.0-0.3 | 10 | 0% | 0% |
| 0.3-0.5 | 7 | 0% | 0% |
| 0.5-0.7 | 48 | 98% | 0% |
| 0.7-0.9 | 97 | 98% | 0% |
| 0.9-1.0 | 94 | 99% | 0% |

**The bands land on the §9 constants.** The lowest similarity ever attached is
0.51, against a commit threshold of 0.5; nothing below it was attached, and
nothing at any similarity was misattached. Degradation is entirely by detaching,
which is §10's "surface, don't guess" behaving as specified rather than as an
aspiration. The highest-similarity detach sits at 0.94, where the margin guard
refuses a tie between repeated bullets: threshold governs the floor, margin
governs ambiguity, and one run shows both.

**The quote tier carries item granularity.** Tier shares are quote 64%, hash 15%,
detached 8%, inverting the block-level result where exact hash did 81% of the
work. Rewording a bullet changes its text, so the hash rarely survives and the
near-duplicate-prone tier does the heavy lifting. It still produced zero false
attachments, which is the specific fear §5.1 recorded when it deferred item
identity.

By task, recovery tracks rewrite intensity as expected: copyedit 100%, rewrite
97%, reword 88%, restructure 83% (all 0% false-attach). By document,
`list_checklist` is weakest at 82%, entirely through safe detaches on its
repeated `Done`/`Pending` labels: the designed degradation, measured rather than
asserted.

**Scope.** One model, one family, 12 calls. It is evidence that the ladder holds
under real rewrites, not a substitute for the deterministic matrix
(`../item_eval.py`, 324 resolutions) that certifies the false-attach bar. Claude
models were not run: no local API credential exists, by design.
