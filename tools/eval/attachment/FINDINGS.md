# Attachment-survival: findings

Question: after an edit moves, splits, merges, edits, or deletes blocks, can a
tool re-attach each original `stay:` to the **correct** block, and does it refuse
to guess when it cannot? This is the question the resolution model in
`../../SPEC.md` (§9) rests on, and the one the marker-survival eval
(`../FINDINGS.md`) explicitly did not test: that eval proved the *id token*
survives an edit, not that it stays bound to the *right* block.

Method: a resolver implements the spec's evidence ladder, strongest first:

1. **marker** , the id's marker is still present -> trust it.
2. **hash** , no marker, but exactly one block's body hash matches -> content
   survived verbatim, just lost its marker.
3. **quote** , no marker and no hash hit -> fuzzy-recover via a W3C
   `TextQuoteSelector`-style match, committed only on a *clear* winner (over
   threshold AND beating the runner-up by a margin), else **DETACHED**.

Marker parsing and hashing are reused from the reference linter
(`../../linter/markstay_lint.py`), not reimplemented. Edits are deterministic
block operators with exact ground truth, so every id is scored right or wrong
with no judge in the loop. The headline case strips all markers first (the
AI-regeneration failure mode), forcing recovery onto hash + quote alone. Harness:
`run_attach_eval.py`; raw results `results.{json,md}`; 32/32 self-tests in
`test_attach.py` (the last three cover CommonMark-tree attachment, SPEC.md §5.2).

Two fixture sets: the marker-survival prose docs (lexically distinct blocks) and
an adversarial fixture (`fixtures/near_dups.md`) of near-duplicate blocks that
differ by a single token, the case where content-based recovery is dangerous.

## What the data says

**1. On normal prose, the resolution model works and is safe.** 180 stripped
cells across reorder / edit / heavy-paraphrase / split / merge / delete / insert
/ decoy / clone: **98% correct re-attachment, 0% false attachment.** The work
splits as hash 81% / quote 16% / detached 3%.

| Tier | share | what it recovers |
|------|------:|------------------|
| hash | 81% | body unchanged, just moved , exact and unambiguous |
| quote | 16% | body drifted (paraphrase, split, merge) , fuzzy |
| detached | 3% | deleted block or genuine ambiguity , correctly gave up |

The hash tier is the workhorse and it is exact: every unchanged-but-relocated
block is recovered with certainty. Quote recovers drifted blocks and held up even
under aggressive synonym-swap paraphrase (scores 0.7-0.96), because a block
carries enough redundant text that you must change most of it before recovery
fails. Deletions resolve to DETACHED (correct), and an exact duplicated twin
(`clone`) is refused rather than coin-flipped , a safe *missed*, never a wrong.

**2. Near-duplicate blocks are the failure mode, and it is severe.** On the
adversarial fixture, even with the guard on: **89% recovery, 4% false attachment
(3 of 72).** Per edit:

| Edit | recovery | false-attach rate |
|------|---------:|------------------:|
| merge | 75% | 25% |
| edit_in_place | 62% | 12% |
| heavy_paraphrase | 88% | 0% |
| others | 100% | 0% |

The mechanism: when blocks differ by one token (`ingest`/`persist`/`dispatch`,
`three`/`five`/`seven`), an edit to the *true* block, or a merge that dilutes it,
makes a **pristine twin** the higher-similarity match. The id then silently binds
to the wrong block. In the worst merge case two ids landed on a twin that already
held its own id, collapsing three references onto one wrong block with no error.
This is precisely the silent mis-attachment the spec's "surface, don't reattach"
rule names, and content recovery alone walks straight into it.

**3. The margin guard is load-bearing but not sufficient.** Requiring a clear
winner (runner-up margin) on the adversarial fixture:

| guard | recovery | false-attach |
|-------|---------:|-------------:|
| off (margin 0) | 93% | 8% (5 wrong) |
| on (margin 0.05) | 89% | 4% (3 wrong) |

The guard halves false attachment by converting ambiguous picks into safe
DETACHED states, at the cost of some recall. It does not eliminate them: where an
edit makes a wrong twin a *confident* winner, the guard cannot tell. So the guard
is necessary but the quote tier still cannot be trusted as authoritative on
repetitive content.

## Conclusions for the spec

- **Identity resolution is sound on distinct prose; treat the quote tier as
  best-effort evidence, never authority.** The trustworthy signals are the
  surviving id token and the exact `hash`; `quote` only narrows candidates and
  must surface uncertainty. This re-justifies, from a second direction, the
  marker-survival eval's mandate: keep the id token alive via the **preservation
  contract**, because once it is gone, recovery on repetitive documents is not
  reliable.
- **The `hash` field earns its place.** It silently and exactly handles 81% of
  re-attachment (every moved-but-unchanged block) and never mis-attaches. The
  spec keeps hash as the primary post-marker tier and pins its normalization
  (`../../SPEC.md` §8), since the whole tier depends on two implementations
  agreeing on the bytes.
- **Quote recovery must default to DETACHED on a near-tie.** The margin guard is
  not optional; without it, false attachment roughly doubles. A quote match
  without a clear margin is an *outdated* marker, not a re-attachment.
- **Within-block text is not enough to disambiguate twins.** This sharpens open
  question #4 (quote/selector format): the prefix/suffix context is what has to
  break twin ambiguity, and the short context tested here does not. The spec's
  selector format should carry enough surrounding context (and likely structural
  position) to separate near-identical blocks, or accept that repetitive
  documents require the id marker to survive.
- **Repetitive documents (config references, API/retry tables, checklists) are
  the risk surface.** For these, content recovery should be considered
  insufficient on its own and the preservation contract treated as mandatory, not
  advisory.

## Limitations and next

- Edits are deterministic so ground truth is exact; this measures the *resolution
  algorithm's* behavior, not real LLM paraphrase at very low similarity. The
  synthetic "heavy" paraphrase still kept ~0.7 text similarity. **Follow-up built**
  (`llm/`): an LLM-driven variant with real rewrites down to 0.3-0.5 similarity,
  ground truth from the linter's `lint_diff` over preserved markers. Result: recovery
  degrades gracefully (100% at high similarity to 36% at 0.3-0.5) while false
  attachment stays ~0% across all bands, the §9 commit rule converts lost recall
  into safe detaches, so v1 §9 holds. See `llm/FINDINGS.md`.
- Granularity is the linter's blank-line block model (whole list, whole table,
  whole fence). Row-level and nested-block attachment (the deferred v1 items) are
  not exercised.
- The quote matcher is `difflib` ratio plus exact-containment and a small
  prefix/suffix bonus. A production resolver would likely use the W3C selector
  trio with tuned context lengths; the threshold/margin numbers here are
  illustrative of the trade-off, not a recommended constant.
