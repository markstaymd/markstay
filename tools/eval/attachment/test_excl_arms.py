"""Tests for the exclusivity arms and the identity-boundary operators.

Runs under pytest or bare:  python test_excl_arms.py
"""

from __future__ import annotations

import itertools
import json
import sys
import time
from dataclasses import fields
from pathlib import Path

import excl_arms as E
import perturb as PB
import ladder_v110 as R

HERE = Path(__file__).parent
DOC1 = (HERE.parent / "docs" / "doc1.md").read_text()
DOC2 = (HERE.parent / "docs" / "doc2.md").read_text()
ADV = (HERE / "fixtures" / "near_dups.md").read_text()
XSEC = (HERE / "fixtures" / "cross_section_dups.md").read_text()
L = PB.L


def _apply(base, op, strip=True):
    before, pbs = PB.annotate(base)
    anchors = R.build_anchors(before)
    after_pbs, adj = E.ALL_OPS[op](pbs)
    truth = PB.default_truth(after_pbs)
    truth.update(adj)
    return pbs, after_pbs, truth, anchors, PB.serialize(after_pbs, strip=strip)


def _summary(res):
    return {k: (v.method, v.target) for k, v in res.items()}


# --- the control does not move ------------------------------------------------


INHERITED = [f.name for f in fields(R.Resolution)]


def _assert_same(ship, mine, where):
    assert ship.keys() == mine.keys(), where
    for k, v in ship.items():
        got = {n: getattr(mine[k], n) for n in INHERITED}
        assert got == {n: getattr(v, n) for n in INHERITED}, (where, k)


def test_flags_off_is_the_frozen_ladder_everywhere():
    """Every arm is the v1.10 ladder plus its flags and nothing else. If this
    reimplementation drifted, an arm's difference from the control could be the
    drift rather than the rule. Every inherited field is compared, candidates
    and their evidence included; only the added `via` is not."""
    for d, base in enumerate((DOC1, DOC2, ADV, XSEC)):
        before, pbs = PB.annotate(base)
        full = R.build_anchors(before)
        for op in E.ALL_OPS:
            after_pbs, _ = E.ALL_OPS[op](pbs)
            for keep in (None, 0, 1):
                anchors = full if keep is None else [
                    a for k, a in enumerate(full) if k % 2 == keep]
                stamped = {a.id for a in anchors}
                shown = [PB.PBlock(text=pb.text, ids=[i for i in pb.ids if i in stamped])
                         for pb in after_pbs]
                for strip in (True, False):
                    after = PB.serialize(shown, strip=strip)
                    _assert_same(R.resolve(anchors, after), E.resolve(anchors, after),
                                 (d, op, keep, strip))
                    if keep is None and strip:
                        kw = {"threshold": 0.4, "margin": 0.1}
                        _assert_same(R.resolve(anchors, after, **kw),
                                     E.resolve(anchors, after, **kw),
                                     (d, op, "t0.4 m0.1"))


def test_flags_off_matches_the_frozen_ladder_under_commonmark():
    """The same parity under §5.2 segmentation, where a loose list or a fence
    with blank lines is one block."""
    for base in (DOC1, DOC2, ADV, XSEC):
        before, pbs = PB.annotate(base)
        anchors = R.build_anchors(before, mode="commonmark")
        for op in ("reorder", "edit_in_place", "merge", "split", "copy_above"):
            after_pbs, _ = E.ALL_OPS[op](pbs)
            for strip in (True, False):
                after = PB.serialize(after_pbs, strip=strip)
                _assert_same(R.resolve(anchors, after, mode="commonmark"),
                             E.resolve(anchors, after, mode="commonmark"),
                             (op, strip))


def test_committed_results_are_what_the_code_produces():
    """Every published number, pinned: regenerate the whole report and compare
    it with the committed JSON (every arm; closed, half-stamped, both operator
    sets, and the copy table). About fifteen seconds, because it is the run."""
    committed = json.loads((HERE / "results_exclusivity.json").read_text())
    assert json.loads(json.dumps(E.run())) == committed


def test_new_operators_stay_out_of_the_published_registry():
    """`results.md` is measured over OPERATORS; adding to it would move every
    published number."""
    assert not set(PB.EXCL_OPERATORS) & set(PB.OPERATORS)
    assert not set(PB.EXCL_OPERATORS) & set(PB.SECTION_OPERATORS)
    assert not set(PB.TWIN_EDIT_OPERATORS) & set(PB.OPERATORS)
    assert not set(PB.TWIN_EDIT_OPERATORS) & set(PB.SECTION_OPERATORS)


def test_headline_counts():
    """The closed-world pooled counts the findings quote. The control's are the
    published numbers summed over the three corpora."""
    s = E.summarize(E.sweep(None, strip=True,
                            arms=["ladder", "t2", "t23", "t23dk"]))["pooled"]
    got = {k: (v["correct"], v["missed"], v["misattached"], v["correct_detach"])
           for k, v in s.items()}
    assert got == {"ladder": (692, 165, 6, 5), "t2": (691, 168, 4, 5),
                   "t23": (690, 173, 0, 5), "t23dk": (690, 173, 0, 5)}


def test_flags_off_is_the_frozen_ladder_when_partly_marked():
    """The same parity on the partly-marked inputs, where tier 1 and the lower
    tiers run in one document. The twin operator is included."""
    for base in (DOC1, DOC2, ADV, XSEC):
        before, pbs = PB.annotate(base)
        anchors = R.build_anchors(before)
        for op in E.ALL_OPS:
            after_pbs, _ = E.ALL_OPS[op](pbs)
            for mark in (0, 1):
                kept = {a.id for k, a in enumerate(anchors) if k % 2 == mark}
                shown = [PB.PBlock(text=pb.text, ids=[i for i in pb.ids if i in kept])
                         for pb in after_pbs]
                after = PB.serialize(shown, strip=False)
                _assert_same(R.resolve(anchors, after), E.resolve(anchors, after),
                             (op, mark))


# --- the freeze ---------------------------------------------------------------


FROZEN_SOURCES = ("excl_arms.py", "heading_arms.py", "twin_corpus.py",
                  "measure_context.py", "clamp_on_sections.py", "llm/llm_attach.py",
                  "llm/run_llm_attach_eval.py", "../replay/arms.py")


def test_frozen_harnesses_import_the_frozen_ladder():
    """An import away from the live reference is how a dated record starts
    describing a resolver it never measured. `audit_cross_section.py` carries its
    own ladder and `eval/dogfood` and `eval/openknowledge/score.py` read only the
    linter, so none of those has an import to check."""
    for name in FROZEN_SOURCES:
        src = (HERE / name).read_text()
        assert "import ladder_v110" in src or "from ladder_v110 import" in src, name
        assert "import resolver" not in src, name
        assert "from mutation_check import resolve_variant" not in src, name
    assert R.__name__ == "ladder_v110"


def test_heading_arms_do_not_reach_the_live_ladder_through_the_harness():
    """`heading_arms` runs through `run_attach_eval.run_case`, which is live."""
    import heading_arms as HA
    import run_attach_eval as RUN

    class Seen(Exception):
        pass

    def spy(*_a, resolve=None, **_k):
        assert resolve is R.resolve
        raise Seen

    live = RUN.run_case
    RUN.run_case = spy
    try:
        HA.run()
    except Seen:
        return
    finally:
        RUN.run_case = live
    raise AssertionError("heading_arms.run never called run_case")


def test_frozen_variant_defaults_are_the_frozen_ladder():
    """`twin_corpus`, `measure_context` and `clamp_on_sections` read the ladder
    through `resolve_variant`. `mutation_check`'s differential moves to the live
    resolver with the spec, so this is what holds the frozen pair together."""
    for base in (DOC1, DOC2, ADV, XSEC):
        before, pbs = PB.annotate(base)
        anchors = R.build_anchors(before)
        for op in E.ALL_OPS:
            after_pbs, _ = E.ALL_OPS[op](pbs)
            for strip in (True, False):
                after = PB.serialize(after_pbs, strip=strip)
                ship = R.resolve(anchors, after)
                got = R.resolve_variant(before, after, R.DEFAULT_THRESHOLD, R.DEFAULT_MARGIN)
                assert ship.keys() == got.keys(), (op, strip)
                for k, v in ship.items():
                    assert (got[k]["method"], got[k]["target"]) == (v.method, v.target), (op, k)
                    assert abs(got[k]["score"] - v.score) < 1e-9, (op, k)


_SEALED = """
import sys
sys.path.insert(0, {here!r})
sys.modules["mutation_check"] = None            # any import of it raises
sys.modules["conformance.mutation_check"] = None
import resolver

def _live(*a, **k):
    raise RuntimeError("live resolver.resolve reached")

resolver.resolve = _live                        # before ladder_v110 can alias it
import ladder_v110 as F
before = "Alpha text about queues.\\n<!-- stay:a -->\\n\\nBeta text about rollbacks.\\n<!-- stay:b -->\\n"
after = "Beta text about rollbacks, edited.\\n\\nAlpha text about queues.\\n"
marked = "# Head\\n\\nBeta text about rollbacks.\\n<!-- stay:b -->\\n\\nAlpha text about queues.\\n"
anchors = F.build_anchors(before)
seen = set()
for doc in (after, marked, before):
    for kw in ({{}}, {{"heading_path": "bonus"}}, {{"heading_path": "filter", "clamp": False}},
               {{"mode": "commonmark"}}):
        seen |= {{r.method for r in F.resolve(anchors, doc, **kw).values()}}
    for kw in ({{}}, {{"unicode_fold": True, "window_stored": False,
                       "store_whole_neighbour": True, "hash_ambiguity": "first-hit"}},
               {{"rank": "body", "guard": "body", "bonus_tiebreak_only": 0.01}}):
        seen |= {{r["method"] for r in F.resolve_variant(before, doc, 0.5, 0.05, **kw).values()}}
assert {{"marker", "hash", "quote"}} <= seen, seen
print("sealed")
"""


def test_the_frozen_ladder_reaches_neither_live_ladder():
    """`mutation_check.py` and `resolver.resolve` move with the spec. Run the frozen
    `resolve` and a mutated `resolve_variant` in a process where importing
    `mutation_check` fails and `resolver.resolve` raises, installed before
    `ladder_v110` loads, so an alias taken at import is caught as well."""
    import subprocess
    out = subprocess.run([sys.executable, "-c", _SEALED.format(here=str(HERE))],
                         capture_output=True, text=True, cwd=HERE)
    assert out.returncode == 0 and out.stdout.strip() == "sealed", out.stderr[-800:]
    # A route the run does not take still has to be written down somewhere, and
    # these are the ones it would be written as. A guard against drift, not against
    # a module built to hide its imports.
    src = (HERE / "ladder_v110.py").read_text()
    assert "mutation_check" not in src.replace("`conformance/mutation_check.py`", "")\
        .replace("`mutation_check.py`", "")
    assert "importlib" not in src and "__import__" not in src
    import ast
    tree = ast.parse(src)
    imports = []  # every import node, at any depth or branch
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports += [(a.name, None) for a in node.names]
        elif isinstance(node, ast.ImportFrom):
            imports += [(node.module or "", a.name) for a in node.names]
    def banned(name):
        last = (name or "").split(".")[-1]
        return last in ("mutation_check", "importlib") or name.startswith("importlib")
    assert not [(m, n) for m, n in imports if banned(m) or banned(n or "")]
    # `from pkg import resolver` names the live module under another route.
    assert not [(m, n) for m, n in imports if n is not None and n.split(".")[-1] == "resolver"]
    from_resolver = sorted(n for m, n in imports if m.split(".")[-1] == "resolver")
    plain_resolver = [m for m, n in imports if n is None and m.split(".")[-1] == "resolver"]
    assert from_resolver == ["Anchor", "L", "Resolution", "build_anchors"], from_resolver
    assert plain_resolver == []
    top = [n for n in tree.body if isinstance(n, ast.ImportFrom) and n.module == "resolver"]
    assert len(top) == 1, "the resolver import must stay one top-level statement"


def test_measure_context_regenerates_its_committed_results(tmp_path=None):
    """`results_context.json` is a dated record on the frozen variant. Written to a
    scratch path, never over the committed file."""
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "ctx"
        subprocess.run([sys.executable, str(HERE / "measure_context.py"), "--out", str(out)],
                       check=True, capture_output=True, cwd=HERE)
        got = json.loads(Path(str(out) + ".json").read_text())
    assert got == json.loads((HERE / "results_context.json").read_text())


# --- the partly-marked run ------------------------------------------------------


def _partly():
    return E.sweep(E.PARTLY_OPS, strip=False, marks=(0, 1), arms=["ladder", E.CHOSEN])


def _counts(r):
    return r["n"], r["correct"], r["missed"], r["misattached"], r["correct_detach"]


def test_partly_marked_keeps_every_anchor_and_every_other_marker():
    before, pbs = PB.annotate(DOC1)
    anchors = R.build_anchors(before)
    for mark in (0, 1):
        cell = E.run_case(DOC1, "reorder", strip=False, marked=mark, arms=["ladder"])
        assert [r["id"] for r in cell["ladder"]] == [a.id for a in anchors]
        methods = {r["id"]: r["method"] for r in cell["ladder"]}
        for k, a in enumerate(anchors):
            assert (methods[a.id] == "marker") == (k % 2 == mark), (mark, a.id)


def test_partly_marked_counts_and_the_stop_rule():
    """The run's whole point. Not blind: `FINDINGS.md` says the stop rule was
    written after a probe had seen zero."""
    s = E.summarize(_partly())
    assert _counts(s["pooled"]["ladder"]) == (2016, 1835, 165, 6, 10)
    assert _counts(s["pooled"][E.CHOSEN]) == (2016, 1829, 177, 0, 10)
    assert s["vs_control"][E.CHOSEN]["new_misattach"] == {}


def test_partly_marked_lost_recoveries_are_findings_a_merge_and_a_thrice_recorded_hash():
    """Five of the six are a merged id whose partner kept its marker, so the
    merged block is claimed at tier 1 and this id has no target. The sixth is the
    unchanged owner of a hash recorded three times."""
    lost = E.lost_recoveries(_partly(), E.CHOSEN)
    merges = [r for r in lost if r["op"] == "merge"]
    assert len(lost) == 6 and len(merges) == 5
    assert all((r["control_method"], r["reason"]) == ("quote", "unmatched") for r in merges)
    other = next(r for r in lost if r["op"] != "merge")
    assert (other["op"], other["control_method"], other["reason"]) == (
        "edit_in_place", "hash", "ambiguous")
    before, _ = PB.annotate(XSEC)
    anchors = R.build_anchors(before)
    owner = next(a for a in anchors if a.id == other["id"])
    assert sum(a.hash == owner.hash for a in anchors) == 3


def test_the_copy_operators_misattachments_are_the_copy_tables_and_only_tier_one():
    """Outside the registered run, the chosen form introduces eight on the
    identity-boundary operators. All eight are tier 1's carriers rule on an edited
    original, the failure finding 9's copy table already prices, and the block tiers
    alone introduce none."""
    ops = list(PB.EXCL_OPERATORS)
    data = E.sweep(ops, strip=False, marks=(0, 1), arms=["ladder", "t23dk", E.CHOSEN])
    s = E.summarize(data)
    assert s["vs_control"]["t23dk"]["new_misattach"] == {}
    assert s["vs_control"][E.CHOSEN]["new_misattach"] == {
        "copy_below_edit_original": 4, "copy_end_edit_original": 4}
    control = {(r["corpus"], r["op"], r["doc"], r["id"])
               for r in E.misattach_cases(data, "ladder")}
    new = [r for r in E.misattach_cases(data, E.CHOSEN)
           if (r["corpus"], r["op"], r["doc"], r["id"]) not in control]
    assert len(new) == 8 and all(r["method"] == "marker" for r in new)
    table = {(row["corpus"], row["doc"], row["op"]) for row in E.copy_table()
             if row["ladder"]["cat"] == "correct" and row[E.CHOSEN]["cat"] == "wrong"}
    assert {(r["corpus"], r["doc"][:2], r["op"]) for r in new} == table


def test_edit_into_twin_is_the_one_shape_that_reaches_the_tier_two_filter():
    """No published operator reaches the filter. This one does, once per document,
    and the filter turns a detach into the correct block."""
    assert not set(PB.TWIN_EDIT_OPERATORS) & set(PB.EXCL_OPERATORS)
    assert E.filter_moves(E.PARTLY_OPS)["moved"] == []
    twin = E.filter_moves(list(PB.TWIN_EDIT_OPERATORS))
    assert twin["n"] == 144 and len(twin["moved"]) == 4
    assert all((m["with_filter"], m["without_filter"]) == ("correct", "missed")
               for m in twin["moved"])
    s = E.summarize(E.sweep(list(PB.TWIN_EDIT_OPERATORS), strip=False, marks=(0, 1),
                            arms=["ladder", E.CHOSEN]))
    assert _counts(s["pooled"]["ladder"]) == (144, 125, 19, 0, 0)
    assert _counts(s["pooled"][E.CHOSEN]) == (144, 129, 15, 0, 0)


def test_edit_into_twin_makes_two_blocks_read_the_same_and_keeps_both_ids():
    for base in (DOC1, DOC2, ADV, XSEC):
        _, pbs = PB.annotate(base)
        after, adj = PB.edit_into_twin(pbs)
        assert adj == {} and [pb.ids for pb in after] == [pb.ids for pb in pbs]
        moved = [k for k, (a, b) in enumerate(zip(pbs, after)) if a.text != b.text]
        assert len(moved) == 1
        assert after[moved[0]].text in [pb.text for pb in pbs if pb.ids]


def test_finding_a_a_block_carrying_two_stays_loses_both_when_its_markers_go():
    """§5 lets one block carry two markers. Their anchors record one hash twice,
    so tier 2 commits to neither, tier 3 makes them contenders, and one copy of the
    text cannot hold two identical quotes. Fails closed, and held by decision: the
    anchor format cannot tell these two from two twins."""
    text = "One block that happens to carry two stays on its own."
    before = f"{text}\n<!-- stay:a -->\n<!-- stay:b -->\n"
    anchors = R.build_anchors(before)
    assert [a.id for a in anchors] == ["a", "b"]
    after = f"{text}\n"
    assert _summary(R.resolve(anchors, after)) == {"a": ("hash", 0), "b": ("hash", 0)}
    got = E.resolve(anchors, after, **dict(E.ARMS)[E.CHOSEN])
    assert {k: (v.method, v.reason) for k, v in got.items()} == {
        "a": ("detached", "contested"), "b": ("detached", "contested")}


def test_finding_b_a_merge_with_one_surviving_marker_loses_the_other_id():
    """The exemption compares tier-3 contenders only. A merged block that keeps
    one marker is claimed at tier 1, so the other id has no target and no contest
    to be exempted from. Fails closed, and held by decision."""
    first = "The nightly build publishes its artefacts to the shared bucket."
    second = "A failed publish pages whoever holds the release rota that week."
    before = f"{first}\n<!-- stay:a -->\n\n{second}\n<!-- stay:b -->\n"
    after = f"{first} {second}\n<!-- stay:a -->\n"
    anchors = R.build_anchors(before)
    assert _summary(R.resolve(anchors, after)) == {"a": ("marker", 0), "b": ("quote", 0)}
    got = E.resolve(anchors, after, **dict(E.ARMS)[E.CHOSEN])
    assert (got["a"].method, got["a"].target) == ("marker", 0)
    assert (got["b"].method, got["b"].reason) == ("detached", "unmatched")
    # With every marker stripped, the same merge keeps both.
    both = E.resolve(anchors, f"{first} {second}\n", **dict(E.ARMS)[E.CHOSEN])
    assert _summary(both) == {"a": ("quote", 0), "b": ("quote", 0)}


# --- operator ground truth ----------------------------------------------------


def test_replace_truth_is_detach_and_the_slot_holds_unrelated_text():
    pbs, after, truth, anchors, md = _apply(DOC1, "replace")
    victim = pbs[PB._nth_marked_para(pbs, 2)].ids[0]
    assert truth[victim]["accept"] is None
    assert len(after) == len(pbs)
    assert PB._UNRELATED in [pb.text for pb in after]
    assert all(victim not in pb.ids for pb in after)
    assert R.resolve(anchors, md)[victim].method == "detached"
    others = [a.id for a in anchors if a.id != victim]
    assert all(truth[i]["accept"] is not None for i in others)


def test_replace_related_keeps_half_the_words_and_still_must_detach():
    pbs, after, truth, _, _ = _apply(DOC1, "replace_related")
    i = PB._nth_marked_para(pbs, 2)
    victim = pbs[i].ids[0]
    assert truth[victim]["accept"] is None
    head = " ".join(pbs[i].text.split()[:4])
    assert after[i].text.startswith(head) and after[i].ids == []


def test_swap_edit_swaps_two_neighbours_and_drifts_both():
    pbs, after, truth, anchors, md = _apply(DOC1, "swap_edit")
    moved = [k for k, (a, b) in enumerate(zip(pbs, after)) if a.ids != b.ids]
    assert len(moved) == 2 and moved[1] == moved[0] + 1
    x, y = moved
    assert after[x].ids == pbs[y].ids and after[y].ids == pbs[x].ids
    assert truth[pbs[x].ids[0]]["accept"] == {y}
    hashes = {L.body_hash(b.content) for b in L.parse_document(md) if b.index >= 0}
    assert not {L.body_hash(pbs[x].text), L.body_hash(pbs[y].text)} & hashes


def test_copy_operators_pin_the_id_to_the_original():
    """SPEC.md §7: a copy mints a new stay. Every copy variant carries the
    original's marker on the pasted block, and truth names the original."""
    for op in PB.COPY_OPERATORS:
        pbs, after, truth, _, md = _apply(DOC1, op, strip=False)
        src = pbs[PB._nth_marked_para(pbs, 2)]
        mid = src.ids[0]
        carriers = [k for k, pb in enumerate(after) if mid in pb.ids]
        assert len(carriers) == 2, op
        assert md.count(f"stay:{mid} ") == 2, op
        orig = next(iter(truth[mid]["accept"]))
        copy = next(k for k in carriers if k != orig)
        where = op.split("_")[1]
        assert {"above": copy == orig - 1, "below": copy == orig + 1,
                "start": copy == 0, "end": copy == len(after) - 1}[where], op
        if op.endswith("_edit_copy"):
            assert after[orig].text == src.text != after[copy].text, op
        elif op.endswith("_edit_original"):
            assert after[copy].text == src.text != after[orig].text, op
        else:
            assert after[copy].text == after[orig].text == src.text, op
        for a in pbs:
            for i in a.ids:
                if i != mid:
                    assert truth[i]["accept"] == {next(k for k, pb in enumerate(after)
                                                       if i in pb.ids)}, (op, i)


def test_stripped_copy_is_an_unmarked_twin():
    _, after, _, _, md = _apply(DOC1, "copy_end", strip=True)
    assert "stay:" not in md
    assert after[-1].text in [pb.text for pb in after[:-1]]


# --- tier 1 for a duplicated id -----------------------------------------------

BEFORE = ("Alpha paragraph about the build server and its nightly queue.\n"
          "<!-- stay:a -->\n\n"
          "Beta paragraph about rollback windows and the staging database.\n"
          "<!-- stay:b -->\n\n"
          "Gamma paragraph about release notes and the changelog owner.\n"
          "<!-- stay:c -->\n")
BETA = "Beta paragraph about rollback windows and the staging database."


def _doc(*blocks):
    return "\n\n".join(blocks) + "\n"


def test_first_occurrence_wins_today_and_the_new_rules_refuse_to_guess():
    """A verbatim copy pasted above the original takes the id at tier 1 under
    the shipped rule. Both proposed rules and outright detach refuse instead."""
    after = _doc("Alpha paragraph about the build server and its nightly queue.\n<!-- stay:a -->",
                 BETA + "\n<!-- stay:b -->", BETA + "\n<!-- stay:b -->",
                 "Gamma paragraph about release notes and the changelog owner.\n<!-- stay:c -->")
    anchors = R.build_anchors(BEFORE)
    assert R.resolve(anchors, after)["b"].target == 1  # the copy
    for dup in ("absent", "carriers"):
        r = E.resolve(anchors, after, dup=dup)["b"]
        assert (r.method, r.reason) == ("detached", "ambiguous"), dup
    r = E.resolve(anchors, after, dup="detach")["b"]
    assert (r.method, r.reason) == ("detached", "duplicated")
    for dup in ("absent", "carriers", "detach"):
        res = E.resolve(anchors, after, dup=dup)
        assert (res["a"].target, res["c"].target) == (0, 3)


def test_an_edited_copy_leaves_the_original_on_the_stored_hash():
    edited = BETA.replace("staging", "production") + " Changed after pasting."
    after = _doc("Alpha paragraph about the build server and its nightly queue.\n<!-- stay:a -->",
                 edited + "\n<!-- stay:b -->", BETA + "\n<!-- stay:b -->",
                 "Gamma paragraph about release notes and the changelog owner.\n<!-- stay:c -->")
    anchors = R.build_anchors(BEFORE)
    assert R.resolve(anchors, after)["b"].target == 1
    r = E.resolve(anchors, after, dup="carriers")["b"]
    assert (r.method, r.target, r.via) == ("marker", 2, "carrier-hash")
    assert E.resolve(anchors, after, dup="absent")["b"].target == 2


def test_an_edited_original_loses_to_its_verbatim_copy_under_both_rules():
    """The case neither rule can get right: the copy is now the only block
    whose body matches what was stored, so hash evidence names it."""
    edited = BETA.replace("staging", "production") + " Changed after pasting."
    after = _doc("Alpha paragraph about the build server and its nightly queue.\n<!-- stay:a -->",
                 edited + "\n<!-- stay:b -->", BETA + "\n<!-- stay:b -->",
                 "Gamma paragraph about release notes and the changelog owner.\n<!-- stay:c -->")
    anchors = R.build_anchors(BEFORE)
    # truth: block 1 is the original (edited), block 2 the pasted copy
    for dup in ("absent", "carriers"):
        assert E.resolve(anchors, after, dup=dup)["b"].target == 2, dup


def test_carriers_never_falls_through_to_an_unmarked_block():
    """The rule chosen for §9.1: a duplicated id resolves only among the
    blocks that carry it. Here both carriers drifted away from the stored text
    and an unmarked verbatim copy sits elsewhere. Treat-as-absent finds that
    copy by hash; carriers stays inside its pool and picks the closer carrier
    by quote, with the margin intact."""
    d1 = "Beta paragraph about rollback windows for the production database tier."
    d2 = "Beta notes on rollback windows and the staging cluster, revised again."
    after = _doc("Alpha paragraph about the build server and its nightly queue.\n<!-- stay:a -->",
                 d1 + "\n<!-- stay:b -->", d2 + "\n<!-- stay:b -->",
                 "Gamma paragraph about release notes and the changelog owner.\n<!-- stay:c -->",
                 BETA)
    anchors = R.build_anchors(BEFORE)
    absent = E.resolve(anchors, after, dup="absent")["b"]
    assert (absent.method, absent.target) == ("hash", 4)
    carriers = E.resolve(anchors, after, dup="carriers")["b"]
    assert (carriers.method, carriers.target, carriers.via) == ("marker", 1, "carrier-quote")
    assert carriers.score - carriers.runner_up_score >= R.DEFAULT_MARGIN


def test_a_single_carrier_is_plain_tier_one_under_every_rule():
    anchors = R.build_anchors(BEFORE)
    for dup in ("first", "absent", "carriers", "detach"):
        res = E.resolve(anchors, BEFORE, dup=dup)
        assert _summary(res) == {"a": ("marker", 0), "b": ("marker", 1),
                                 "c": ("marker", 2)}


# --- exclusivity ----------------------------------------------------------------

TWINS = ("Rollback restores the previous image and replays the queue.\n"
         "<!-- stay:x -->\n\n"
         "Middle paragraph that nobody touches during the edit.\n"
         "<!-- stay:m -->\n\n"
         "Rollback restores the previous image and replays the queue.\n"
         "<!-- stay:y -->\n")


def test_shipped_tier_two_collapses_two_ids_onto_one_survivor():
    """Finding 7's many-to-one shape: delete one twin and drift nothing else.
    The survivor is the unique hash hit for both ids."""
    after = _doc("Rollback restores the previous image and replays the queue.",
                 "Middle paragraph that nobody touches during the edit.")
    anchors = R.build_anchors(TWINS)
    ship = R.resolve(anchors, after)
    assert ship["x"].target == ship["y"].target == 0
    t2 = E.resolve(anchors, after, t2_excl=True)
    assert t2["x"].method != "hash" and t2["y"].method != "hash"
    t23 = E.resolve(anchors, after, t2_excl=True, t3_excl=True)
    assert t23["x"].reason == t23["y"].reason == "contested"
    assert t23["m"].target == 1


def test_contained_exemption_readmits_the_twin_collapse_and_disjoint_does_not():
    after = _doc("Rollback restores the previous image and replays the queue.",
                 "Middle paragraph that nobody touches during the edit.")
    anchors = R.build_anchors(TWINS)
    m = E.resolve(anchors, after, t2_excl=True, t3_excl=True, merge_exempt="contained")
    assert m["x"].target == m["y"].target == 0
    d = E.resolve(anchors, after, t2_excl=True, t3_excl=True, merge_exempt="disjoint")
    assert d["x"].method == d["y"].method == "detached"


def test_a_clean_merge_detaches_under_t23_and_survives_the_exemption():
    """§5 lets a merged block carry both ids. Plain tier-3 exclusivity calls the
    two ids a contest and detaches both; either exemption keeps them."""
    _, _, truth, anchors, md = _apply(DOC1, "merge")
    merged = [i for i, t in truth.items()
              if t["accept"] and sum(1 for u in truth.values()
                                     if u["accept"] == t["accept"]) == 2]
    assert len(merged) == 2
    t23 = E.resolve(anchors, md, t2_excl=True, t3_excl=True)
    assert all(t23[i].reason == "contested" for i in merged)
    for mode in ("contained", "disjoint"):
        r = E.resolve(anchors, md, t2_excl=True, t3_excl=True, merge_exempt=mode)
        assert all(r[i].target in truth[i]["accept"] for i in merged), mode


def test_claiming_a_rival_opens_a_margin_only_when_rivals_leave_the_pool():
    """`replace_related` on near_dups: the replaced block's near-duplicate
    siblings outscore the replacement, so the ladder detaches. Once those
    siblings are claimed by their own stays, removing them from the pool leaves
    the half-kept replacement alone over the threshold. Keeping them as rivals
    keeps the detach."""
    pbs, _, truth, anchors, md = _apply(ADV, "replace_related")
    victim = pbs[PB._nth_marked_para(pbs, 2)].ids[0]
    assert truth[victim]["accept"] is None
    assert R.resolve(anchors, md)[victim].method == "detached"
    pool = E.resolve(anchors, md, t2_excl=True, t3_excl=True)
    assert pool[victim].method == "quote"
    kept = E.resolve(anchors, md, t2_excl=True, t3_excl=True, rivals="kept")
    assert (kept[victim].method, kept[victim].reason) == ("detached", "ambiguous")


def test_disjoint_placement_searches_every_occurrence():
    """Quotes `abcd` and `bcde` fit `abcdef abcd` only if `abcd` takes its
    second occurrence. A greedy first-occurrence pick found that placement in
    one contender order and not the other."""
    for quotes in (["abcd", "bcde"], ["bcde", "abcd"]):
        assert E._merged("abcdef abcd", quotes, disjoint=True)
    assert E._merged("aaaa", ["aa", "aa"], disjoint=True)
    assert not E._merged("aaa", ["aa", "aa"], disjoint=True)
    assert not E._merged("x y", ["x y", "x y"], disjoint=True)
    # Only the overlapping second occurrence of `bb` (offset 2) leaves room for `ab`.
    assert E._merged("abbb", ["ab", "bb"], disjoint=True)
    # An empty quote fails the exemption; no contenders at all satisfies it.
    assert not E._merged("abc", ["", "a"], disjoint=True)
    assert not E._merged("abc", [""], disjoint=False)
    assert E._merged("abc", [], disjoint=True)
    # Touching occurrences do not overlap (half-open spans).
    assert E._merged("abcd", ["ab", "cd"], disjoint=True)
    before = "abcd\n<!-- stay:p -->\n\nbcde\n<!-- stay:q -->\n"
    anchors = R.build_anchors(before)
    for perm in itertools.permutations(anchors):
        for flags in ({"merge_exempt": "disjoint"},
                      {"merge_exempt": "disjoint", "rivals": "kept"}):
            res = E.resolve(list(perm), "abcdef abcd\n", t2_excl=True,
                            t3_excl=True, **flags)
            assert _summary(res) == {"p": ("quote", 0), "q": ("quote", 0)}, flags


def test_disjoint_placement_is_polynomial_on_repetitive_text():
    """Three identical contenders over a block that repeats their text almost
    three times. Enumerating occurrences took over six seconds here; the
    subset programme makes 2^3 * 3 searches. Three copies of 899 characters
    need 2697 and the body has 2696 before the X, so no placement exists."""
    q = ("0, " * 300).strip()
    body = ("0, " * 899).strip() + "X"
    start = time.perf_counter()
    assert not E._merged(body, [q, q, q], disjoint=True)
    assert E._merged(body, [q, q], disjoint=True)
    assert time.perf_counter() - start < 0.5
    before = "\n\n".join(f"{q}\n<!-- stay:{c} -->" for c in "abc") + "\n"
    start = time.perf_counter()
    res = E.resolve(R.build_anchors(before), body + "\n", **dict(E.ARMS)["t23dk"])
    assert time.perf_counter() - start < 3.0
    assert all(r.reason == "contested" for r in res.values())


def test_disjoint_placement_matches_exhaustive_search():
    """The subset programme against brute force over every choice of
    occurrences, on short random strings where brute force is cheap."""
    import random

    def brute(body, quotes):
        occ = [[i for i in range(len(body)) if body.startswith(q, i)] for q in quotes]
        for choice in itertools.product(*occ):
            spans = sorted((s, s + len(quotes[j])) for j, s in enumerate(choice))
            if all(a[1] <= b[0] for a, b in zip(spans, spans[1:])):
                return True
        return False

    rng = random.Random(1)
    for _ in range(5000):
        body = "".join(rng.choice("ab") for _ in range(rng.randint(1, 10)))
        quotes = ["".join(rng.choice("ab") for _ in range(rng.randint(1, 4)))
                  for _ in range(rng.randint(1, 4))]
        assert E._merged(body, quotes, disjoint=True) == brute(body, quotes), (body, quotes)


def test_a_carrier_quote_commit_keeps_the_quote_tiers_fields():
    """A duplicated id resolved by quote among its carriers is a tier-1
    result built from the quote tier's own: only `method` changes. Built by
    hand, it could silently drop a field the quote tier set."""
    d1 = "Beta paragraph about rollback windows for the production database tier."
    d2 = "Beta notes on rollback windows and the staging cluster, revised again."
    after = _doc("Alpha paragraph about the build server and its nightly queue.\n<!-- stay:a -->",
                 d1 + "\n<!-- stay:b -->", d2 + "\n<!-- stay:b -->",
                 "Gamma paragraph about release notes and the changelog owner.\n<!-- stay:c -->")
    anchors = R.build_anchors(BEFORE)
    blocks = [b.content for b in L.parse_document(after) if b.index >= 0]
    b = next(a for a in anchors if a.id == "b")
    direct = E._quote_tier(b, blocks, R.DEFAULT_THRESHOLD, R.DEFAULT_MARGIN, {1, 2},
                           "carrier-quote")
    got = E.resolve(anchors, after, dup="carriers")["b"]
    assert direct.method == "quote" and got.method == "marker"
    for name in INHERITED + ["via"]:
        if name != "method":
            assert getattr(got, name) == getattr(direct, name), name
    assert got.candidates == direct.candidates
    assert got.runner_up_score > 0.0


def test_a_block_claimed_at_tier_one_does_not_block_a_hash_hit():
    """Two different blocks are rewritten to read the same, and only one keeps
    its marker. That block is claimed at tier 1, so the other copy is the only
    unclaimed block with the stored hash and commits at tier 2. Counting the
    claimed block as a second hit used to detach it."""
    before = ("Please close the door.\n<!-- stay:A -->\n\n"
              "Shut the door, please.\n<!-- stay:B -->\n")
    after = ("Please close the door.\n\n"
             "Please close the door.\n<!-- stay:B -->\n")
    anchors = R.build_anchors(before)
    assert R.resolve(anchors, after)["A"].method == "detached"
    for flags in ({"t2_excl": True}, {"t2_excl": True, "t3_excl": True}):
        res = E.resolve(anchors, after, **flags)
        assert _summary(res) == {"A": ("hash", 0), "B": ("marker", 1)}, flags


def test_exclusive_tiers_do_not_depend_on_anchor_order():
    """§9.2: a tier is evaluated for every stay before any commit, so the
    order a tool enumerates stays in cannot pick a contest's winner."""
    for base, op in ((ADV, "merge"), (XSEC, "heading_rename"), (XSEC, "edit_in_place"),
                     (DOC1, "merge")):
        _, _, _, anchors, md = _apply(base, op)
        for flags in ({"t2_excl": True}, {"t2_excl": True, "t3_excl": True},
                      {"t2_excl": True, "t3_excl": True, "merge_exempt": "disjoint"},
                      {"t2_excl": True, "t3_excl": True, "merge_exempt": "disjoint",
                       "rivals": "kept"}):
            fwd = E.resolve(anchors, md, **flags)
            rev = E.resolve(list(reversed(anchors)), md, **flags)
            assert _summary(fwd) == _summary(rev), (op, flags)
            rot = anchors[len(anchors) // 2:] + anchors[:len(anchors) // 2]
            assert _summary(E.resolve(rot, md, **flags)) == _summary(fwd), (op, flags)


def test_half_stamped_hides_unstamped_markers_and_leaves_the_ladder_alone():
    """The shipped ladder resolves each anchor independently, so dropping half
    the anchors cannot change the others' answers. Only arms that look across
    anchors (exclusivity, historical uniqueness) can move."""
    full = E.run_case(XSEC, "edit_in_place", strip=False, arms=["ladder"])
    half = E.run_case(XSEC, "edit_in_place", strip=False, keep=0, arms=["ladder"])
    assert len(half["ladder"]) < len(full["ladder"])
    stripped_full = {r["id"]: r["cat"] for r in
                     E.run_case(XSEC, "edit_in_place", strip=True, arms=["ladder"])["ladder"]}
    for r in E.run_case(XSEC, "edit_in_place", strip=True, keep=1,
                        arms=["ladder"])["ladder"]:
        assert stripped_full[r["id"]] == r["cat"]


def test_every_other_id_is_untouched_by_a_marked_copy():
    rows = E.copy_table()
    assert len(rows) == 4 * len(PB.COPY_OPERATORS)
    assert all(row[lab]["others_all_correct"] for row in rows for lab in E.TIER1_ARMS)


def test_binomial_interval_matches_heading_arms_and_survives_large_n():
    import heading_arms as HA

    for k, n in ((0, 72), (3, 180), (6, 868)):
        assert all(abs(a - b) < 1e-9 for a, b in
                   zip(HA.clopper_pearson(k, n), E.clopper_pearson(k, n)))
    lo, hi = E.clopper_pearson(6, 4000)
    assert 0 < lo < 6 / 4000 < hi < 0.01


def main():
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as exc:
            failed += 1
            print(f"  FAIL: {t.__name__}: {exc}")
    print(f"{len(tests) - failed}/{len(tests)} tests passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
