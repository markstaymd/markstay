"""Should §9.1 assign blocks exclusively, and what should tier 1 do with an id
whose marker appears twice?

SPEC.md §9.2 makes child assignment exclusive at every tier: a tier is evaluated
for every stay before any commit, a block claimed by a stronger tier leaves the
pool, and a block two stays reach at the same tier goes to neither. CHILD HASH
also requires the hash to have been unique when it was recorded. §9.1 says none
of this for blocks, and its tier 1 never says what happens when the same id's
marker sits on two blocks. The v1.10 ladder takes the first one in document
order (`ladder_v110.py`, `surviving.setdefault`). These arms price both gaps.

    ladder        the v1.10 ladder, called directly (the control), frozen so the
                  control does not move when `resolver.py` takes the chosen form
    t2            tier 2 exclusive: commit a hash hit only when the hash was
                  unique among the stored anchors, the block is unclaimed, and
                  one anchor claims it. Tier 3 is the shipped one.
    t23           tiers 2 and 3 exclusive: §9.2's discipline applied to blocks.
                  At tier 3 claimed blocks leave the ranking, and a block two
                  anchors reach goes to neither (detached, reason `contested`).
    t23m          t23, except a tier-3 contest commits every contender when each
                  one's normalized quote is verbatim inside the block. That is
                  the clean merge, which §5 allows to carry both ids, and the
                  exemption as the prototype proposed it.
    t23d          post-hoc: t23m with the quotes required to occupy *disjoint*
                  places in the block. Added after t23m ran, because two
                  byte-identical twins are each "contained" in their surviving
                  copy, so plain containment hands both ids to one block, which
                  is the collapse exclusivity exists to stop.
    absent        a marker found on two or more blocks is treated as absent:
                  the id falls through to the shipped tiers 2 and 3 over the
                  whole document.
    carriers      a marker found on two or more blocks resolves only among the
                  blocks carrying it: a hash hit unique among the carriers, then
                  quote over the carriers with the usual threshold and margin,
                  else DETACHED. It never falls through to the rest of the
                  document.
    t23dk         post-hoc: t23d with claimed blocks kept as margin rivals at
                  tier 3. Added after t23 introduced misattachments by claiming
                  the rivals that had kept a weak wrong candidate below the
                  margin; this is the form chosen for v1.11.
    t23+carriers  t23 with the carriers rule at tier 1.
    t23dk+carriers
                  t23dk with the carriers rule at tier 1: the form chosen for
                  v1.11, every rule at once.
    detach        copy table only: a marker on two or more blocks detaches the
                  id outright, the zero-risk baseline for the two rules above.

`absent`, `carriers` and `detach` differ from the control only when a marker survives on
two blocks, so their numbers come from the copy operators with markers kept.

Every arm reads only what the control reads: the stored anchors and the edited
document. None uses block position as evidence. With every flag off, `resolve` here
returns what `ladder_v110.resolve` does, which a test asserts over every corpus and
operator, so an arm differs from the control only by its flags.

The partly-marked run keeps every anchor and strips every other id's marker from
the edited document, once for each parity. It is the run that reaches tiers 2 and 3
with blocks already claimed at tier 1, which markers stripped throughout never does.

Run:  python excl_arms.py      (writes results_exclusivity.{json,md})
"""

from __future__ import annotations

import json
import math
import sys
from dataclasses import dataclass, replace
from functools import lru_cache
from pathlib import Path

import perturb as PB
import ladder_v110 as R
import run_attach_eval as RUN
from quote import Candidate, Selector, normalize, rank_candidates

L = PB.L
HERE = Path(__file__).parent
DOCS_DIR = HERE.parent / "docs"

ARMS = [
    ("ladder", None),
    ("t2", {"t2_excl": True}),
    ("t23", {"t2_excl": True, "t3_excl": True}),
    ("t23m", {"t2_excl": True, "t3_excl": True, "merge_exempt": "contained"}),
    ("t23d", {"t2_excl": True, "t3_excl": True, "merge_exempt": "disjoint"}),
    ("t23dk", {"t2_excl": True, "t3_excl": True, "merge_exempt": "disjoint",
               "rivals": "kept"}),
    ("absent", {"dup": "absent"}),
    ("carriers", {"dup": "carriers"}),
    ("t23+carriers", {"t2_excl": True, "t3_excl": True, "dup": "carriers"}),
    ("t23dk+carriers", {"t2_excl": True, "t3_excl": True, "merge_exempt": "disjoint",
                        "rivals": "kept", "dup": "carriers"}),
]
COPY_ONLY_ARMS = [("detach", {"dup": "detach"})]
CHOSEN = "t23dk+carriers"
# Not an arm: the chosen form with tier 2's claimed filter removed, run only to
# count what the filter changes.
NO_T2_FILTER = "chosen, no tier-2 filter"
DIAGNOSTIC_ARMS = [(NO_T2_FILTER, {**dict(ARMS)[CHOSEN], "t2_filter": False})]
TIER1_ARMS = ("ladder", "detach", "absent", "carriers", "t23+carriers",
              "t23dk+carriers")
POSTHOC_ARMS = {"t23d", "t23dk", "t23dk+carriers"}

MISATTACHED = ("wrong", "false_attach")


@dataclass
class ExclResolution(R.Resolution):
    """A Resolution that also says which rule decided it, so the copy table can
    tell a carrier-hash commit from a carrier-quote one. Diagnostic only."""

    via: str | None = None


@lru_cache(maxsize=8192)
def _ranked(quote: str, prefix: str, suffix: str, bodies: tuple[str, ...],
            threshold: float) -> tuple[Candidate, ...]:
    """The shipped tier-3 ranking. Every arm ranks the same anchor against the
    same document, so the full sweep computes each ranking once.

    The key carries only what `resolve` varies, `threshold` included, which is
    passed as `heading_gate`. Clamp and the other heading arguments are fixed
    at their defaults here; if `resolve` ever takes them, they must join the
    key, or arms would share rankings computed under different rules."""
    return tuple(rank_candidates(Selector(quote, prefix=prefix, suffix=suffix),
                                 list(bodies), heading_gate=threshold))


def _quote_tier(a: R.Anchor, bodies: list[str], threshold: float, margin: float,
                pool: set[int] | None, via: str, rivals_kept: bool = False
                ) -> ExclResolution:
    """Shipped tier 3 over the whole document, or over `pool` when given.

    Candidates are ranked against the full document and filtered afterwards,
    so prefix and suffix context still compare against each block's physical
    neighbours rather than against its neighbours in the filtered list. With
    `rivals_kept`, only the target must come from `pool`: blocks outside it
    still count as the runner-up, so claiming a rival cannot open a margin."""
    sel = a.selector
    ranked = list(_ranked(sel.quote, sel.prefix, sel.suffix, tuple(bodies), threshold))
    if pool is not None:
        free = [c for c in ranked if c.target in pool]
        if rivals_kept and free:
            ranked = [free[0]] + [c for c in ranked if c.target != free[0].target]
        else:
            ranked = free
    idx = ranked[0].target if ranked else -1
    score = ranked[0].score if ranked else 0.0
    runner = ranked[1].score if len(ranked) > 1 else 0.0
    if idx >= 0 and score >= threshold and (score - runner) >= margin:
        return ExclResolution(a.id, "quote", idx, score, runner_up_score=runner, via=via)
    if idx >= 0 and score >= threshold:
        return ExclResolution(a.id, "detached", None, score, reason="ambiguous",
                              candidates=R._ambiguous_candidates(ranked, margin),
                              runner_up_score=runner, via=via)
    return ExclResolution(a.id, "detached", None, score, reason="unmatched",
                          runner_up_score=runner, via=via)


def resolve(
    anchors: list[R.Anchor],
    after_md: str,
    threshold: float = R.DEFAULT_THRESHOLD,
    margin: float = R.DEFAULT_MARGIN,
    mode: str = "blank-line",
    t2_excl: bool = False,
    t3_excl: bool = False,
    merge_exempt: str | None = None,
    rivals: str = "pool",
    dup: str = "first",
    t2_filter: bool = True,
) -> dict[str, ExclResolution]:
    """The §9.1 ladder with the arms' rules as flags. `dup` is the tier-1 rule
    for an id whose marker is on several blocks: `first` (shipped), `absent`,
    `carriers` or `detach`. `merge_exempt` is None, `contained` or `disjoint`.
    `rivals` says what a block claimed at a stronger tier is to the exclusive
    quote tier: gone from the `pool` (§9.2's rule for children), or `kept` as a
    rival for the margin but never a target. `t2_filter=False` lets exclusive tier
    2 count claimed blocks, which is diagnostic: `filter_moves` uses it to measure
    what the filter does."""
    if rivals not in ("pool", "kept"):
        raise ValueError(f"unknown rivals rule: {rivals!r}")
    if dup not in ("first", "absent", "carriers", "detach"):
        raise ValueError(f"unknown dup rule: {dup!r}")
    blocks = [b for b in L.parse_document(after_md, mode=mode) if b.index >= 0]
    bodies = [b.content for b in blocks]

    carriers: dict[str, list[int]] = {}
    for idx, b in enumerate(blocks):
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                seen = carriers.setdefault(mk.id, [])
                if idx not in seen:
                    seen.append(idx)

    out: dict[str, ExclResolution] = {}
    claimed: set[int] = set()

    # Tier 1. A carrier-rule commit is still tier 1: the marker is the evidence
    # that limits the pool, hash and quote only choose within it.
    for a in anchors:
        on = carriers.get(a.id)
        if not on:
            continue
        if len(on) == 1 or dup == "first":
            out[a.id] = ExclResolution(a.id, "marker", on[0], 1.0, via="marker")
        elif dup == "detach":
            out[a.id] = ExclResolution(a.id, "detached", None, 0.0,
                                       reason="duplicated", via="duplicated")
        elif dup == "carriers":
            hits = [i for i in on if L.body_hash(bodies[i]) == a.hash]
            if len(hits) == 1:
                out[a.id] = ExclResolution(a.id, "marker", hits[0], 1.0, via="carrier-hash")
            else:
                r = _quote_tier(a, bodies, threshold, margin, set(on), "carrier-quote")
                out[a.id] = replace(r, method="marker") if r.method == "quote" else r
        # dup == "absent": leave it to tiers 2 and 3
    claimed |= {r.target for r in out.values() if r.target is not None}

    # Tier 2.
    hash_to_idx: dict[str, list[int]] = {}
    for idx, body in enumerate(bodies):
        hash_to_idx.setdefault(L.body_hash(body), []).append(idx)
    recorded: dict[str, int] = {}
    for a in anchors:
        recorded[a.hash] = recorded.get(a.hash, 0) + 1
    proposals: dict[str, int] = {}
    for a in anchors:
        if a.id in out:
            continue
        hits = hash_to_idx.get(a.hash, [])
        if t2_excl:
            # A block claimed at tier 1 has left the pool, so it cannot make
            # an unclaimed hit look ambiguous.
            if t2_filter:
                hits = [h for h in hits if h not in claimed]
            if recorded[a.hash] > 1:
                continue
        if len(hits) != 1:
            continue
        proposals[a.id] = hits[0]
    reach: dict[int, int] = {}
    for t in proposals.values():
        reach[t] = reach.get(t, 0) + 1
    for aid, t in proposals.items():
        if not t2_excl or reach[t] == 1:
            out[aid] = ExclResolution(aid, "hash", t, 1.0, via="hash")
            claimed.add(t)

    # Tier 3.
    pending = {a.id: _quote_tier(a, bodies, threshold, margin,
                                 None if not t3_excl else
                                 set(range(len(bodies))) - claimed, "quote",
                                 rivals_kept=rivals == "kept")
               for a in anchors if a.id not in out}
    if t3_excl:
        by_target: dict[int, list[str]] = {}
        for aid, r in pending.items():
            if r.method == "quote" and r.target is not None:
                by_target.setdefault(r.target, []).append(aid)
        quotes = {a.id: a.selector.nquote for a in anchors}
        for t, aids in by_target.items():
            if len(aids) == 1:
                continue
            if merge_exempt and _merged(normalize(bodies[t]), [quotes[a] for a in aids],
                                        merge_exempt == "disjoint"):
                continue
            for aid in aids:
                r = pending[aid]
                pending[aid] = ExclResolution(aid, "detached", None, r.score,
                                              reason="contested",
                                              runner_up_score=r.runner_up_score,
                                              via="quote")
    out.update(pending)
    return out


def _merged(body: str, quotes: list[str], disjoint: bool) -> bool:
    """Every quote verbatim inside `body`. With `disjoint`, there must be a
    choice of one occurrence per quote with no two occurrences overlapping, so
    two identical quotes need two copies of their text in the block.

    The disjoint test is a dynamic programme over subsets of the contenders.
    `end[S]` is the smallest offset by which every quote in S can be placed,
    pairwise non-overlapping, inside `body[:end[S]]`; `end[{}]` is 0, and
    `end[S]` is the minimum over i in S of `find(q_i, end[S - {i}]) + len(q_i)`,
    where `find(q, p)` is the first occurrence of q starting at or after p.
    Any disjoint placement can be read left to right, and taking each quote's
    earliest occurrence after the previous end never ends later than any other
    choice, so the programme is exact. It costs 2^k * k searches for k
    contenders, each linear in the body with a linear-time string search, and
    does not depend on how many times a quote occurs. A greedy pick depended on
    the order the contenders arrived in (`abcd` and `bcde` fit `abcdef abcd`
    only if `abcd` takes its second occurrence), and an enumeration of
    occurrences was exponential in their number on repetitive text."""
    if not all(quotes):
        return False
    if not disjoint:
        return all(q in body for q in quotes)
    if sum(map(len, quotes)) > len(body):
        return False
    k = len(quotes)
    end: dict[int, int] = {0: 0}
    for mask in range(1, 1 << k):
        best = -1
        for i in range(k):
            if not mask & (1 << i):
                continue
            before = end.get(mask & ~(1 << i), -1)
            if before < 0:
                continue
            at = body.find(quotes[i], before)
            if at >= 0 and (best < 0 or at + len(quotes[i]) < best):
                best = at + len(quotes[i])
        end[mask] = best
    return end[(1 << k) - 1] >= 0


# --- intervals --------------------------------------------------------------

def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p), summed in log space. `heading_arms.py`
    sums `comb(n, i) * p**i` directly, which overflows a float once n reaches
    the low thousands; the pooled tables here pass that."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    lp, lq = math.log(p), math.log1p(-p)
    lg = math.lgamma(n + 1)
    return min(1.0, sum(math.exp(lg - math.lgamma(i + 1) - math.lgamma(n - i + 1)
                                 + i * lp + (n - i) * lq) for i in range(k + 1)))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact binomial interval by bisection, as in `heading_arms.py`."""
    if n == 0:
        return 0.0, 1.0
    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(80):
            mid = (a + b) / 2
            if 1 - _binom_cdf(k - 1, n, mid) < alpha / 2:
                a = mid
            else:
                b = mid
        lo = (a + b) / 2
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(80):
            mid = (a + b) / 2
            if _binom_cdf(k, n, mid) > alpha / 2:
                a = mid
            else:
                b = mid
        hi = (a + b) / 2
    return lo, hi


# --- harness ----------------------------------------------------------------

def corpora() -> list[dict]:
    fixture = HERE / "fixtures" / "cross_section_dups.md"
    published = list(PB.OPERATORS)
    return [
        {"name": "distinct prose", "bases": [(DOCS_DIR / f"{d}.md").read_text()
                                             for d in ("doc1", "doc2")],
         "existing": published},
        {"name": "near_dups", "bases": [(HERE / "fixtures" / "near_dups.md").read_text()],
         "existing": published},
        {"name": "cross-section fixture", "bases": [fixture.read_text()],
         "existing": published + list(PB.SECTION_OPERATORS)},
    ]


ALL_OPS = {**PB.OPERATORS, **PB.SECTION_OPERATORS, **PB.EXCL_OPERATORS,
           **PB.TWIN_EDIT_OPERATORS}
# The partly-marked run takes every published and section operator on every corpus.
# Section operators leave a corpus without sections unchanged, so that document's
# ids contribute correct resolutions and nothing else.
PARTLY_OPS = list(PB.OPERATORS) + list(PB.SECTION_OPERATORS)


def run_arm(label: str, anchors, after_md, threshold, margin):
    flags = dict(ARMS + COPY_ONLY_ARMS + DIAGNOSTIC_ARMS)[label]
    if flags is None:
        return R.resolve(anchors, after_md, threshold=threshold, margin=margin)
    return resolve(anchors, after_md, threshold=threshold, margin=margin, **flags)


def run_case(base_md: str, op: str, strip: bool, keep: int | None = None,
             arms=None, threshold=R.DEFAULT_THRESHOLD, margin=R.DEFAULT_MARGIN,
             marked: int | None = None) -> dict[str, list[dict]]:
    """One (document, operator, strip) cell under every arm. `keep` selects the
    half-stamped variant: only blocks whose index has parity `keep` carry a
    marker, so unstamped blocks compete with no anchor of their own. The edit
    is applied to the fully annotated document either way, so the stamped and
    half-stamped runs perform the same edit. `marked` selects the partly-marked
    variant, which keeps every anchor but leaves a marker in the edited document
    only on ids of that parity, so `strip` must be False for it to mean anything."""
    before_md, pblocks = PB.annotate(base_md)
    anchors = R.build_anchors(before_md)
    if keep is not None:
        anchors = [a for k, a in enumerate(anchors) if k % 2 == keep]
    stamped = {a.id for a in anchors}
    if marked is not None:
        stamped = {a.id for k, a in enumerate(anchors) if k % 2 == marked}
    after_pb, adj = ALL_OPS[op](pblocks)
    truth = PB.default_truth(after_pb)
    truth.update(adj)
    shown = [PB.PBlock(text=pb.text, ids=[i for i in pb.ids if i in stamped])
             for pb in after_pb]
    after_md = PB.serialize(shown, strip=strip)
    out = {}
    for label in arms or [a[0] for a in ARMS]:
        res = run_arm(label, anchors, after_md, threshold, margin)
        rows = []
        for a in anchors:
            cat, method = RUN.score_one(res[a.id], truth[a.id])
            rows.append({"id": a.id, "cat": cat, "method": method,
                         "target": res[a.id].target,
                         "reason": res[a.id].reason,
                         "via": getattr(res[a.id], "via", None)})
        out[label] = rows
    return out


def count(rows: list[dict]) -> dict[str, int]:
    c: dict[str, int] = {}
    for r in rows:
        c[r["cat"]] = c.get(r["cat"], 0) + 1
    return c


def rates(cats: dict[str, int]) -> dict:
    correct = cats.get("correct", 0)
    missed = cats.get("missed", 0)
    mis = sum(cats.get(k, 0) for k in MISATTACHED)
    survivable = correct + cats.get("wrong", 0) + missed
    total = sum(cats.values())
    return {
        "n": total, "survivable": survivable, "cats": cats,
        "correct": correct, "missed": missed, "misattached": mis,
        "correct_detach": cats.get("correct_detach", 0),
        "recovery": correct / survivable if survivable else 0.0,
        "recovery_ci": list(clopper_pearson(correct, survivable)),
        "misattach_rate": mis / total if total else 0.0,
        "misattach_ci": list(clopper_pearson(mis, total)),
    }


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in b.items():
        out[k] = out.get(k, 0) + v
    return out


def sweep(op_sets: list[str] | None, strip: bool, keeps=(None,),
          threshold=R.DEFAULT_THRESHOLD, margin=R.DEFAULT_MARGIN, arms=None,
          marks=(None,)) -> dict:
    """Run every corpus through its operators. `op_sets=None` means each
    corpus's existing operators (published, plus section ones on the
    cross-section fixture). Returns per-corpus, per-operator cases."""
    data = {}
    for corpus in corpora():
        ops = corpus["existing"] if op_sets is None else op_sets
        per_op = {}
        for op in ops:
            cases = []
            for d, base in enumerate(corpus["bases"]):
                for keep in keeps:
                    for mark in marks:
                        cell = run_case(base, op, strip, keep, arms=arms,
                                        threshold=threshold, margin=margin, marked=mark)
                        tag = (f"d{d}" + ("" if keep is None else f"k{keep}")
                               + ("" if mark is None else f"m{mark}"))
                        cases.append((tag, cell))
            per_op[op] = cases
        data[corpus["name"]] = per_op
    return data


def summarize(data: dict) -> dict:
    """Pooled and per-corpus rates per arm, per-operator counts, and the
    case-by-case comparison against the control."""
    first = next(iter(next(iter(data.values())).values()))[0][1]
    labels = list(first)
    out = {"pooled": {}, "corpora": {}, "by_op": {}, "vs_control": {}}
    pooled = {lab: {} for lab in labels}
    by_op: dict[str, dict[str, dict]] = {}
    keyed: dict[str, dict[str, str]] = {lab: {} for lab in labels}
    for cname, per_op in data.items():
        cor = {lab: {} for lab in labels}
        for op, cases in per_op.items():
            for tag, cell in cases:
                for lab in labels:
                    c = count(cell[lab])
                    cor[lab] = _merge(cor[lab], c)
                    by_op.setdefault(op, {}).setdefault(lab, {})
                    by_op[op][lab] = _merge(by_op[op][lab], c)
                    for r in cell[lab]:
                        keyed[lab][f"{cname}|{op}|{tag}|{r['id']}"] = r["cat"]
        out["corpora"][cname] = {lab: rates(cor[lab]) for lab in labels}
        for lab in labels:
            pooled[lab] = _merge(pooled[lab], cor[lab])
    out["pooled"] = {lab: rates(pooled[lab]) for lab in labels}
    out["by_op"] = {op: {lab: rates(c) for lab, c in arms.items()}
                    for op, arms in by_op.items()}
    for lab in labels:
        diff = {"lost_recovery": {}, "gained_recovery": {},
                "new_misattach": {}, "fixed_misattach": {}}
        for key, base in keyed["ladder"].items():
            now = keyed[lab][key]
            op = key.split("|")[1]
            if base == "correct" and now != "correct":
                diff["lost_recovery"][op] = diff["lost_recovery"].get(op, 0) + 1
            if base != "correct" and now == "correct":
                diff["gained_recovery"][op] = diff["gained_recovery"].get(op, 0) + 1
            if base not in MISATTACHED and now in MISATTACHED:
                diff["new_misattach"][op] = diff["new_misattach"].get(op, 0) + 1
            if base in MISATTACHED and now not in MISATTACHED:
                diff["fixed_misattach"][op] = diff["fixed_misattach"].get(op, 0) + 1
        out["vs_control"][lab] = diff
    return out


def misattach_cases(data: dict, label: str) -> list[dict]:
    """Every misattached id under one arm, for the report's case list."""
    rows = []
    for cname, per_op in data.items():
        for op, cases in per_op.items():
            for tag, cell in cases:
                for r in cell[label]:
                    if r["cat"] in MISATTACHED:
                        rows.append({"corpus": cname, "op": op, "doc": tag,
                                     "id": r["id"], "cat": r["cat"],
                                     "method": r["method"]})
    return rows


def lost_recoveries(data: dict, label: str) -> list[dict]:
    """Every id the control recovers and `label` does not, with why."""
    rows = []
    for cname, per_op in data.items():
        for op, cases in per_op.items():
            for tag, cell in cases:
                control = {r["id"]: r for r in cell["ladder"]}
                for r in cell[label]:
                    if control[r["id"]]["cat"] == "correct" and r["cat"] != "correct":
                        rows.append({"corpus": cname, "op": op, "doc": tag, "id": r["id"],
                                     "cat": r["cat"], "reason": r["reason"],
                                     "control_method": control[r["id"]]["method"]})
    return rows


def filter_moves(op_sets: list[str], threshold=R.DEFAULT_THRESHOLD,
                 margin=R.DEFAULT_MARGIN) -> dict:
    """How many partly-marked resolutions tier 2's claimed filter changes: the
    chosen form against itself with the filter removed. A shape no run reaches
    here is a rule with no corpus behind it, whatever the totals say."""
    data = sweep(op_sets, strip=False, marks=(0, 1), threshold=threshold, margin=margin,
                 arms=[CHOSEN, NO_T2_FILTER])
    n, moved = 0, []
    for cname, per_op in data.items():
        for op, cases in per_op.items():
            for tag, cell in cases:
                off = {r["id"]: r for r in cell[NO_T2_FILTER]}
                for r in cell[CHOSEN]:
                    n += 1
                    o = off[r["id"]]
                    if (r["method"], r["target"]) != (o["method"], o["target"]):
                        moved.append({"corpus": cname, "op": op, "doc": tag, "id": r["id"],
                                      "with_filter": r["cat"], "without_filter": o["cat"]})
    return {"n": n, "moved": moved}


def copy_table() -> list[dict]:
    """The copied id's outcome under each tier-1 arm, markers kept. Only that
    id is interesting: every other id resolves at tier 1 on its own block,
    which `test_excl_arms.py` asserts rather than this table repeating it."""
    rows = []
    for corpus in corpora():
        for d, base in enumerate(corpus["bases"]):
            _, pblocks = PB.annotate(base)
            i = PB._nth_marked_para(pblocks, 2)
            assert i is not None
            src = pblocks[i].ids[0]
            for op in PB.COPY_OPERATORS:
                cell = run_case(base, op, strip=False, arms=list(TIER1_ARMS))
                row = {"corpus": corpus["name"], "doc": f"d{d}", "op": op}
                for lab in TIER1_ARMS:
                    r = next(x for x in cell[lab] if x["id"] == src)
                    row[lab] = {"cat": r["cat"], "method": r["method"],
                                "reason": r["reason"], "via": r["via"]}
                    others = [x for x in cell[lab] if x["id"] != src]
                    row[lab]["others_all_correct"] = all(
                        x["cat"] == "correct" for x in others)
                rows.append(row)
    return rows


def run(threshold=R.DEFAULT_THRESHOLD, margin=R.DEFAULT_MARGIN) -> dict:
    new_ops = list(PB.EXCL_OPERATORS)
    closed = sweep(None, strip=True, threshold=threshold, margin=margin)
    closed_new = sweep(new_ops, strip=True, threshold=threshold, margin=margin)
    half = sweep(None, strip=True, keeps=(0, 1), threshold=threshold, margin=margin)
    half_new = sweep(new_ops, strip=True, keeps=(0, 1), threshold=threshold,
                     margin=margin)
    partly = sweep(PARTLY_OPS, strip=False, marks=(0, 1), threshold=threshold,
                   margin=margin)
    twin_ops = list(PB.TWIN_EDIT_OPERATORS)
    twin = sweep(twin_ops, strip=False, marks=(0, 1), threshold=threshold, margin=margin)
    partly_new = sweep(new_ops, strip=False, marks=(0, 1), threshold=threshold,
                       margin=margin)
    return {
        "threshold": threshold, "margin": margin,
        "arms": [a[0] for a in ARMS],
        "closed": summarize(closed),
        "closed_misattached": {lab: misattach_cases(closed, lab) for lab, _ in ARMS},
        "closed_new": summarize(closed_new),
        "closed_new_misattached": {lab: misattach_cases(closed_new, lab)
                                   for lab, _ in ARMS},
        "half": summarize(half),
        "half_new": summarize(half_new),
        "partly": summarize(partly),
        "partly_misattached": {lab: misattach_cases(partly, lab) for lab, _ in ARMS},
        "partly_lost": lost_recoveries(partly, CHOSEN),
        "partly_filter": filter_moves(PARTLY_OPS, threshold, margin),
        "twin": summarize(twin),
        "twin_misattached": {lab: misattach_cases(twin, lab) for lab, _ in ARMS},
        "twin_filter": filter_moves(twin_ops, threshold, margin),
        "partly_new": summarize(partly_new),
        "partly_new_misattached": {lab: misattach_cases(partly_new, lab)
                                   for lab, _ in ARMS},
        "copy_kept": copy_table(),
    }


# --- report -----------------------------------------------------------------

def _pct(x):
    return f"{100 * x:.1f}%"


def _ci(pair):
    return f"[{100 * pair[0]:.1f}, {100 * pair[1]:.1f}]"


def _arm_table(L: list[str], summary: dict) -> None:
    L.append("| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI "
             "| misattach rate | 95% CI |")
    L.append("|---|--:|--:|--:|--:|--:|--:|---|--:|---|")
    for lab, r in summary.items():
        L.append(f"| {lab} | {r['n']} | {r['correct']} | {r['missed']} | "
                 f"{r['misattached']} | {r['correct_detach']} | {_pct(r['recovery'])} | "
                 f"{_ci(r['recovery_ci'])} | {_pct(r['misattach_rate'])} | "
                 f"{_ci(r['misattach_ci'])} |")


def _cmc(r: dict) -> str:
    return f"{r['correct']}/{r['missed']}/{r['misattached']}/{r['correct_detach']}"


def _op_table(L: list[str], summary: dict, only_differing: bool) -> None:
    labels = list(summary["pooled"])
    L.append("Cells are correct / missed / misattached / detach ok, pooled over "
             "every corpus.\n")
    L.append("| Operator | " + " | ".join(labels) + " |")
    L.append("|---" * (len(labels) + 1) + "|")
    for op, arms in summary["by_op"].items():
        cells = [_cmc(arms[lab]) for lab in labels]
        if only_differing and len(set(cells)) == 1:
            continue
        L.append(f"| {op} | " + " | ".join(cells) + " |")


def _vs_table(L: list[str], summary: dict) -> None:
    L.append("| Arm | recoveries lost | recoveries gained | misattachments fixed "
             "| misattachments introduced |")
    L.append("|---|---|---|---|---|")

    def fmt(d):
        n = sum(d.values())
        return f"{n}" + (f" ({', '.join(f'{k} {v}' for k, v in sorted(d.items()))})"
                         if n else "")
    for lab, d in summary["vs_control"].items():
        if lab == "ladder":
            continue
        L.append(f"| {lab} | {fmt(d['lost_recovery'])} | {fmt(d['gained_recovery'])} | "
                 f"{fmt(d['fixed_misattach'])} | {fmt(d['new_misattach'])} |")


def _mis_table(L: list[str], by_arm: dict[str, list[dict]]) -> None:
    L.append("| Arm | Corpus | Operator | Doc | Id | Outcome | Tier |")
    L.append("|---|---|---|---|---|---|---|")
    for lab, rows in by_arm.items():
        for r in rows:
            L.append(f"| {lab} | {r['corpus']} | {r['op']} | {r['doc']} | `{r['id']}` | "
                     f"{r['cat']} | {r['method']} |")


def report(data: dict) -> str:
    L = ["# Block-tier exclusivity and duplicated ids: the arms\n"]
    L.append(
        f"Threshold {data['threshold']}, margin {data['margin']}. Intervals are 95% "
        "Clopper-Pearson. Outcomes follow `run_attach_eval.py`: *misattached* is "
        "`wrong` plus `false_attach`, the outcomes §10's \"surface, don't "
        "guess\" rule exists to prevent. Every table except the partly-marked "
        "section and the last strips markers, so tier 1 never fires there and "
        "`absent` and `carriers` equal the control by construction.\n")
    L.append("| Arm | Rule |\n|---|---|")
    blurb = {
        "ladder": "the v1.10 ladder, frozen in `ladder_v110.py` (control)",
        "t2": "tier 2 exclusive, with historical uniqueness",
        "t23": "tiers 2 and 3 exclusive (§9.2's discipline on blocks)",
        "t23m": "t23, but a tier-3 contest commits when every contender's quote is "
                "verbatim inside the block (the clean merge)",
        "t23d": "**post-hoc**: t23m, with the quotes at disjoint places in the block",
        "t23dk": "**post-hoc**: t23d, with claimed blocks kept as margin rivals at tier 3 "
                 "(the block tiers chosen for v1.11)",
        "absent": "a marker on two or more blocks is treated as absent; tiers 2 and "
                  "3 run over the whole document",
        "carriers": "a marker on two or more blocks resolves only among its "
                    "carriers, by hash then quote; never falls through",
        "t23+carriers": "t23 with the carriers rule at tier 1",
        "t23dk+carriers": "**post-hoc**: t23dk with the carriers rule at tier 1 "
                          "(the full form chosen for v1.11)",
        "detach": "copy table only: a marker on two or more blocks detaches the id",
    }
    for lab in data["arms"] + [a[0] for a in COPY_ONLY_ARMS]:
        L.append(f"| {lab} | {blurb[lab]} |")

    L.append("\n## Closed world, existing operators\n")
    L.append("Every block stamped. The nine published operators on every corpus, "
             "plus the five section operators on the cross-section fixture.\n")
    _arm_table(L, data["closed"]["pooled"])
    for cname, summary in data["closed"]["corpora"].items():
        L.append(f"\n### {cname}\n")
        _arm_table(L, summary)
    L.append("\n### Per operator, where any arm differs\n")
    _op_table(L, data["closed"], only_differing=True)
    L.append("\n### Case by case against the control\n")
    _vs_table(L, data["closed"])
    L.append("\n### Every misattachment, by arm\n")
    _mis_table(L, data["closed_misattached"])

    L.append("\n## Closed world, identity-boundary operators\n")
    L.append("The operators in `perturb.EXCL_OPERATORS`, markers stripped, so a "
             "pasted copy is an unmarked twin. `replace_related`'s ground truth "
             "(detach) is semantic rather than lexical; read its row apart.\n")
    _arm_table(L, data["closed_new"]["pooled"])
    L.append("")
    _op_table(L, data["closed_new"], only_differing=False)
    L.append("\n### Case by case against the control\n")
    _vs_table(L, data["closed_new"])
    L.append("\n### Misattachments that differ from the control\n")
    base = {(r["corpus"], r["op"], r["doc"], r["id"])
            for r in data["closed_new_misattached"]["ladder"]}
    _mis_table(L, {lab: [r for r in rows
                         if (r["corpus"], r["op"], r["doc"], r["id"]) not in base]
                   for lab, rows in data["closed_new_misattached"].items()})

    L.append("\n## Open world (half-stamped)\n")
    L.append("Only every other block carries a marker, run once for each parity. "
             "Unstamped blocks still compete for every anchor, which is what a "
             "partly stamped document or freshly pasted text looks like.\n")
    L.append("### Existing operators\n")
    _arm_table(L, data["half"]["pooled"])
    L.append("")
    _vs_table(L, data["half"])
    L.append("\n### Identity-boundary operators\n")
    _arm_table(L, data["half_new"]["pooled"])
    L.append("")
    _vs_table(L, data["half_new"])

    L.append("\n## Partly marked\n")
    L.append("Every block stamped, every anchor kept, and every other id's marker "
             "left in the edited document, once for each parity. This is where tiers "
             "2 and 3 meet blocks already claimed at tier 1. **This run is not blind**: "
             "its stop rule (the chosen form introduces no misattachment against the "
             "control) was written after a probe of this same sweep had shown zero.\n")
    L.append("### Published and section operators, every corpus\n")
    L.append("All fourteen operators on all three corpora, two parities. Section "
             "operators leave a corpus without sections unchanged, which accounts for "
             "280 of the 2016 resolutions, all correct under every arm.\n")
    _arm_table(L, data["partly"]["pooled"])
    L.append("")
    _vs_table(L, data["partly"])
    L.append("")
    _op_table(L, data["partly"], only_differing=True)
    L.append(f"\n### Every recovery `{CHOSEN}` loses against the control\n")
    L.append("| Corpus | Operator | Doc | Id | Control's tier | Outcome | Reason |")
    L.append("|---|---|---|---|---|---|---|")
    for r in data["partly_lost"]:
        L.append(f"| {r['corpus']} | {r['op']} | {r['doc']} | `{r['id']}` | "
                 f"{r['control_method']} | {r['cat']} | {r['reason']} |")
    L.append("\n### Every misattachment, by arm\n")
    _mis_table(L, data["partly_misattached"])
    L.append("\n### Tier 2's claimed filter\n")
    pf, tf = data["partly_filter"], data["twin_filter"]
    L.append(f"The chosen form against itself with the filter removed. Across the "
             f"sweep above the filter changes {len(pf['moved'])} of {pf['n']} "
             f"resolutions. `edit_into_twin` rewrites one marked paragraph into "
             f"another's exact text, each keeping its own id, and there the filter "
             f"changes {len(tf['moved'])} of {tf['n']}. That operator is built to "
             f"reach the filter, so it shows the path runs and says nothing about how "
             f"often the shape occurs.\n")
    L.append("| Corpus | Doc | Id | with the filter | without it |")
    L.append("|---|---|---|---|---|")
    for r in tf["moved"]:
        L.append(f"| {r['corpus']} | {r['doc']} | `{r['id']}` | {r['with_filter']} | "
                 f"{r['without_filter']} |")
    L.append("\n### `edit_into_twin`\n")
    _arm_table(L, data["twin"]["pooled"])
    L.append("")
    _vs_table(L, data["twin"])
    L.append("\n### Identity-boundary operators\n")
    L.append("Outside the registered run. A `copy_*` operator pastes the marker too, "
             "so the parity that keeps the copied id has that id on two blocks and "
             "tier 1's carriers rule decides it. Those are the copy table's "
             "edited-original cases below, under a second name; `t23dk`, which keeps "
             "the shipped tier 1, introduces none.\n")
    _arm_table(L, data["partly_new"]["pooled"])
    L.append("")
    _vs_table(L, data["partly_new"])

    L.append("\n## A copy that keeps the original's marker\n")
    L.append("Markers kept. The second marked paragraph is pasted with its marker "
             "above or below the original, or at the document's start or end, "
             "verbatim, with the copy drifted, or with the original drifted. "
             "SPEC.md §7 says the copy mints a new stay, so the id belongs to the "
             "original in every row. Cells are the copied id's outcome and the "
             "rule that decided it; every other id resolves correctly at tier 1 "
             "under every arm.\n")
    L.append("| Operator | " + " | ".join(TIER1_ARMS) + " |")
    L.append("|---" * (len(TIER1_ARMS) + 1) + "|")
    agg: dict[str, dict[str, dict[str, int]]] = {}
    for row in data["copy_kept"]:
        for lab in TIER1_ARMS:
            c = agg.setdefault(row["op"], {}).setdefault(lab, {})
            cat = row[lab]["cat"]
            c[cat] = c.get(cat, 0) + 1
    for op, arms in agg.items():
        cells = []
        for lab in arms:
            c = arms[lab]
            cells.append(f"{c.get('correct', 0)} / {c.get('missed', 0)} / "
                         f"{c.get('wrong', 0)}")
        L.append(f"| {op} | " + " | ".join(cells) + " |")
    L.append("\nCells are correct / missed / wrong over the four documents. "
             "Per document:\n")
    L.append("| Corpus | Doc | Operator | " + " | ".join(TIER1_ARMS) + " |")
    L.append("|---" * (len(TIER1_ARMS) + 3) + "|")
    for row in data["copy_kept"]:
        cells = []
        for lab in TIER1_ARMS:
            r = row[lab]
            why = r["via"] or r["method"]
            if r["method"] == "detached" and r["reason"]:
                why = f"{why}, {r['reason']}"
            cells.append(f"{r['cat']} ({why})")
        L.append(f"| {row['corpus']} | {row['doc']} | {row['op']} | "
                 + " | ".join(cells) + " |")
    return "\n".join(L) + "\n"


def write(out: str) -> dict:
    data = run()
    Path(out + ".json").write_text(json.dumps(data, indent=1) + "\n")
    Path(out + ".md").write_text(report(data))
    return data


if __name__ == "__main__":
    dest = sys.argv[1] if len(sys.argv) > 1 else str(HERE / "results_exclusivity")
    result = write(dest)
    print(f"wrote {dest}.json and {dest}.md")
    for lab, r in result["closed"]["pooled"].items():
        print(f"  {lab:13s} n={r['n']} correct={r['correct']} missed={r['missed']} "
              f"misattached={r['misattached']} detach_ok={r['correct_detach']}")
    print("partly marked:")
    for lab in ("ladder", CHOSEN):
        r = result["partly"]["pooled"][lab]
        print(f"  {lab:13s} n={r['n']} correct={r['correct']} missed={r['missed']} "
              f"misattached={r['misattached']} detach_ok={r['correct_detach']}")
