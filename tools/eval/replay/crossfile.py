#!/usr/bin/env python3
"""Cross-file replay: when a stayed block moves to another document, does
id-free matching find it there, and how often does it attach to the wrong block?

`replay.py` asks this within one document and finds the ids buy little there.
SPEC.md §2.2 says a stay survives movement between documents, and only the id
carries it across: a resolver holding one document's evidence has nothing to
search. This replays a repository's history for exactly those events.

A **move** is an id whose real marker leaves one in-scope document at a commit
and is a real marker in another in-scope document at that commit or within the
next k - 1 commits that touch the scope (k = 1, 5, 20). Its block there is the
ground truth. An id that leaves and is found nowhere in the window is a
**deletion**; one that comes back to its own document first is a **return**.
Membership is by real marker, so an id left behind as a mention in prose or in an
inline code span has still left. Commits are the first-parent chain filtered to
the scope, so k counts edits to the scope, not unrelated commits. A move that
changes kind (a block stay arriving as a list item's stay) is counted and not
scored, because no arm's answer can be compared with it.

The original binary decision rule was fixed before any data was read:

    Over all cross-file moves found, if the best id-free arm searching every
    document in the store at the newer commit re-finds at least 95% of moved
    blocks with at most 1% misattached, inline ids are not needed even for
    moves on this data. Otherwise the ids pay for moves.

After an earlier call had been read, the estimator and decision procedure changed
to population-weighted design intervals and three outcomes. One store-wide arm
whose whole interval meets both bars yields `ids-not-needed`; every such arm
wholly outside at least one bar yields `ids-pay`; otherwise the call is
`insufficient-evidence`. The bars and the arms are unchanged. The current
procedure is post hoc; the raw-count call is retained for comparison.

Arms (each sees only the older revision's stored evidence and the newer
documents' bodies with markers ignored):

  child ladder, source only   SPEC.md §9.2 on the source document at the newer
                              commit, what a one-document resolver does (a port
                              of `markstay_lint._resolve_children`, tested equal
                              to it, because the shipped quote tiers are unpruned)
  child ladder, all docs      the same ladder over every in-scope document,
                              pooled: containers resolve across the store and
                              tier 4's document scope becomes the store
  child hash, all docs        tier 4 alone over the store (both-sides unique)
  child quote, all docs       §9 scoring against every child in the store, with
                              each candidate's own siblings as context
  block arms                  the same four for block-level stays, through the
                              §9.1 ladder, tested equal to `arms.py` on one document

Neighbour context never crosses a document boundary: the block before a
document's first block is nothing, not the last block of whichever document
happens to sort first.

A real store is too large to score whole, so moves are sampled (`sample_moves`) and
`--deletions` sets a seeded sample of deletions; the results carry the full population
counts beside them. By default one move is drawn per commit per stratum, so every
commit that moves anything is seen. Every attachment decision is the exact §9 metric.
The bounds in `bounded_pick` only skip work that cannot change a commit decision, and
`ro_matches` is difflib's algorithm on numpy, which makes a store-scale run practical;
without numpy the same numbers come from difflib itself. The similarity buckets are
exact too: a value under `arms.PRUNE` reads as 0.0, and every such value is in the
lowest bucket either way.

The current call uses population-weighted estimates and a design interval
that respects the sample (`design_ci`): the wider of a Fay-Feuer gamma interval
over the weighted draws, so one draw standing for a large commit does not read as
certainty, and a seeded bootstrap over commits inside each stratum. Moves the design
cannot speak for, those in commits never
drawn (with an explicit `--moves` smaller than the commits) and kind-changing moves,
widen that interval to the worst case for their share of all moves, so they can stop
a call but cannot make one. The raw-count call is reported beside it.

Nothing from the replayed repository is written except aggregate counts, unless
`--sanity N` asks for N sampled moves, and every sampled block-stay move, to be
written for reading by hand. `--out` is refused inside the replayed repository.

Run (no network, no API; outputs to --out only; at most 12 workers):

    python crossfile.py --root REPO --glob 'docs/**/*.md' --out DIR [--label A]
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import random
import subprocess
import sys
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field, replace
from pathlib import Path

try:
    import numpy as _np
except ImportError:  # the numbers are the same, a store-scale run is not practical
    _np = None

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import arms as A  # noqa: E402
import replay as RP  # noqa: E402

L = A.L
MODE = "commonmark"  # the segmenter that addresses list-item stays (SPEC.md §5.5)
KS = (1, 5, 20)
FIND_BAR = 0.95
MISATTACH_BAR = 0.01
SEED = 20261031
BOOT = 2000  # bootstrap replicates behind every design interval

CHILD_ARMS = ("child ladder, source only", "child ladder, all docs", "child hash, all docs", "child quote, all docs")
BLOCK_ARMS = ("block ladder, source only", "block ladder, all docs", "block hash, all docs", "block quote, all docs")
# The decision rule is over every move, so each pair of arms is also scored as
# one: the child arm for a child stay, the block arm for a block stay.
COMBINED = ("ladder, source only", "ladder, all docs", "hash, all docs", "quote, all docs")


# --- git ----------------------------------------------------------------------------


def chain(root: Path, rev: str = "HEAD") -> list[tuple[str, dict[str, str | None]]]:
    """(commit, {in-scope path: blob after the commit, or None if deleted}) along
    the first-parent chain, oldest first, keeping only commits that change the
    scope. Renames are split into a delete and an add, so a renamed document is a
    document whose ids all left and reappeared elsewhere (reported apart)."""
    out = subprocess.run(
        ["git", "-C", str(root), "log", "--first-parent", "--diff-merges=first-parent", "--reverse",
         "--no-renames", "--raw", "--no-abbrev", "--format=C %H", rev, "--", *RP.pathspecs()],
        capture_output=True, text=True, check=True,
    ).stdout
    commits: list[tuple[str, dict]] = []
    for ln in out.splitlines():
        if ln.startswith("C "):
            commits.append((ln[2:], {}))
        elif ln.startswith(":") and commits:
            meta, path = ln.split("\t", 1)
            parts = meta.split()
            new, status = parts[3], parts[4]
            if RP.in_scope(path):
                commits[-1][1][path] = None if status.startswith("D") or set(new) == {"0"} else new
    return [(c, ch) for c, ch in commits if ch]


class Blobs:
    """`git cat-file --batch`, one process, text decoded leniently."""

    def __init__(self, root: Path):
        self.p = subprocess.Popen(["git", "-C", str(root), "cat-file", "--batch"],
                                  stdin=subprocess.PIPE, stdout=subprocess.PIPE)

    def get(self, sha: str) -> str:
        self.p.stdin.write(sha.encode() + b"\n")
        self.p.stdin.flush()
        head = self.p.stdout.readline().split()
        if len(head) < 3 or head[1] != b"blob":
            raise KeyError(sha)
        data = self.p.stdout.read(int(head[2]))
        self.p.stdout.read(1)
        return data.decode("utf-8", errors="replace")

    def close(self):
        self.p.stdin.close()
        self.p.wait()


# --- parsing ------------------------------------------------------------------------


def _real_markers(md: str, blocks: list) -> set[int]:
    """The markers of a parse that do not sit in an inline code span, by object id
    (a marker in a code span is a quoted example, as `replay.real_blocks` treats it)."""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    seen: Counter = Counter()

    def real(mk) -> bool:
        line = lines[mk.line - 1] if 0 < mk.line <= len(lines) else ""
        at = RP._occurrence(line, mk.raw, seen[(mk.line, mk.raw)])
        seen[(mk.line, mk.raw)] += 1
        return not (at >= 0 and any(s <= at < e for s, e in RP._code_spans(line)))

    out = set()
    for b in blocks:
        out.update(id(mk) for mk in b.markers if real(mk))
        for c in b.children:
            out.update(id(mk) for mk in c.markers if real(mk))
    return out


def parse(md: str) -> list:
    """Content blocks with their direct-child blocks, and every marker sitting in
    an inline code span removed from both."""
    blocks = [b for b in L.parse_document(md, mode=MODE, child_blocks=True) if b.index >= 0]
    keep = _real_markers(md, blocks)
    for b in blocks:
        b.markers = [mk for mk in b.markers if id(mk) in keep]
        for c in b.children:
            c.markers = [mk for mk in c.markers if id(mk) in keep]
    return blocks


def summarize(blocks) -> dict:
    """id -> list of (kind, location): `block` (block index), `child` (child
    index), or `unaddressed` (a `subhash` marker no direct child owns)."""
    out: dict[str, list] = defaultdict(list)
    for b in blocks:
        for mk in b.markers:
            if mk.id and not mk.malformed:
                out[mk.id].append(("unaddressed" if mk.has_subhash else "block", b.index))
        for c in b.children:
            for mk in c.markers:
                if mk.id and not mk.malformed:
                    out[mk.id].append(("child", c.index))
    return dict(out)


def _parse_one(args):
    sha, md = args
    blocks = parse(md)
    return sha, blocks, summarize(blocks)


# --- the multi-document child ladder ---------------------------------------------------


@dataclass
class Unit:
    """One newer document, parsed, markers ignored by every arm."""

    path: str
    blocks: list
    hashes: list = field(default_factory=list)  # block body hashes
    chashes: dict = field(default_factory=dict)  # child.index -> child body hash

    norms: list = field(default_factory=list)  # block bodies, §9-normalized
    ccands: list = field(default_factory=list)  # (child index, norm, prev sibling, next sibling)

    def __post_init__(self):
        self.hashes = [L.body_hash(b.content) for b in self.blocks]
        self.chashes = {c.index: L.body_hash(c.content) for b in self.blocks for c in b.children}
        self.norms = [L._match_normalize(b.content) for b in self.blocks]
        for b in self.blocks:
            kinds = defaultdict(list)
            for c in b.children:
                kinds[c.kind].append(c)
            for sib in kinds.values():
                for i, c in enumerate(sib):
                    self.ccands.append((c.index, L._match_normalize(c.content),
                                        sib[i - 1].content if i > 0 else "",
                                        sib[i + 1].content if i + 1 < len(sib) else ""))


_COUNTS: dict[str, Counter] = {}
_BODY: dict[tuple[str, str], float] = {}


def _counts(s: str) -> Counter:
    c = _COUNTS.get(s)
    if c is None:
        c = _COUNTS[s] = Counter(s)
    return c


def _pruned_body(q: str, c: str) -> float:
    """`markstay_lint._body_score` over already-normalized strings, 0.0 under
    `arms.PRUNE` (exact at and above it; see `arms.body_norm`). The two
    `SequenceMatcher` upper bounds are computed here first, from lengths and
    character counts, so no matcher is built for a candidate they rule out:
    `quick_ratio` is exactly twice the multiset intersection over the combined
    length, and with no junk heuristic nothing is excluded from it."""
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    la, lb = len(q), len(c)
    if 2 * min(la, lb) / (la + lb) < A.PRUNE:
        return 0.0
    qc, cc = _counts(q), _counts(c)
    if len(qc) > len(cc):
        qc, cc = cc, qc
    inter = 0
    for ch, v in qc.items():
        w = cc.get(ch)
        if w:
            inter += v if v < w else w
    if 2.0 * inter / (la + lb) < A.PRUNE:
        return 0.0
    key = (q, c)
    v = _BODY.get(key)
    if v is None:
        v = _BODY[key] = _exact_body(q, c)
    return v


def ro_matches(a: str, b: str, small: int = 2000) -> int:
    """Characters Ratcliff/Obershelp matches, `SequenceMatcher(None, a, b,
    autojunk=False)`'s recursion and tie-break, with numpy doing the row work
    that difflib does in a Python loop over a dict. A range under `small` goes to
    difflib itself. `test_crossfile.py` checks it against difflib."""
    if not a or not b:
        return 0
    if _np is None:
        return sum(m.size for m in A.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks())
    al = [ord(ch) for ch in a]
    bb = _np.frombuffer(b.encode("utf-32-le"), dtype=_np.uint32)
    order = _np.argsort(bb, kind="stable")
    vals, starts = _np.unique(bb[order], return_index=True)
    ends = _np.append(starts[1:], len(bb))
    b2j = {int(v): order[x:y] for v, x, y in zip(vals, starts, ends)}
    row = _np.zeros(len(b) + 1, dtype=_np.int32)  # row[j + 1] is difflib's j2len[j]
    empty = _np.empty(0, dtype=order.dtype)
    total = 0
    stack = [(0, len(a), 0, len(b))]
    while stack:
        alo, ahi, blo, bhi = stack.pop()
        if ahi - alo <= small and bhi - blo <= small:
            total += sum(m.size for m in A.SequenceMatcher(
                None, a[alo:ahi], b[blo:bhi], autojunk=False).get_matching_blocks())
            continue
        besti, bestj, bestsize = alo, blo, 0
        touched = empty
        for i in range(alo, ahi):
            pos = b2j.get(al[i])
            idx = empty if pos is None else pos[_np.searchsorted(pos, blo):_np.searchsorted(pos, bhi)]
            if idx.size == 0:
                if touched.size:
                    row[touched + 1] = 0
                    touched = empty
                continue
            k = row[idx] + 1
            if touched.size:
                row[touched + 1] = 0
            row[idx + 1] = k
            touched = idx
            m = int(k.argmax())  # the first maximum, so the earliest j, as difflib's strict >
            if k[m] > bestsize:
                bestsize = int(k[m])
                besti, bestj = i - bestsize + 1, int(idx[m]) - bestsize + 1
        if touched.size:
            row[touched + 1] = 0
        if bestsize:
            total += bestsize
            if alo < besti and blo < bestj:
                stack.append((alo, besti, blo, bestj))
            if besti + bestsize < ahi and bestj + bestsize < bhi:
                stack.append((besti + bestsize, ahi, bestj + bestsize, bhi))
    return total


def _exact_body(q: str, c: str) -> float:
    """`arms.body_norm`, through `ro_matches` once the strings are long."""
    if _np is None or len(q) + len(c) < 4000:
        return A.body_norm(q, c)
    base = 2.0 * ro_matches(q, c) / (len(q) + len(c))
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if short in long:
        base = max(base, len(short) / len(long))
    return base if base >= A.PRUNE else 0.0


def _upper(q: str, c: str) -> float:
    """An upper bound on `_pruned_body(q, c)` that builds no matcher: the larger
    of `quick_ratio` (from character counts) and the containment floor, 0.0 when
    the result would be pruned anyway."""
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    la, lb = len(q), len(c)
    if 2 * min(la, lb) / (la + lb) < A.PRUNE:
        return 0.0
    qc, cc = _counts(q), _counts(c)
    if len(qc) > len(cc):
        qc, cc = cc, qc
    inter = 0
    for ch, v in qc.items():
        w = cc.get(ch)
        if w:
            inter += v if v < w else w
    ub = 2.0 * inter / (la + lb)
    short, long = (q, c) if la <= lb else (c, q)
    if short in long:
        ub = max(ub, len(short) / len(long))
    return ub if ub >= A.PRUNE else 0.0


def lcs_len(a: str, b: str) -> int:
    """Length of a longest common subsequence, bit-parallel over Python ints
    (Allison-Dix / Hyyro). The characters Ratcliff/Obershelp matches form a
    common subsequence, so 2 * lcs / (la + lb) bounds its ratio from above."""
    if len(a) < len(b):
        a, b = b, a
    masks: dict[str, int] = {}
    for i, ch in enumerate(a):
        masks[ch] = masks.get(ch, 0) | (1 << i)
    full = (1 << len(a)) - 1
    v = full
    for ch in b:
        u = v & masks.get(ch, 0)
        v = ((v + u) | (v - u)) & full
    return len(a) - v.bit_count()


def _upper_lcs(q: str, c: str) -> float:
    """The tighter bound: the LCS ratio, or the containment floor."""
    ub = 2.0 * lcs_len(q, c) / (len(q) + len(c))
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if short in long:
        ub = max(ub, len(short) / len(long))
    return ub


def bounded_pick(q: str, norms: list[str], ctx_of) -> int | None:
    """`_pick` over every candidate's §9 total (body + context, which adds at
    most 0.1), computed best-bound first and stopped once no remaining candidate
    can change the decision: none can reach 0.5 while the best is under it, or
    none can come within the 0.05 margin of the (clamped) best. Same answer as
    scoring all of them; `test_crossfile.py` checks it against brute force."""
    order = sorted(((u, n) for n, c in enumerate(norms) if (u := _upper(q, c)) > 0), reverse=True)
    scored, best = [], None

    def hopeless(lim):
        if best is None:
            return lim < 0.5
        bc = min(best, 1.0)
        return (bc >= 0.5 and lim < bc - 0.05) or (bc < 0.5 and lim < 0.5)

    for ub, n in order:
        if hopeless(ub + 0.1):
            break  # sorted: every later bound is lower still
        # Long prose has near-identical character counts, so the first bound
        # passes almost any list against any list; the LCS bound does not.
        if ub < 1.0 and len(q) + len(norms[n]) > 400 and hopeless(_upper_lcs(q, norms[n]) + 0.1):
            continue
        body = _pruned_body(q, norms[n])
        if not body:
            continue
        tot = body + ctx_of(n)
        scored.append((tot, n))
        if best is None or tot > best:
            best = tot
    return _pick(scored)


def _ctx(stored: str, neighbour: str, prefix: bool) -> float:
    if not stored:
        return 0.0
    w = L._CONTEXT_CHARS
    a, b = (stored[-w:], neighbour[-w:]) if prefix else (stored[:w], neighbour[:w])
    return 0.05 * L._match_ratio(L._match_normalize(a), L._match_normalize(b))


def _pick(scored: list[tuple[float, int]]) -> int | None:
    """The §9 commit rule over (total, candidate) pairs: best >= 0.5 and a 0.05
    margin over the runner-up, both clamped at 1.0 as `_best_match` clamps."""
    if not scored:
        return None
    scored.sort(reverse=True)
    best = min(scored[0][0], 1.0)
    runner = min(scored[1][0], 1.0) if len(scored) > 1 else 0.0
    return scored[0][1] if best >= 0.5 and best - runner >= 0.05 else None


def _commit(out: dict, claimed: set, tier: str, proposals: dict) -> None:
    counts = Counter(proposals.values())
    for aid, target in proposals.items():
        if counts[target] == 1:
            out[aid] = (tier, target)
            claimed.add(target)


def resolve_parents(anchors, units: list[Unit]) -> dict:
    """`markstay_lint._resolve_parents` over pooled documents with markers
    ignored: no marker tier, then exclusive hash and quote tiers. Block keys are
    (unit, block position). A candidate's context is its neighbours among the
    unclaimed blocks of its own document, as the shipped tier's is in one."""
    pooled = [(u, i) for u, unit in enumerate(units) for i in range(len(unit.blocks))]
    by_hash = defaultdict(list)
    for k in pooled:
        by_hash[units[k[0]].hashes[k[1]]].append(k)
    reps = {}
    for a in anchors:
        if a.parent_id is not None:
            reps.setdefault(a.parent_id, a)
    out, claimed = {}, set()
    props = {}
    for pid, a in reps.items():
        hits = by_hash.get(a.parent_hash, [])
        if len(hits) == 1:
            props[pid] = hits[0]
    counts = Counter(props.values())
    for pid, t in props.items():
        if counts[t] == 1:
            out[pid] = (t, "hash")
            claimed.add(t)
    qprops = {}
    cands = [k for k in pooled if k not in claimed]
    norms = [units[k[0]].norms[k[1]] for k in cands]
    for pid, a in reps.items():
        if pid in out:
            continue
        q = L._match_normalize(a.parent_quote)

        def ctx_of(n, a=a):
            s = 0.0
            if a.parent_prefix:
                same = n > 0 and cands[n - 1][0] == cands[n][0]
                s += _ctx(a.parent_prefix, units[cands[n - 1][0]].blocks[cands[n - 1][1]].content if same else "", True)
            if a.parent_suffix:
                same = n + 1 < len(cands) and cands[n + 1][0] == cands[n][0]
                s += _ctx(a.parent_suffix, units[cands[n + 1][0]].blocks[cands[n + 1][1]].content if same else "", False)
            return s

        # A candidate under PRUNE totals under 0.45 whatever its context adds,
        # so it can neither commit nor sit within the margin of a committable
        # best; `bounded_pick` leaves those out, as `arms.py` does.
        got = bounded_pick(q, norms, ctx_of)
        if got is not None:
            qprops[pid] = cands[got]
    counts = Counter(qprops.values())
    for pid, t in qprops.items():
        if counts[t] == 1:
            out[pid] = (t, "quote")
            claimed.add(t)
    return out


def child_ladder(anchors, units: list[Unit]) -> dict:
    """`markstay_lint._resolve_children` on markers-stripped documents, pooled
    across `units`: id -> (tier, (unit, child index)) or ("detached", None).
    With one unit it is the shipped ladder (`test_crossfile.py` checks that);
    with several, tier 0 resolves containers across the store and tier 4's
    document scope is the store."""
    parents = resolve_parents(anchors, units)
    by_hash = defaultdict(list)
    for u, unit in enumerate(units):
        for b in unit.blocks:
            for c in b.children:
                by_hash[unit.chashes[c.index]].append((u, c.index))
    out, claimed = {}, set()

    def parent(a):
        info = parents.get(a.parent_id) if a.parent_id else None
        return (info[0][0], units[info[0][0]].blocks[info[0][1]]) if info else None

    def gated(a):
        return a.parent_id is not None and a.parent_id not in parents

    props = {}
    for a in anchors:
        if gated(a):
            continue
        p = parent(a)
        if p is None or units[p[0]].hashes[p[1].index] != a.parent_hash:
            continue
        sib = [c for c in p[1].children if c.kind == a.kind]
        o = a.ordinal - 1
        if 0 <= o < len(sib) and (p[0], sib[o].index) not in claimed:
            props[a.id] = (p[0], sib[o].index)
    _commit(out, claimed, "parent-hash", props)

    props = {}
    for a in anchors:
        if a.id in out or gated(a):
            continue
        p = parent(a)
        if p is None or a.sibling_hash_count != 1:
            continue
        hits = [(p[0], c.index) for c in p[1].children
                if c.kind == a.kind and units[p[0]].chashes[c.index] == a.hash and (p[0], c.index) not in claimed]
        if len(hits) == 1:
            props[a.id] = hits[0]
    _commit(out, claimed, "hash", props)

    props = {}
    for a in anchors:
        if a.id in out or gated(a) or a.document_hash_count != 1:
            continue
        hits = [k for k in by_hash.get(a.hash, []) if k not in claimed]
        if len(hits) == 1:
            props[a.id] = hits[0]
    _commit(out, claimed, "document-hash", props)

    props = {}
    for a in anchors:
        if a.id in out or gated(a):
            continue
        p = parent(a)
        if p is None:
            continue
        cands = [c for c in p[1].children if c.kind == a.kind and (p[0], c.index) not in claimed]
        idx, score, runner = L._best_match(a.quote, a.prefix, a.suffix, [c.content for c in cands])
        if idx >= 0 and score >= 0.5 and score - runner >= 0.05:
            props[a.id] = (p[0], cands[idx].index)
    _commit(out, claimed, "quote", props)
    for a in anchors:
        out.setdefault(a.id, ("detached", None))
    return out


def child_hash(anchors, units: list[Unit]) -> dict:
    """Tier 4 alone over the store: recorded unique in the source document and
    exactly one child anywhere now, assigned exclusively."""
    by_hash = defaultdict(list)
    for u, unit in enumerate(units):
        for ci, h in unit.chashes.items():
            by_hash[h].append((u, ci))
    out, claimed, props = {}, set(), {}
    for a in anchors:
        hits = by_hash.get(a.hash, [])
        if a.document_hash_count == 1 and len(hits) == 1:
            props[a.id] = hits[0]
    _commit(out, claimed, "document-hash", props)
    for a in anchors:
        out.setdefault(a.id, ("detached", None))
    return out


def child_quote(anchors, units: list[Unit]) -> dict:
    """§9 scoring of each anchor's quote against every child in the store, each
    candidate's context being its own neighbouring siblings, under the commit
    rule, assigned exclusively."""
    cands = [((u, ci), nc, prev, nxt) for u, unit in enumerate(units) for ci, nc, prev, nxt in unit.ccands]
    out, claimed, props = {}, set(), {}
    norms = [nc for _, nc, _, _ in cands]
    for a in anchors:
        q = L._match_normalize(a.quote)
        got = bounded_pick(q, norms, lambda n, a=a: _ctx(a.prefix, cands[n][2], True)
                           + _ctx(a.suffix, cands[n][3], False))
        if got is not None:
            props[a.id] = cands[got][0]
    _commit(out, claimed, "quote", props)
    for a in anchors:
        out.setdefault(a.id, ("detached", None))
    return out


def source_only(anchors, md_new: str | None, unit: "Unit | None" = None) -> dict:
    """The §9.2 ladder on the source document's newer revision alone, what a
    one-document resolver does. A moved id is not in it, so any attachment is
    wrong. With `unit` (the cached parse) it runs `child_ladder` on that one
    document, which `test_crossfile.py` checks equals the shipped
    `_resolve_children`; without it, the shipped code itself, whose quote tiers
    run for hours on a 500 KB tracker with hundreds of lists."""
    if md_new is None:
        return {a.id: ("detached", None) for a in anchors}
    if unit is not None:
        got = child_ladder(anchors, [unit])
        return {mid: (t, None if k is None else ("source", k[1])) for mid, (t, k) in got.items()}
    got = L._resolve_children(anchors, A.strip_markers(md_new), MODE)
    return {mid: (t, None if t == "detached" else ("source", ix)) for mid, (t, ix) in got.items()}


# --- block arms (for block-level stays that move) ---------------------------------------


def _block_quote(anchors, units: list[Unit]) -> dict:
    """§9.1's tier 3 over every block of `units`, each candidate's context being
    its neighbours in its own document. On one document it is `arms.arm_quote`."""
    keys = [(u, i) for u, unit in enumerate(units) for i in range(len(unit.blocks))]
    norms = [units[u].norms[i] for u, i in keys]
    out = {}
    for a in anchors:
        def ctx_of(n, a=a):
            u, i = keys[n]
            blocks = units[u].blocks
            return (_ctx(a.prefix, blocks[i - 1].content if i > 0 else "", True)
                    + _ctx(a.suffix, blocks[i + 1].content if i + 1 < len(blocks) else "", False))

        got = bounded_pick(a.nq, norms, ctx_of)
        out[a.id] = None if got is None else keys[got]
    return out


def _block_hash(anchors, units: list[Unit]) -> dict:
    """§9.1's tier 2 over every block of `units`: exactly one block has the hash."""
    idx = defaultdict(list)
    for u, unit in enumerate(units):
        for i, h in enumerate(unit.hashes):
            idx[h].append((u, i))
    return {a.id: idx[a.hash][0] if len(idx.get(a.hash, ())) == 1 else None for a in anchors}


def block_arms(md_old: str, blocks_old, ids: set[str], units: list[Unit], src_unit: "Unit | None") -> dict:
    """§9.1 arms for block stays over the source document alone and over every
    document: ladder (hash, then quote), hash alone, quote alone. Answers are
    (unit, block index), or ("source", block index) for the source-only arm."""
    anchors = A.build_anchors(md_old, blocks_old, ids)

    def ladder(us):
        h, q = _block_hash(anchors, us), _block_quote(anchors, us)
        return {m: h[m] if h[m] is not None else q[m] for m in h}

    out = {}
    if src_unit is None:
        out[BLOCK_ARMS[0]] = {a.id: None for a in anchors}
    else:
        out[BLOCK_ARMS[0]] = {m: None if g is None else ("source", g[1]) for m, g in ladder([src_unit]).items()}
    h, q = _block_hash(anchors, units), _block_quote(anchors, units)
    out[BLOCK_ARMS[1]] = {m: h[m] if h[m] is not None else q[m] for m in h}
    out[BLOCK_ARMS[2]] = h
    out[BLOCK_ARMS[3]] = q
    return out


# --- scan ------------------------------------------------------------------------------


@dataclass
class Event:
    """One id leaving one document at chain position i."""

    id: str
    src: str
    i: int
    old_blob: str
    cands: list = field(default_factory=list)  # (j, path, blob) sightings elsewhere
    back: list = field(default_factory=list)  # (j, blob) sightings in src again
    pre: list = field(default_factory=list)  # (path, blob) carrying it at i - 1, elsewhere
    # filled after parsing
    kind: str | None = None
    status: str = ""  # move | deletion | return | censored | dropped:<why>
    d: int | None = None  # j - i for a move or return
    dst: str | None = None
    j: int | None = None
    dst_kind: str | None = None
    dst_loc: int | None = None
    src_alive: bool = True
    pre_existing: bool = False


def scan(commits, ids_of, kmax: int) -> list[Event]:
    """Every real marker leaving a document, and where its id is seen elsewhere
    within kmax chain positions. `ids_of(blob)` is the blob's real-marker ids, so
    a mention left in prose or inline code does not keep an id in its document."""
    cur: dict[str, str] = {}
    where: dict[str, set] = defaultdict(set)
    events: list[Event] = []
    pending: list[Event] = []
    for i, (c, changes) in enumerate(commits):
        removed = []
        diffs = []
        # Read every change against the state before this commit, then apply
        # them all: a path processed earlier in the same commit must not look
        # as if it carried an id before the commit did.
        for path, sha in changes.items():
            old = cur.get(path)
            old_ids = ids_of(old) if old else frozenset()
            new_ids = ids_of(sha) if sha else frozenset()
            diffs.append((path, sha, old_ids, new_ids))
            for m in sorted(old_ids - new_ids):
                ev = Event(m, path, i, old)
                ev.pre = [(p, cur[p]) for p in sorted(where[m]) if p != path]
                removed.append(ev)
        for path, sha, old_ids, new_ids in diffs:
            for m in old_ids - new_ids:
                where[m].discard(path)
            for m in new_ids - old_ids:
                where[m].add(path)
            if sha:
                cur[path] = sha
            else:
                cur.pop(path, None)
        pending.extend(removed)
        events.extend(removed)
        keep = []
        for ev in pending:
            if i - ev.i >= kmax:
                continue
            for p in sorted(where.get(ev.id, ())):
                if p == ev.src:
                    ev.back.append((i, cur[p]))
                else:
                    ev.cands.append((i, p, cur[p]))
            keep.append(ev)
        pending = keep
    return events


def snapshot_at(commits, js: set[int]) -> dict[int, dict[str, str]]:
    cur: dict[str, str] = {}
    out = {}
    for i, (_, changes) in enumerate(commits):
        for p, sha in changes.items():
            if sha:
                cur[p] = sha
            else:
                cur.pop(p, None)
        if i in js:
            out[i] = dict(cur)
    return out


# --- scoring ---------------------------------------------------------------------------


def clopper(x, n):
    return RP.clopper_pearson(x, n)


def rate_row(c: Counter) -> dict:
    n = c["correct"] + c["missed"] + c["wrong"]
    return {
        "n": n, "correct": c["correct"], "missed": c["missed"], "wrong": c["wrong"],
        "found_rate": c["correct"] / n if n else None, "found_ci": clopper(c["correct"], n),
        "misattach_rate": c["wrong"] / n if n else None, "misattach_ci": clopper(c["wrong"], n),
        "miss_rate": c["missed"] / n if n else None,
    }


def _gamma_cdf(x: float, a: float) -> float:
    """The regularized lower incomplete gamma function P(a, x)."""
    if x <= 0:
        return 0.0
    front = math.exp(a * math.log(x) - x - math.lgamma(a))
    if x < a + 1:  # the series
        term = total = 1.0 / a
        n = a
        for _ in range(100_000):
            n += 1
            term *= x / n
            total += term
            if term < total * 1e-14:
                break
        return front * total
    # the continued fraction (Lentz), for the upper tail
    tiny = 1e-300
    b = x + 1 - a
    c = 1 / tiny
    d = 1 / b
    h = d
    for i in range(1, 100_000):
        an = -i * (i - a)
        b += 2
        d = an * d + b
        d = tiny if abs(d) < tiny else d
        c = b + an / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        step = d * c
        h *= step
        if abs(step - 1) < 1e-14:
            break
    return 1 - front * h


def _gamma_q(p: float, shape: float, scale: float) -> float:
    """The p-quantile of a gamma distribution, by bisection."""
    lo, hi = 0.0, max(1.0, shape) * 2
    while _gamma_cdf(hi, shape) < p:
        hi *= 2
    for _ in range(200):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if _gamma_cdf(mid, shape) < p else (lo, mid)
    return scale * (lo + hi) / 2


def weighted_interval(ws, ys) -> tuple[float, float]:
    """95% bounds on the expected value of the sum of ws[i] * ys[i], for independent
    0/1 draws with unequal weights: the Fay-Feuer gamma interval (Statistics in
    Medicine, 1997), a gamma approximation for weighted Poisson counts whose
    conservative coverage rests on simulation, not proof. Using it for Bernoulli draws
    is this harness's adaptation, and `test_crossfile.py` checks its coverage by
    simulation on skewed populations. Near a rate of 1 it bounds the complement,
    where the Poisson shape fits. Its upper bound on no events is 3.69 times the
    largest weight, so a single draw standing for a large commit cannot certify that
    commit: this is the case an effective-sample-size interval gets wrong."""
    mass = sum(ws)
    if not mass:
        return (0.0, 0.0)

    def bounds(hits):
        y = sum(w for w, h in zip(ws, hits) if h)
        v = sum(w * w for w, h in zip(ws, hits) if h)
        wm = max(ws)
        lo = _gamma_q(0.025, y * y / v, v / y) if y > 0 else 0.0
        return lo, _gamma_q(0.975, (y + wm) ** 2 / (v + wm * wm), (v + wm * wm) / (y + wm))

    hits = [bool(y) for y in ys]
    if sum(w for w, h in zip(ws, hits) if h) <= mass / 2:
        lo, hi = bounds(hits)
    else:
        a, b = bounds([not h for h in hits])
        lo, hi = mass - b, mass - a
    return max(lo, 0.0), min(hi, mass)


def design_ci(evs, ys, seed: int = SEED + 3, B: int = BOOT, unscored: float = 0.0) -> dict:
    """A weighted proportion and a 95% interval fit for the sampling design.
    Point: inside each stratum, the weighted mean of `ys`; across strata, the
    means weighted by stratum population. Interval: the wider of two, per side.
    `weighted_interval` reads the draws as independent, which a commit's are of
    another commit's by construction, and speaks about this population, so a commit
    whose every move was drawn (`ev.certain`) carries no uncertainty there: scoring
    every move leaves only the bootstrap. The other is
    the percentile interval of a bootstrap resampling commits inside each stratum (commits are the clusters:
    moves of one prune share a document and its wording), which reads the commits as
    a sample of what a prune does, and returns no variance for a stratum with no
    events. Mass no draw speaks for is then added at its worst case rather than
    estimated, stratum by stratum: commits never drawn (`ev.uncovered`, their share
    of the stratum, known from the frame) and `unscored`, a share of all moves left
    out of `evs`. The ratio estimate cannot see a large commit it never drew; this is
    what stops that deciding the call."""
    strata: dict = defaultdict(lambda: defaultdict(lambda: [0.0, 0.0]))
    gap: dict = {}
    for ev, y in zip(evs, ys):
        gap[ev.stratum] = getattr(ev, "uncovered", 0.0)
        cell = strata[ev.stratum][ev.j]
        cell[0] += ev.weight
        cell[1] += ev.weight * y
    if not strata:
        return {"point": None, "lo": 0.0, "hi": 1.0, "n": 0}
    names = sorted(strata)
    pop = {h: sum(c[0] for c in strata[h].values()) for h in names}
    total = sum(pop.values())
    share = {h: pop[h] / total for h in names}
    point = {h: sum(c[1] for c in strata[h].values()) / pop[h] for h in names}
    rng = random.Random(seed)
    cells = {h: [tuple(strata[h][j]) for j in sorted(strata[h])] for h in names}
    per = {h: [] for h in names}
    for _ in range(B):
        for h in names:
            draw = rng.choices(cells[h], k=len(cells[h]))
            per[h].append(sum(c[1] for c in draw) / sum(c[0] for c in draw))
    # All of this is over the mass the draws speak for; `missing` is the rest.
    seen = {h: share[h] * (1 - gap[h]) for h in names}
    overall = sorted(sum(seen[h] * per[h][b] for h in names) for b in range(B))
    boot_lo, boot_hi = overall[int(0.025 * B)], overall[min(B - 1, int(0.975 * B))]
    ws = [ev.weight / total * (1 - gap[ev.stratum]) for ev in evs]
    known = sum(w * y for ev, w, y in zip(evs, ws, ys) if getattr(ev, "certain", False))
    open_draws = [(w, y) for ev, w, y in zip(evs, ws, ys) if not getattr(ev, "certain", False)]
    w_lo, w_hi = weighted_interval([w for w, _ in open_draws], [y for _, y in open_draws])
    w_lo, w_hi = w_lo + known, w_hi + known
    missing = sum(share[h] * gap[h] for h in names)
    lo, hi = min(boot_lo, w_lo), max(boot_hi, w_hi) + missing
    pt = sum(share[h] * point[h] for h in names)
    return {"point": pt, "lo": lo * (1 - unscored), "hi": hi * (1 - unscored) + unscored,
            "unseen": missing * (1 - unscored) + unscored,
            "boot": [boot_lo, boot_hi], "weighted": [w_lo, w_hi], "n": len(evs)}


# Shared with workers by fork: the repository, parsed newer documents keyed by
# (path, blob), raw text of the blobs the source-side arms read, and the snapshots.
_G: dict = {"root": None, "units": {}, "text": {}, "snaps": {}}
_W: dict = {}  # per worker: its own `git cat-file` process


def _worker_blob(sha: str) -> str:
    b = _W.get("blobs")
    if b is None or _W.get("root") != _G["root"]:
        b = _W["blobs"] = Blobs(_G["root"])
        _W["root"] = _G["root"]
    return b.get(sha)


def child_anchors(md: str) -> list:
    """`markstay_lint._build_child_anchors`, one per id, reading real markers only:
    the shipped builder also reads a marker quoted in an inline code span, so an
    example showing an id would stand in for the item that id names, or for the
    container's own id. It emits one anchor per valid child marker in document
    order, so walking the same parse pairs each anchor with its marker and its
    container. A duplicated id keeps its first real occurrence."""
    blocks = [b for b in L.parse_document(md, mode=MODE, child_blocks=True) if b.index >= 0]
    real = _real_markers(md, blocks)
    raw = iter(L._build_child_anchors(md, MODE))
    seen, out = set(), []
    for b in blocks:
        parent = next((mk.id for mk in b.markers
                       if id(mk) in real and mk.id and not mk.malformed and not mk.has_subhash), None)
        for c in b.children:
            for mk in c.markers:
                if not mk.id or mk.malformed:
                    continue
                x = next(raw)
                if id(mk) in real and x.id not in seen:
                    seen.add(x.id)
                    out.append(replace(x, parent_id=parent))
    return out


def _summarize_sha(sha: str):
    md = _worker_blob(sha)
    return sha, summarize(parse(md)) if "stay:" in md else {}


def _parse_unit(key):
    path, sha = key
    return key, Unit(path, parse(_worker_blob(sha)))


def _score_group(task):
    """All arms for one (source blob, newer chain position, source path) group.
    Runs in a worker against the shared parsed snapshot; returns
    {id: {arm: answer}} with answers as (path, kind, loc) or None."""
    started = time.time()
    ob, j, src, kinds = task
    snap = _G["snaps"][j]
    units = [_G["units"][(p, sha)] for p, sha in sorted(snap.items())]
    md_old = _G["text"][ob]
    md_src_new = _G["text"][snap[src]] if src in snap else None
    src_unit = _G["units"][(src, snap[src])] if src in snap else None
    ids = set(kinds)
    out = {m: {} for m in ids}
    child_ids = {m for m in ids if kinds[m] == "child"}
    block_ids_ = {m for m in ids if kinds[m] == "block"}
    if child_ids:
        # Every child anchor of the source document resolves together, as a
        # resolver over that document would.
        anchors = child_anchors(md_old)
        res = {
            CHILD_ARMS[0]: source_only(anchors, md_src_new, src_unit),
            CHILD_ARMS[1]: child_ladder(anchors, units),
            CHILD_ARMS[2]: child_hash(anchors, units),
            CHILD_ARMS[3]: child_quote(anchors, units),
        }
        for arm, got in res.items():
            for m in child_ids:
                t, key = got.get(m, ("detached", None))
                if key is None:
                    out[m][arm] = None
                elif key[0] == "source":
                    out[m][arm] = ("<source>", "child", key[1])
                else:
                    out[m][arm] = (units[key[0]].path, "child", key[1])
    if block_ids_:
        blocks_old = parse(md_old)
        res = block_arms(md_old, blocks_old, block_ids_, units, src_unit)
        for arm, got in res.items():
            for m in block_ids_:
                key = got.get(m)
                if key is None:
                    out[m][arm] = None
                elif key[0] == "source":
                    out[m][arm] = ("<source>", "block", key[1])
                else:
                    out[m][arm] = (units[key[0]].path, "block", key[1])
    return (ob, j, src), out, time.time() - started


def bucket(d: int) -> str:
    """The window stratum a move's delay puts it in: k = 1, only k = 5, only k = 20."""
    return "d0" if d == 0 else "d1-4" if d < 5 else "d5-19"


def sample_moves(moves, n: int, seed: int) -> tuple[list, dict]:
    """A seeded sample of moves, stratified by stay kind (block or child), by
    window and by destination commit. With n = 0 each stratum draws one move from
    every commit in it, so no commit goes unseen and each draw weighs its commit's
    size. Otherwise each (kind, window) stratum gets a share of n proportional to
    its size, but never fewer than min(size, 30), and the share of a stratum in
    commits never drawn is recorded (`uncovered`) for `design_ci` to bound; inside a
    stratum the commits are visited in seeded random order, one random move per
    commit per round, so a commit that moved hundreds of items contributes no more
    than one that moved a few until the small ones run out. A second round starts
    only when a stratum's quota exceeds its commits, and the frame records the
    most draws any commit gave. Each sampled move carries the weight
    (cell size / cell sample) for its (stratum, commit) cell, rescaled so each
    stratum's weights sum to its population, so weighted rates estimate the
    whole population."""
    rng = random.Random(seed)
    strata = defaultdict(list)
    for ev in moves:
        ev.stratum = f"{ev.kind}:{bucket(ev.d)}"
        strata[ev.stratum].append(ev)
    if 0 < len(moves) <= n:
        for ev in moves:
            ev.weight, ev.certain = 1.0, True
        return list(moves), {b: {"population": len(v), "sample": len(v), "census": True} for b, v in strata.items()}
    names = sorted(strata)
    if n <= 0:
        quota = {b: len({ev.j for ev in strata[b]}) for b in names}
    else:
        quota = {b: max(min(len(strata[b]), 30), round(n * len(strata[b]) / len(moves))) for b in names}
        while sum(quota.values()) > n and max(quota.values()) > 1:  # no stratum goes undrawn
            big = max(names, key=lambda b: quota[b])
            quota[big] -= 1
        while sum(quota.values()) < n:
            room = [b for b in names if quota[b] < len(strata[b])]
            quota[max(room, key=lambda b: len(strata[b]) - quota[b])] += 1
    picked, frame = [], {}
    for b in names:
        cells = defaultdict(list)
        for ev in sorted(strata[b], key=lambda e: (e.j, e.src, e.id)):
            cells[ev.j].append(ev)
        order = sorted(cells)
        rng.shuffle(order)
        for c in order:
            rng.shuffle(cells[c])
        got = defaultdict(list)
        while sum(map(len, got.values())) < quota[b]:
            for c in order:
                if cells[c] and sum(map(len, got.values())) < quota[b]:
                    got[c].append(cells[c].pop())
        # Weight: the cell's size over its sample, rescaled so the stratum's
        # weights sum to its population (commits never drawn are represented by
        # the drawn ones, a ratio estimate).
        covered = sum(len(evs) + len(cells[c]) for c, evs in got.items())
        for c, evs in got.items():
            size = len(evs) + len(cells[c])
            for ev in evs:
                ev.weight = size / len(evs) * len(strata[b]) / covered
                ev.certain = size == len(evs)
                ev.uncovered = 1 - covered / len(strata[b])
                picked.append(ev)
        frame[b] = {"population": len(strata[b]), "sample": quota[b],
                    "commits": len(order), "commits_sampled": len(got),
                    "moves_in_undrawn_commits": len(strata[b]) - covered,
                    "max_draws_per_commit": max(map(len, got.values()), default=0)}
    return picked, frame


def _log(label, msg, t0):
    print(f"[{label}] {time.time() - t0:7.0f}s {msg}", file=sys.stderr, flush=True)


def _open_answers(path: Path, header: dict) -> tuple[dict, "object"]:
    """Scored groups from an earlier, interrupted run of the same draw, and the file
    to append to. A different header starts over, and a line cut off by the
    interruption is dropped. The file holds ids and paths from the replayed
    repository, so it lives in `--out` and goes when the run finishes."""
    answers: dict = {}
    head = json.dumps(header, sort_keys=True)
    if path.exists():
        raw = path.read_text().split("\n")
        if raw[0] == head:
            for ln in raw[1:]:
                try:
                    key, got = json.loads(ln)
                except ValueError:
                    continue
                answers[tuple(key)] = {m: {a: None if v is None else tuple(v) for a, v in row.items()}
                                       for m, row in got.items()}
    f = path.open("w")
    f.write(head + "\n")
    for key, got in answers.items():
        f.write(json.dumps([key, got]) + "\n")
    f.flush()
    return answers, f


def run(root: Path, globs, out: Path, label: str, ks, jobs: int, sanity_n: int,
        n_moves: int = 0, n_dels: int = 150, profile: int = 0, budget: float = 45 * 60,
        rev: str = "HEAD", keep_answers: bool = False) -> dict:
    t0 = time.time()
    RP.configure(root, globs, out)
    out.mkdir(parents=True, exist_ok=True)
    kmax = max(ks)
    rev = subprocess.run(["git", "-C", str(root), "rev-parse", rev], capture_output=True, text=True,
                         check=True).stdout.strip()
    commits = chain(root, rev)
    blobs = Blobs(root)
    _G.update(root=root, units={}, text={}, snaps={})
    _log(label, f"{len(commits)} commits touch the scope", t0)

    # Real markers of every revision in scope: departures are read from these.
    need = sorted({sha for _, ch in commits for sha in ch.values() if sha})
    summ: dict[str, dict] = {}
    with mp.get_context("fork").Pool(jobs) as pool:
        for x, (sha, sm) in enumerate(pool.imap_unordered(_summarize_sha, need, chunksize=8), 1):
            summ[sha] = sm
            if x % 4000 == 0 or x == len(need):
                _log(label, f"parsed {x}/{len(need)} revisions", t0)
    idsets = {sha: frozenset(sm) for sha, sm in summ.items()}
    events = scan(commits, idsets.__getitem__, kmax)
    _log(label, f"{len(events)} real markers leave a document", t0)

    n = len(commits)
    for ev in events:
        own = summ[ev.old_blob][ev.id]
        if len(own) > 1:
            ev.status = "dropped:duplicated-in-source"
            continue
        ev.kind = own[0][0]
        if ev.kind == "unaddressed":
            ev.status = "dropped:unaddressed-in-source"
            continue
        ev.pre_existing = bool(ev.pre)
        sightings = defaultdict(list)
        for j, p, b in ev.cands:
            sightings[j].append((p, summ[b][ev.id]))
        first = min(sightings, default=None)
        first_back = min((j for j, _ in ev.back), default=None)
        if first is not None and (first_back is None or first <= first_back):
            hits = sightings[first]
            if len(hits) > 1 or len(hits[0][1]) > 1:
                ev.status = "dropped:ambiguous-destination"
                ev.d = first - ev.i
                continue
            ev.status, ev.d, ev.j, ev.dst = "move", first - ev.i, first, hits[0][0]
            ev.dst_kind, ev.dst_loc = hits[0][1][0]
        elif first_back is not None:
            ev.status, ev.d = "return", first_back - ev.i
        elif ev.i + kmax > n:
            ev.status = "censored"  # the history ends inside the widest window
        else:
            ev.status = "deletion"
    del summ, idsets

    moves = [ev for ev in events if ev.status == "move"]
    # A move that changes kind has no answer an arm could give: a block arm's
    # answer is a block and the id now names an item. Counted, not scored.
    frame_moves = [ev for ev in moves if ev.kind == ev.dst_kind]
    dels = [ev for ev in events if ev.status == "deletion" and ev.kind in ("child", "block")]
    snaps = snapshot_at(commits, {ev.j for ev in moves} | {ev.i for ev in dels})
    for ev in moves:
        ev.src_alive = ev.src in snaps[ev.j]

    def groups_of(ms, ds):
        g = defaultdict(dict)
        for ev in ms:
            g[(ev.old_blob, ev.j, ev.src)][ev.id] = ev.kind
        for ev in ds:
            g[(ev.old_blob, ev.i, ev.src)][ev.id] = ev.kind
        return g

    population = {"moves": len(moves), "scoreable_moves": len(frame_moves),
                  "kind_changing": len(moves) - len(frame_moves), "deletions": len(dels),
                  "groups": len(groups_of(frame_moves, dels))}
    smoves, frame = sample_moves(frame_moves, n_moves, SEED)
    rng = random.Random(SEED + 1)
    sdels = rng.sample(sorted(dels, key=lambda e: (e.i, e.src, e.id)), min(n_dels, len(dels)))
    for ev in events:
        ev.sampled = False
    for ev in smoves + sdels:
        ev.sampled = True
    groups = groups_of(smoves, sdels)
    _log(label, f"population {population}; sample {len(smoves)} moves, {len(sdels)} deletions, "
                f"{len(groups)} groups", t0)

    # Parse each needed snapshot document once, by (path, blob).
    js = {j for _, j, _ in groups}
    _G["snaps"] = {j: snaps[j] for j in js}
    want = sorted({(p, sha) for j in js for p, sha in snaps[j].items()})
    for ob, j, src in groups:
        _G["text"][ob] = blobs.get(ob)
        if src in snaps[j]:
            _G["text"][snaps[j][src]] = blobs.get(snaps[j][src])
    units = {}
    with mp.get_context("fork").Pool(jobs) as pool:
        for x, (key, unit) in enumerate(pool.imap_unordered(_parse_unit, want, chunksize=2), 1):
            units[key] = unit
            if x % 500 == 0 or x == len(want):
                _log(label, f"parsed {x}/{len(want)} snapshot documents", t0)
    _G["units"] = units

    tasks = [(ob, j, src, kinds) for (ob, j, src), kinds in sorted(groups.items())]
    # A long run must survive a reboot. The draw is seeded, so a rerun of the same
    # header asks for the same groups.
    ckpt = out / f"answers-{label}.jsonl"
    answers, ckf = _open_answers(ckpt, {"rev": rev, "globs": sorted(globs), "seed": SEED, "moves": n_moves,
                                        "deletions": n_dels, "ks": list(ks), "groups": len(tasks)})
    resumed = len(answers)
    _log(label, f"resuming with {resumed} of {len(tasks)} groups scored", t0)

    def keep(key, got):
        answers[key] = got
        ckf.write(json.dumps([key, got]) + "\n")
        ckf.flush()

    timing = {"resumed_groups": resumed}
    took = []
    if profile and tasks and not resumed:
        rng2 = random.Random(SEED + 2)
        probe = rng2.sample(tasks, min(profile, len(tasks)))
        for t in probe:
            key, got, sec = _score_group(t)
            took.append(sec)
            keep(key, got)
            _log(label, f"profile group {len(took)}/{len(probe)}: {sec:.1f}s, {len(t[3])} ids", t0)
        mean = sum(took) / len(took)
        est = mean * len(tasks) / jobs
        timing.update(profiled_groups=len(took), mean_group_seconds=mean,
                      max_group_seconds=max(took), estimated_seconds=est)
        _log(label, f"profiled {len(took)} groups: mean {mean:.1f}s, max {max(took):.1f}s; "
                    f"estimate {est / 60:.1f} min for {len(tasks)} groups on {jobs} workers", t0)
        if est > budget:
            raise SystemExit(f"estimate {est / 60:.0f} min exceeds the {budget / 60:.0f} min budget: "
                             "shrink --moves (not below 150)")
    todo = [t for t in tasks if (t[0], t[1], t[2]) not in answers]
    with mp.get_context("fork").Pool(jobs) as pool:
        for x, (key, got, sec) in enumerate(pool.imap_unordered(_score_group, todo), 1):
            keep(key, got)
            took.append(sec)
            _log(label, f"group {x + len(tasks) - len(todo)}/{len(tasks)} {sec:.1f}s", t0)
    # How alike the old block and the block the id names now are: the ids are
    # the truth here, and a low score says the id itself may have relocated.
    # The same exact §9 metric as the arms.
    old_cache: dict = {}
    for ev in smoves:
        if ev.old_blob not in old_cache:
            old_cache[ev.old_blob] = parse(_G["text"][ev.old_blob])
        old = _body_of(old_cache[ev.old_blob], ev.kind, ev.id)
        unit = _G["units"].get((ev.dst, snaps[ev.j][ev.dst]))
        new = _loc_body(unit, ev.dst_kind, ev.dst_loc) if unit else None
        ev.truth_score = _sim(old, new)
        g = answers.get((ev.old_blob, ev.j, ev.src), {}).get(ev.id, {})
        ev.answer_scores = {}
        for arm, got in g.items():
            if not got or got[0] == "<source>":
                continue
            u = _G["units"].get((got[0], snaps[ev.j].get(got[0])))
            ev.answer_scores[arm] = _sim(old, _loc_body(u, got[1], got[2]) if u else None)
    timing["total_seconds"] = time.time() - t0
    timing["slowest_groups"] = sorted(took, reverse=True)[:5]
    res = report(label, root, commits, events, answers, ks)
    res["truth_similarity"] = truth_table(smoves)
    res["metric"] = "exact §9 Ratcliff/Obershelp for every decision and bucket, numpy" if _np is not None else "exact §9, difflib"
    if sanity_n:
        res["block_comparison"] = dump_blocks(out, label, smoves, old_cache, snaps)
    res["population"] = population
    res["rev"] = rev
    res["sample"] = {"seed": SEED, "deletion_seed": SEED + 1, "bootstrap_seed": SEED + 3, "bootstrap_replicates": BOOT,
                     "moves": len(smoves), "deletions": len(sdels), "groups": len(groups), "frame": frame,
                     "rule": "moves: stratified by stay kind, window (d = 0, 1-4, 5-19) and destination "
                             "commit, " + ("one draw per commit per stratum" if n_moves <= 0 else
                                           "round-robin over commits in seeded order") + "; deletions: simple random; "
                             "kind-changing moves are outside the frame"}
    res["timing"] = timing
    if sanity_n:
        res["sanity_counts"] = write_sanity(out, label, smoves, blobs, snaps, sanity_n)
    blobs.close()
    ckf.close()
    if not keep_answers:
        ckpt.unlink()
    return res


def report(label, root, commits, events, answers, ks) -> dict:
    status = Counter(ev.status for ev in events)
    res = {"label": label, "commits": len(commits),
           "first": commits[0][0] if commits else None, "last": commits[-1][0] if commits else None,
           "removals": len(events), "status": dict(status), "ks": list(ks)}
    moves = [ev for ev in events if ev.status == "move"]
    res["move_kinds"] = dict(sorted(Counter(f"{ev.kind}->{ev.dst_kind}" for ev in moves).items()))
    res["moves_by_window"] = {}
    res["deletions_by_window"] = {}
    for k in ks:
        mk = [ev for ev in moves if ev.d < k]
        res["moves_by_window"][str(k)] = {
            "moves": len(mk),
            "source_alive": sum(ev.src_alive for ev in mk),
            "source_gone": sum(not ev.src_alive for ev in mk),
            "kind_changing": sum(ev.kind != ev.dst_kind for ev in mk),
            "pre_existing": sum(ev.pre_existing for ev in mk),
            "by_kind": dict(Counter(ev.kind for ev in mk)),
            "commits": len({ev.j for ev in mk}),
            "max_per_commit": max(Counter(ev.j for ev in mk).values(), default=0),
            "per_commit_sizes": sorted(Counter(ev.j for ev in mk).values(), reverse=True),
            "ten_largest_commits_share": sum(sorted(Counter(ev.j for ev in mk).values(), reverse=True)[:10]) / len(mk)
            if mk else None,
            "single_move_commits": sum(v == 1 for v in Counter(ev.j for ev in mk).values()),
            "source_docs": len({ev.src for ev in mk}),
            "dest_docs": len({ev.dst for ev in mk}),
        }
        # A deletion at window k: not found elsewhere and not back within k.
        res["deletions_by_window"][str(k)] = sum(
            1 for ev in events
            if ev.kind in ("child", "block")
            and (ev.status == "deletion" or (ev.status in ("move", "return") and ev.d >= k)
                 or (ev.status == "dropped:ambiguous-destination" and ev.d >= k))
        )
    # Per arm, per window, per kind.
    arms = {}
    dele = {}
    for ev in events:
        ev.answers = None
        if not getattr(ev, "sampled", True):
            continue
        if ev.status == "move":
            g = answers.get((ev.old_blob, ev.j, ev.src))
            ev.answers = g.get(ev.id) if g else None
        elif ev.status == "deletion" and ev.kind in ("child", "block"):
            g = answers.get((ev.old_blob, ev.i, ev.src))
            ev.answers = g.get(ev.id) if g else None
    scored = [ev for ev in moves if getattr(ev, "sampled", True)]

    def outcome(ev, arm):
        got = ev.answers.get(arm) if ev.answers else None
        if got is None:
            return "missed"
        return "correct" if got == (ev.dst, ev.dst_kind, ev.dst_loc) else "wrong"

    def tabulate(evs, intervals=True, unscored=0.0):
        table, weighted = defaultdict(Counter), defaultdict(Counter)
        commits_wrong, commits_seen = defaultdict(set), defaultdict(set)
        answered = defaultdict(list)
        for ev in evs:
            names = CHILD_ARMS if ev.kind == "child" else BLOCK_ARMS
            for x, arm in enumerate(names):
                o = outcome(ev, arm)
                for name in (arm, COMBINED[x]):
                    table[name][o] += 1
                    weighted[name][o] += getattr(ev, "weight", 1.0)
                    commits_seen[name].add(ev.j)
                    answered[name].append((ev, o))
                    if o == "wrong":
                        commits_wrong[name].add(ev.j)
        rows = {}
        for arm, c in sorted(table.items()):
            w = weighted[arm]
            tot = sum(w.values())
            rows[arm] = {**rate_row(c), "commits": len(commits_seen[arm]),
                         "commits_with_wrong": len(commits_wrong[arm]),
                         "weighted_found": w["correct"] / tot if tot else None,
                         "weighted_misattach": w["wrong"] / tot if tot else None}
            if intervals:
                es = [e for e, _ in answered[arm]]
                # The rule is over all moves, so only the combined rows answer for
                # the kind-changing ones; a per-kind row is a diagnostic of its kind.
                gap = unscored if arm in COMBINED else 0.0
                rows[arm]["design"] = {
                    "found": design_ci(es, [o == "correct" for _, o in answered[arm]], unscored=gap),
                    "misattach": design_ci(es, [o == "wrong" for _, o in answered[arm]], unscored=gap),
                }
        return rows

    for ev in scored:  # a test or census run may leave these unset
        ev.weight = getattr(ev, "weight", 1.0)
        ev.stratum = getattr(ev, "stratum", f"{ev.kind}:{bucket(ev.d)}")
    for k in ks:
        within = [ev for ev in moves if ev.d < k]
        changed = sum(ev.kind != ev.dst_kind for ev in within)
        arms[str(k)] = tabulate([ev for ev in scored if ev.d < k], unscored=changed / len(within) if within else 0.0)
    k0 = str(max(ks))
    inside = [ev for ev in scored if ev.d < max(ks)]
    subsets = {
        "child": [ev for ev in inside if ev.kind == "child"],
        "block": [ev for ev in inside if ev.kind == "block"],
        "fresh (not elsewhere before the commit)": [ev for ev in inside if not ev.pre_existing],
        "already elsewhere before the commit": [ev for ev in inside if ev.pre_existing],
        "source document still there": [ev for ev in inside if ev.src_alive],
        "source document gone": [ev for ev in inside if not ev.src_alive],
    }
    res["breakdown"] = {"k": k0, **{name: {"n": len(evs), "arms": tabulate(evs, name in ("child", "block"))}
                                    for name, evs in subsets.items()}}
    table = defaultdict(Counter)
    for ev in events:
        if ev.status == "deletion" and ev.answers:
            for arm, got in ev.answers.items():
                table[arm]["false_attach" if got is not None else "detached"] += 1
    for arm, c in sorted(table.items()):
        n = c["false_attach"] + c["detached"]
        dele[arm] = {"n": n, "false_attach": c["false_attach"],
                     "rate": c["false_attach"] / n if n else None, "ci": clopper(c["false_attach"], n)}
    res["arms"] = arms
    res["deletions_scored"] = dele
    res["verdict"] = verdict(arms)
    res["verdict_raw_counts"] = verdict_unweighted(arms)
    return res


def verdict(arms: dict) -> dict:
    """The current (post hoc) rule, per window, over all moves: the combined all-documents
    arms, on population-weighted estimates and their design intervals. One arm
    inside both bars on its interval means the ids are not needed; every arm
    outside a bar on its interval means they pay; anything else is insufficient
    evidence. `best_arm` is the arm the call turns on: the arm that passes, or the
    one that kept it from `ids-pay`, or under `ids-pay` the one nearest the bars,
    with `blocked_by` naming the bar it misses."""
    out = {}
    for k, table in arms.items():
        rows = {a: r["design"] for a, r in table.items() if a in COMBINED and a.endswith("all docs") and r["n"]}
        if not rows:
            out[k] = {"call": "no-data"}
            continue

        def passes(x):
            return x["found"]["lo"] >= FIND_BAR and x["misattach"]["hi"] <= MISATTACH_BAR

        def fails(x):
            return x["found"]["hi"] < FIND_BAR or x["misattach"]["lo"] > MISATTACH_BAR

        def nearness(x):
            return max(x["found"]["hi"] - FIND_BAR, MISATTACH_BAR - x["misattach"]["lo"]) \
                if not fails(x) else min(x["found"]["hi"] - FIND_BAR, MISATTACH_BAR - x["misattach"]["lo"])

        if any(passes(x) for x in rows.values()):
            call = "ids-not-needed"
            best = max((a for a, x in rows.items() if passes(x)), key=lambda a: rows[a]["found"]["point"])
        elif all(fails(x) for x in rows.values()):
            call = "ids-pay"
            best = max(rows, key=lambda a: nearness(rows[a]))
        else:
            call = "insufficient-evidence"
            best = max((a for a, x in rows.items() if not fails(x)), key=lambda a: rows[a]["found"]["point"])
        x = rows[best]
        blocked = [b for b, miss in (("found", x["found"]["hi"] < FIND_BAR),
                                     ("misattached", x["misattach"]["lo"] > MISATTACH_BAR)) if miss]
        out[k] = {"call": call, "best_arm": best, "blocked_by": blocked,
                  "point_pass": x["found"]["point"] >= FIND_BAR and x["misattach"]["point"] <= MISATTACH_BAR}
    return out


def verdict_unweighted(arms: dict) -> dict:
    """The same rule on raw sample counts and Clopper-Pearson intervals, which
    ignore the unequal inclusion of a one-per-commit sample. Reported for
    comparison with `verdict`, never as the call."""
    out = {}
    for k, table in arms.items():
        rows = {a: r for a, r in table.items() if a in COMBINED and a.endswith("all docs") and r["n"]}
        if not rows:
            out[k] = {"call": "no-data"}
            continue
        ok = any(x["found_ci"][0] >= FIND_BAR and x["misattach_ci"][1] <= MISATTACH_BAR for x in rows.values())
        bad = all(x["found_ci"][1] < FIND_BAR or x["misattach_ci"][0] > MISATTACH_BAR for x in rows.values())
        out[k] = {"call": "ids-not-needed" if ok else "ids-pay" if bad else "inconclusive"}
    return out


def write_sanity(out: Path, label: str, moves, blobs: "Blobs", snaps: dict, n: int) -> dict:
    """Up to n moves, the old block beside the block its id names now, for
    reading by hand. Written only to --out, which `main` keeps outside the
    replayed repository. Returns the counts: per kind, how many are byte-identical."""
    rng = random.Random(SEED)
    sample = rng.sample(moves, min(n, len(moves)))
    rows = []
    for x, ev in enumerate(sample, 1):
        old = _body_of(parse(blobs.get(ev.old_blob)), ev.kind, ev.id)
        new = _body_of(parse(blobs.get(snaps[ev.j][ev.dst])), ev.dst_kind, ev.id)
        rows.append({"event": f"{label}-{x}", "kind": f"{ev.kind}->{ev.dst_kind}", "d": ev.d,
                     "identical": old == new, "old": old, "new": new})
    (out / f"sanity-{label}.json").write_text(json.dumps(rows, indent=1) + "\n")
    return dict(sorted(Counter(f"{r['kind']} {'identical' if r['identical'] else 'differs'}" for r in rows).items()))


def _loc_body(unit, kind, loc):
    if unit is None or loc is None:
        return None
    if kind == "block":
        return unit.blocks[loc].content if 0 <= loc < len(unit.blocks) else None
    for b in unit.blocks:
        for c in b.children:
            if c.index == loc:
                return c.content
    return None


def _sim(a, b) -> float | None:
    """§9 body score, exact at and above `arms.PRUNE` and 0.0 under it. Only
    `_sim_bucket` reads it for the report, and its lowest bucket starts above PRUNE."""
    if a is None or b is None:
        return None
    return _pruned_body(L._match_normalize(a), L._match_normalize(b))


def _sim_bucket(x) -> str:
    return "none" if x is None else ">=0.8" if x >= 0.8 else "0.5-0.8" if x >= 0.5 else "<0.5"


def truth_table(smoves) -> dict:
    """Per kind: how alike each sampled move's old block and its id's new block
    are, and per combined arm, the outcome crossed with that bucket. A wrong
    answer is also bucketed by how alike *it* is to the old block."""
    out = {}
    for kind in ("child", "block"):
        evs = [ev for ev in smoves if ev.kind == kind]
        row = {"n": len(evs), "truth": dict(Counter(_sim_bucket(ev.truth_score) for ev in evs)), "arms": {}}
        names = CHILD_ARMS if kind == "child" else BLOCK_ARMS
        for x, arm in enumerate(names):
            tab = Counter()
            for ev in evs:
                got = ev.answers.get(arm) if ev.answers else None
                if got is None:
                    o = "missed"
                elif got == (ev.dst, ev.dst_kind, ev.dst_loc):
                    o = "correct"
                else:
                    o = "wrong:answer " + _sim_bucket(ev.answer_scores.get(arm))
                tab[f"truth {_sim_bucket(ev.truth_score)} | {o}"] += 1
            row["arms"][COMBINED[x]] = dict(sorted(tab.items()))
        out[kind] = row
    return out


def dump_blocks(out: Path, label: str, smoves, old_cache, snaps) -> dict:
    """Every sampled block-stay move with the old block, the id's new block and
    each arm's answer, for reading by hand. Scratch output only (--out). Returns the
    counts of a mechanical comparison of the two blocks."""
    rows = []
    for ev in smoves:
        if ev.kind != "block":
            continue
        old = _body_of(old_cache[ev.old_blob], ev.kind, ev.id)
        unit = _G["units"].get((ev.dst, snaps[ev.j][ev.dst]))
        rows.append({"truth_score": ev.truth_score, "answer_scores": ev.answer_scores,
                     "same_doc_answer": {a: (g[0] == ev.dst) for a, g in (ev.answers or {}).items() if g},
                     "old": old or "", "truth": _loc_body(unit, "block", ev.dst_loc) or ""})
    (out / f"blocks-{label}.json").write_text(json.dumps(rows, indent=1) + "\n")

    def alike(r):
        old, new = r["old"], r["truth"]
        return "identical" if old == new else "same first 40 characters" if old.strip()[:40] == new.strip()[:40] else "other"

    counts = dict(sorted(Counter(alike(r) for r in rows).items()))
    counts["bare rules"] = sum(r["old"].strip() in ("---", "***", "___") for r in rows)
    return counts


def _body_of(blocks, kind, mid):
    for b in blocks:
        if kind != "child" and any(mk.id == mid for mk in b.markers):
            return b.content
        for c in b.children:
            if any(mk.id == mid for mk in c.markers):
                return c.content
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", required=True)
    ap.add_argument("--glob", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--label", default="store")
    ap.add_argument("--ks", default=",".join(map(str, KS)))
    ap.add_argument("--rev", default="HEAD", help="replay the history up to this commit")
    ap.add_argument("--jobs", type=int, default=min(12, max(1, (mp.cpu_count() or 2) - 2)))
    ap.add_argument("--moves", type=int, default=0,
                    help="moves to score, a stratified sample; 0 draws one per commit per stratum")
    ap.add_argument("--deletions", type=int, default=150, help="deletions to score, a simple sample")
    ap.add_argument("--profile", type=int, default=3, help="groups to time serially before the pool")
    ap.add_argument("--budget-min", type=float, default=45.0, help="stop if the profile predicts more")
    ap.add_argument("--sanity", type=int, default=0, help="write N sampled moves for reading by hand")
    ap.add_argument("--keep-answers", action="store_true",
                    help="keep the scored groups in --out, so a change to the statistics need not rescore")
    args = ap.parse_args()
    out = Path(args.out).resolve()
    root = Path(args.root).resolve()
    if out == root or root in out.parents:
        ap.error("--out must sit outside the repository being replayed")
    res = run(root, args.glob, out, args.label, tuple(int(x) for x in args.ks.split(",")),
              min(args.jobs, 12), args.sanity, args.moves, args.deletions, args.profile, args.budget_min * 60, args.rev,
              args.keep_answers)
    (out / f"crossfile-{args.label}.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: res[k] for k in ("population", "sample", "move_kinds", "verdict", "verdict_raw_counts",
                                          "timing")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
