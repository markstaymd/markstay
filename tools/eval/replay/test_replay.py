#!/usr/bin/env python3
"""Self-tests for the history replay.

Dependency-free, no network, reads this repository's git history. Run:
python test_replay.py

The arms in `arms.py` are fast ports, so the load-bearing tests check them
against the shipped code they port: the ladder against `resolver.resolve` on a
markers-stripped document, the quote tiers against `quote.rank_candidates`, and
the per-component assignment against one dense Hungarian. Real revision pairs
from this repository are the inputs, because a port that agrees on toy input and
disagrees on the corpus is the failure that matters here.
"""

from __future__ import annotations

import random
import sys

import arms as A
import replay as RP
from quote import Selector, body_score, rank_candidates

L = A.L
R = A.R

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def rev(md: str, commit: str = "0" * 40, path: str = "doc.md") -> RP.Rev:
    blocks, quoted = RP.real_blocks(md)
    return RP.Rev(commit, path, md, blocks, A.block_ids(blocks), 0, quoted)


def real_pairs(doc: str, k: int, limit: int):
    """Up to `limit` stamped revision pairs of `doc` at gap k, spread evenly."""
    revs = [r for r in (RP.parse_rev(c, p) for c, p in RP.history(doc, RP.CORPUS_REV)) if r]
    marked = [r for r in revs if r.stamped]
    n = len(marked) - k
    step = max(1, n // limit)
    return [(marked[i], marked[i + k]) for i in range(0, n, step)][:limit]


def stripped_case(old: RP.Rev, new: RP.Rev):
    keep = {m for m, ix in old.ids.items() if len(ix) == 1}
    anchors = A.build_anchors(old.md, old.blocks, keep)
    after = A.build_after(new.md, new.blocks)
    return anchors, after


# --- statistics --------------------------------------------------------------------


def test_clopper_pearson_known_values():
    lo, hi = RP.clopper_pearson(5, 100)
    check("CP 5/100 lower", abs(lo - 0.01643) < 2e-5)
    check("CP 5/100 upper", abs(hi - 0.11284) < 2e-5)
    lo, hi = RP.clopper_pearson(0, 300)
    check("CP 0/n lower is 0", lo == 0.0)
    check("CP 0/n upper is 1 - (a/2)^(1/n)", abs(hi - (1 - 0.025 ** (1 / 300))) < 1e-9)
    lo, hi = RP.clopper_pearson(40, 40)
    check("CP n/n", hi == 1.0 and abs(lo - 0.025 ** (1 / 40)) < 1e-9)


# --- similarity ---------------------------------------------------------------------


def test_body_norm_matches_body_score_above_the_prune_floor():
    old, new = real_pairs("ROADMAP.md", 20, 1)[0]
    rng = random.Random(7)
    pairs = [(a.content, b.content) for a in old.blocks for b in new.blocks]
    agree = True
    for q, c in rng.sample(pairs, min(400, len(pairs))):
        want = body_score(Selector(quote=q), c)
        got = A.body_norm(A.normalize(q), A.normalize(c))
        if want >= A.PRUNE:
            agree &= abs(want - got) < 1e-12
        else:
            agree &= got == 0.0
    check("body_norm equals body_score at and above PRUNE, 0 below", agree)


# --- arms against the shipped code -------------------------------------------------------


def test_ladder_matches_the_shipped_resolver_on_stripped_history():
    """The decision that matters, target or detach, for every anchor."""
    agree, total, drifted = True, 0, 0
    for doc, k, limit in (("SPEC.md", 20, 1), ("SPEC_DECISIONS.md", 20, 1), ("ROADMAP.md", 5, 3), ("CLAUDE.md", 20, 2)):
        for old, new in real_pairs(doc, k, limit):
            anchors, after = stripped_case(old, new)
            stripped = A.strip_markers(new.md)
            check(f"{doc}: stripping keeps every body", [
                b.content for b in L.parse_document(stripped) if b.index >= 0] == after.bodies)
            keep = {a.id for a in anchors}
            shipped = R.resolve([a for a in R.build_anchors(old.md) if a.id in keep], stripped)
            fast = A.arm_ladder(anchors, after, A.Scores())
            for a in anchors:
                total += 1
                drifted += shipped[a.id].method == "quote" or shipped[a.id].method == "detached"
                agree &= shipped[a.id].target == fast[a.id]
                check(f"{doc}: no marker tier once stripped", shipped[a.id].method != "marker")
    check("ladder decisions equal resolver.resolve", agree)
    check(f"the comparison reaches the quote tier ({drifted} of {total})", drifted > 20 and total > 300)


def _ranked_pick(sel, after, paths=None, penalty=0.0):
    ranked = rank_candidates(
        sel, after.bodies, candidate_paths=paths, heading_penalty=penalty,
        heading_gate=A.THRESHOLD,
    )
    if not ranked:
        return None
    score = ranked[0].score
    runner = ranked[1].score if len(ranked) > 1 else 0.0
    return ranked[0].target if score >= A.THRESHOLD and score - runner >= A.MARGIN else None


def test_quote_arms_match_rank_candidates():
    agree_q = agree_h = True
    n = 0
    for old, new in real_pairs("ROADMAP.md", 20, 2) + real_pairs("CLAUDE.md", 5, 2):
        anchors, after = stripped_case(old, new)
        shipped = {a.id: a for a in R.build_anchors(old.md)}
        S = A.Scores()
        q = A.arm_quote(anchors, after, S)
        h = A.arm_heading_quote(anchors, after, S)
        for a in anchors:
            sel = shipped[a.id].selector
            n += 1
            agree_q &= _ranked_pick(sel, after) == q[a.id]
            agree_h &= _ranked_pick(sel, after, after.paths, A.HEADING_PENALTY) == h[a.id]
    check("quote decisions equal rank_candidates", agree_q)
    check("heading+quote decisions equal rank_candidates with the D12c penalty", agree_h)
    check("quote comparison is not trivially small", n > 100)


def _total(match, anchors, after, S):
    n_a = len(after.bodies)
    return sum(
        S.get(anchors[i].nq, after.norms[j]) + A.EPS * (1 - abs(anchors[i].pos - j / n_a))
        for i, j in match.items()
    )


def test_component_assignment_equals_the_dense_one():
    agree = True
    for old, new in real_pairs("ROADMAP.md", 20, 2) + real_pairs("CLAUDE.md", 20, 1):
        anchors, after = stripped_case(old, new)
        S = A.Scores()
        rows, cols = list(range(len(anchors))), list(range(len(after.bodies)))
        sparse = A.assign(rows, cols, anchors, after, S)
        dense = A.assign(rows, cols, anchors, after, S, dense=True)
        agree &= abs(_total(sparse, anchors, after, S) - _total(dense, anchors, after, S)) < 1e-9
    check("per-component optimum equals the dense optimum", agree)


# --- ground truth and its repair -------------------------------------------------------------


P = "The paragraph that a reference was held on, long enough to score well against itself."
Q = "A second paragraph about something else entirely, with its own words and its own claim."
N = "A freshly inserted paragraph, unrelated in wording to anything that came before it here."


def _case(old_md, new_md):
    doc = RP.Doc("doc.md", [])
    c = RP.make_case(doc, 1, rev(old_md), rev(new_md, commit="1" * 40))
    RP.repair(c, RP.Table())
    return c


def test_lost_id_is_repaired_to_its_surviving_block():
    c = _case(f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n", f"{P}\n\n{Q}\n<!-- stay:bbbb -->\n")
    check("lost: pre-registered truth says gone", c.truth["aaaa"] == "gone")
    check("lost: repaired to the unstamped survivor", c.repair.get("aaaa") == (0, "lost"))


def test_relocated_id_is_repaired_to_its_old_text():
    c = _case(
        f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n",
        f"{P}\n\n{N}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n",
    )
    check("relocated: the id now names the inserted block", c.truth["aaaa"] == 1)
    check("relocated: repaired to the original paragraph", c.repair.get("aaaa") == (0, "relocated"))
    check("relocated: an untouched id is left alone", "bbbb" not in c.repair)


def test_deleted_block_and_claimed_twin_are_not_repaired():
    c = _case(f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n", f"{Q}\n<!-- stay:bbbb -->\n")
    check("deleted: stays gone", c.truth["aaaa"] == "gone" and "aaaa" not in c.repair)
    c = _case(f"{P}\n<!-- stay:aaaa -->\n\n{P}\n<!-- stay:bbbb -->\n", f"{P}\n<!-- stay:bbbb -->\n")
    check("twin: a block another surviving id owns is not a survivor", "aaaa" not in c.repair)


def test_a_marker_quoted_in_inline_code_is_not_an_id():
    md = (
        "A fence's info string (` ```md <!-- stay:x --> `) can hold one.\n<!-- stay:aaaa -->\n\n"
        "The baseline finds `<!-- stay:x -->` anywhere.\n<!-- stay:bbbb -->\n"
    )
    r = rev(md)
    check("quoted markers are left out", set(r.ids) == {"aaaa", "bbbb"} and r.quoted == 2)


def test_quoted_marker_does_not_make_a_revision_stamped():
    quoting = "# Plan\n\nWe write `<!-- stay:x -->` after a block.\n\nMore prose.\n\nAnd more.\n"
    check("one quoted marker over four blocks is not stamped", not rev(quoting).stamped)
    stamped = f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n"
    check("half the blocks stamped is stamped", rev(stamped).stamped)


def test_cost_counts_a_relocation_and_a_lost_id():
    old = rev(f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n")
    new = rev(f"{P}\n\n{N}\n<!-- stay:aaaa -->\n\n{Q}\n", commit="1" * 40)
    row, _ = RP.cost_history(RP.Doc("doc.md", [old, new]), RP.Table())
    check("cost: relocation counted", row.get("relocated") == 1)
    check("cost: the id dropped off a surviving block counted", row.get("verbatim_unstamped") == 1)


def test_quoted_example_and_identical_real_marker_on_one_line():
    md = "The form is `<!-- stay:aaaa -->` as written here. <!-- stay:aaaa -->\n\nOther.\n"
    r = rev(md)
    check("quoted-plus-real: the real one is kept", r.ids == {"aaaa": [0]} and r.quoted == 1)
    md = "Real first <!-- stay:aaaa --> then `<!-- stay:aaaa -->` quoted.\n"
    r = rev(md)
    check("real-plus-quoted: the real one is kept", r.ids == {"aaaa": [0]} and r.quoted == 1)
    # Through case construction, scoring and repair: the quoted copy gives the
    # id no second anchor, so losing only the real marker leaves one proposal,
    # and the surviving block is repaired rather than scored gone.
    body = "The form is `<!-- stay:aaaa -->` as written here."
    c = _case(f"{body} <!-- stay:aaaa -->\n\n{Q}\n<!-- stay:bbbb -->\n",
              f"{body}\n\n{Q}\n<!-- stay:bbbb -->\n")
    check("quoted-plus-real: one anchor per id", [a.id for a in c.anchors].count("aaaa") == 1)
    check("quoted-plus-real: the lost real marker is lost", c.truth["aaaa"] == "gone")
    check("quoted-plus-real: the survivor is repaired", c.repair.get("aaaa") == (0, "lost"))
    check("quoted-plus-real: no contested repair", c.repair_contested == 0)


def test_coverage_counts_blocks_not_ids():
    two_on_one = f"{P}\n<!-- stay:aaaa -->\n<!-- stay:bbbb -->\n\n{Q}\n\n{N}\n\nFourth block.\n"
    check("two ids on one of four blocks is not stamped", not rev(two_on_one).stamped)
    one_on_two = f"{P}\n<!-- stay:aaaa -->\n\n{Q}\n<!-- stay:aaaa -->\n\n{N}\n\nFourth block.\n"
    check("one id on two of four blocks is stamped", rev(one_on_two).stamped)


def _lcs_len(a, b):
    dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
    for i in range(len(a)):
        for j in range(len(b)):
            dp[i + 1][j + 1] = dp[i][j] + 1 if a[i] == b[j] else max(dp[i][j + 1], dp[i + 1][j])
    return dp[-1][-1]


def test_lcs_is_a_longest_common_subsequence():
    got = A._lcs_pairs(list("aaaa"), list("abaa"))
    check("lcs: aaaa vs abaa matches three", len(got) == 3)
    rng = random.Random(11)
    ok = True
    for _ in range(300):
        a = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        b = [rng.choice("abc") for _ in range(rng.randint(0, 12))]
        pairs = A._lcs_pairs(a, b)
        ok &= len(pairs) == _lcs_len(a, b)
        ok &= all(a[i] == b[j] for i, j in pairs)
        ok &= all(p < q for p, q in zip(pairs, pairs[1:])) and all(
            p[1] < q[1] for p, q in zip(pairs, pairs[1:]))
    check("lcs: length optimal and pairs strictly increasing on random sequences", ok)


def test_repairs_are_one_to_one():
    x = "The surviving paragraph that two lost ids both resemble closely enough to claim it."
    p1 = x + " One."
    p2 = x + " A rather longer second tail."
    c = _case(f"{p1}\n<!-- stay:aaaa -->\n\n{p2}\n<!-- stay:bbbb -->\n\n{Q}\n<!-- stay:cccc -->\n",
              f"{x}\n\n{Q}\n<!-- stay:cccc -->\n")
    check("one-to-one: the closer id wins the block", c.repair == {"aaaa": (0, "lost")})
    check("one-to-one: the loser is counted", c.repair_contested == 1)
    c = _case(f"{p1}\n<!-- stay:aaaa -->\n\n{p1}\n<!-- stay:bbbb -->\n\n{Q}\n<!-- stay:cccc -->\n",
              f"{x}\n\n{Q}\n<!-- stay:cccc -->\n")
    check("one-to-one: a tie goes to neither", c.repair == {} and c.repair_contested == 2)


def _real_cases(doc, k, limit, losing=False):
    """Stamped pairs as cases; with `losing`, only pairs where some id is gone,
    so the fallback half of `ids+ladder` is exercised."""
    revs = [r for r in (RP.parse_rev(c, p) for c, p in RP.history(doc, RP.CORPUS_REV)) if r]
    marked = [r for r in revs if r.stamped]
    d = RP.Doc(doc, revs, marked)
    out = []
    for i in range(len(marked) - k):
        old, new = marked[i], marked[i + k]
        if losing and not set(old.ids) - set(new.ids):
            continue
        out.append(RP.make_case(d, k, old, new))
        if len(out) == limit:
            break
    return out


def test_ids_plus_ladder_matches_the_shipped_resolver_with_markers_kept():
    agree, n, fallback = True, 0, 0
    for doc, k, limit in (("SPEC.md", 1, 3), ("SPEC_DECISIONS.md", 1, 2), ("CLAUDE.md", 20, 1)):
        for c in _real_cases(doc, k, limit, losing=doc != "CLAUDE.md"):
            ours = RP.ids_plus_ladder(c, A.arm_ladder(c.anchors, c.after, A.Scores()))
            keep = {a.id for a in c.anchors}
            shipped = R.resolve([a for a in R.build_anchors(c.old.md) if a.id in keep], c.new.md)
            for a in c.anchors:
                n += 1
                fallback += a.id not in c.new.ids
                agree &= shipped[a.id].target == ours[a.id]
    check(f"ids+ladder equals resolver.resolve with markers kept ({fallback} fallbacks of {n})",
          agree and fallback > 20)


def test_structural_and_lcs_agree_on_pinned_pairs():
    agree = True
    for doc, k, limit in (("ROADMAP.md", 20, 3), ("CLAUDE.md", 20, 2), ("SPEC_DECISIONS.md", 5, 2)):
        for old, new in real_pairs(doc, k, limit):
            anchors, after = stripped_case(old, new)
            S = A.Scores()
            agree &= A.arm_structural(anchors, after, S) == A.arm_lcs(anchors, after, S)
    check("structural and lcs give the same answers on pinned pairs", agree)


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    total = PASS + FAIL
    print(f"{PASS}/{total} checks passed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
