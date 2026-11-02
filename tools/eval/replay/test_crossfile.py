#!/usr/bin/env python3
"""Self-tests for the cross-file replay, on synthetic documents only.

Run: python test_crossfile.py

The load-bearing check is that `crossfile.child_ladder` over one document is the
shipped §9.2 ladder (`markstay_lint._resolve_children` on the markers-stripped
document): the pooled ladder is that code with its scope widened, so it must
agree before it is widened. The scan is checked on a throwaway git repository
built here, so no replayed history is needed to run the tests.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "impl" / "py" / "src"))
import crossfile as X  # noqa: E402
import replay as RP  # noqa: E402
from markstay.stamp import stamp  # noqa: E402

L = X.L
A = X.A

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def stamped(md: str, tag: str) -> str:
    n = iter(range(10_000))
    return stamp(md, mode=X.MODE, child_blocks=True, new_id=lambda: f"{tag}{next(n):04d}").text


TRACKER = """# Tracker

Intro paragraph about what this tracker follows.

## Action

- [ ] Wire the nightly export into the reporting bucket
- [x] Rotate the staging credentials after the audit
- [ ] Draft the rollback note for the schema change
- [x] Done
- [ ] Confirm the alert thresholds with the on-call rota

## Notes

- Release train leaves on Thursdays
- [x] Done
"""

ARCHIVE = """# Closed items

## Closed

- [x] Retire the legacy cron host
"""


def _lines_without(md: str, needle: str) -> tuple[str, str]:
    """`md` without the line containing `needle`, and that line."""
    lines = md.split("\n")
    i = next(i for i, ln in enumerate(lines) if needle in ln)
    return "\n".join(lines[:i] + lines[i + 1:]), lines[i]


def _append_item(md: str, after: str, line: str) -> str:
    lines = md.split("\n")
    i = next(i for i, ln in enumerate(lines) if after in ln)
    return "\n".join(lines[: i + 1] + [line] + lines[i + 1:])


def _key(blocks, child_index):
    for b in blocks:
        for c in b.children:
            if c.index == child_index:
                return (b.index, c.ordinal, c.kind)
    return None


# --- the pooled ladder, one document: the shipped ladder -----------------------------------


def _edits(base: str):
    """Before/after pairs covering every tier: unchanged, edited, reordered,
    deleted, glyph change, an item moved between lists, a dropped marker."""
    yield "unchanged", base
    yield "edited", base.replace("nightly export", "nightly CSV export")
    no_rot, rot = _lines_without(base, "Rotate the staging")
    yield "deleted", no_rot
    yield "reordered", _append_item(no_rot, "Confirm the alert", rot)
    yield "glyph", base.replace("- [", "* [")
    no_draft, draft = _lines_without(base, "Draft the rollback")
    yield "moved-list", _append_item(no_draft, "Release train", draft.replace("- [ ] ", "- "))
    yield "marker-dropped", base.replace(draft, draft.split(" <!--")[0])
    yield "twin-edited", base.replace("- [x] Done", "- [x] Done, finally")


def test_one_unit_child_ladder_is_the_shipped_ladder():
    base = stamped(TRACKER, "t")
    anchors = L._build_child_anchors(base, X.MODE)
    check("fixture carries child anchors", len(anchors) >= 7)
    for name, after in _edits(base):
        shipped = L._resolve_children(anchors, A.strip_markers(after), X.MODE)
        sblocks = [b for b in L.parse_document(A.strip_markers(after), mode=X.MODE, child_blocks=True)
                   if b.index >= 0]
        unit = X.Unit("doc.md", X.parse(after))
        ours = X.child_ladder(anchors, [unit])
        for a in anchors:
            ts, ixs = shipped[a.id]
            to, ko = ours[a.id]
            want = (ts, None if ixs is None else _key(sblocks, ixs))
            got = (to, None if ko is None else _key(unit.blocks, ko[1]))
            check(f"{name}: {a.id} {want} == {got}", want == got)


def test_source_only_is_the_shipped_ladder():
    base = stamped(TRACKER, "t")
    anchors = L._build_child_anchors(base, X.MODE)
    after, _ = _lines_without(base, "Rotate the staging")
    got = X.source_only(anchors, after)
    shipped = L._resolve_children(anchors, A.strip_markers(after), X.MODE)
    check("source-only answers are the shipped tiers",
          {m: t for m, (t, _) in got.items()} == {m: t for m, (t, _) in shipped.items()})
    ported = X.source_only(anchors, after, X.Unit("doc.md", X.parse(after)))
    check("source-only through the port gives the shipped tiers",
          {m: t for m, (t, _) in ported.items()} == {m: t for m, (t, _) in shipped.items()})
    check("source-only on a deleted document detaches everything",
          all(t == "detached" for t, _ in X.source_only(anchors, None).values()))


# --- the pooled arms on a move --------------------------------------------------------------


def _moved(base_t: str, base_a: str, needle: str):
    t_after, line = _lines_without(base_t, needle)
    a_after = _append_item(base_a, "Retire the legacy", line)
    mid = L.find_markers(line)[0].id
    return t_after, a_after, mid


def _truth(unit: X.Unit, mid: str):
    for b in unit.blocks:
        for c in b.children:
            if any(mk.id == mid for mk in c.markers):
                return c.index
    return None


def test_a_verbatim_move_is_found_across_documents_and_not_in_the_source():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    anchors = L._build_child_anchors(t, X.MODE)
    t_after, a_after, mid = _moved(t, a, "Rotate the staging")
    units = [X.Unit("tracker.md", X.parse(t_after)), X.Unit("archive.md", X.parse(a_after))]
    want = (1, _truth(units[1], mid))
    lad = X.child_ladder(anchors, units)
    check("pooled ladder finds the moved item at tier 4", lad[mid] == ("document-hash", want))
    check("hash arm finds it", X.child_hash(anchors, units)[mid][1] == want)
    check("quote arm finds it", X.child_quote(anchors, units)[mid][1] == want)
    check("source-only cannot", X.source_only(anchors, t_after)[mid][1] is None)
    others = [x.id for x in anchors if x.id != mid]
    check("the items left behind keep their blocks",
          all(lad[m][1] is not None and lad[m][1][0] == 0 for m in others
              if "Done" not in next(x.quote for x in anchors if x.id == m)))


def test_a_moved_twin_is_not_attached_by_hash():
    """`Done` has a byte-identical twin in the tracker's notes, so tier 4's
    recorded uniqueness fails and the hash arm must not attach it anywhere."""
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    anchors = L._build_child_anchors(t, X.MODE)
    t_after, a_after, mid = _moved(t, a, "- [x] Done")
    units = [X.Unit("tracker.md", X.parse(t_after)), X.Unit("archive.md", X.parse(a_after))]
    check("hash arm detaches a twin", X.child_hash(anchors, units)[mid][1] is None)
    check("pooled ladder does not hash-attach a twin", X.child_ladder(anchors, units)[mid][0] != "document-hash")


def _quote_brute(anchors, units):
    """`child_quote` without the PRUNE shortcut, for the equivalence check."""
    cands = []
    for u, unit in enumerate(units):
        for b in unit.blocks:
            sib = [c for c in b.children if c.kind == "list"]
            for i, c in enumerate(sib):
                cands.append(((u, c.index), c.content, sib[i - 1].content if i else "",
                              sib[i + 1].content if i + 1 < len(sib) else ""))
    out, claimed, props = {}, set(), {}
    for a in anchors:
        scored = [(L._body_score(a.quote, body) + X._ctx(a.prefix, p, True) + X._ctx(a.suffix, n, False), k)
                  for k, (_, body, p, n) in enumerate(cands)]
        got = X._pick(scored)
        if got is not None:
            props[a.id] = cands[got][0]
    X._commit(out, claimed, "quote", props)
    return {a.id: out.get(a.id, ("detached", None))[1] for a in anchors}


def test_quote_pruning_changes_no_decision():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    anchors = L._build_child_anchors(t, X.MODE)
    for needle in ("Rotate the staging", "Draft the rollback", "- [x] Done"):
        t_after, a_after, _ = _moved(t, a, needle)
        a_after = a_after.replace("Rotate the staging credentials", "Rotate staging creds")
        units = [X.Unit("tracker.md", X.parse(t_after)), X.Unit("archive.md", X.parse(a_after))]
        fast = {m: k for m, (_, k) in X.child_quote(anchors, units).items()}
        check(f"pruned quote == brute force ({needle})", fast == _quote_brute(anchors, units))


# --- block arms -----------------------------------------------------------------------------


def test_block_arms_follow_a_moved_paragraph():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    t_after, para = _lines_without(t, "Intro paragraph")
    marker_line = t_after.split("\n")[t.split("\n").index(para)]
    t_after = t_after.replace(marker_line + "\n", "", 1)
    a_after = a + "\n" + para + "\n" + marker_line + "\n"
    mid = L.find_markers(marker_line)[0].id
    blocks_old = X.parse(t)
    units = [X.Unit("tracker.md", X.parse(t_after)), X.Unit("archive.md", X.parse(a_after))]
    got = X.block_arms(t, blocks_old, {mid}, units, units[0])
    j = next(i for i, b in enumerate(units[1].blocks) if any(mk.id == mid for mk in b.markers))
    check("block ladder, all docs, finds the paragraph", got["block ladder, all docs"][mid] == (1, j))
    check("block hash, all docs, finds the paragraph", got["block hash, all docs"][mid] == (1, j))
    check("block ladder, source only, does not", got["block ladder, source only"][mid] is None)


# --- scope ------------------------------------------------------------------------------------


def test_globs_and_default_scope():
    g = RP.glob_re("tracking/**/*.md")
    check("** matches zero directories", bool(g.match("tracking/T.md")))
    check("** matches several", bool(g.match("tracking/a/b/T.md")))
    check("prefix is literal", not g.match("trackingX/T.md"))
    g = RP.glob_re("archive/*/*_closed_*.md")
    check("* is one segment", bool(g.match("archive/2026-10/t_closed_2026-10.md")))
    check("* does not cross /", not g.match("archive/2026-10/x/t_closed_2026-10.md"))
    RP.configure()
    check("default scope keeps the umbrella's selection",
          RP.in_scope("SPEC.md") and not RP.in_scope("impl/py/README.md") and RP.pathspecs() == ["*.md"])


# --- the scan, on a throwaway repository --------------------------------------------------------


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@example.invalid", *args],
                   check=True, capture_output=True)


def test_scan_classifies_moves_deletions_and_returns():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    ids = {name: L.find_markers(_lines_without(t, name)[1])[0].id
           for name in ("Wire the nightly", "Rotate the staging", "Draft the rollback", "Confirm the alert")}
    with tempfile.TemporaryDirectory() as tmp:
        repo, out = Path(tmp) / "repo", Path(tmp) / "out"
        (repo / "docs").mkdir(parents=True)
        _git(repo, "init", "-q")
        step = [0]

        def commit(files: dict[str, str]):
            for p, text in files.items():
                (repo / p).write_text(text)
            (repo / "pad.txt").write_text(str(step[0]))  # out of scope: never a chain position
            step[0] += 1
            _git(repo, "add", "-A")
            _git(repo, "commit", "-q", "-m", f"c{step[0]}")

        commit({"docs/tracker.md": t, "docs/archive.md": a})
        # 1: a move inside one commit (the prune shape)
        t1, a1, _ = _moved(t, a, "Rotate the staging")
        commit({"docs/tracker.md": t1, "docs/archive.md": a1})
        # 2: a deletion
        t2, _ = _lines_without(t1, "Wire the nightly")
        commit({"docs/tracker.md": t2})
        # 3: an id leaves, then lands in the archive two scope commits later
        t3, line3 = _lines_without(t2, "Draft the rollback")
        commit({"docs/tracker.md": t3})
        commit({})  # touches only pad.txt: not a chain position, so the window does not move
        commit({})
        commit({})
        commit({"docs/tracker.md": t3 + "\nA later note.\n"})
        commit({"docs/archive.md": _append_item(a1, "Retire the legacy", line3)})
        # 4: an id leaves and comes back to its own document
        t4, line4 = _lines_without(t3 + "\nA later note.\n", "Confirm the alert")
        commit({"docs/tracker.md": t4})
        commit({"docs/tracker.md": _append_item(t4, "Release train", line4)})
        # 5: copy-then-delete across two commits: the id is in the archive
        # before it leaves the tracker, so the move is flagged as pre-existing.
        t5 = _append_item(t4, "Release train", line4)
        _, line5 = _lines_without(t5, "Confirm the alert")
        a5 = _append_item(_append_item(a1, "Retire the legacy", line3), "Retire the legacy", line5)
        commit({"docs/archive.md": a5})
        t6, _ = _lines_without(t5, "Confirm the alert")
        commit({"docs/tracker.md": t6})
        for n in range(4):  # history long enough that nothing is censored at kmax = 3
            commit({"docs/tracker.md": t6 + f"\nPad {n}.\n"})
        res = X.run(repo, ["docs/*.md"], out, "T", (1, 3), 1, 0, profile=0)
        by = res["moves_by_window"]
        check("two moves inside the commit window", by["1"]["moves"] == 2)
        check("three moves within three scope commits", by["3"]["moves"] == 3)
        check("only the copy-then-delete is pre-existing", by["3"]["pre_existing"] == 1)
        check("the out-of-scope commits add no chain position", res["commits"] == step[0] - 3)
        check("all moves are child stays", res["move_kinds"] == {"child->child": 3})
        st = res["status"]
        check("one deletion, one return", st.get("deletion") == 1 and st.get("return") == 1)
        arms1 = res["arms"]["1"]
        check("the verbatim moves are found by the pooled ladder",
              arms1["child ladder, all docs"]["correct"] == 2 and arms1["ladder, all docs"]["correct"] == 2)
        check("and missed by the source-only ladder",
              arms1["child ladder, source only"]["correct"] == 0)
        check("breakdown splits fresh from pre-existing",
              res["breakdown"]["already elsewhere before the commit"]["n"] == 1
              and res["breakdown"]["fresh (not elsewhere before the commit)"]["n"] == 2)
        check("the deletion is scored", res["deletions_scored"]["child hash, all docs"]["n"] == 1)
        json.dumps(res)  # serialisable, as main writes it
        check("nothing but the result is written", sorted(p.name for p in out.iterdir()) == [])
        _ = ids


def test_prefilter_is_exact():
    import random as _r
    rng = _r.Random(3)
    words = ["alpha", "beta", "gamma", "export", "the", "a", "rotate", "staging", "creds", "x"]
    for _ in range(400):
        q = " ".join(rng.choice(words) for _ in range(rng.randint(1, 12)))
        c = " ".join(rng.choice(words) for _ in range(rng.randint(1, 30)))
        check(f"prefilter == body_norm ({q!r}, {c!r})", X._pruned_body(q, c) == A.body_norm(q, c))


class _Ev:
    def __init__(self, n, d, j):
        self.id, self.src, self.d, self.j, self.kind = f"m{n}", "s", d, j, "child"


def test_sample_is_stratified_seeded_and_weighted():
    # One huge commit and many small ones in the k = 1 stratum, a few slow moves.
    evs = [_Ev(n, 0, 0) for n in range(500)]
    evs += [_Ev(500 + n, 0, 1 + n // 2) for n in range(100)]
    evs += [_Ev(700 + n, 3, 100 + n) for n in range(10)]
    evs += [_Ev(800 + n, 12, 200 + n) for n in range(40)]
    got, frame = X.sample_moves(evs, 120, 7)
    again, _ = X.sample_moves([_Ev(int(e.id[1:]), e.d, e.j) for e in evs], 120, 7)
    check("sample size", len(got) == 120)
    check("seeded: same draw twice", sorted(e.id for e in got) == sorted(e.id for e in again))
    check("small strata keep a floor", frame["child:d1-4"]["sample"] == 10 and frame["child:d5-19"]["sample"] == 30)
    big = sum(1 for e in got if e.j == 0)
    check("one large commit cannot dominate", big <= 2)
    check("the frame records the most draws from a commit",
          frame["child:d5-19"]["max_draws_per_commit"] == 1 and frame["child:d0"]["max_draws_per_commit"] > 1)
    many, frame2 = X.sample_moves([_Ev(n, 0, n % 3) for n in range(60)], 30, 7)
    check("a quota over the commits draws a commit twice, and says so", frame2["child:d0"]["max_draws_per_commit"] > 1)
    check("weights restore the population",
          abs(sum(e.weight for e in got) - len(evs)) < 1e-6
          and abs(sum(e.weight for e in got if e.d == 0) - 600) < 1e-6)


def test_bounded_pick_matches_brute_force():
    import random as _r
    rng = _r.Random(11)
    words = ["deploy", "alpha", "beta", "service", "verify", "the", "node", "retire", "x", "done"]
    for trial in range(300):
        q = " ".join(rng.choice(words) for _ in range(rng.randint(1, 8)))
        norms = [" ".join(rng.choice(words) for _ in range(rng.randint(1, 10))) for _ in range(rng.randint(1, 25))]
        if rng.random() < 0.3:
            norms[rng.randrange(len(norms))] = q
        bonus = [rng.choice([0.0, 0.03, 0.05, 0.1]) for _ in norms]
        brute = X._pick([(X._pruned_body(q, c) + bonus[n], n) for n, c in enumerate(norms) if X._pruned_body(q, c)])
        fast = X.bounded_pick(q, norms, lambda n: bonus[n])
        check(f"bounded pick == brute force (trial {trial})", fast == brute)


def test_lcs_bound():
    import random as _r
    from difflib import SequenceMatcher
    rng = _r.Random(5)
    for trial in range(200):
        a = "".join(rng.choice("abcde ") for _ in range(rng.randint(0, 60)))
        b = "".join(rng.choice("abcde ") for _ in range(rng.randint(0, 60)))
        dp = [[0] * (len(b) + 1) for _ in range(len(a) + 1)]
        for i in range(len(a) - 1, -1, -1):
            for j in range(len(b) - 1, -1, -1):
                dp[i][j] = dp[i + 1][j + 1] + 1 if a[i] == b[j] else max(dp[i + 1][j], dp[i][j + 1])
        check(f"bit-parallel LCS == DP (trial {trial})", X.lcs_len(a, b) == dp[0][0])
        if a and b:
            m = sum(x.size for x in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
            check(f"R/O matches <= LCS (trial {trial})", m <= dp[0][0])


def test_bounded_pick_on_long_prose():
    import random as _r
    rng = _r.Random(13)
    vocab = "the a of to deploy service verify retire node alpha beta gamma export bucket audit".split()
    para = lambda n: " ".join(rng.choice(vocab) for _ in range(n))  # noqa: E731
    for trial in range(20):
        q = para(rng.randint(60, 120))
        norms = [para(rng.randint(60, 120)) for _ in range(8)]
        if trial % 2:
            norms[3] = q[: len(q) // 2] + " edited " + q[len(q) // 2:]
        bonus = [rng.choice([0.0, 0.05, 0.1]) for _ in norms]
        brute = X._pick([(X._pruned_body(q, c) + bonus[n], n) for n, c in enumerate(norms) if X._pruned_body(q, c)])
        check(f"bounded pick on long prose (trial {trial})", X.bounded_pick(q, norms, lambda n: bonus[n]) == brute)


class _Cell:
    def __init__(self, j, kind, weight, stratum=None):
        self.j, self.kind, self.weight, self.stratum = j, kind, weight, stratum or f"{kind}:d0"


def _row(found, wrong):
    """An arm row from (commit, weight, correct) draws; `wrong` lists wrong commits."""
    evs = [_Cell(j, "child", w) for j, w, _ in found]
    return {"n": len(evs), "design": {
        "found": X.design_ci(evs, [ok for _, _, ok in found]),
        "misattach": X.design_ci(evs, [j in wrong for j, _, _ in found]),
    }, **X.rate_row(__import__("collections").Counter(
        correct=sum(ok for _, _, ok in found), wrong=len(wrong),
        missed=len(found) - sum(ok for _, _, ok in found) - len(wrong)))}


def test_verdict_rule():
    clean = [(j, 1.0, True) for j in range(2000)]
    v = X.verdict({"1": {"ladder, all docs": _row(clean, set())}})
    check("a clean pooled arm at n = 2000 passes on the interval", v["1"]["call"] == "ids-not-needed")
    check("and is the arm named", v["1"]["best_arm"] == "ladder, all docs")
    few = [(j, 1.0, j != 0) for j in range(20)]
    v = X.verdict({"1": {"ladder, all docs": _row(few, set())}})
    check("n = 20 cannot certify", v["1"]["call"] == "insufficient-evidence")
    half = [(j, 1.0, j % 2 == 0) for j in range(1000)]
    v = X.verdict({"1": {"hash, all docs": _row(half, set())}})
    check("half found fails", v["1"]["call"] == "ids-pay" and v["1"]["blocked_by"] == ["found"])
    v = X.verdict({"1": {"child hash, all docs": _row(clean, set())}})
    check("a per-kind arm alone does not decide the rule over all moves", v["1"]["call"] == "no-data")
    v = X.verdict({"1": {"hash, all docs": _row(half, set()), "quote, all docs": _row(few, set())}})
    check("best_arm is the arm keeping the call from ids-pay",
          v["1"]["call"] == "insufficient-evidence" and v["1"]["best_arm"] == "quote, all docs")


def test_verdict_uses_population_weights():
    """One commit of 970 moves found, 300 small commits missed: the raw count says
    0.3% found, while the population is 97% found. Raw counts must not call this."""
    draws = [(0, 970.0, True)] + [(j, 0.1, False) for j in range(1, 301)]
    row = _row(draws, set())
    check("raw found rate is tiny", row["found_rate"] < 0.01)
    check("weighted estimate sees the large commit", abs(row["design"]["found"]["point"] - 0.97) < 1e-9)
    arms = {"1": {"hash, all docs": row}}
    check("raw counts would say the ids pay", X.verdict_unweighted(arms)["1"]["call"] == "ids-pay")
    check("the weighted call does not", X.verdict(arms)["1"]["call"] != "ids-pay")


def test_design_interval():
    evs = [_Cell(j, "child", 1.0 + j % 3) for j in range(300)]
    none = X.design_ci(evs, [False] * 300)
    check("zero events still leave an upper bound", none["point"] == 0.0 and none["hi"] > 0.005)
    check("and it is the largest weight's", abs(none["hi"] - 3.689 * 3 / sum(e.weight for e in evs)) < 1e-3)
    a, b = X.design_ci(evs, [j % 7 == 0 for j in range(300)]), X.design_ci(evs, [j % 7 == 0 for j in range(300)])
    check("the interval is seeded", a == b)
    check("the point lies inside", a["lo"] <= a["point"] <= a["hi"])
    equal = [_Cell(j, "child", 1.0) for j in range(300)]
    clustered = [_Cell(j // 30, "child", 1.0) for j in range(300)]
    ys = [j % 60 < 30 for j in range(300)]
    check("clustering widens the bootstrap",
          X.design_ci(clustered, ys)["boot"][1] - X.design_ci(clustered, ys)["boot"][0]
          > X.design_ci(equal, ys)["boot"][1] - X.design_ci(equal, ys)["boot"][0])
    mixed = [_Cell(j, "child", 9.0) for j in range(90)] + [_Cell(j, "block", 1.0) for j in range(10)]
    d = X.design_ci(mixed, [e.kind == "child" for e in mixed])
    check("strata combine by population", abs(d["point"] - 810 / 820) < 1e-9)


def test_an_interrupted_run_resumes_from_its_answers():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    with tempfile.TemporaryDirectory() as tmp:
        repo, out, commit = _repo(tmp)
        commit({"docs/tracker.md": t, "docs/archive.md": a})
        t1, a1, _ = _moved(t, a, "Rotate the staging")
        commit({"docs/tracker.md": t1, "docs/archive.md": a1})
        t2, a2, _ = _moved(t1, a1, "Draft the rollback")
        commit({"docs/tracker.md": t2, "docs/archive.md": a2})
        args = (repo, ["docs/*.md"], out, "R", (1,), 1, 0)
        first = X.run(*args, keep_answers=True)
        path = out / "answers-R.jsonl"
        lines = path.read_text().split("\n")
        check("two groups were scored", first["timing"]["resumed_groups"] == 0 and len(lines) == 4)
        path.write_text("\n".join(lines[:2]) + "\n" + lines[2][:20])  # one group, one torn line
        again = X.run(*args, keep_answers=True)
        check("the whole group resumes and the torn one is rescored", again["timing"]["resumed_groups"] == 1)
        check("to the same numbers", again["arms"] == first["arms"] and again["verdict"] == first["verdict"])
        path.write_text('{"other": "draw"}\n' + "\n".join(lines[1:]))
        check("another draw's answers are not used", X.run(*args, keep_answers=True)["timing"]["resumed_groups"] == 0)
        X.run(*args)
        check("a finished run leaves no answers behind", not path.exists())
        para = "A paragraph that moves whole between two documents here."
        block = stamped(para + "\n\n---\n", "b")
        marks = block.split("\n\n")[0]
        commit({"docs/block.md": block})
        commit({"docs/block.md": "---\n", "docs/archive.md": a2 + "\n" + marks + "\n"})
        res = X.run(repo, ["docs/*.md"], out, "S", (1,), 1, 5)
        window = res["moves_by_window"]["1"]
        check("the frame carries the commit-size figures",
              window["single_move_commits"] == 3 and abs(window["ten_largest_commits_share"] - 1.0) < 1e-12)
        check("the sanity counts cover the draws", sum(res["sanity_counts"].values()) == 3)
        check("the block comparison counts what it compared",
              res["block_comparison"].get("identical") == 1 and res["block_comparison"]["bare rules"] == 0)
        check("the store text stays in the scratch files", para not in json.dumps(res))


def test_weighted_interval():
    check("a gamma quantile: one event's worth of nothing", abs(X._gamma_q(0.975, 1.0, 1.0) + __import__("math").log(0.025)) < 1e-9)
    # Equal weights of 1 reduce to the exact Poisson (Garwood) interval on 3 events.
    lo, hi = X.weighted_interval([1.0] * 100, [j < 3 for j in range(100)])
    check("three events: Garwood's lower bound", abs(lo - 0.6187) < 1e-3)
    check("three events: Garwood's upper bound", abs(hi - 8.7673) < 1e-3)
    lo, hi = X.weighted_interval([0.01] * 100, [True] * 100)
    check("all hits mirror no events", lo == 1 - X.weighted_interval([0.01] * 100, [False] * 100)[1] and abs(hi - 1) < 1e-12)
    check("no mass, no interval", X.weighted_interval([], []) == (0.0, 0.0))


def _coverage(sizes, bad):
    """How often the interval holds the true rate, over seeded one-per-commit draws
    from commits of these sizes with these numbers of bad moves."""
    import random as _r
    rng = _r.Random(11)
    total = sum(sizes)
    truth = sum(bad) / total
    ws = [m / total for m in sizes]
    held = 0
    trials = 1500
    for _ in range(trials):
        ys = [rng.random() < b / m for m, b in zip(sizes, bad)]
        lo, hi = X.weighted_interval(ws, ys)
        held += lo - 1e-12 <= truth <= hi + 1e-12
    return held / trials


def test_one_large_commit_cannot_certify_itself():
    """One 300-move commit and 970 commits of ten. If 150 of the 300 are misattached
    the truth is 1.5%, and half of all samples see no error at all. An effective-size
    interval then reads under 1%, which would call ids-not-needed."""
    evs = [_Ev(n, 0, 0) for n in range(300)]
    evs += [_Ev(300 + n, 0, 1 + n // 10) for n in range(9700)]
    got, _ = X.sample_moves(evs, 0, 7)
    none = X.design_ci(got, [False] * len(got))
    check("no error seen", none["point"] == 0.0)
    check("the bound stays above the truth", none["hi"] > 0.015)
    arms = {"1": {"hash, all docs": {"n": len(got), "design": {"found": X.design_ci(got, [True] * len(got)), "misattach": none}}}}
    check("so nothing is certified", X.verdict(arms)["1"]["call"] == "insufficient-evidence")
    sizes, bad = [300] + [10] * 970, [150] + [0] * 970
    check("it covers that population", _coverage(sizes, bad) >= 0.95)
    sizes = [154, 148, 88, 83, 83, 65] + [12] * 100 + [3] * 200
    for name, b in (("half the large commits", [m // 2 for m in sizes[:6]] + [0] * 300),
                    ("a few everywhere", [m // 8 for m in sizes]),
                    ("almost all", [m - 1 for m in sizes])):
        check(f"it covers a skewed population: {name}", _coverage(sizes, b) >= 0.95)


def test_undrawn_mass_is_added_stratum_by_stratum():
    """All 8,000 block moves represented and hit; of 2,000 child moves in 1,000
    commits, only 100 commits drawn, all missed. The undrawn children could take the
    truth to 98% found, so the upper bound must reach it."""
    class Kind(_Ev):
        def __init__(self, n, j, kind):
            super().__init__(n, 0, j)
            self.kind = kind
    evs = [Kind(n, n // 20, "block") for n in range(8000)]
    evs += [Kind(8000 + n, 1000 + n // 2, "child") for n in range(2000)]
    got, frame = X.sample_moves(evs, 500, 7)
    check("children go undrawn", frame["child:d0"]["moves_in_undrawn_commits"] > 0)
    found = X.design_ci(got, [e.kind == "block" for e in got])
    undrawn = frame["child:d0"]["moves_in_undrawn_commits"] / 10_000
    check("the upper bound holds the undrawn children", found["hi"] >= 0.8 + undrawn)
    check("and says how much", abs(found["unseen"] - undrawn) < 1e-9)
    tiny, tiny_frame = X.sample_moves(evs, 1, 7)
    check("no stratum goes undrawn", set(tiny_frame) == {"block:d0", "child:d0"} and {e.kind for e in tiny} == {"block", "child"})


def test_a_commit_drawn_whole_carries_no_uncertainty():
    evs = [_Ev(n, 0, n) for n in range(100)]
    got, _ = X.sample_moves(evs, 100, 7)
    ci = X.design_ci(got, [True] * 100)
    check("a census of hits is exact", ci["lo"] == 1.0 and ci["hi"] == 1.0)
    miss = X.design_ci(got, [False] * 100)
    check("and of misses", miss["lo"] == 0.0 and miss["hi"] == 0.0)
    rows = {"n": 100, "design": {"found": ci, "misattach": miss}}
    check("a census can certify", X.verdict({"1": {"hash, all docs": rows}})["1"]["call"] == "ids-not-needed")
    mixed = [_Ev(n, 0, n) for n in range(10)] + [_Ev(10 + n, 0, 100) for n in range(90)]
    got, _ = X.sample_moves(mixed, 0, 7)
    check("only commits of one move are certain", sorted(e.certain for e in got) == [False] + [True] * 10)
    whole = X.design_ci(got, [False] * len(got))
    check("the open commit still bounds the rest", 0.8 < whole["hi"] <= 0.9)


def test_commits_never_drawn_are_bounded():
    """One commit of 50,000 hits and 999 commits of one miss each. A sample of 300
    misses the large commit, and the ratio estimate over what it drew reads 0% found:
    the frame knows how much it did not see, so that must not call `ids-pay`."""
    evs = [_Ev(n, 0, 0) for n in range(50_000)] + [_Ev(50_000 + j, 0, j) for j in range(1, 1000)]
    got, frame = X.sample_moves(evs, 300, 7)
    if any(e.j == 0 for e in got):
        got, frame = X.sample_moves(evs, 300, 8)
    check("the sample misses the large commit", not any(e.j == 0 for e in got))
    check("the frame says how much it missed", frame["child:d0"]["moves_in_undrawn_commits"] > 50_000)
    ci = X.design_ci(got, [False] * len(got))
    check("the estimate reads zero", ci["point"] == 0.0)
    check("the bound reaches the population's true 98% found", ci["hi"] >= 0.98)
    arms = {"1": {"hash, all docs": {"n": len(got), "design": {
        "found": ci, "misattach": X.design_ci(got, [False] * len(got))}}}}
    check("so the call is not ids-pay", X.verdict(arms)["1"]["call"] == "insufficient-evidence")


def test_every_commit_is_drawn_by_default():
    evs = [_Ev(n, 0, 0) for n in range(500)] + [_Ev(500 + n, 0, 1 + n // 2) for n in range(100)]
    evs += [_Ev(700 + n, 3, 100 + n) for n in range(10)]
    got, frame = X.sample_moves(evs, 0, 7)
    check("one draw per commit per stratum", len(got) == 1 + 50 + 10 and len({(e.j, e.stratum) for e in got}) == len(got))
    check("nothing unseen", all(f["moves_in_undrawn_commits"] == 0 and f["max_draws_per_commit"] == 1 for f in frame.values()))
    check("each draw weighs its commit", next(e for e in got if e.j == 0).weight == 500.0)
    check("weights restore the population", abs(sum(e.weight for e in got) - len(evs)) < 1e-9)
    check("no widening", X.design_ci(got, [e.j % 2 == 0 for e in got])["unseen"] == 0.0)
    check("no moves, no draws", X.sample_moves([], 0, 7) == ([], {}))


def test_unscored_moves_are_bounded_as_hits_or_misses():
    """2,000 hits plus 2,000 kind-changing moves no arm can answer: an arm finds at
    most half of all moves for sure, so this must not read as 100% found."""
    evs = [_Cell(j, "child", 1.0) for j in range(2000)]
    row = {"n": 2000, "design": {"found": X.design_ci(evs, [True] * 2000, unscored=0.5),
                                 "misattach": X.design_ci(evs, [False] * 2000, unscored=0.5)}}
    check("the lower bound falls to the half that was scored", row["design"]["found"]["lo"] <= 0.5)
    check("the call is withheld", X.verdict({"1": {"hash, all docs": row}})["1"]["call"] == "insufficient-evidence")
    misses = {"n": 2000, "design": {"found": X.design_ci(evs, [False] * 2000, unscored=0.5),
                                    "misattach": X.design_ci(evs, [False] * 2000, unscored=0.5)}}
    check("a bound that cannot rescue the arm does not stop ids-pay", X.verdict({"1": {"hash, all docs": misses}})["1"]["call"] == "ids-pay")
    tiny = X.design_ci(evs, [True] * 2000, unscored=1 / 3133)
    check("one in 3,133 moves the bound by about that", 0 < X.design_ci(evs, [True] * 2000)["lo"] - tiny["lo"] < 1 / 3000)


def test_exact_ratio_matches_difflib():
    import random as _r
    from difflib import SequenceMatcher
    rng = _r.Random(21)
    for trial in range(300):
        al = rng.choice(["ab", "abc de", "abcdefgh \u00e9\u20ac\U0001F600 "])
        a = "".join(rng.choice(al) for _ in range(rng.randint(0, 120)))
        b = "".join(rng.choice(al) for _ in range(rng.randint(0, 120)))
        if rng.random() < 0.3:
            b = a[: len(a) // 2] + "xy" + a[len(a) // 2 :]
        want = sum(m.size for m in SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
        check(f"ro_matches == difflib (trial {trial})", X.ro_matches(a, b, small=8) == want)
    long_a = "x" * 8000 + "y" + "x" * 8000
    long_b = "x" * 8000 + "z" + "x" * 8000
    want = 2 * 16000 / 32002
    check("a 16,000-character quote with one character changed keeps its exact score",
          abs(X._exact_body(long_a, long_b) - want) < 1e-12 and X._pruned_body(long_a, long_b) > 0.99)


# --- review regressions -------------------------------------------------------------


def test_context_stops_at_a_document_boundary():
    """Two tied twins. Unrelated documents on either side of the first end and start
    on the anchor's stored neighbours, which would hand it the margin if context
    crossed a document boundary. The second twin's own neighbours match nothing."""
    twin = "A paragraph that appears word for word in two separate documents here."
    # Edited on both sides: an exact twin scores 1.0, where the clamp would swallow
    # any context a leak added and this test could not fail.
    edited = twin.replace("word for word", "nearly verbatim")
    prefix, suffix = "the stored neighbour before the block", "the stored neighbour after the block"
    old = f"{prefix}\n\n{twin} <!-- stay:aaaaaaaa -->\n\n{suffix}\n"
    anchors = A.build_anchors(old, X.parse(old), {"aaaaaaaa"})
    check("the twins score low enough for context to count",
          L._match_ratio(L._match_normalize(twin), L._match_normalize(edited)) < 0.95)
    before = X.Unit("a.md", X.parse(f"# Unrelated\n\n{prefix}\n"))
    after = X.Unit("c.md", X.parse(f"{suffix}\n\n# Unrelated\n"))
    t1 = X.Unit("b.md", X.parse(f"{edited}\n"))
    t2 = X.Unit("d.md", X.parse(f"7777777\n\n{edited}\n\n8888888\n"))
    check("no document, no contest: a tie detaches", X._block_quote(anchors, [t1, t2])["aaaaaaaa"] is None)
    check("unrelated documents do not break the tie",
          X._block_quote(anchors, [before, t1, after, t2])["aaaaaaaa"] is None)
    for order in ([t2, before, t1, after], [before, t1, t2, after]):
        check("unit order changes nothing", X._block_quote(anchors, order)["aaaaaaaa"] is None)
    # The control: the same neighbours inside one document do count.
    near = X.Unit("e.md", X.parse(f"{prefix}\n\n{edited}\n\n{suffix}\n"))
    got = X._block_quote(anchors, [near, t2])["aaaaaaaa"]
    check("context inside a document breaks the tie", got == (0, 1))


def test_container_context_stops_at_a_document_boundary():
    prefix, suffix = "the stored neighbour before the list", "the stored neighbour after the list"
    items = "- one item here for the list\n- second item here for the list\n"
    old = stamped(f"{prefix}\n\n{items}\n{suffix}\n", "c")
    anchors = [a for a in L._build_child_anchors(old, X.MODE)]
    edited = items.replace("second item", "another entry")  # low enough for context to count
    check("the containers score low enough for context to count",
          L._match_ratio(L._match_normalize(items), L._match_normalize(edited)) < 0.9)
    before = X.Unit("a.md", X.parse(f"# Unrelated\n\n{prefix}\n"))
    after = X.Unit("c.md", X.parse(f"{suffix}\n\n# Unrelated\n"))
    t1 = X.Unit("b.md", X.parse(edited))
    t2 = X.Unit("d.md", X.parse(f"7777777\n\n{edited}\n8888888\n"))
    check("twin containers: no parent resolves", not X.resolve_parents(anchors, [t1, t2]))
    check("unrelated documents do not resolve one", not X.resolve_parents(anchors, [before, t1, after, t2]))
    near = X.Unit("e.md", X.parse(f"{prefix}\n\n{edited}\n{suffix}\n"))
    got = X.resolve_parents(anchors, [near, t2])
    check("context inside a document resolves it", [v[0][0] for v in got.values()] == [0])


def test_block_arms_match_the_shipped_arms_on_one_document():
    t = stamped(TRACKER, "t")
    blocks_old = X.parse(t)
    ids = {mk.id for b in blocks_old for mk in b.markers if mk.id and not mk.has_subhash}
    anchors = A.build_anchors(t, blocks_old, ids)
    for name, new in _edits(t):
        nb = X.parse(new)
        after = A.build_after(new, nb)
        unit = X.Unit("doc.md", nb)
        S = A.Scores()
        pick = lambda got: {m: None if g is None else g[1] for m, g in got.items()}  # noqa: E731
        check(f"{name}: quote == arms.arm_quote", pick(X._block_quote(anchors, [unit])) == A.arm_quote(anchors, after, S))
        check(f"{name}: hash == arms.arm_hash", pick(X._block_hash(anchors, [unit])) == A.arm_hash(anchors, after, S))


def _repo(tmp):
    repo, out = Path(tmp) / "repo", Path(tmp) / "out"
    (repo / "docs").mkdir(parents=True)
    _git(repo, "init", "-q")
    step = [0]

    def commit(files):
        for p, text in files.items():
            (repo / p).parent.mkdir(parents=True, exist_ok=True)
            (repo / p).write_text(text)
        step[0] += 1
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", f"c{step[0]}")

    return repo, out, commit


def test_a_marker_that_moves_away_leaving_a_mention_is_a_move():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    with tempfile.TemporaryDirectory() as tmp:
        repo, out, commit = _repo(tmp)
        commit({"docs/tracker.md": t, "docs/archive.md": a})
        t1, a1, mid = _moved(t, a, "Rotate the staging")
        commit({"docs/tracker.md": t1 + f"\nThat item was `stay:{mid}`, see the archive.\n", "docs/archive.md": a1})
        res = X.run(repo, ["docs/*.md"], out, "M", (1,), 1, 0)
        check("the departure is seen despite the mention", res["moves_by_window"]["1"]["moves"] == 1)
        check("and scored", res["arms"]["1"]["child hash, all docs"]["correct"] == 1)


def test_an_inline_example_of_an_id_is_not_its_anchor():
    """The real item carries an id an earlier item shows as an example. The example
    must not stand in for it, or every arm resolves to the example left behind."""
    real = "Rotate the staging credentials after the audit"
    example = "- [ ] See `<!-- stay:aaaaaaaa subhash=sha256:000000000000 -->` for the form"
    item = f"- [x] {real} <!-- stay:aaaaaaaa subhash=sha256:{L.body_hash('[x] ' + real)[:12]} -->"
    old = f"# T\n\n{example}\n{item}\n- [ ] Something else entirely stays here\n"
    raw = L._build_child_anchors(old, X.MODE)
    check("the shipped builder reads the example first", [a.id for a in raw][:1] == ["aaaaaaaa"] and "See" in raw[0].quote)
    got = [a for a in X.child_anchors(old) if a.id == "aaaaaaaa"]
    check("only the real item is the anchor", len(got) == 1 and real in got[0].quote)
    after = X.Unit("a.md", X.parse(f"# T\n\n{example}\n- [ ] Something else entirely stays here\n"))
    arch = X.Unit("b.md", X.parse(f"# A\n\n{item}\n"))
    want = (1, _truth(arch, "aaaaaaaa"))
    anchors = X.child_anchors(old)
    check("store-wide hash finds the moved item", X.child_hash(anchors, [after, arch])["aaaaaaaa"][1] == want)
    check("store-wide quote finds it", X.child_quote(anchors, [after, arch])["aaaaaaaa"][1] == want)
    check("the pooled ladder finds it", X.child_ladder(anchors, [after, arch])["aaaaaaaa"][1] == want)
    only = "- [ ] Shows `<!-- stay:bbbbbbbb subhash=sha256:000000000000 -->` and is not it\n"
    check("an id only ever quoted has no anchor", not any(a.id == "bbbbbbbb" for a in X.child_anchors(only)))
    quoted = "Shows `<!-- stay:cccccccc hash=sha256:000000000000 -->` first\n<!-- stay:dddddddd hash=sha256:000000000000 -->\n\n"
    para = "- one item here <!-- stay:eeeeeeee subhash=sha256:000000000000 -->\n<!-- stay:ffffffff hash=sha256:000000000000 -->\n"
    check("a real container keeps its id", {a.parent_id for a in X.child_anchors(quoted + para)} == {"ffffffff"})
    # Two identical lists, one with a container stay: only its own items get that id.
    twin = "- same item in both lists"
    pair = (f"{twin} <!-- stay:11111111 subhash=sha256:000000000000 -->\n<!-- stay:22222222 hash=sha256:000000000000 -->\n\n"
            "Between them.\n\n"
            f"{twin} <!-- stay:33333333 subhash=sha256:000000000000 -->\n")
    parents = {a.id: a.parent_id for a in X.child_anchors(pair)}
    check("a twin list does not lend its container id", parents == {"11111111": "22222222", "33333333": None})
    tricky = "- list `<!-- stay:cccccccc hash=sha256:000000000000 -->` first <!-- stay:eeeeeeee subhash=sha256:000000000000 -->\n<!-- stay:ffffffff hash=sha256:000000000000 -->\n"
    check("a quoted id is not the container's", {a.parent_id for a in X.child_anchors(tricky)} == {"ffffffff"})


def test_a_mention_alone_is_not_a_destination():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    with tempfile.TemporaryDirectory() as tmp:
        repo, out, commit = _repo(tmp)
        commit({"docs/tracker.md": t, "docs/archive.md": a})
        t1, line = _lines_without(t, "Wire the nightly")
        mid = L.find_markers(line)[0].id
        commit({"docs/tracker.md": t1, "docs/archive.md": a + f"\nThe id `stay:{mid}` is gone.\n"})
        for n in range(3):
            commit({"docs/tracker.md": t1 + f"\nPad {n}.\n"})
        res = X.run(repo, ["docs/*.md"], out, "N", (1,), 1, 0)
        check("no move", res["moves_by_window"]["1"]["moves"] == 0)
        check("a deletion", res["status"].get("deletion") == 1)


def test_kind_changing_moves_are_counted_and_not_scored():
    t, a = stamped(TRACKER, "t"), stamped(ARCHIVE, "a")
    with tempfile.TemporaryDirectory() as tmp:
        repo, out, commit = _repo(tmp)
        para = "A lone paragraph that will come back as a list item."
        base = stamped(para + "\n\n" + "## Keep\n", "p")
        mid = L.find_markers(base)[0].id
        commit({"docs/source.md": base, "docs/archive.md": a, "docs/tracker.md": t})
        digest = L.body_hash(para)
        arrived = _append_item(a, "Retire the legacy", f"- {para} <!-- stay:{mid} subhash=sha256:{digest[:12]} -->")
        commit({"docs/source.md": "## Keep\n", "docs/archive.md": arrived})
        # and a child stay arriving as a block stay
        t1, line = _lines_without(t, "Rotate the staging")
        mid2 = L.find_markers(line)[0].id
        body = line.split(" <!--")[0][2:]
        commit({"docs/tracker.md": t1,
                "docs/other.md": f"{body}\n<!-- stay:{mid2} hash=sha256:{L.body_hash(body)[:12]} -->\n"})
        res = X.run(repo, ["docs/*.md"], out, "K", (1,), 1, 0)
        check("both moves are seen", res["moves_by_window"]["1"]["moves"] == 2)
        check("both change kind", res["moves_by_window"]["1"]["kind_changing"] == 2)
        check("the kinds are reported", res["move_kinds"] == {"block->child": 1, "child->block": 1})
        check("neither is scored", res["arms"]["1"] == {})
        check("the verdict has no data", res["verdict"]["1"]["call"] == "no-data")
        # One ordinary move beside them: the combined interval answers for the two.
        t2, line2 = _lines_without(t1, "Wire the nightly")
        commit({"docs/tracker.md": t2, "docs/archive.md": _append_item(arrived, "Retire the legacy", line2)})
        res = X.run(repo, ["docs/*.md"], out, "K", (1,), 1, 0)
        row = res["arms"]["1"]["hash, all docs"]["design"]["found"]
        check("the combined interval carries their share", abs(row["unseen"] - 2 / 3) < 1e-9)
        check("a per-kind row does not", res["arms"]["1"]["child hash, all docs"]["design"]["found"]["unseen"] == 0.0)
        check("nor can one scored move decide", res["verdict"]["1"]["call"] == "insufficient-evidence")


def test_default_scope_of_ids_elsewhere_reaches_excluded_documents():
    with tempfile.TemporaryDirectory() as tmp:
        repo, out, commit = _repo(tmp)
        md = "A paragraph. <!-- stay:abcd1234 -->\n"
        commit({"docs/one.md": md, "examples/two.md": md})
        head = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        RP.configure(repo)
        check("the umbrella's default counts an excluded destination",
              RP.ids_elsewhere(head, "abcd1234", "docs/one.md") == ["examples/two.md"])
        check("though that document is outside the corpus", not RP.in_scope("examples/two.md"))
        RP.configure(repo, ["docs/*.md"], out)
        check("explicit globs restrict it", RP.ids_elsewhere(head, "abcd1234", "docs/one.md") == [])
    RP.configure()


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    for t in tests:
        t()
    print(f"{PASS} passed, {FAIL} failed")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
