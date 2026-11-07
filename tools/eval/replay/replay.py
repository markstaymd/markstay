#!/usr/bin/env python3
"""Replay real edit history: do inline ids beat id-free matching?

Every other attachment comparison in this repo runs on synthetic edit operators.
This one runs on the umbrella's own stamped Markdown, which agents have edited
for months under a linter that requires ids to be kept. That history is real
edits with ground truth: an id present in two revisions names the same block in
both.

For each document and each commit gap k, every pair (revision i, revision i+k)
is scored. Ground truth comes from the ids; every arm (`arms.py`) sees only the
older revision's stored evidence and the newer revision's bodies with markers
stripped. The decision rule was fixed before any data was read:

    At k = 20, if the best id-free arm misattaches at most 1% and misses at most
    5% of surviving ids, inline ids do not earn their cost for within-document
    tracking, and markstay's case rests only on cross-file moves and external
    references. If id-free arms degrade steeply with k while ids hold, the
    metadata pays for any reference held across editing sessions.

Run (about four minutes on 20 cores, no network, no API):

    python replay.py              # writes results.json, results.md, sanity.md

The corpus is read at a pinned commit so the committed results reproduce;
`--rev` moves it. `--root` and `--glob` point the same harness at another
repository's history (`--out` is then required, so nothing lands here), and
`crossfile.py` reuses its git and parsing layer for moves between documents.
"""

from __future__ import annotations

import argparse
import json
import math
import multiprocessing as mp
import random
import re
import subprocess
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
UMBRELLA = HERE.parents[1]
# The repository read, the Markdown it scopes to, and where reports go. The
# defaults are the umbrella run the committed results come from; `configure`
# points them elsewhere (`--root`, `--glob`, `--out`).
ROOT = UMBRELLA
GLOBS: tuple[str, ...] | None = None  # None: every tracked .md outside EXCLUDE_*
OUT = HERE
sys.path.insert(0, str(HERE))
import arms as A  # noqa: E402

L = A.L

CORPUS_REV = "5ee925df40edbf189e8c4f4842d522987e239306"
KS = (1, 5, 20, 50)
MAX_PAIRS = 200  # per document per k; above this, pairs are subsampled evenly
MIN_REVS = 2  # stamped revisions a document needs to yield a pair
# A revision is stamped when at least this share of its content blocks carries a
# block id (blocks, not ids: two ids on one block cover one block). Without it a document that only *quotes* a marker in inline code (which
# SPEC.md §3.3 still reads as a marker) counts as stamped: PLAN_FENCE_RULE.md
# carries one id, `x`, across 72 blocks. Stamped revisions here sit at 85-100%,
# quoting ones under 5%, so the cut is not delicate.
MIN_COVERAGE = 0.5
# The two id arms: the marker tier alone, and the marker tier with the shipped
# ladder behind it for ids whose marker is gone, which is markstay as designed.
MARKERS = "markers only"
IDS_LADDER = "ids+ladder"
ID_ARMS = (MARKERS, IDS_LADDER)
ORDER = [*ID_ARMS, *A.ARMS]
MISATTACH_BAR = 0.01
MISS_BAR = 0.05
NEAR = 0.8  # body score at which a vanished id's block counts as surviving
SANITY_N = 30
REPAIR_N = 30
SEED = 20261031

# Tracked Markdown outside these never enters the corpus: fixtures and generated
# reports carry markers a tool wrote, mirrors and vendored corpora duplicate a
# source, and this directory would otherwise read its own findings.
EXCLUDE_PREFIXES = (
    "conformance/",
    "impl/",
    "examples/",
    "linter/examples/",
    "eval/docs/",
    "eval/replay/",
    "eval/openknowledge/out/",
    "eval/attachment/llm/",
)
EXCLUDE_PARTS = ("/fixtures/",)
EXCLUDE_NAMES = ("results", "RESULTS")


# --- scope -----------------------------------------------------------------------


def configure(root=None, globs=None, out=None) -> None:
    """Point the harness at another repository. `globs` are git-style path
    globs (`**/` for any directory depth, `*` within one segment); with none, the
    umbrella's own selection applies. Clears the git caches."""
    global ROOT, GLOBS, OUT
    ROOT = Path(root).resolve() if root else UMBRELLA
    GLOBS = tuple(globs) if globs else None
    OUT = Path(out) if out else HERE
    _SHOW.clear()
    _XINDEX.clear()
    _XPARSE.clear()


def glob_re(glob: str) -> re.Pattern:
    out, i = [], 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def in_scope(path: str) -> bool:
    """Whether `path` is a document of the corpus: the umbrella's selection by
    default, otherwise a match for one of the configured globs."""
    if GLOBS is None:
        return path.endswith(".md") and not excluded(path)
    return any(glob_re(g).match(path) for g in GLOBS)


def pathspecs() -> list[str]:
    """The same scope as git pathspecs, for `git grep` and `git log`."""
    if GLOBS is None:
        return ["*.md"]
    return [":(glob)" + g for g in GLOBS]


# --- git -------------------------------------------------------------------------


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(ROOT), *args], capture_output=True, text=True, check=True
    ).stdout


_SHOW: dict[tuple[str, str], str | None] = {}


def show(commit: str, path: str) -> str | None:
    key = (commit, path)
    if key not in _SHOW:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "show", f"{commit}:{path}"],
            capture_output=True,
            text=True,
        )
        _SHOW[key] = r.stdout if r.returncode == 0 else None
    return _SHOW[key]


def excluded(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return (
        path.startswith(EXCLUDE_PREFIXES)
        or any(p in "/" + path for p in EXCLUDE_PARTS)
        or name.startswith(EXCLUDE_NAMES)
    )


def history(path: str, rev: str) -> list[tuple[str, str]]:
    """(commit, path at that commit) oldest first, along the first-parent chain,
    following renames. First parent keeps every pair an ancestor/descendant pair."""
    out = git("log", "--first-parent", "--follow", "--format=C %H", "--name-only", rev, "--", path)
    revs, cur = [], None
    for ln in out.splitlines():
        if ln.startswith("C "):
            cur = ln[2:]
        elif ln.strip() and cur:
            revs.append((cur, ln.strip()))
            cur = None
    return revs[::-1]


# --- documents and revisions ----------------------------------------------------


@dataclass
class Rev:
    commit: str
    path: str
    md: str
    blocks: list
    ids: dict  # block-level id -> [block index]
    child_ids: int
    quoted: int = 0  # markers inside inline code, left out of `ids`

    @property
    def stamped(self) -> bool:
        covered = {ix for idxs in self.ids.values() for ix in idxs}
        return bool(self.blocks) and len(covered) >= MIN_COVERAGE * len(self.blocks)


@dataclass
class Doc:
    name: str  # path at the pinned commit
    revs: list[Rev]  # every revision that parsed, oldest first
    marked: list[Rev] = field(default_factory=list)  # the stamped ones
    shared_dropped: int = 0  # revisions another document's series owns


def _code_spans(line: str) -> list[tuple[int, int]]:
    """Inline code spans on one line: a backtick run closed by the next run of
    the same length (CommonMark's rule, without spans that cross lines)."""
    runs = [(m.start(), m.end()) for m in re.finditer(r"`+", line)]
    spans, i = [], 0
    while i < len(runs):
        s, e = runs[i]
        for j in range(i + 1, len(runs)):
            if runs[j][1] - runs[j][0] == e - s:
                spans.append((e, runs[j][0]))
                i = j
                break
        i += 1
    return spans


def _occurrence(line: str, raw: str, n: int) -> int:
    """Start of the n-th (0-based) occurrence of `raw` on `line`, or -1. Markers
    come out of the parser in document order, so the n-th marker with this text
    on this line is the n-th occurrence of it: a quoted example and an identical
    real marker on one line each find their own span."""
    at = -1
    for _ in range(n + 1):
        at = line.find(raw, at + 1)
        if at < 0:
            return -1
    return at


def real_blocks(md: str) -> tuple[list, int]:
    """Content blocks with every marker that sits inside an inline code span
    removed, and how many were removed. SPEC.md §3.3 reads such a marker as a
    marker on purpose, but in this corpus every one is a quoted example
    (`<!-- stay:x -->` in prose), and left in it shows up as a duplicate id or as a
    cross-file move between two documents quoting the same example."""
    lines = md.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks = [b for b in L.parse_document(md) if b.index >= 0]
    quoted = 0
    seen: Counter = Counter()  # (line, raw) -> markers of that text already placed
    for b in blocks:
        keep = []
        for mk in b.markers:
            line = lines[mk.line - 1] if 0 < mk.line <= len(lines) else ""
            at = _occurrence(line, mk.raw, seen[(mk.line, mk.raw)])
            seen[(mk.line, mk.raw)] += 1
            if at >= 0 and any(s <= at < e for s, e in _code_spans(line)):
                quoted += 1
            else:
                keep.append(mk)
        b.markers = keep
    return blocks, quoted


def parse_rev(commit: str, path: str) -> Rev | None:
    md = show(commit, path)
    if md is None:
        return None
    blocks, quoted = real_blocks(md)
    ids = A.block_ids(blocks)
    child = sum(
        1 for b in blocks for mk in b.markers if mk.id and not mk.malformed and mk.has_subhash
    )
    return Rev(commit, path, md, blocks, ids, child, quoted)


def load_corpus(rev: str) -> tuple[list[Doc], list[dict]]:
    """Every tracked, non-excluded Markdown file at `rev` with at least MIN_REVS
    marker-carrying revisions. A revision `--follow` reaches through two series
    (a file split out of another inherits its history) belongs to the series
    whose own path it is, so no edit is counted twice."""
    paths = git("ls-tree", "-r", "--name-only", rev).split("\n")
    series = {p: history(p, rev) for p in paths if p and in_scope(p)}
    owner: dict[tuple[str, str], str] = {}
    for name, revs in sorted(series.items()):
        for cr in revs:
            owner.setdefault(cr, name)
    for name, revs in series.items():  # a series always owns its own path
        for cr in revs:
            if cr[1] == name:
                owner[cr] = name
    docs, skipped = [], []
    for name, revs in sorted(series.items()):
        mine = [cr for cr in revs if owner[cr] == name]
        parsed = [r for r in (parse_rev(c, p) for c, p in mine) if r is not None]
        d = Doc(name, parsed, [r for r in parsed if r.stamped], len(revs) - len(mine))
        if len(d.marked) >= MIN_REVS:
            docs.append(d)
        elif any(r.ids for r in parsed) or d.shared_dropped:
            skipped.append(
                {
                    "doc": name,
                    "marked_revisions": len(d.marked),
                    "revisions_with_any_id": sum(bool(r.ids) for r in parsed),
                    "shared_dropped": d.shared_dropped,
                }
            )
    return docs, skipped


# --- cross-file ids ---------------------------------------------------------------

_XINDEX: dict[str, dict[str, set[str]]] = {}
_XPARSE: dict[tuple[str, str], set[str]] = {}


def ids_elsewhere(commit: str, mid: str, here: str) -> list[str]:
    """Tracked Markdown files other than `here` that carry `mid` as a real block
    marker at `commit` (grepped, then confirmed by the reference parser, so a
    mention in prose or an example inside a fence does not count)."""
    if commit not in _XINDEX:
        r = subprocess.run(
            ["git", "-C", str(ROOT), "grep", "-o", "-E", r"stay:[A-Za-z0-9_-]+", commit, "--", *pathspecs()],
            capture_output=True,
            text=True,
        )
        idx: dict[str, set[str]] = defaultdict(set)
        for ln in r.stdout.splitlines():
            _, path, tok = ln.split(":", 2)
            idx[tok[5:]].add(path)
        _XINDEX[commit] = idx
    out = []
    for path in sorted(_XINDEX[commit].get(mid, ())):
        # Without explicit globs every tracked Markdown file counts as elsewhere,
        # including ones the corpus excludes, as `make_case` has always read it.
        if path == here or (GLOBS is not None and not in_scope(path)):
            continue
        key = (commit, path)
        if key not in _XPARSE:
            md = show(commit, path) or ""
            _XPARSE[key] = set(A.block_ids(real_blocks(md)[0]))
        if mid in _XPARSE[key]:
            out.append(path)
    return out


# --- similarity table, filled in parallel --------------------------------------------

_STRS: list[str] = []


def _work(keys: list[int]) -> list[tuple[int, float]]:
    out = []
    for key in keys:
        v = A.body_norm(_STRS[key >> 32], _STRS[key & 0xFFFFFFFF])
        if v:
            out.append((key, v))
    return out


class Table(A.Scores):
    """`arms.Scores` over interned strings with integer keys, so a few million
    entries fit comfortably, and a bulk fill that runs in a process pool."""

    def __init__(self):
        super().__init__()
        self.ids: dict[str, int] = {}
        self.strs: list[str] = []

    def intern(self, s: str) -> int:
        i = self.ids.get(s)
        if i is None:
            i = self.ids[s] = len(self.strs)
            self.strs.append(s)
        return i

    def get(self, q: str, c: str) -> float:
        if q == c:
            return 1.0 if q else 0.0
        key = (self.intern(q) << 32) | self.intern(c)
        v = self.table.get(key)
        if v is None:
            v = A.body_norm(q, c)
            self.table[key] = v
        return v

    def fill(self, wanted: set[int], jobs: int) -> None:
        global _STRS
        todo = sorted(k for k in wanted if k not in self.table)
        for k in todo:
            self.table[k] = 0.0
        if not todo:
            return
        _STRS = self.strs
        size = max(1, len(todo) // (jobs * 8))
        chunks = [todo[i : i + size] for i in range(0, len(todo), size)]
        with mp.get_context("fork").Pool(jobs) as pool:
            for got in pool.imap_unordered(_work, chunks):
                self.table.update(got)


# --- pairs and ground truth ----------------------------------------------------------


def pairs_for(n: int, k: int) -> tuple[list[int], int]:
    starts = list(range(n - k)) if n > k else []
    total = len(starts)
    if total > MAX_PAIRS:
        step = total / MAX_PAIRS
        starts = [starts[int(i * step)] for i in range(MAX_PAIRS)]
    return starts, total


@dataclass
class Case:
    """One revision pair, ready to score."""

    doc: str
    k: int
    old: Rev
    new: Rev
    anchors: list
    after: A.After
    truth: dict  # id -> block index | "gone" | "xmove"
    dup_old: int
    dup_new: int
    # Where the ids are wrong about the block, filled by `repair` once the
    # similarity table exists: id -> (block index, "lost" | "relocated").
    repair: dict = field(default_factory=dict)
    start: int = 0  # index of the older revision among the document's stamped ones
    repair_contested: int = 0  # repairs dropped because another id claimed the block


def make_case(doc: Doc, k: int, old: Rev, new: Rev) -> Case:
    dup_old = {m for m, ix in old.ids.items() if len(ix) > 1}
    dup_new = {m for m, ix in new.ids.items() if len(ix) > 1}
    keep = set(old.ids) - dup_old
    truth: dict[str, object] = {}
    excluded_new = 0
    for mid in sorted(keep):
        if mid in new.ids:
            if mid in dup_new:
                excluded_new += 1
                continue
            truth[mid] = new.ids[mid][0]
        elif ids_elsewhere(new.commit, mid, new.path):
            truth[mid] = "xmove"
        else:
            truth[mid] = "gone"
    anchors = A.build_anchors(old.md, old.blocks, set(truth))
    after = A.build_after(new.md, new.blocks)
    return Case(doc.name, k, old, new, anchors, after, truth, len(dup_old), excluded_new)


def repair(case: Case, T: Table) -> None:
    """Find where the ids themselves are wrong about the block.

    Ids are kept by agents and a linter, and history shows two ways they fail
    while the block lives on. A **lost** id is gone from the document, yet one
    block scores at least NEAR against its old text. A **relocated** id survives
    on a block scoring under the §9 threshold (0.5) against its old text, the
    shape a paragraph inserted above a trailing marker leaves, while one block
    scores at least NEAR against that old text. Only blocks carrying no id that
    survived from the older revision are candidates (such a block is that id's),
    and the candidate must be the only one at NEAR or above. Repairs are
    one-to-one within a pair.

    Defined after the pre-registered scoring was first read, which is why both
    scorings are reported. `sanity.md` checks the repairs by hand."""
    owned = {t for t in case.truth.values() if isinstance(t, int)}
    free = [j for j in range(len(case.after.bodies)) if j not in owned]
    proposals: dict[int, list[tuple[float, str, str]]] = defaultdict(list)
    for a in case.anchors:
        t = case.truth[a.id]
        if t == "xmove":
            continue
        if isinstance(t, int):
            if case.after.hashes[t] == a.hash or T.get(a.nq, case.after.norms[t]) >= A.THRESHOLD:
                continue
            kind = "relocated"
        else:
            kind = "lost"
        near = [j for j in free if T.get(a.nq, case.after.norms[j]) >= NEAR]
        if len(near) == 1:
            proposals[near[0]].append((T.get(a.nq, case.after.norms[near[0]]), a.id, kind))
    # One-to-one: a block two ids reach goes to the one scoring highest against
    # it, and to neither on a tie, so the result does not depend on anchor order.
    for j, props in proposals.items():
        props.sort(reverse=True)
        if len(props) > 1 and props[0][0] == props[1][0]:
            case.repair_contested += len(props)
            continue
        case.repair_contested += len(props) - 1
        case.repair[props[0][1]] = (j, props[0][2])


def repaired_truth(case: Case) -> dict:
    """Ground truth with each repaired id pointed at the block that survived
    it. The pre-registered scoring takes the ids at their word; this one asks
    which block a reference meant, which is what the decision rule is about."""
    return {**case.truth, **{m: j for m, (j, _) in case.repair.items()}}


def wanted_keys(case: Case, T: Table) -> set[int]:
    out = set()
    for a in case.anchors:
        qa = T.intern(a.nq)
        la = len(a.nq)
        for c in case.after.norms:
            if c == a.nq or not c or not la:
                continue
            if 2 * min(la, len(c)) / (la + len(c)) < A.PRUNE:
                continue
            out.add((qa << 32) | T.intern(c))
    return out


# --- scoring -----------------------------------------------------------------------

CATS = ("correct", "missed", "wrong", "correct_detach", "false_attach", "xmove_detach", "xmove_attach")


def outcome(t, g) -> str:
    if t == "xmove":
        return "xmove_detach" if g is None else "xmove_attach"
    if t == "gone":
        return "correct_detach" if g is None else "false_attach"
    if g is None:
        return "missed"
    return "correct" if g == t else "wrong"


def events(case: Case, truth: dict, got: dict) -> list[tuple]:
    """One tuple per scored id: what was asked, what came back, how it scored.
    Blocks are keyed by their §8 hash, so the same question asked by two
    overlapping revision pairs is the same tuple."""
    h = case.after.hashes
    out = []
    for a in case.anchors:
        t, g = truth[a.id], got[a.id]
        out.append((
            case.doc, a.id, a.hash,
            h[t] if isinstance(t, int) else t,
            None if g is None else h[g],
            outcome(t, g),
        ))
    return out


def id_answers(case: Case) -> dict:
    """What the markers themselves say: tier 1 on the unstripped newer revision."""
    return {
        a.id: case.new.ids[a.id][0]
        if a.id in case.new.ids and len(case.new.ids[a.id]) == 1
        else None
        for a in case.anchors
    }


def all_answers(case: Case, T: Table) -> dict:
    """Every arm's answer for every anchor. `ids+ladder` is markstay as designed:
    the marker tier first, then the v1.10 ladder's hash and quote tiers for an
    id whose marker is gone (`ladder_v110.resolve` on the unstripped revision;
    `test_replay.py` checks the two agree)."""
    answers = {name: fn(case.anchors, case.after, T) for name, fn in A.ARMS.items()}
    return {MARKERS: id_answers(case), IDS_LADDER: ids_plus_ladder(case, answers["ladder"]), **answers}


def ids_plus_ladder(case: Case, ladder: dict) -> dict:
    """The marker's block where the marker survives, the ladder's answer where it
    is gone. A duplicated marker never reaches here: `make_case` excludes an id
    duplicated in either revision, so `id_answers`'s `[0]` is the only block."""
    markers = id_answers(case)
    return {mid: ladder[mid] if mid not in case.new.ids else g for mid, g in markers.items()}


def score_case(case: Case, T: Table) -> dict:
    """Per arm and truth, the event tuples for this pair. `markers only` is
    perfect under the pre-registered truth by construction."""
    truths = {"primary": case.truth, "repaired": repaired_truth(case)}
    answers = all_answers(case, T)
    return {
        name: {t: events(case, truth, got) for t, truth in truths.items()}
        for name, got in answers.items()
    }


def clopper_pearson(x: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact two-sided binomial interval, by bisection on the regularized
    incomplete beta function (stdlib only)."""
    if n == 0:
        return (0.0, 1.0)

    def ibeta(a: float, b: float, z: float) -> float:
        if z <= 0:
            return 0.0
        if z >= 1:
            return 1.0
        lbt = math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b) + a * math.log(z) + b * math.log(1 - z)
        if z < (a + 1) / (a + b + 2):
            return math.exp(lbt) * _betacf(a, b, z) / a
        return 1 - math.exp(lbt) * _betacf(b, a, 1 - z) / b

    def quantile(p: float, a: float, b: float) -> float:
        lo, hi = 0.0, 1.0
        for _ in range(200):
            mid = (lo + hi) / 2
            if ibeta(a, b, mid) < p:
                lo = mid
            else:
                hi = mid
        return (lo + hi) / 2

    lower = 0.0 if x == 0 else quantile(alpha / 2, x, n - x + 1)
    upper = 1.0 if x == n else quantile(1 - alpha / 2, x + 1, n - x)
    return (lower, upper)


def _betacf(a: float, b: float, z: float) -> float:
    tiny, eps = 1e-300, 3e-16
    qab, qap, qam = a + b, a + 1, a - 1
    c, d = 1.0, 1 - qab * z / qap
    d = tiny if abs(d) < tiny else d
    d = 1 / d
    h = d
    for m in range(1, 10000):
        m2 = 2 * m
        aa = m * (b - m) * z / ((qam + m2) * (a + m2))
        d = 1 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * z / ((a + m2) * (qap + m2))
        d = 1 + aa * d
        d = tiny if abs(d) < tiny else d
        c = 1 + aa / c
        c = tiny if abs(c) < tiny else c
        d = 1 / d
        de = d * c
        h *= de
        if abs(de - 1) < eps:
            break
    return h


def rates(c: Counter) -> dict:
    surv = c["correct"] + c["missed"] + c["wrong"]
    gone = c["correct_detach"] + c["false_attach"]
    mis = c["wrong"] + c["false_attach"]
    n = surv + gone
    out = {
        "n": n,
        "survivors": surv,
        "gone": gone,
        "xmove": c["xmove_detach"] + c["xmove_attach"],
        **{k: c[k] for k in CATS},
        "misattached": mis,
        "misattach_rate": mis / n if n else None,
        "misattach_ci": clopper_pearson(mis, n),
        "miss_rate": c["missed"] / surv if surv else None,
        "miss_ci": clopper_pearson(c["missed"], surv),
        "recovery": c["correct"] / surv if surv else None,
    }
    return out


# --- cost side ------------------------------------------------------------------------


def marker_bytes(md: str) -> tuple[int, int, int, int]:
    """(marker bytes, document bytes, marker-only lines, lines) at one revision."""
    stripped = A.strip_markers(md)
    text = md.replace("\r\n", "\n").replace("\r", "\n")
    return (
        len(text.encode()) - len(stripped.encode()),
        len(text.encode()),
        len(text.split("\n")) - len(stripped.split("\n")),
        len(text.split("\n")),
    )


def cost_history(doc: Doc, T: Table) -> tuple[dict, Counter]:
    """Per consecutive revision pair whose older side is stamped: what happened
    to every id that left, and how many ids were newly duplicated or minted.
    A block in the newer revision that carries an id surviving from the older one
    is that id's block, so it is never taken as the survivor of a different id."""
    c, edits_with = Counter(), Counter()
    edits = 0
    for old, new in zip(doc.revs, doc.revs[1:]):
        if not old.stamped:
            continue
        edits += 1
        e = Counter()
        findings = L.lint_diff(old.md, new.md)
        for f in findings:
            if f.code in ("DROPPED_ID", "DUPLICATED_ID", "ADOPTED_ID", "NEW_ID", "RELOCATED_ID"):
                e["lint_" + f.code] += 1
        adopted = {f.id for f in findings if f.code == "ADOPTED_ID"}
        dup_old = {m for m, ix in old.ids.items() if len(ix) > 1}
        for m, ix in new.ids.items():
            if len(ix) > 1 and m not in dup_old:
                e["newly_duplicated"] += 1
        kept = set(old.ids) & set(new.ids)
        free = [b for b in new.blocks if not (set(A.block_ids([b])) & kept)]
        free_hashes: dict[str, list] = {}
        for b in free:
            free_hashes.setdefault(L.body_hash(b.content), []).append(b)
        free_norms = [A.normalize(b.content) for b in free]
        for m, ix in old.ids.items():
            if m in dup_old or m not in new.ids or len(new.ids[m]) != 1:
                continue
            body = old.blocks[ix[0]].content
            now = new.blocks[new.ids[m][0]].content
            nq = A.normalize(body)
            if L.body_hash(body) == L.body_hash(now) or T.get(nq, A.normalize(now)) >= A.THRESHOLD:
                continue
            near = [b for b, nc in zip(free, free_norms) if T.get(nq, nc) >= NEAR]
            if len(near) == 1:
                e["relocated"] += 1
        for m, ix in old.ids.items():
            if m in new.ids or m in dup_old:
                continue
            if m in adopted:
                e["adopted"] += 1
                continue
            if ids_elsewhere(new.commit, m, new.path):
                e["xmove"] += 1
                continue
            body = old.blocks[ix[0]].content
            hits = free_hashes.get(L.body_hash(body), [])
            if hits:
                stamped = any(A.block_ids([b]) for b in hits)
                e["verbatim_reminted" if stamped else "verbatim_unstamped"] += 1
                e["lost_block_survives"] += 1
                continue
            nq = A.normalize(body)
            best, bj = 0.0, -1
            for j, nc in enumerate(free_norms):
                s = T.get(nq, nc)
                if s > best:
                    best, bj = s, j
            if best >= NEAR:
                stamped = bool(A.block_ids([free[bj]]))
                e["near_reminted" if stamped else "near_unstamped"] += 1
                e["lost_block_survives"] += 1
            else:
                e["removed"] += 1
        c.update(e)
        edits_with.update({k: 1 for k, v in e.items() if v})
    return {"edits": edits, **dict(c)}, edits_with


# --- sanity sample -----------------------------------------------------------------------


def sanity_pool(cases: list[Case]) -> tuple[list[dict], int, int]:
    """Distinct id correspondences whose block text changed between the two
    revisions. An unchanged one is the same block by construction."""
    seen, pool, total, unchanged = set(), [], 0, 0
    for case in cases:
        olds = {a.id: a for a in case.anchors}
        for mid, t in case.truth.items():
            if not isinstance(t, int):
                continue
            a = olds[mid]
            new_body = case.after.bodies[t]
            key = (case.doc, mid, a.hash, case.after.hashes[t])
            if key in seen:
                continue
            seen.add(key)
            total += 1
            if a.hash == case.after.hashes[t]:
                unchanged += 1
                continue
            old_body = case.old.blocks[case.old.ids[mid][0]].content
            pool.append(
                {
                    "key": f"{case.doc}#{mid}@{case.old.commit[:7]}..{case.new.commit[:7]}",
                    "doc": case.doc,
                    "id": mid,
                    "k": case.k,
                    "score": round(A.body_norm(a.nq, case.after.norms[t]), 3),
                    "old": old_body,
                    "new": new_body,
                }
            )
    return pool, total, unchanged


def repair_pool(cases: list[Case]) -> list[dict]:
    """Distinct repairs, for checking by hand that each repaired block is the
    one a reference held on the id meant."""
    seen, pool = set(), []
    for case in cases:
        olds = {a.id: a for a in case.anchors}
        for mid, (j, kind) in case.repair.items():
            a = olds[mid]
            key = (case.doc, mid, a.hash, case.after.hashes[j])
            if key in seen:
                continue
            seen.add(key)
            t = case.truth[mid]
            pool.append({
                "key": f"repair:{case.doc}#{mid}@{case.old.commit[:7]}..{case.new.commit[:7]}",
                "kind": kind,
                "k": case.k,
                "score": round(A.body_norm(a.nq, case.after.norms[j]), 3),
                "old": case.old.blocks[case.old.ids[mid][0]].content,
                "id_now": case.after.bodies[t] if isinstance(t, int) else None,
                "id_now_score": round(A.body_norm(a.nq, case.after.norms[t]), 3)
                if isinstance(t, int) else None,
                "repaired": case.after.bodies[j],
            })
    return pool


# --- report -----------------------------------------------------------------------------

TRUTHS = ("primary", "repaired")
TRUTH_LABEL = {
    "primary": "pre-registered truth (the ids at their word)",
    "repaired": "repaired truth (a lost or relocated id points at the block that survived it)",
}


def pct(x):
    return "n/a" if x is None else f"{100 * x:.2f}%"


def ci(t):
    return f"[{100 * t[0]:.2f}, {100 * t[1]:.2f}]"


def verdict(at20: dict) -> dict:
    """Apply the pre-registered rule to pooled k = 20 numbers, id-free arms only."""
    rows = {}
    for arm, r in at20.items():
        if arm in ID_ARMS or r["n"] == 0:
            continue
        point = r["misattach_rate"] <= MISATTACH_BAR and r["miss_rate"] <= MISS_BAR
        sure_pass = r["misattach_ci"][1] <= MISATTACH_BAR and r["miss_ci"][1] <= MISS_BAR
        sure_fail = r["misattach_ci"][0] > MISATTACH_BAR or r["miss_ci"][0] > MISS_BAR
        rows[arm] = {"point_pass": point, "ci_pass": sure_pass, "ci_fail": sure_fail}
    if not rows:
        call = "no-data"
    elif any(v["ci_pass"] for v in rows.values()):
        call = "ids-not-needed"
    elif all(v["ci_fail"] for v in rows.values()):
        call = "ids-pay"
    else:
        call = "inconclusive"
    return {"call": call, "arms": rows}


def _arm_table(w, pooled: dict) -> None:
    w("| arm | n | correct | missed | wrong | detach ok | false attach | misattached | 95% CI | missed | 95% CI | cross-file attached |")
    w("|---|--:|--:|--:|--:|--:|--:|--:|---|--:|---|--:|")
    for arm, r in pooled.items():
        w(
            f"| {arm} | {r['n']} | {r['correct']} | {r['missed']} | {r['wrong']} | "
            f"{r['correct_detach']} | {r['false_attach']} | {pct(r['misattach_rate'])} | "
            f"{ci(r['misattach_ci'])} | {pct(r['miss_rate'])} | {ci(r['miss_ci'])} | "
            f"{r['xmove_attach']}/{r['xmove']} |"
        )


def fenced(text: str) -> list[str]:
    """A text fence one backtick longer than any run inside `text`, so a quoted
    block that itself holds a fence cannot close it early."""
    longest = max((len(m) for m in re.findall(r"`+", text)), default=0)
    fence = "`" * max(4, longest + 1)
    return [fence + "text", text, fence]


def write_reports(
    res: dict, sanity: list[dict], repairs: list[dict], relocations: list[dict], judgments: dict
) -> None:
    (OUT / "results.json").write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    out = []
    w = out.append
    w("# History replay: results")
    w("")
    w(f"Generated by `replay.py` over the umbrella at `{res['rev'][:12]}`. Do not edit by hand.")
    w("Every id-free arm sees the older revision's stored evidence and the newer revision's")
    w("bodies with markers stripped. `markers only` is the marker tier on the unstripped")
    w("revision; `ids+ladder` is that tier with the shipped ladder behind it for ids whose")
    w("marker is gone, which is markstay as designed and the row the question turns on. Rates:")
    w("misattached = (wrong + false attach) over every scored id; missed = missed over")
    w("surviving ids. Intervals are 95% Clopper-Pearson and treat ids as independent, which")
    w("they are not (see `FINDINGS.md`). Cross-file moves are scored apart from both.")
    w("")
    w("## Corpus")
    w("")
    w(f"A revision is stamped when block ids cover at least {MIN_COVERAGE:.0%} of its content blocks.")
    w("")
    w("Markers inside an inline code span are quoted examples and are left out (`real_blocks`).")
    w("")
    w("| document | revisions | stamped | ids at first stamped | ids at last | child ids (not scored) | quoted markers, most at once |")
    w("|---|--:|--:|--:|--:|--:|--:|")
    for d in res["corpus"]:
        w(
            f"| `{d['doc']}` | {d['revisions']} | {d['marked']} | {d['ids_first']} | "
            f"{d['ids_last']} | {d['child_ids']} | {d['quoted_markers']} |"
        )
    if res["skipped"]:
        w("")
        w("Carry an id somewhere in their history but have fewer than two stamped revisions "
          "of their own (stamped / with any id): "
          + ", ".join(f"`{s['doc']}` ({s['marked_revisions']}/{s['revisions_with_any_id']})"
                      for s in res["skipped"]) + ".")
    w("")
    w("## Pairs")
    w("")
    w("| k | pairs | scored | ids | survivors | gone | repaired: lost | repaired: relocated | repairs dropped as contested | cross-file | dup ids excluded |")
    w("|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|--:|")
    for k in res["ks"]:
        p = res["pairs"][str(k)]
        w(
            f"| {k} | {p['available']} | {p['scored']} | {p['ids']} | {p['survivors']} | "
            f"{p['gone']} | {p['lost']} | {p['relocated']} | {p['repair_contested']} | {p['xmove']} | "
            f"{p['dup_old'] + p['dup_new']} |"
        )
    arms = ORDER
    w("")
    w("## Summary by gap")
    w("")
    w("Misattached / missed, pooled over every scored pair. `distinct` counts each")
    w("distinct (document, id, old text, truth block, answer) once. That is a different")
    w("population, not a correction for overlap: an unchanged block collapses to one")
    w("question however many pairs ask it, while every changed version of a block stays")
    w("separate, so it weights the hard cases. Read it as event counts.")
    for truth in TRUTHS:
        for kind in ("pooled", "distinct"):
            w("")
            w(f"{TRUTH_LABEL[truth].capitalize()}, {kind}:")
            w("")
            ks_with = [k for k in res["ks"] if res["pairs"][str(k)]["ids"]]
            w("| arm | " + " | ".join(f"k = {k}" for k in ks_with) + " |")
            w("|---|" + "---|" * len(ks_with))
            for arm in arms:
                cells = []
                for k in ks_with:
                    r = res[kind][truth][str(k)][arm]
                    cells.append(f"{pct(r['misattach_rate'])} / {pct(r['miss_rate'])}")
                w(f"| {arm} | " + " | ".join(cells) + " |")
    for truth in TRUTHS:
        for kind in ("pooled", "distinct"):
            w("")
            w(f"## {kind.capitalize()}, {TRUTH_LABEL[truth]}")
            for k in res["ks"]:
                table = res[kind][truth][str(k)]
                w("")
                w(f"### k = {k}")
                w("")
                if not any(r["n"] for r in table.values()):
                    w("No document has enough stamped revisions for this gap.")
                    continue
                _arm_table(w, table)
    for truth in TRUTHS:
        w("")
        w(f"## Per document, k = 20, {truth} truth")
        w("")
        w("Misattached / missed per arm, so no one large file carries the pooled number.")
        w("")
        w("| document | ids | " + " | ".join(arms) + " |")
        w("|---|--:|" + "---|" * len(arms))
        for doc, by_arm in res["per_doc"][truth].get("20", {}).items():
            n = by_arm["ladder"]["n"]
            if not n:
                continue
            cells = [f"{pct(by_arm[a]['misattach_rate'])} / {pct(by_arm[a]['miss_rate'])}" for a in arms]
            w(f"| `{doc}` | {n} | " + " | ".join(cells) + " |")
        w("")
        w(f"Pooled k = 20 without `{res['largest_doc_20']}`, the document contributing the most ids:")
        w("")
        w("| arm | n | misattached | 95% CI | missed | 95% CI |")
        w("|---|--:|--:|---|--:|---|")
        for arm, r in res["pooled_without_largest_20"][truth].items():
            w(f"| {arm} | {r['n']} | {pct(r['misattach_rate'])} | {ci(r['misattach_ci'])} | "
              f"{pct(r['miss_rate'])} | {ci(r['miss_ci'])} |")
    w("")
    w("## Decision rule at k = 20")
    w("")
    w(f"Bars: misattached at most {MISATTACH_BAR:.0%}, missed at most {MISS_BAR:.0%}. "
      "`ids-not-needed` needs one id-free arm whose interval sits inside both bars; "
      "`ids-pay` needs every id-free arm's interval outside at least one; anything else "
      "is `inconclusive`.")
    for truth in TRUTHS:
        v = res["verdict"][truth]
        w("")
        w(f"{TRUTH_LABEL[truth].capitalize()}: **{v['call']}**.")
        w("")
        w("| arm | passes on point estimate | passes on interval | fails on interval |")
        w("|---|---|---|---|")
        for arm, r in v["arms"].items():
            w(f"| {arm} | {r['point_pass']} | {r['ci_pass']} | {r['ci_fail']} |")
    w("")
    w("### Disjoint windows")
    w("")
    w("Pairs at k = 20 overlap: neighbouring pairs share 19 of their 20 edits, so the")
    w("intervals above are far too narrow. Here the k = 20 pairs are split by start offset")
    w("modulo 20, giving 20 subsamples in which no two pairs share an edit. For each arm:")
    w("how many offsets pass both bars on the point estimate and on the interval, and the")
    w("range of the two rates across offsets.")
    for truth in TRUTHS:
        w("")
        w(f"{TRUTH_LABEL[truth].capitalize()}:")
        w("")
        w("| arm | offsets | pass (point) | pass (interval) | misattached, min to max | missed, min to max | ids per offset |")
        w("|---|--:|--:|--:|---|---|---|")
        for arm, rows in res["disjoint"].get(truth, {}).items():
            rows = [r for r in rows if r["n"]]
            if not rows:
                continue
            pp = sum(r["misattach_rate"] <= MISATTACH_BAR and r["miss_rate"] <= MISS_BAR for r in rows)
            pi = sum(r["misattach_ci"][1] <= MISATTACH_BAR and r["miss_ci"][1] <= MISS_BAR for r in rows)
            mr = [r["misattach_rate"] for r in rows]
            ms = [r["miss_rate"] for r in rows]
            ns = [r["n"] for r in rows]
            w(f"| {arm} | {len(rows)} | {pp} | {pi} | {pct(min(mr))} to {pct(max(mr))} | "
              f"{pct(min(ms))} to {pct(max(ms))} | {min(ns)} to {max(ns)} |")
    w("")
    w("## Id survival by gap")
    w("")
    w("| k | ids | same id k revisions later | gone | lost (block survives) | relocated | cross-file |")
    w("|--:|--:|--:|--:|--:|--:|--:|")
    for k in res["ks"]:
        p = res["pairs"][str(k)]
        if p["ids"]:
            w(f"| {k} | {p['ids']} | {pct(p['survivors'] / p['ids'])} | {pct(p['gone'] / p['ids'])} | "
              f"{pct(p['lost'] / p['ids'])} | {pct(p['relocated'] / p['ids'])} | {pct(p['xmove'] / p['ids'])} |")
    w("")
    w("## Cost")
    w("")
    w(f"Marker bytes at `{res['rev'][:12]}`, for documents stamped there:")
    w("")
    w("| document | marker bytes | document bytes | share | marker-only lines | lines |")
    w("|---|--:|--:|--:|--:|--:|")
    for row in res["cost"]["bytes"]:
        w(f"| `{row['doc']}` | {row['marker_bytes']} | {row['bytes']} | {pct(row['share'])} | "
          f"{row['marker_lines']} | {row['lines']} |")
    w("")
    w("What happened to ids over every consecutive revision pair whose older side is")
    w("stamped. An edit is one commit touching the document. `removed`: the block went")
    w(f"too (no block in the newer revision scores {NEAR} or more against it). `verbatim` /")
    w(f"`near`: the block survived byte-for-byte / at {NEAR}+ but lost the id, and either got a")
    w("fresh one (`reminted`) or none (`unstamped`). `relocated`: the id stayed but now sits on")
    w("a block scoring under 0.5 against its old text, while its old text survives on one")
    w(f"unclaimed block at {NEAR}+ (the `repair` rule). `lost_block_survives` sums the four")
    w("`verbatim` / `near` columns. `lint_*` are `lint_diff`'s own counts.")
    w("")
    keys = [
        "relocated", "lost_block_survives", "removed", "xmove", "adopted", "verbatim_reminted", "verbatim_unstamped",
        "near_reminted", "near_unstamped", "newly_duplicated",
        "lint_DROPPED_ID", "lint_DUPLICATED_ID", "lint_RELOCATED_ID", "lint_NEW_ID",
    ]
    w("| document | edits | " + " | ".join(keys) + " |")
    w("|---|--:|" + "--:|" * len(keys))
    for row in res["cost"]["history"]:
        w(f"| `{row['doc']}` | {row['edits']} | " + " | ".join(str(row.get(k, 0)) for k in keys) + " |")
    t = res["cost"]["history_total"]
    w(f"| **all** | {t['edits']} | " + " | ".join(str(t.get(k, 0)) for k in keys) + " |")
    e = max(t["edits"], 1)
    w("| **per 100 edits** | 100 | " + " | ".join(f"{100 * t.get(k, 0) / e:.1f}" for k in keys) + " |")
    w("")
    w("Edits with at least one such event, out of all edits: "
      + ", ".join(f"{k} {v}" for k, v in sorted(res["cost"]["edits_with"].items())) + ".")
    (OUT / "results.md").write_text("\n".join(out) + "\n")

    s = ["# History replay: ground-truth sanity sample", ""]
    s.append(
        f"{SANITY_N} id correspondences drawn (seed {SEED}) from the "
        f"{res['sanity']['changed']} distinct ones whose block text changed between the two "
        f"revisions. The other {res['sanity']['unchanged']} of {res['sanity']['total']} "
        "distinct correspondences are byte-identical, the same block by construction. Each "
        "pair is judged by hand in `sanity_judgments.json`: is the newer block plausibly the "
        "same logical block as the older one?"
    )
    s.append("")
    counts = Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in sanity)
    s.append("Judged: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=str)) + ".")
    for i, x in enumerate(sanity, 1):
        j = judgments.get(x["key"], {})
        s += ["", f"## {i}. `{x['key']}`", ""]
        s.append(f"k = {x['k']}, body score {x['score']}. Same block: **{j.get('same', 'unjudged')}**."
                 + (f" {j['note']}" if j.get("note") else ""))
        for label, body in (("Older", x["old"]), ("Newer", x["new"])):
            text = body if len(body) <= 900 else body[:900] + "\n[...]"
            s += ["", f"{label}:", "", *fenced(text)]
    s += ["", "# Repairs", ""]
    s.append(
        f"{len(repairs)} of the {res['sanity']['repairs']} distinct repairs (seed {SEED}). "
        "Same question: is the repaired block the one a reference held on the id meant? "
        "For a relocated id, the block the id sits on now is shown too."
    )
    s.append("")
    counts = Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in repairs)
    s.append("Judged: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=str)) + ".")
    for i, x in enumerate(repairs, 1):
        s += _repair_entry(f"R{i}", x, judgments)
    s += ["", "# Every relocation", ""]
    s.append(
        f"All {len(relocations)} distinct relocations, sampled or not, because a relocation is "
        "where the ids are wrong and the arms right, so each one carries weight. The id-now "
        "score is the id's current block against its old text (0.0 means under the 0.35 floor "
        "below which scores are not computed)."
    )
    s.append("")
    counts = Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in relocations)
    s.append("Judged: " + ", ".join(f"{k} {v}" for k, v in sorted(counts.items(), key=str)) + ".")
    for i, x in enumerate(relocations, 1):
        s += _repair_entry(f"L{i}", x, judgments)
    (OUT / "sanity.md").write_text("\n".join(s) + "\n")


def _repair_entry(label: str, x: dict, judgments: dict) -> list[str]:
    j = judgments.get(x["key"], {})
    out = ["", f"## {label}. `{x['key']}` ({x['kind']})", ""]
    now = f", id-now block scores {x['id_now_score']}" if x["id_now"] is not None else ""
    out.append(f"k = {x['k']}, repaired block scores {x['score']}{now}. "
               f"Right block: **{j.get('same', 'unjudged')}**." + (f" {j['note']}" if j.get("note") else ""))
    shown = [("Older", x["old"]), ("Repaired to", x["repaired"])]
    if x["id_now"] is not None:
        shown.append(("Id now sits on", x["id_now"]))
    for name, body in shown:
        text = body if len(body) <= 900 else body[:900] + "\n[...]"
        out += ["", f"{name}:", "", *fenced(text)]
    return out


def misattachments(case: Case, got_by_arm: dict, repaired: dict) -> list[dict]:
    """Every misattachment under the repaired truth, for reading rather than
    counting. Written only with --dump."""
    out = []
    olds = {a.id: a for a in case.anchors}
    for arm, got in got_by_arm.items():
        for mid, g in got.items():
            t = repaired[mid]
            if g is None or g == t or t == "xmove":
                continue
            a = olds[mid]
            out.append({
                "doc": case.doc, "k": case.k, "arm": arm, "id": mid,
                "old": case.old.commit[:7], "new": case.new.commit[:7],
                "truth": t if isinstance(t, str) else "block",
                "score": round(A.body_norm(a.nq, case.after.norms[g]), 3),
                "old_text": case.old.blocks[case.old.ids[mid][0]].content[:300],
                "got_text": case.after.bodies[g][:300],
                "truth_text": case.after.bodies[t][:300] if isinstance(t, int) else None,
            })
    return out


# --- main --------------------------------------------------------------------------------


def run(rev: str, ks: tuple[int, ...], jobs: int, dump: str | None = None) -> None:
    rev = git("rev-parse", rev).strip()
    docs, skipped = load_corpus(rev)
    print(f"corpus: {len(docs)} documents at {rev[:12]}", file=sys.stderr)
    T = Table()

    cases_by_k: dict[int, list[Case]] = {}
    pair_meta = {}
    for k in ks:
        cases, avail, scored = [], 0, 0
        for d in docs:
            starts, total = pairs_for(len(d.marked), k)
            avail += total
            scored += len(starts)
            for i in starts:
                case = make_case(d, k, d.marked[i], d.marked[i + k])
                case.start = i
                cases.append(case)
        cases_by_k[k] = cases
        pair_meta[k] = (avail, scored)

    wanted = set()
    for cases in cases_by_k.values():
        for case in cases:
            wanted |= wanted_keys(case, T)
    print(f"similarity table: {len(wanted)} pairs", file=sys.stderr)
    T.fill(wanted, jobs)
    for cases in cases_by_k.values():
        for case in cases:
            repair(case, T)

    res = {"rev": rev, "ks": list(ks), "arms": ORDER, "skipped": skipped,
           "min_coverage": MIN_COVERAGE, "max_pairs": MAX_PAIRS}
    res["corpus"] = [
        {
            "doc": d.name,
            "revisions": len(d.revs),
            "marked": len(d.marked),
            "ids_first": len(d.marked[0].ids),
            "ids_last": len(d.marked[-1].ids),
            "child_ids": max(r.child_ids for r in d.revs),
            "quoted_markers": max(r.quoted for r in d.revs),
            "shared_dropped": d.shared_dropped,
        }
        for d in docs
    ]
    res["pooled"] = {t: {} for t in TRUTHS}
    res["distinct"] = {t: {} for t in TRUTHS}
    res["disjoint"] = {t: {} for t in TRUTHS}
    res["per_doc"] = {t: {} for t in TRUTHS}
    res["pairs"] = {}
    k20 = {t: {} for t in TRUTHS}
    dumped = []
    for k in ks:
        pooled = {t: defaultdict(Counter) for t in TRUTHS}
        per_doc = {t: defaultdict(lambda: defaultdict(Counter)) for t in TRUTHS}
        distinct = {t: defaultdict(set) for t in TRUTHS}
        by_offset = {t: defaultdict(lambda: defaultdict(Counter)) for t in TRUTHS}
        meta = Counter()
        for case in cases_by_k[k]:
            got = score_case(case, T)
            for arm, by_truth in got.items():
                for t, evs in by_truth.items():
                    c = Counter(e[-1] for e in evs)
                    pooled[t][arm].update(c)
                    per_doc[t][case.doc][arm].update(c)
                    distinct[t][arm].update(evs)
                    by_offset[t][case.start % k][arm].update(c)
            if dump and k == 20:
                answers = all_answers(case, T)
                dumped += misattachments(case, answers, repaired_truth(case))
            meta["ids"] += len(case.anchors)
            meta["survivors"] += sum(isinstance(t, int) for t in case.truth.values())
            meta["gone"] += sum(t == "gone" for t in case.truth.values())
            meta["lost"] += sum(kind == "lost" for _, kind in case.repair.values())
            meta["relocated"] += sum(kind == "relocated" for _, kind in case.repair.values())
            meta["repair_contested"] += case.repair_contested
            meta["xmove"] += sum(t == "xmove" for t in case.truth.values())
            meta["dup_old"] += case.dup_old
            meta["dup_new"] += case.dup_new
        avail, scored = pair_meta[k]
        res["pairs"][str(k)] = {"available": avail, "scored": scored, **{
            x: meta[x] for x in ("ids", "survivors", "gone", "lost", "relocated", "repair_contested",
                               "xmove", "dup_old", "dup_new")}}
        order = ORDER
        for t in TRUTHS:
            res["pooled"][t][str(k)] = {a: rates(pooled[t][a]) for a in order}
            res["distinct"][t][str(k)] = {
                a: rates(Counter(e[-1] for e in distinct[t][a])) for a in order
            }
            res["per_doc"][t][str(k)] = {
                doc: {a: rates(by_arm[a]) for a in order} for doc, by_arm in sorted(per_doc[t].items())
            }
            if k == 20:
                k20[t] = per_doc[t]
                res["disjoint"][t] = {
                    a: [{"offset": o, **rates(by_offset[t][o][a])} for o in sorted(by_offset[t])]
                    for a in order
                }
        print(f"k={k}: {scored} pairs", file=sys.stderr)

    counts = k20["primary"]
    largest = max(counts, key=lambda d: sum(counts[d]["ladder"].values()), default=None)
    res["largest_doc_20"] = largest
    res["pooled_without_largest_20"] = {}
    res["verdict"] = {}
    for t in TRUTHS:
        rest = defaultdict(Counter)
        for doc, by_arm in k20[t].items():
            if doc != largest:
                for a, c in by_arm.items():
                    rest[a].update(c)
        res["pooled_without_largest_20"][t] = {a: rates(rest[a]) for a in ORDER}
        res["verdict"][t] = verdict(res["pooled"][t].get("20", {}))

    by_bytes = []
    for d in docs:
        head = show(rev, d.name)
        if head is None or not parse_rev(rev, d.name).stamped:
            continue
        mb, b, ml, ln = marker_bytes(head)
        by_bytes.append({"doc": d.name, "marker_bytes": mb, "bytes": b, "share": mb / b if b else 0,
                         "marker_lines": ml, "lines": ln})
    tot = {k: sum(r[k] for r in by_bytes) for k in ("marker_bytes", "bytes", "marker_lines", "lines")}
    by_bytes.append({"doc": "all", **tot, "share": tot["marker_bytes"] / tot["bytes"] if tot["bytes"] else 0})
    hist, edits_with = [], Counter()
    for d in docs:
        row, ew = cost_history(d, T)
        hist.append({"doc": d.name, **row})
        edits_with.update(ew)
    total = Counter()
    for row in hist:
        total.update({k: v for k, v in row.items() if k != "doc"})
    res["cost"] = {"bytes": by_bytes, "history": hist, "history_total": dict(total),
                   "edits_with": dict(edits_with)}

    all_cases = [c for k in ks for c in cases_by_k[k]]
    pool, n_total, n_unch = sanity_pool(all_cases)
    rng = random.Random(SEED)
    sample = sorted(rng.sample(pool, min(SANITY_N, len(pool))), key=lambda x: x["key"])
    rpool = repair_pool(all_cases)
    rsample = sorted(rng.sample(rpool, min(REPAIR_N, len(rpool))), key=lambda x: x["key"])
    res["sanity"] = {"total": n_total, "unchanged": n_unch, "changed": len(pool),
                     "sample": [x["key"] for x in sample], "repairs": len(rpool),
                     "repairs_by_kind": dict(Counter(x["kind"] for x in rpool)),
                     "repair_sample": [x["key"] for x in rsample]}
    jpath = OUT / "sanity_judgments.json"
    judgments = json.loads(jpath.read_text()) if jpath.exists() else {}
    res["sanity"]["judged"] = dict(Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in sample))
    res["sanity"]["repairs_judged"] = dict(
        Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in rsample))
    relocations = sorted((x for x in rpool if x["kind"] == "relocated"), key=lambda x: x["key"])
    res["sanity"]["relocations"] = [x["key"] for x in relocations]
    res["sanity"]["relocations_judged"] = dict(
        Counter(judgments.get(x["key"], {}).get("same", "unjudged") for x in relocations))
    write_reports(res, sample, rsample, relocations, judgments)
    if dump:
        Path(dump).write_text(json.dumps(dumped, indent=1) + "\n")
    print("verdict: " + ", ".join(f"{t} {res['verdict'][t]['call']}" for t in TRUTHS), file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--rev", help=f"commit to read the corpus at (default {CORPUS_REV[:12]}, or HEAD with --root)")
    ap.add_argument("--root", help="another repository to replay (needs --out)")
    ap.add_argument("--glob", action="append", help="path glob selecting its documents, repeatable")
    ap.add_argument("--out", help="directory for results.{json,md} and sanity.md")
    ap.add_argument("--ks", default=",".join(map(str, KS)))
    ap.add_argument("--jobs", type=int, default=max(1, (mp.cpu_count() or 2) - 2))
    ap.add_argument("--dump", help="write every k = 20 misattachment (repaired truth) here as JSON")
    args = ap.parse_args()
    if args.root and not args.out:
        ap.error("--root needs --out, so another repository's results never land here")
    configure(args.root, args.glob, args.out)
    if args.out:
        Path(args.out).mkdir(parents=True, exist_ok=True)
    run(args.rev or (CORPUS_REV if not args.root else "HEAD"), tuple(int(x) for x in args.ks.split(",")), args.jobs, args.dump)
    return 0


if __name__ == "__main__":
    sys.exit(main())
