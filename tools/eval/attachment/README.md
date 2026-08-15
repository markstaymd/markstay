# Attachment-survival eval

Does a markstay id stay attached to the **correct** block after an edit moves,
splits, merges, edits, or deletes content, and does the resolver refuse to guess
when it cannot? This is the test of the resolution model (`id` / `hash` / `quote`
from `../../SPEC.md` §2.1, §9), distinct from the marker-survival eval
(`../FINDINGS.md`), which only checked that the id *token* survives.

No network, no API key, no install: every edit is a deterministic block operator
with exact ground truth, so each id is scored right or wrong with no judge.

## Run

```bash
python run_attach_eval.py        # writes results.{json,md}
python run_attach_eval.py --granularity item   # writes results_item.{json,md}
python test_attach.py            # self-tests
```

Options: `--threshold` and `--margin` tune the quote-recovery tier;
`--docs doc1,doc2` selects the realistic fixtures (reused from `../docs/`).

`build_anchors` and `resolve` take a `mode=` argument (`"blank-line"` default,
`"commonmark"` for `../../SPEC.md` §5.2 segmentation), which MUST match between
the two calls. CommonMark mode lets a whole loose list or a blank-line-containing
fence attach as a single block; the self-tests cover the recovery of each as one
block. It is the linter's optional `markdown-it-py` extra, inherited through the
reused `parse_document`.

## Files

| File | Role |
|------|------|
| `resolver.py` | the evidence ladder: marker -> hash -> quote -> DETACHED. Reuses the linter's `parse_document` / `body_hash`. |
| `quote.py` | W3C `TextQuoteSelector`-style recovery: similarity + exact-containment + prefix/suffix tiebreak. |
| `perturb.py` | deterministic edit operators (reorder, edit, heavy-paraphrase, split, merge, delete, insert, decoy, clone) with ground-truth tracking. |
| `run_attach_eval.py` | harness, scoring, report. |
| `item_eval.py` | opt-in list-item identity: a shape x operation matrix (6 list shapes x 9 edit operations), gated per shape so benign families cannot dilute an adversarial failure. |
| `results_item.{json,md}` | the item-granularity result, with the 95% Clopper-Pearson bound on the false-attach rate. |
| `fixtures/near_dups.md` | adversarial near-duplicate blocks (the danger case). |
| `FINDINGS.md` | what the data says and what it means for the spec. |

## Headline

On lexically distinct prose: 98% correct re-attachment, 0% false attachment
(hash does 81% of the work, exactly). On near-duplicate blocks: false attachment
appears (4% with the guard, 8% without), worst on merge. Takeaway: content
recovery is best-effort evidence, not authority; the surviving id token and exact
hash are the trustworthy signals, and the margin guard (default to DETACHED on a
near-tie) is mandatory. See `FINDINGS.md`.

The experimental item-granularity matrix measures 95.0% recovery, 0.0% false
attachment (0/324), and 5.0% detach on surviving items, with a 95%
Clopper-Pearson upper bound of 0.92% on the false-attach rate. The n is the point:
with zero observed events that bound is `1 - 0.05**(1/n)`, so roughly 300
resolutions are the minimum at which a clean run can certify a ~1% bar, and an
earlier 55-resolution form could not have done so at any score.

An earlier run measured 3.6% false attachment from a near-duplicate wrong-parent
cascade. That was a resolver defect rather than a granularity limit: parents were
resolved per anchor, so a deleted list could quote-match onto its surviving
near-duplicate sibling at a wide margin, precisely because the edit had removed
the only rival that would have contested the match. Parent tiers now assign
exclusively. Re-running this matrix against the pre-fix resolver still reports six
false attachments across two shapes, so the clean result is a behaviour change and
not a weaker test.

Real LLM rewrites agree from an independent direction: `llm/` at
`--granularity item` scores 256 resolutions on gpt4o at 92.2% recovery and 0.0%
false attachment (bound 1.16%), with the attach floor landing on §9's 0.5
threshold. See `llm/FINDINGS.md`.

The prototype stays opt-in regardless. Both safety bars are met; what is still
unmeasured is the benefit half, catch precision on real item drops against the
`COLLECTION_SHRANK` count heuristic it would replace.
