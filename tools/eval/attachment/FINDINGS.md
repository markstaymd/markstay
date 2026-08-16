# Attachment-survival: findings
<!-- stay:s78biQbJ hash=sha256:56c16c3adf51 -->

Question: after an edit moves, splits, merges, edits, or deletes blocks, can a
tool re-attach each original `stay:` to the **correct** block, and does it refuse
to guess when it cannot? This is the question the resolution model in
`../../SPEC.md` (§9) rests on, and the one the marker-survival eval
(`../FINDINGS.md`) explicitly did not test: that eval proved the *id token*
survives an edit, not that it stays bound to the *right* block.
<!-- stay:uFmxSNwG hash=sha256:363642c6a59e -->

Method: a resolver implements the spec's evidence ladder, strongest first:
<!-- stay:Qpa2CO2f hash=sha256:cc9dc1673d1f -->

1. **marker** , the id's marker is still present -> trust it.
2. **hash** , no marker, but exactly one block's body hash matches -> content
   survived verbatim, just lost its marker.
3. **quote** , no marker and no hash hit -> fuzzy-recover via a W3C
   `TextQuoteSelector`-style match, committed only on a *clear* winner (over
   threshold AND beating the runner-up by a margin), else **DETACHED**.
<!-- stay:nVYXiMO5 hash=sha256:134a023d4118 -->

Marker parsing and hashing are reused from the reference linter
(`../../linter/markstay_lint.py`), not reimplemented. Edits are deterministic
block operators with exact ground truth, so every id is scored right or wrong
with no judge in the loop. The headline case strips all markers first (the
AI-regeneration failure mode), forcing recovery onto hash + quote alone. Harness:
`run_attach_eval.py`; raw results `results.{json,md}`; 89 self-test checks in
`test_attach.py` (covering CommonMark-tree attachment, SPEC.md §5.2, and the
experimental heading-path arms).
<!-- stay:OHADOYsn hash=sha256:f46853a703b4 -->

Two fixture sets: the marker-survival prose docs (lexically distinct blocks) and
an adversarial fixture (`fixtures/near_dups.md`) of near-duplicate blocks that
differ by a single token, the case where content-based recovery is dangerous.
<!-- stay:PBOGjniw hash=sha256:31b832545b61 -->

## What the data says
<!-- stay:K1dvEAUO hash=sha256:5bd080d64465 -->

**1. On normal prose, the resolution model works and is safe.** 180 stripped
cells across reorder / edit / heavy-paraphrase / split / merge / delete / insert
/ decoy / clone: **99% correct re-attachment, 0% false attachment.** The work
splits as hash 81% / quote 17% / detached 2%. (Was 98% / 16% / 3% before the §9
stored-context window landed; see finding 6.)
<!-- stay:8u2sysdW hash=sha256:2af00e58a1c6 -->

| Tier | share | what it recovers |
|------|------:|------------------|
| hash | 81% | body unchanged, just moved , exact and unambiguous |
| quote | 17% | body drifted (paraphrase, split, merge) , fuzzy |
| detached | 2% | deleted block or genuine ambiguity , correctly gave up |
<!-- stay:vjzvc7ym hash=sha256:032845ea2f5c -->

The hash tier is the workhorse and it is exact: every unchanged-but-relocated
block is recovered with certainty. Quote recovers drifted blocks and held up even
under aggressive synonym-swap paraphrase (scores 0.7-0.96), because a block
carries enough redundant text that you must change most of it before recovery
fails. Deletions resolve to DETACHED (correct), and an exact duplicated twin
(`clone`) is refused rather than coin-flipped , a safe *missed*, never a wrong.
<!-- stay:QDQrjAOu hash=sha256:f4f5adc4258d -->

**2. Near-duplicate blocks are the failure mode, and it is severe.** On the
adversarial fixture, even with the guard on: **90% recovery, 3% false attachment
(2 of 72).** Per edit:
<!-- stay:oNnTs2lV hash=sha256:efe08567ec2d -->

| Edit | recovery | false-attach rate |
|------|---------:|------------------:|
| merge | 75% | 25% |
| edit_in_place | 62% | 12% |
| heavy_paraphrase | 88% | 0% |
| others | 100% | 0% |
<!-- stay:KX9llPLf hash=sha256:bb873e718a24 -->

The mechanism: when blocks differ by one token (`ingest`/`persist`/`dispatch`,
`three`/`five`/`seven`), an edit to the *true* block, or a merge that dilutes it,
makes a **pristine twin** the higher-similarity match. The id then silently binds
to the wrong block. In the worst merge case two ids landed on a twin that already
held its own id, collapsing three references onto one wrong block with no error.
This is precisely the silent mis-attachment the spec's "surface, don't reattach"
rule names, and content recovery alone walks straight into it.
<!-- stay:Of2DKMqj hash=sha256:349255efe8c6 -->

**3. The margin guard is load-bearing but not sufficient.** Requiring a clear
winner (runner-up margin) on the adversarial fixture:
<!-- stay:8FFjJcVz hash=sha256:245ca3a97219 -->

| guard | recovery | false-attach |
|-------|---------:|-------------:|
| off (margin 0) | 93% | 8% (5 wrong) |
| on (margin 0.05) | 90% | 3% (2 wrong) |
<!-- stay:E2x77n3z hash=sha256:2bd1142cf87b -->

The guard halves false attachment by converting ambiguous picks into safe
DETACHED states, at the cost of some recall. It does not eliminate them: where an
edit makes a wrong twin a *confident* winner, the guard cannot tell. So the guard
is necessary but the quote tier still cannot be trusted as authoritative on
repetitive content.
<!-- stay:j0tgaGYX hash=sha256:de528f1dee77 -->

## Conclusions for the spec
<!-- stay:w8lRBlG0 hash=sha256:4b3be0704e7d -->

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
<!-- stay:DnVs9GIt hash=sha256:32e1d70996d1 -->

## Does the context bonus ever decide anything? (2026-08)
<!-- stay:xcCbsnOS hash=sha256:adb8c837f78b -->

The bullet above says prefix/suffix context "is what has to break twin ambiguity,
and the short context tested here does not". That was an observation without a
measurement behind it. `measure_context.py` supplies the measurement, and
`results_context.md` is the output: every id that reaches the QUOTE tier is
resolved twice, once on the aggregate score the resolver uses and once on body
score alone, and the two are compared. The denominator is QUOTE opportunities,
not ids, because marker and hash resolutions never consult the selector.
<!-- stay:FIqSP9Oz hash=sha256:82766e22f13b -->

Across doc1, doc2 and `fixtures/near_dups.md`, all nine operators, markers
stripped and kept: **53 QUOTE opportunities out of 504 resolutions, of which
context changed an attachment decision on 6 (11.3%)**. That rate rose from 5
(9.4%) when the §9 stored-context window landed, which is the expected direction:
the bonus now reaches its full 0.05 instead of being starved by an unwindowed
neighbour, so it decides slightly more often. A further 4 differ only in
which block ranked first while both readings detach, three of them identical even
in the reported score; those are counted separately, because folding them into the
headline doubles the apparent rate for changes no consumer can observe.
<!-- stay:CQ0e5gVW hash=sha256:60410d559a88 -->

- **3 commits the bonus is solely responsible for, all correct.** Body-only
  scoring would have detached; the context recovered them.
- **3 recoveries the bonus prevented: 2 of them wrong, 1 correct.** This is the
  half nobody had looked at. The bonus can lift a *runner-up* more than the
  winner and destroy a margin, and on the near-duplicate fixture that is the guard
  doing its job (two false attachments stopped) at a cost of one genuine recovery
  on doc2.
- **4 where the winning block changed but the commit/detach outcome did not**,
  three of them at 1.0/1.0 where the clamp has flattened everything. Excluded from
  the headline: both readings detach, so nothing observable differs.
<!-- stay:txUSSaDC hash=sha256:262283bc256a -->

So the mechanism is live and, on this corpus, net positive: +3 correct
recoveries and 2 false attachments prevented, against 1 lost recovery. That
settles "is the §9 hazard live" as **yes**, and it settles the direction as
favourable.
<!-- stay:XDrHCIsi hash=sha256:46552ce2058d -->

Two reasons the bonus is weaker than §9 intends, both found while pinning this
and both recorded in `../../SPEC_DECISIONS.md`:
<!-- stay:GFQfRTYd hash=sha256:8a238c5b41ee -->

1. `best_match` clamps each score to 1.0 before the guard, so for *structurally
   identical* blocks (the case §9 names the bonus for) the margin is always 0 and
   the pair always detaches. Removing the clamp from the guard changes **0 of 504**
   resolutions across these corpora. That is a statement about the cases tested,
   not a clean bill of health: the operators here never produce exact duplicate
   bodies with unequal context, which is the arrangement the change is *for*, and
   in the constructed case it turns a detach into a commit. Landing it wants a
   targeted exact-twin evaluation first.
2. ~~The stored prefix/suffix are the whole neighbour block~~ **Corrected, see
   finding 6.** Through v1.2 the stored prefix/suffix were the whole neighbour
   block rather than the 48 characters §9 specifies, while the candidate side
   *was* windowed to 48, so a perfectly preserved 185-character neighbour
   contributed 0.041 instead of 0.05. Unlike the clamp this was never a design
   choice: §9 states the limit outright.
<!-- stay:tIbrf5ka hash=sha256:9574b1557bce -->

**The two were coupled, and the window half has now landed, so the clamp can
finally be priced honestly.** The clamp change looked inert on realistic prose
*because of* the window defect: a 185-character neighbour contributed 0.041, never
enough to clear the margin, so the clamp never got the chance to act. Re-run in the
post-window world it is **still 0 of 252** here, which remains a statement about
what these operators produce rather than a clean bill of health, since none of them
places an exact twin far from its original. Where that arrangement does exist, in
the conformance corpus, the option flips `near-dup-margin-guard-detaches` from a
correct detach to a committed near-duplicate.
<!-- stay:IZKv4j07 hash=sha256:5942fa4f1ebc -->

The window is applied; the clamp is not. See `../../SPEC_DECISIONS.md` for why
they were separated and why the window was recorded as a nonconformance rather
than as a future improvement.
<!-- stay:5Xq44GTQ hash=sha256:019e2a82f3b9 -->

## 6. The stored-context window, corrected (2026-08)
<!-- stay:e04cqyAw hash=sha256:6d02e2aa5f89 -->

§9 limits a stored prefix/suffix to 48 characters of the neighbour on each side.
Every implementation through v1.2 stored the whole block and windowed only the
candidate side at match time, so the bonus was capped near `2*48/(len+48)`. All
four shared the asymmetry, which is why no cross-implementation check saw it. The
reference and all four implementations now window at build time, and window the
stored side at match time as well so a selector from a pre-fix tool is not
penalised for carrying more than §9 allows.
<!-- stay:Hrg9W7Sl hash=sha256:1fa23c448d2a -->

Every number in this file above was re-measured after the correction. What moved:
<!-- stay:wuLJoSSW hash=sha256:3e666468d677 -->

| Corpus | Before | After |
|--------|--------|-------|
| Realistic prose, stripped | 98% recovery, 0% false attachment | **99%**, 0% |
| Near-duplicate fixture, guard on | 89% recovery, 4% false attachment | **90%**, **3%** |
| Both, stripped-marker denominator | 95.6% recovery, 1.2% false attachment | **96.4%**, **0.8%** |
| Context decided an outcome | 5 of 53 QUOTE opportunities | **6 of 53** |
<!-- stay:k2zAGBnn hash=sha256:176cc7280d8a -->

`measure_context.py` keeps the `pre_fix_v1_2` variant so the correction's evidence
stays reproducible after the fact rather than only before it.
<!-- stay:0qsWYabO hash=sha256:178c0a552570 -->

**One result there is worth more than the improvement**, because it is why the
corpus grew an `anchors` category: a `nonconformant_producer` variant, storing
whole neighbour blocks against a conforming resolver, changes **0 of 252**
resolutions. With the match-time window in place a storage defect is invisible to
resolution, so asserting resolutions can never catch one. The corpus now asserts
what `build_anchors` emits.
<!-- stay:AljrpFzj hash=sha256:bc574285422e -->

## 7. Exact duplicates defeat the hash tier, not just the quote tier (2026-08)
<!-- stay:fl5PNSQf hash=sha256:79d12bf564d9 -->

Found while building `twin_corpus.py` to price the clamp options, and it is the more
serious of the two things that corpus turned up.
<!-- stay:4xq94bkb hash=sha256:2fdf4f0f6e17 -->

Take a marked block that has a verbatim copy somewhere else in the document, then
edit or delete the marked one. The copy is now the **unique** block whose body hash
matches the anchor, so §9.1's tier 2 commits to it at score 1.0 and the quote tier's
margin guard never runs. Two of the five twin cases resolve this way, identically
under every clamp option, which is why no amount of scoring work touches them.
<!-- stay:KX69M1Yx hash=sha256:26e8aeda803e -->

| Case | correct | got |
|------|---------|-----|
| marked block edited, verbatim copy elsewhere | the edited block | `hash` -> the copy |
| marked block deleted, verbatim copy elsewhere | detach | `hash` -> the copy |
<!-- stay:9WUbr88g hash=sha256:de1546aeaf76 -->

Tier 2 reads a unique hash hit as "this content survived verbatim and merely lost its
marker". That holds while bodies are unique. With duplicate content in the document
it fails, and it fails *confidently*: no margin, no ambiguity signal, score 1.0. The
`hash_ambiguity` mutation in `conformance/mutation_check.py` covers the case of
several hits; this is the case of exactly one hit that is not the original.
<!-- stay:o4fvFKpZ hash=sha256:bff2ab065e0d -->

Not fixed here. Recorded because it is a tier-2 question rather than a §9 scoring
question, and because the near-duplicate framing in finding 2 above understates it:
that finding is about *similar* blocks reaching the quote tier, and this is about
*identical* ones never getting there.
<!-- stay:3dlTKDne hash=sha256:00976211f25f -->

## 8. Section position as a third contextual signal (2026-08)
<!-- stay:Qeq9WEGE hash=sha256:e7144154c311 -->

This closes the open question finding 2 left behind, which asked whether the
selector format should carry "structural position" to separate near-identical
blocks. It was measured rather than argued: `heading_arms.py`, thirteen arms over
four corpora (`results_headingpath.{json,md}`), plus the same preference run on
the real-document audit at four heading-churn levels
(`audit_cross_section.py`, `results_crosssection{,_churn50}.{json,md}`).
<!-- stay:FjRIkt25 hash=sha256:6c0f0840896d -->

**Under the pre-registered decision rule, no arm shipped.** The rule asked for
zero false attachments on the multi-section fixture; the floor is four and no arm
reaches it. Everything below is exploratory reading after that gate failed, which
is a weaker kind of evidence and is labelled as such rather than swapped in for
the gate.
<!-- stay:dEyrOZfT hash=sha256:17faf5292e1c -->

**The gate could not have discriminated the thing it was pointed at.** Those four
false attachments are decided at the **hash** tier at score 1.0: a drifted block
whose pristine twin still carries the stored body, which is finding 7's problem
one tier above the one being measured. No quote-tier arm can move them, and the
incompatibility was visible in the plan before the arms ran. The axis is not
entirely inert, though, and the earlier draft of this finding was wrong to say so:
lifting the **clamp** takes the count from four to five, and that fifth is a
quote-tier commit. So the false-attach axis discriminates the clamp and not the
heading path.
<!-- stay:bclrYe4L hash=sha256:11d01c2fbc6d -->

### What the arms measured
<!-- stay:hhut2bkJ hash=sha256:2b06bc16316c -->

On the fixture, a preference for candidates whose enclosing heading path matches
the stored one, expressed as a penalty on mismatched candidates with the clamp
kept (`D12c`), lifts recovery from **73.5% to 80.5%** over the thirteen
pre-registered operators (`73.6% -> 80.6%` including `cross_section_move_edit`,
which was added mid-experiment and is broken out for that reason). False
attachment stays at the control's four events, no case the shipped resolver
recovered is lost, and all three negative controls are bit-identical.
<!-- stay:99SD9GwH hash=sha256:49b3ce8b4065 -->

| corpus | control | `D12c` |
|--------|---------|--------|
| cross-section fixture, 13 pre-registered operators (n=572) | 73.5% / 0.7% | **80.5% / 0.7%** |
| the same plus the post-hoc operator (n=616) | 73.6% / 0.6% | 80.6% / 0.6% |
| near_dups, single-section control (n=72) | 90.1% / 2.8% | identical |
| distinct prose, regression guard (n=180) | 98.9% / 0% | identical |
| no headings, empty-path guard (n=81) | 98.8% / 0% | identical |
<!-- stay:0NfTxIxc hash=sha256:b9c346cd8715 -->

**Read that as a ceiling on an engineered corpus, not as an expected effect.**
The fixture was authored for this experiment around cross-section twins, so it
rewards the signal by construction; and its n is 44 blocks put through fourteen
operators rather than 616 independent trials, so the Clopper-Pearson intervals in
the artifact treat correlated repetitions as independent and are too narrow.
<!-- stay:lWbpR0LC hash=sha256:e52ec7a7e383 -->

### The real-document run is what makes the answer conditional
<!-- stay:O67rTCqA hash=sha256:c6ad6d400fdc -->

The same arm on ~220 of this repo's documents, ~5,700 anchors, each block drifted
in turn (append drift; the other two drifts agree on direction):
<!-- stay:HIIBqwdR hash=sha256:03751160b101 -->

| heading churn | 0% | 25% | 50% | 100% |
|---|---|---|---|---|
| A (shipped) | 93.5% / 1.27% | 93.5% / 1.27% | 93.5% / 1.27% | 93.5% / 1.27% |
| B12c (bonus, clamp kept) | 93.7% / **0.63%** | 93.7% / 0.75% | 93.7% / 0.94% | 93.5% / 1.27% |
| D12c (penalty, clamp kept) | **95.2%** / 1.22% | 94.8% / 1.39% | 94.4% / 1.58% | 93.9% / **1.72%** |
<!-- stay:nXQnNzO5 hash=sha256:14c6d6e47848 -->

**Neither form dominates, and their floors are opposite.** At full churn no path
matches: the bonus then adds nothing to anybody and degrades to the shipped
resolver exactly, while the penalty subtracts from *everybody*, which cancels the
clamp and degrades to the clamp-lifted control **A'** and its worse precision.
So the bonus buys precision at flat recovery with a floor that cannot regress,
and the penalty buys recovery at a precision cost that grows with churn. The
fixture cannot see this, because its twins are byte-identical and the clamp makes
the bonus inert there. Which one is right depends on how much an editor renames
headings, which is a property of the documents, not of the design.
<!-- stay:vCmuxRrT hash=sha256:910bfb036cdc -->

### Two results that are about method
<!-- stay:q1QV3MMn hash=sha256:68933b332b5b -->

**A bonus and a penalty are not the same experiment.** Ungated they differ by a
constant and rank identically, and the constant lands twice, because `best_match`
clamps the best and runner-up individually to 1.0 before the margin test. On a
document where *every* candidate matches, a bonus is therefore not inert: it
pushes both into the ceiling, collapses the margin and detaches. Measured on
`near_dups`, a 0.12 bonus takes recovery from 90.1% to 83.1% while carrying no
information at all; the penalty moves nothing. (The gated arms shipped here are
not a pure constant apart, since the gate is evaluated per candidate: where one
candidate clears the threshold and another does not, the two forms also differ in
ranking.) A penalty additionally cannot lift a weak body match over the commit
threshold, so the 0.5 bar stays a body-score bar.
<!-- stay:4O2AnJd4 hash=sha256:4007c53a90b1 -->

**A hard filter fails a guarantee, and pricing it needed a new operator.**
`cross_section_move` cannot see the cost, because a block that moves with its
text intact is recovered at the **hash** tier and the quote tier never runs.
`cross_section_move_edit` (moved *and* drifted, deliberately the least twin-like
block in the document) reaches tier 3, and there the filter detaches a block the
shipped resolver recovers at 0.913, which is what `SPEC.md` §2.2 requires to
survive. That single case is a constructed counterexample rather than a rate, and
it is not the filter's only loss: on the same corpus it also loses two
`heavy_paraphrase` recoveries, which are drift in place and have nothing to do
with §2.2. The real-document run is the stronger evidence, and it is brutal:
recovery **97.7% -> 72.7% -> 45.4% -> 0%** as heading churn goes 0 -> 25 -> 50 ->
100%, because a filter has no candidates left when the stored path stops
matching.
<!-- stay:BTMjf6bY hash=sha256:86cf0f1287f9 -->

### Verdict
<!-- stay:2OXYEeXH hash=sha256:54a9c2fe6285 -->

Two statements, kept apart because only the first is a result.
<!-- stay:28gMOtq0 hash=sha256:8a612f526c80 -->

**What the experiment shows.** Section position is real recovery evidence on
cross-section twins, `D12c` is the safest formulation tested, and its calibration
is not established: 0.12 was borrowed from revdown, the penalty form was selected
post hoc on the corpus that reports its gain, and on real documents it trades
precision for recall in a way that worsens as headings churn. There is a second
credible design (`B12c`) with the opposite trade and a floor that cannot regress.
<!-- stay:aWUln2dV hash=sha256:91f13bca6dc9 -->

**What the project decided, which the data neither proves nor refutes.** Not
proposed for the spec. The cost is a normative field, a derivation four
implementations must agree on bit for bit (that derivation alone took four
corrections an outside review found), and a spec version; the benefit accrues to
a consumer who has this failure, and there is none. The flag stays experimental
and canonical-Python-only, with the numbers recorded so the question is reopened
from evidence rather than from intuition.
<!-- stay:t12XE56K hash=sha256:673db23cd508 -->

## Limitations and next
<!-- stay:bDKGV1Dh hash=sha256:5a77eea2831c -->

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
- The near-duplicate residual above is the open failure mode, and on the fixtures
  it is measured on it is **entirely within-section**: `near_dups.md` contains no
  cross-section twins at all, so no structural signal can reduce that number by a
  single case (finding 8). Real documents are the other way round: sampled here,
  52% to 90% of confusions have an offender in another section.
<!-- stay:o2BIoqkh hash=sha256:abe768bdf2a8 -->
