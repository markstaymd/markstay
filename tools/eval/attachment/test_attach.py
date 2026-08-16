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
XSEC = (HERE / "fixtures" / "cross_section_dups.md").read_text()

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


# --- CommonMark-tree attachment (SPEC.md §5.2, v1.1) ----------------------

def test_commonmark_loose_list_binds_whole_list():
    # The §5.2 contrast: the `list` stay binds the *last item* under blank-line
    # segmentation but the *whole list* under commonmark. (Both modes yield 3
    # anchors, since only marked blocks anchor and the bare items carry none.)
    before = ("Intro paragraph here.\n<!-- stay:intro -->\n\n"
              "- item one\n\n- item two\n\n- item three\n<!-- stay:list -->\n\n"
              "Closing paragraph here.\n<!-- stay:close -->\n")
    a_bl = {a.id: a for a in R.build_anchors(before, mode="blank-line")}
    a_cm = {a.id: a for a in R.build_anchors(before, mode="commonmark")}
    check("blank-line: list stay binds the last item only (the §5.2 limit)",
          a_bl["list"].selector.quote == "- item three")
    check("commonmark: list stay binds the whole loose list",
          all(x in a_cm["list"].selector.quote
              for x in ("item one", "item two", "item three")))


def test_commonmark_loose_list_recovers_as_whole_block():
    # Strip every marker and move the loose list to the top. commonmark mode must
    # recover the whole list as a single block via the hash tier, no false attach.
    before = ("Intro paragraph here.\n<!-- stay:intro -->\n\n"
              "- item one\n\n- item two\n\n- item three\n<!-- stay:list -->\n\n"
              "Closing paragraph here.\n<!-- stay:close -->\n")
    after = ("- item one\n\n- item two\n\n- item three\n\n"
             "Intro paragraph here.\n\nClosing paragraph here.\n")
    anchors = R.build_anchors(before, mode="commonmark")
    res = R.resolve(anchors, after, mode="commonmark")
    check("loose list recovered by the hash tier", res["list"].method == "hash")
    after_blocks = [b for b in R.L.parse_document(after, mode="commonmark") if b.index >= 0]
    tgt = after_blocks[res["list"].target].content
    check("recovered target is the whole list",
          "item one" in tgt and "item three" in tgt)
    check("every other stay also recovered (no detach on a survivor)",
          res["intro"].method == "hash" and res["close"].method == "hash")


def test_commonmark_blank_line_fence_recovers_as_whole_block():
    before = ("Lead-in line.\n<!-- stay:lead -->\n\n"
              "```py\nx = 1\n\ny = 2\n```\n<!-- stay:code -->\n")
    after = ("```py\nx = 1\n\ny = 2\n```\n\nLead-in line.\n")  # markers stripped, fence moved
    anchors = R.build_anchors(before, mode="commonmark")
    check("fence with internal blank is one anchor", len(anchors) == 2)
    res = R.resolve(anchors, after, mode="commonmark")
    check("blank-line fence recovered by the hash tier", res["code"].method == "hash")


# --- section-structure operators (PB.SECTION_OPERATORS) --------------------
# These exist to price a resolver that uses heading position as evidence, so
# what each one must preserve is the interesting part, not the counts it emits.


def test_heading_level_reads_atx_and_setext():
    check("ATX level", PB.heading_level("## Persist") == 2)
    check("ATX deep level", PB.heading_level("##### Deep") == 5)
    check("setext h1", PB.heading_level("Title\n=====") == 1)
    check("setext h2", PB.heading_level("Appendix\n--------") == 2)
    check("paragraph is not a heading", PB.heading_level("Just prose.") == 0)
    check("a thematic break is not a setext heading",
          PB.heading_level("---") == 0)
    check("hash without a space is not an ATX heading",
          PB.heading_level("#notaheading") == 0)


def test_cross_section_move_keeps_every_id_and_block():
    _, pbs = PB.annotate(XSEC)
    out, adj = PB.cross_section_move(pbs)
    check("move drops no block", len(out) == len(pbs))
    check("move drops no id",
          sorted(i for p in out for i in p.ids) ==
          sorted(i for p in pbs for i in p.ids))
    check("move overrides no ground truth (SPEC.md 2.2: movement is survivable)",
          adj == {})
    check("something actually moved",
          [p.text for p in out] != [p.text for p in pbs])


def test_section_move_relocates_a_whole_section_intact():
    _, pbs = PB.annotate(XSEC)
    out, _ = PB.section_move(pbs)
    check("section move preserves the multiset of blocks",
          sorted(p.text for p in out) == sorted(p.text for p in pbs))
    heads = [i for i, p in enumerate(out) if PB.heading_level(p.text)]
    moved = out[heads[-1]:] if heads else []
    check("the relocated section still leads with its heading",
          bool(moved) and PB.heading_level(moved[0].text) > 0)


def test_heading_rename_keeps_levels_and_ids():
    _, pbs = PB.annotate(XSEC)
    out, _ = PB.heading_rename(pbs)
    before = [PB.heading_level(p.text) for p in pbs]
    check("rename preserves every heading level", before ==
          [PB.heading_level(p.text) for p in out])
    check("rename preserves block count", len(out) == len(pbs))
    renamed = [a.text != b.text for a, b in zip(pbs, out)]
    check("rename touches some headings but not all", any(renamed))
    check("rename touches no body block",
          all(not changed or PB.heading_level(a.text)
              for a, changed in zip(pbs, renamed)))


def test_heading_delete_forces_its_own_id_to_detach():
    _, pbs = PB.annotate(XSEC)
    out, adj = PB.heading_delete(pbs)
    check("delete removes exactly one block", len(out) == len(pbs) - 1)
    check("the deleted heading's id must detach",
          len(adj) == 1 and all(v["accept"] is None for v in adj.values()))
    gone = (set(i for p in pbs for i in p.ids) -
            set(i for p in out for i in p.ids))
    check("the detaching id is the deleted heading's", gone == set(adj))


def test_cross_section_fixture_is_segmenter_agnostic():
    bl = [b.content for b in R.L.parse_document(XSEC) if b.index >= 0]
    cm = [b.content for b in R.L.parse_document(XSEC, mode="commonmark")
          if b.index >= 0]
    check("fixture parses identically under both segmenters (SPEC.md 5.4)",
          bl == cm)


def test_cross_section_fixture_holds_both_twin_classes():
    """The fixture is only useful if it contains the case the mechanism targets
    *and* the case it provably cannot touch. Assert both are present, so a later
    edit cannot quietly turn it into a one-sided corpus."""
    import run_attach_eval as RA
    shape = RA.fixture_shape(XSEC, 1)
    check("has cross-section rivals (the target class)",
          shape["cross_section_blocks"] > 0)
    check("has same-section-only rivals (the negative control)",
          shape["same_section_only_blocks"] > 0)
    check("has uncontested blocks (the regression guard)",
          shape["uncontested_blocks"] > 0)
    check("clears the ~1% bar's sizing rule at 13 operators",
          shape["cross_section_blocks"] * 13 >= 300)


# --- the heading-path experiment (all flags default to off) ----------------


def _resolve_all(base, op, **kw):
    before, pblocks = PB.annotate(base)
    after_pblocks, adj = {**PB.OPERATORS, **PB.SECTION_OPERATORS}[op](pblocks)
    after = PB.serialize(after_pblocks, strip=True)
    anchors = R.build_anchors(before)
    truth = PB.default_truth(after_pblocks)
    truth.update(adj)
    return R.resolve(anchors, after, **kw), truth, anchors


def _same(a, b):
    return all(a[k].method == b[k].method and a[k].target == b[k].target for k in a)


def test_heading_off_is_the_shipped_resolver():
    """The experiment must be invisible when it is off, or every arm is
    measured against a control that already moved."""
    for op in ("edit_in_place", "merge", "clone"):
        base_res, _, _ = _resolve_all(ADV, op)
        off, _, _ = _resolve_all(ADV, op, heading_path="off")
        check(f"{op}: heading_path=off matches the default", _same(base_res, off))


def test_no_stored_path_makes_every_arm_inert():
    """An anchor with no heading path has no heading evidence. Without this
    guard a bonus arm rewards every candidate for matching the empty path, and
    a filter arm keeps only candidates that are equally unscoped."""
    import heading_arms as HA
    flat = HA.strip_headings(DOC1)
    for op in ("edit_in_place", "clone"):
        control, _, anchors = _resolve_all(flat, op)
        check(f"{op}: no anchor stored a path",
              all(not a.heading_path for a in anchors))
        for mode in ("bonus", "penalty", "filter"):
            arm, _, _ = _resolve_all(flat, op, heading_path=mode)
            check(f"{op}: {mode} is inert with no stored path", _same(control, arm))


def test_blockquote_nested_headings_do_not_scope_blocks():
    """A heading inside a blockquote does not change outer structure, so a
    document written that way carries no paths and every arm stays inert."""
    md = ("> # Quoted heading\n\nThe ingest stage validates each record before "
          "the queue accepts it.\n\n> ## Another quoted heading\n\nThe dispatch "
          "stage validates each record before the queue accepts it.\n")
    control, _, anchors = _resolve_all(md, "edit_in_place")
    check("blockquote headings store no path",
          all(not a.heading_path for a in anchors))
    for mode in ("bonus", "penalty", "filter"):
        arm, _, _ = _resolve_all(md, "edit_in_place", heading_path=mode)
        check(f"blockquote headings: {mode} is inert", _same(control, arm))


def test_penalty_cannot_lift_a_candidate_over_the_commit_threshold():
    """The bonus form can: body at the noise floor plus a full context stack
    plus a heading bonus can cross 0.5 on non-body evidence. A penalty only ever
    lowers a mismatched candidate, so the commit bar stays a body-score bar."""
    sel = Selector(quote="the ingest stage validates each record",
                   heading_path=("Deploy", "Ingest"))
    cands = ["something else entirely, unrelated words here", "and another one"]
    paths = [["Deploy", "Ingest"], ["Other"]]
    _, base, _ = best_match(sel, cands)
    _, bonus, _ = best_match(sel, cands, paths, heading_bonus=0.12)
    _, penalty, _ = best_match(sel, cands, paths, heading_penalty=0.12)
    check("a bonus raises the winning score", bonus >= base)
    check("a penalty never raises it", penalty <= base)


def test_a_uniform_bonus_is_not_a_no_op_under_the_clamp():
    """Why the penalty form exists. On a single-section document every
    candidate matches, so the preference carries no information; a bonus still
    pushes both the best and the runner-up into the clamp's 1.0 ceiling, which
    collapses the margin and detaches. The negative control caught this."""
    detached = lambda r: sum(1 for x in r.values() if x.method == "detached")
    moved = False
    for op in PB.OPERATORS:
        control, _, _ = _resolve_all(ADV, op)
        bonus, _, _ = _resolve_all(ADV, op, heading_path="bonus")
        penalty, _, _ = _resolve_all(ADV, op, heading_path="penalty")
        moved = moved or detached(bonus) > detached(control)
        check(f"{op}: a penalty leaves the single-section control untouched",
              _same(control, penalty))
    check("a clamped bonus detaches more on a single-section document", moved)


def test_a_filter_cannot_recover_a_block_that_changed_section():
    """SPEC.md §2.2: a stay MUST survive movement within a document. The
    operator moves the fixture's most distinctive paragraph into another section
    and drifts it, so only the quote tier can recover it. A preference does; a
    filter cannot, by construction, which is why arm C is priced and not
    shipped."""
    op = "cross_section_move_edit"
    control, truth, _ = _resolve_all(XSEC, op)
    moved = [i for i, t in truth.items()
             if control[i].method == "quote" and control[i].target in (t["accept"] or ())]
    check("the shipped resolver recovers a moved, drifted block by quote",
          bool(moved))
    pen, _, _ = _resolve_all(XSEC, op, heading_path="penalty")
    filt, _, _ = _resolve_all(XSEC, op, heading_path="filter")
    check("a penalty still recovers it",
          all(pen[i].target == control[i].target for i in moved))
    check("a filter detaches at least one of them",
          any(filt[i].method == "detached" for i in moved))


def test_heading_paths_compare_component_by_component():
    """A joined string leaves the delimiter and its escaping unspecified, and
    lets a one-component path collide with a two-component one."""
    from quote import canonical_path
    check("a/b is not the same path as a then b",
          canonical_path(["a/b"]) != canonical_path(["a", "b"]))
    check("emphasis does not change a path",
          canonical_path(["**Rollback**"]) == canonical_path(["Rollback"]))


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    total = PASS + FAIL
    print(f"{PASS}/{total} checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
