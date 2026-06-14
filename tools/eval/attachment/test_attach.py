#!/usr/bin/env python3
"""Self-tests for the attachment-survival eval.

Dependency-free, no network. Run:  python test_attach.py
Asserts invariants of the resolution model, not brittle exact counts, except
where an exact count is the point (e.g. a deleted block must detach).
"""

from __future__ import annotations

import sys
from pathlib import Path

import perturb as PB
import resolver as R
from quote import Selector, best_match

HERE = Path(__file__).parent
DOC1 = (HERE.parent / "docs" / "doc1.md").read_text()
ADV = (HERE / "fixtures" / "near_dups.md").read_text()

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def _run(base, op, strip, threshold=0.5, margin=R.DEFAULT_MARGIN):
    before, pbs = PB.annotate(base)
    anchors = R.build_anchors(before)
    after_pbs, adj = PB.OPERATORS[op](pbs)
    after = PB.serialize(after_pbs, strip=strip)
    truth = PB.default_truth(after_pbs)
    truth.update(adj)
    res = R.resolve(anchors, after, threshold=threshold, margin=margin)
    return anchors, truth, res


def cats(anchors, truth, res):
    out = {"correct": 0, "wrong": 0, "missed": 0, "correct_detach": 0, "false_attach": 0}
    for a in anchors:
        r, t = res[a.id], truth[a.id]
        if t["accept"] is None:
            out["correct_detach" if r.method == "detached" else "false_attach"] += 1
        elif r.method == "detached":
            out["missed"] += 1
        elif r.target in t["accept"]:
            out["correct"] += 1
        else:
            out["wrong"] += 1
    return out


# --- anchors / parsing reuse ---------------------------------------------

def test_anchors_one_per_block():
    before, pbs = PB.annotate(DOC1)
    anchors = R.build_anchors(before)
    n_blocks = sum(len(pb.ids) for pb in pbs)
    check("one anchor per identified block", len(anchors) == n_blocks)
    check("anchor ids match block ids",
          {a.id for a in anchors} == {i for pb in pbs for i in pb.ids})


# --- tiers ----------------------------------------------------------------

def test_marker_tier():
    anchors, truth, res = _run(DOC1, "reorder", strip=False)
    check("markers kept -> all resolve by marker",
          all(res[a.id].method == "marker" for a in anchors))
    check("markers kept -> all correct", cats(anchors, truth, res)["correct"] == len(anchors))


def test_hash_tier():
    anchors, truth, res = _run(DOC1, "reorder", strip=True)
    check("stripped + reorder -> hash recovers every block",
          all(res[a.id].method == "hash" for a in anchors))
    check("stripped + reorder -> all correct, none wrong",
          cats(anchors, truth, res)["wrong"] == 0)


def test_quote_tier():
    anchors, truth, res = _run(DOC1, "heavy_paraphrase", strip=True)
    used_quote = any(res[a.id].method == "quote" for a in anchors)
    c = cats(anchors, truth, res)
    check("heavy paraphrase exercises the quote tier", used_quote)
    check("heavy paraphrase -> no false attachment on distinct blocks", c["wrong"] == 0)


def test_every_anchor_resolved():
    anchors, _, res = _run(DOC1, "merge", strip=True)
    check("every anchor gets a resolution", all(a.id in res for a in anchors))


# --- structural edits -----------------------------------------------------

def test_delete_detaches():
    anchors, truth, res = _run(DOC1, "delete", strip=True)
    deleted = [a.id for a in anchors if truth[a.id]["accept"] is None]
    check("delete produces at least one detach target", len(deleted) >= 1)
    check("deleted ids resolve to DETACHED",
          all(res[i].method == "detached" for i in deleted))
    check("delete -> no false attach", cats(anchors, truth, res)["false_attach"] == 0)


def test_split_lands_on_a_child():
    anchors, truth, res = _run(DOC1, "split", strip=True)
    split_ids = [a.id for a in anchors if len(truth[a.id]["accept"] or []) > 1]
    check("split marks a multi-child acceptance set", len(split_ids) >= 1)
    for i in split_ids:
        r = res[i]
        check(f"split id {i} lands on a child or safely detaches",
              r.method == "detached" or r.target in truth[i]["accept"])


def test_merge_both_ids_to_merged_block():
    # On distinct (non-adversarial) blocks the merged pair should co-locate.
    anchors, truth, res = _run(DOC1, "merge", strip=True)
    check("merge on distinct blocks -> no false attach",
          cats(anchors, truth, res)["false_attach"] == 0)
    check("merge on distinct blocks -> no wrong",
          cats(anchors, truth, res)["wrong"] == 0)


# --- the guard ------------------------------------------------------------

def test_clone_refuses_to_guess():
    # An identical twin with the marker stripped is unrecoverable; the resolver
    # must DETACH rather than coin-flip onto one of the twins.
    anchors, truth, res = _run(DOC1, "clone", strip=True)
    c = cats(anchors, truth, res)
    check("clone never false-attaches", c["wrong"] == 0)
    check("clone forces at least one safe miss (the twin)", c["missed"] >= 1)


def test_margin_guard_reduces_false_attach():
    # The adversarial fixture is the only place a false attach is reachable.
    _, _, res_off = _run(ADV, "edit_in_place", strip=True, threshold=0.3, margin=0.0)
    anchors, truth, res_on = _run(ADV, "edit_in_place", strip=True, threshold=0.5, margin=0.05)
    a2, t2, _ = _run(ADV, "edit_in_place", strip=True, threshold=0.3, margin=0.0)
    wrong_off = cats(a2, t2, res_off)["wrong"]
    wrong_on = cats(anchors, truth, res_on)["wrong"]
    check("guard off exposes false attachments on near-duplicates", wrong_off > 0)
    check("guard on reduces (or holds) false attachments", wrong_on <= wrong_off)


def test_adversarial_is_harder_than_realistic():
    a1, t1, r1 = _run(DOC1, "edit_in_place", strip=True)
    a2, t2, r2 = _run(ADV, "edit_in_place", strip=True)
    check("realistic blocks: 0 wrong", cats(a1, t1, r1)["wrong"] == 0)
    check("near-duplicate blocks: recovery is strictly harder",
          cats(a2, t2, r2)["wrong"] + cats(a2, t2, r2)["missed"] >= 1)


# --- quote matcher units --------------------------------------------------

def test_quote_matcher():
    cands = ["the quick brown fox jumps", "a totally different sentence here",
             "the quick brown fox leaps high"]
    idx, score, runner = best_match(Selector(quote="the quick brown fox jumps"), cands)
    check("exact quote wins", idx == 0 and score == 1.0)
    idx2, score2, _ = best_match(Selector(quote="completely unrelated text xyz"), cands)
    check("no good match scores low", score2 < 0.5)


# --- determinism ----------------------------------------------------------

def test_determinism():
    a, t, r1 = _run(ADV, "heavy_paraphrase", strip=True)
    _, _, r2 = _run(ADV, "heavy_paraphrase", strip=True)
    check("resolution is deterministic",
          all(r1[x.id].target == r2[x.id].target for x in a))


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    total = PASS + FAIL
    print(f"{PASS}/{total} checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
