"""Id-free resolution arms for the history replay.

Every arm sees what the shipped resolver sees once markers are stripped from the
newer revision: the anchors built from the older revision (stored quote, hash,
the §9 prefix/suffix, the experimental heading path) and the newer revision's
block bodies. None of them reads an id from the newer revision.

Arms

  ladder         SPEC.md §9.1 tiers 2 and 3, the shipped `resolver.resolve` with
                 tier 1 unavailable. Same decisions as the shipped code on a
                 markers-stripped document; `test_replay.py` checks that on real
                 revision pairs.
  hash           tier 2 alone.
  quote          tier 3 alone, the §9 commit rule (0.5 / 0.05).
  heading+quote  tier 3 with the `D12c` heading-path penalty from
                 `eval/attachment/heading_arms.py` (penalty 0.12, gated at the
                 threshold, clamped). Experimental evidence, never specified.
  structural     global one-to-one max-similarity assignment, similarity >= 0.5,
                 a 0.01 position tiebreak. Ported from the identity-survival
                 prototype (`hungarian` there).
  lcs            diff-style: an exact LCS over block hashes (dynamic programming,
                 not `SequenceMatcher`), a similarity assignment inside each gap
                 between exact matches, then a global assignment over the
                 leftovers to catch moves.

Two things differ from the prototype, and neither changes what an arm decides.
Position is the anchor's block index in the older revision over that revision's
block count, rather than its rank among anchors, because a real document is only
partly stamped. And an assignment is solved per connected component of the
similarity >= 0.5 graph rather than as one matrix: every admissible weight is
positive and every row has a free dummy, so the maximum decomposes exactly, and
one 250 x 280 Hungarian per revision pair in pure Python is what made the whole
replay infeasible.

Scores below `PRUNE` are not computed. A candidate whose body score is under
0.35 totals under 0.45 even with the full 0.1 context bonus, so it can neither be
committed (that needs 0.5) nor sit within the 0.05 margin of a committable best.
The structural arms never admit an edge under 0.5. So pruning changes no
decision in any arm, only the reported runner-up score, which nothing here reads.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from functools import lru_cache
from pathlib import Path

_ATTACH = Path(__file__).resolve().parents[1] / "attachment"
if str(_ATTACH) not in sys.path:
    sys.path.insert(0, str(_ATTACH))
import resolver as R  # noqa: E402
from quote import (  # noqa: E402
    _ratio,
    canonical_path,
    normalize,
    window_prefix,
    window_suffix,
)

L = R.L

THRESHOLD = R.DEFAULT_THRESHOLD
MARGIN = R.DEFAULT_MARGIN
FLOOR = 0.5  # structural admission floor, the prototype's value
EPS = 0.01  # position tiebreak weight, the prototype's value
PRUNE = 0.35  # see the module docstring
HEADING_PENALTY = 0.12  # D12c


def body_norm(q: str, c: str) -> float:
    """`quote.body_score` over already-normalized strings, with sub-PRUNE values
    returned as 0.0. Exact at and above PRUNE: `real_quick_ratio` and
    `quick_ratio` are upper bounds on `ratio`, and the containment floor is never
    above `real_quick_ratio`."""
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    sm = SequenceMatcher(None, q, c, autojunk=False)
    if sm.real_quick_ratio() < PRUNE or sm.quick_ratio() < PRUNE:
        return 0.0
    base = sm.ratio()
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if short in long:
        base = max(base, len(short) / len(long))
    return base if base >= PRUNE else 0.0


@lru_cache(maxsize=None)
def _ctx_prefix(stored: str, prev_text: str) -> float:
    return 0.05 * _ratio(normalize(window_prefix(stored)), normalize(window_prefix(prev_text)))


@lru_cache(maxsize=None)
def _ctx_suffix(stored: str, next_text: str) -> float:
    return 0.05 * _ratio(normalize(window_suffix(stored)), normalize(window_suffix(next_text)))


@dataclass
class Anchor:
    """One stored id from the older revision."""

    id: str
    hash: str
    nq: str  # normalized quote
    prefix: str
    suffix: str
    heading_path: tuple[str, ...]
    pos: float  # block index / block count in the older revision


@dataclass
class After:
    """The newer revision with markers stripped: bodies only."""

    bodies: list[str]
    norms: list[str]
    hashes: list[str]
    paths: list[tuple[str, ...]] = field(default_factory=list)
    cands: dict = field(default_factory=dict)  # anchor id -> [(j, score >= PRUNE)]


class Scores:
    """Body scores for one revision pair, read from a shared table keyed by the
    normalized strings (filled in bulk by the harness, or lazily here)."""

    def __init__(self, table: dict | None = None):
        self.table = {} if table is None else table

    def get(self, q: str, c: str) -> float:
        if q == c:
            return 1.0 if q else 0.0
        key = (q, c)
        v = self.table.get(key)
        if v is None:
            v = body_norm(q, c)
            self.table[key] = v
        return v


def candidates(a: Anchor, after: After, S: Scores) -> list[tuple[int, float]]:
    """Every body scoring at least PRUNE against the anchor's quote, computed
    once per revision pair and shared by all arms."""
    got = after.cands.get(a.id)
    if got is None:
        got = []
        for j, nc in enumerate(after.norms):
            s = S.get(a.nq, nc)
            if s >= PRUNE:
                got.append((j, s))
        after.cands[a.id] = got
    return got


def _ctx(a: Anchor, after: After, j: int) -> float:
    b = after.bodies
    bonus = 0.0
    if a.prefix:
        bonus += _ctx_prefix(a.prefix, b[j - 1] if j > 0 else "")
    if a.suffix:
        bonus += _ctx_suffix(a.suffix, b[j + 1] if j + 1 < len(b) else "")
    return bonus


def quote_pick(a: Anchor, after: After, S: Scores, heading: bool = False) -> int | None:
    """Tier 3 for one anchor: the `rank_candidates` order (total, index)
    descending, committed only on score >= 0.5 and a 0.05 margin, clamped."""
    spath = canonical_path(a.heading_path) if (heading and a.heading_path) else None
    best = second = None
    for j, s in candidates(a, after, S):
        tot = s + _ctx(a, after, j)
        if spath is not None and s >= THRESHOLD and canonical_path(after.paths[j]) != spath:
            tot -= HEADING_PENALTY
        key = (tot, j)
        if best is None or key > best:
            best, second = key, best
        elif second is None or key > second:
            second = key
    if best is None:
        return None
    score = min(best[0], 1.0)
    runner = min(second[0], 1.0) if second is not None else 0.0
    if score >= THRESHOLD and score - runner >= MARGIN:
        return best[1]
    return None


def _hash_index(after: After) -> dict[str, list[int]]:
    idx: dict[str, list[int]] = {}
    for j, h in enumerate(after.hashes):
        idx.setdefault(h, []).append(j)
    return idx


def arm_hash(anchors, after, S):
    idx = _hash_index(after)
    out = {}
    for a in anchors:
        hits = idx.get(a.hash, [])
        out[a.id] = hits[0] if len(hits) == 1 else None
    return out


def arm_quote(anchors, after, S):
    return {a.id: quote_pick(a, after, S) for a in anchors}


def arm_heading_quote(anchors, after, S):
    return {a.id: quote_pick(a, after, S, heading=True) for a in anchors}


def arm_ladder(anchors, after, S):
    idx = _hash_index(after)
    out = {}
    for a in anchors:
        hits = idx.get(a.hash, [])
        out[a.id] = hits[0] if len(hits) == 1 else quote_pick(a, after, S)
    return out


# --- assignment ----------------------------------------------------------------


def hungarian_max(w: list[list[float]]) -> list[int]:
    """Max-weight assignment for an n x m matrix, n <= m. Column per row.
    The prototype's implementation, unchanged."""
    n = len(w)
    m = len(w[0]) if n else 0
    assert n <= m
    INF = float("inf")
    u = [0.0] * (n + 1)
    v = [0.0] * (m + 1)
    p = [0] * (m + 1)
    way = [0] * (m + 1)
    for i in range(1, n + 1):
        p[0] = i
        j0 = 0
        minv = [INF] * (m + 1)
        used = [False] * (m + 1)
        while True:
            used[j0] = True
            i0 = p[j0]
            delta = INF
            j1 = 0
            for j in range(1, m + 1):
                if not used[j]:
                    cur = -w[i0 - 1][j - 1] - u[i0] - v[j]
                    if cur < minv[j]:
                        minv[j] = cur
                        way[j] = j0
                    if minv[j] < delta:
                        delta = minv[j]
                        j1 = j
            for j in range(m + 1):
                if used[j]:
                    u[p[j]] += delta
                    v[j] -= delta
                else:
                    minv[j] -= delta
            j0 = j1
            if p[j0] == 0:
                break
        while True:
            j1 = way[j0]
            p[j0] = p[j1]
            j0 = j1
            if j0 == 0:
                break
    out = [-1] * n
    for j in range(1, m + 1):
        if p[j]:
            out[p[j] - 1] = j - 1
    return out


def _assign_dense(rows, cols, weight) -> dict[int, int]:
    """The prototype's `assign`: admissible weights, -1e6 elsewhere, one zero
    dummy column per row so a row may stay unmatched."""
    w = []
    for i in rows:
        r = [weight.get((i, j), -1e6) for j in cols]
        r.extend([0.0] * len(rows))
        w.append(r)
    got = hungarian_max(w)
    out = {}
    for ri, cj in enumerate(got):
        if 0 <= cj < len(cols) and w[ri][cj] > 0:
            out[rows[ri]] = cols[cj]
    return out


def assign(rows, cols, anchors, after, S, dense: bool = False) -> dict[int, int]:
    """One-to-one max-weight pairing of anchor rows to body columns, weight =
    similarity + EPS * position agreement, admitted at similarity >= FLOOR.
    Solved per connected component unless `dense` (the test compares the two)."""
    if not rows or not cols:
        return {}
    n_a = len(after.bodies)
    weight: dict[tuple[int, int], float] = {}
    adj: dict[tuple[str, int], list[tuple[str, int]]] = {}
    colset = set(cols)
    for i in rows:
        a = anchors[i]
        for j, s in candidates(a, after, S):
            if j in colset and s >= FLOOR:
                pos = 1 - abs(a.pos - j / max(n_a, 1))
                weight[(i, j)] = s + EPS * pos
                adj.setdefault(("r", i), []).append(("c", j))
                adj.setdefault(("c", j), []).append(("r", i))
    if dense:
        return _assign_dense(rows, cols, weight)
    out: dict[int, int] = {}
    seen: set = set()
    for start in [("r", i) for i in rows]:
        if start in seen or start not in adj:
            continue
        comp, stack = [], [start]
        seen.add(start)
        while stack:
            node = stack.pop()
            comp.append(node)
            for nxt in adj.get(node, []):
                if nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        crow = sorted(x for k, x in comp if k == "r")
        ccol = sorted(x for k, x in comp if k == "c")
        if len(crow) == 1 and len(ccol) == 1:
            out[crow[0]] = ccol[0]
            continue
        out.update(_assign_dense(crow, ccol, weight))
    return out


def arm_structural(anchors, after, S, dense: bool = False):
    match = assign(list(range(len(anchors))), list(range(len(after.bodies))), anchors, after, S, dense)
    return {a.id: match.get(i) for i, a in enumerate(anchors)}


def _lcs_pairs(a: list[str], b: list[str]) -> list[tuple[int, int]]:
    """A longest common subsequence of two hash sequences, as index pairs.
    Plain O(nm) dynamic programming: `SequenceMatcher` is not an LCS (on `aaaa`
    against `abaa` it matches two, not three), and block sequences here are a few
    hundred long. The backtrack takes a match whenever one is on an optimal path,
    otherwise steps in the older sequence first, so the result is deterministic."""
    n, m = len(a), len(b)
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n - 1, -1, -1):
        row, nxt = dp[i], dp[i + 1]
        ai = a[i]
        for j in range(m - 1, -1, -1):
            row[j] = nxt[j + 1] + 1 if ai == b[j] else max(nxt[j], row[j + 1])
    out, i, j = [], 0, 0
    while i < n and j < m:
        if a[i] == b[j] and dp[i][j] == dp[i + 1][j + 1] + 1:
            out.append((i, j))
            i, j = i + 1, j + 1
        elif dp[i + 1][j] >= dp[i][j + 1]:
            i += 1
        else:
            j += 1
    return out


def arm_lcs(anchors, after, S):
    n, m = len(anchors), len(after.bodies)
    match = dict(_lcs_pairs([a.hash for a in anchors], after.hashes))
    bounds = [(-1, -1)] + sorted(match.items()) + [(n, m)]
    for (i0, j0), (i1, j1) in zip(bounds, bounds[1:]):
        match.update(assign(list(range(i0 + 1, i1)), list(range(j0 + 1, j1)), anchors, after, S))
    used = set(match.values())
    rows = [i for i in range(n) if i not in match]
    cols = [j for j in range(m) if j not in used]
    match.update(assign(rows, cols, anchors, after, S))
    return {a.id: match.get(i) for i, a in enumerate(anchors)}


ARMS = {
    "ladder": arm_ladder,
    "hash": arm_hash,
    "quote": arm_quote,
    "heading+quote": arm_heading_quote,
    "structural": arm_structural,
    "lcs": arm_lcs,
}


# --- building the two sides from a revision ------------------------------------


def block_ids(blocks) -> dict[str, list[int]]:
    """Block-level stay ids -> content-block indices. Child markers (`subhash`)
    are not block stays (SPEC.md §16) and are left out."""
    out: dict[str, list[int]] = {}
    for b in blocks:
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                out.setdefault(mk.id, []).append(b.index)
    return out


def build_anchors(md: str, blocks, keep: set[str]) -> list[Anchor]:
    """Anchors for the ids in `keep`, with the anchor's block position in the
    older revision. Built from `blocks` as `resolver.build_anchors` builds them
    (same quote, window, hash and heading path), not by reparsing `md`: a
    reparse sees the quoted examples `replay.real_blocks` removed, and one
    sharing a real id would give that id a second anchor."""
    paths = L.heading_paths(md, blocks)
    n = max(len(blocks), 1)
    out = []
    for i, b in enumerate(blocks):
        prev_text = blocks[i - 1].content if i > 0 else ""
        next_text = blocks[i + 1].content if i + 1 < len(blocks) else ""
        for mk in b.markers:
            if not mk.id or mk.malformed or mk.has_subhash or mk.id not in keep:
                continue
            out.append(
                Anchor(
                    id=mk.id,
                    hash=L.body_hash(b.content),
                    nq=normalize(b.content),
                    prefix=window_prefix(prev_text),
                    suffix=window_suffix(next_text),
                    heading_path=tuple(paths[i]),
                    pos=i / n,
                )
            )
    return out


def build_after(md: str, blocks) -> After:
    bodies = [b.content for b in blocks]
    return After(
        bodies=bodies,
        norms=[normalize(x) for x in bodies],
        hashes=[L.body_hash(x) for x in bodies],
        paths=[tuple(p) for p in L.heading_paths(md, blocks)],
    )


def strip_markers(md: str) -> str:
    """The newer revision with every marker outside a fence removed (SPEC.md
    §3.3), and a line that held nothing but markers deleted rather than blanked,
    so the strip cannot split a block under blank-line segmentation."""
    text = md.replace("\r\n", "\n").replace("\r", "\n")
    code = L.code_lines(L._blank_frontmatter(text))
    stripped = L._strip_markers_outside_code(text, code)
    a, b = text.split("\n"), stripped.split("\n")
    if len(a) != len(b):  # a marker spanning lines; keep the plain strip
        return stripped
    blank = lambda s: s.strip(" \t\f\v") == ""  # noqa: E731
    return "\n".join(y for x, y in zip(a, b) if not (blank(y) and not blank(x)))
