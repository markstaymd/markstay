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
| `fixtures/near_dups.md` | adversarial near-duplicate blocks (the danger case). |
| `FINDINGS.md` | what the data says and what it means for the spec. |

## Headline

On lexically distinct prose: 98% correct re-attachment, 0% false attachment
(hash does 81% of the work, exactly). On near-duplicate blocks: false attachment
appears (4% with the guard, 8% without), worst on merge. Takeaway: content
recovery is best-effort evidence, not authority; the surviving id token and exact
hash are the trustworthy signals, and the margin guard (default to DETACHED on a
near-tie) is mandatory. See `FINDINGS.md`.
