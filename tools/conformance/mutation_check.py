#!/usr/bin/env python3
"""Does the `resolve` corpus actually bite?

`run_py.py` asks "does the reference still agree with the corpus". This asks the
question that matters for an interop standard: **would a plausible second
implementation of SPEC.md §9 be caught?** A vector nothing can fail is
decoration, which is the failure this whole repair started from (see
SPEC_DECISIONS.md, "What pinning the QUOTE tier settled").

Each mutation below is a reading of §9 a competent implementer could arrive at
honestly, or an off-by-one an implementer could make. The check runs the whole
`resolve` corpus against each and reports which vectors catch it. An uncaught
mutation is a missing vector, not a bug here.

What this proves, and what it does not
--------------------------------------
`resolve_variant` reimplements the §9.1 ladder so the mutations are parameters
rather than edits to production code. That is a second implementation and it can
drift, so two things guard it: `--differential` compares the unmutated variant
against `resolver.resolve` over generated document pairs, and the `baseline` case
requires it to reproduce every frozen vector.

Both are agreement checks, not equivalence proofs. The variant borrows the
reference's normalization, similarity, context scoring, parsing and hashing, so a
bug inside a shared helper would leave the reference, the generator and this file
all agreeing and all wrong. Catching *that* is what the JS and Rust
implementations are for; this file's scope is the ladder and the commit rule
built on top of those helpers.

Not vendored into the published mirrors: it checks the corpus, not an
implementation, so it belongs to the canonical tree only.

Exit status is 0 when every mutation behaves as declared and the baseline is
clean.

Run:  python3 conformance/mutation_check.py [--verbose] [--differential]
"""

from __future__ import annotations

import json
import random
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "linter"))
sys.path.insert(0, str(ROOT / "eval" / "attachment"))
sys.path.insert(0, str(ROOT / "impl" / "py" / "src"))
sys.path.insert(0, str(HERE))

import markstay_lint as L  # noqa: E402
import quote as Q  # noqa: E402
import resolver as R  # noqa: E402

TOL = 1e-9


def load() -> list[tuple[str, dict]]:
    out = []
    for tier in ("spec", "gen"):
        data = json.loads((HERE / tier / "resolve.json").read_text())
        for v in data["vectors"]:
            out.append((tier, v))
    return out


# --- the scoring stack, with §9's choices exposed -------------------------

def _unicode_normalize(text: str) -> str:
    """§9 pins an ASCII fold precisely so implementations agree. This is the
    Unicode fold an implementer reaches for when they do not read that far."""
    return re.sub(r"\s+", " ", text.strip()).casefold()


def _norm(text: str, unicode_fold: bool) -> str:
    return _unicode_normalize(text) if unicode_fold else Q.normalize(text)


def body_score_variant(quote: str, candidate: str, *, containment_floor: bool,
                       unicode_fold: bool, normalize_sides: str = "both") -> float:
    q = _norm(quote, unicode_fold) if normalize_sides in ("both", "quote") else quote
    c = (_norm(candidate, unicode_fold)
         if normalize_sides in ("both", "candidate") else candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    base = Q._ratio(q, c)
    if containment_floor:
        short, long = (q, c) if len(q) <= len(c) else (c, q)
        if short and short in long:
            base = max(base, len(short) / len(long))
    return base


def context_bonus_variant(sel, prev_text: str, next_text: str, *, sides: str,
                          window: int, unicode_fold: bool,
                          weight: float = 0.05,
                          window_stored: bool = True) -> float:
    """`window_stored` is the match-time half of §9's 48-character limit: the
    reference windows BOTH sides, so a selector carrying more than §9 allows
    (built by a pre-v1.2 tool, or assembled by a consumer) is scored against the
    same amount of text as one that conforms. Setting it False is the pre-fix
    asymmetry, where only the candidate side was cut."""
    pfx = sel.prefix[-window:] if window_stored else sel.prefix
    sfx = sel.suffix[:window] if window_stored else sel.suffix
    bonus = 0.0
    if sel.prefix and sides in ("both", "prefix"):
        bonus += weight * Q._ratio(_norm(pfx, unicode_fold),
                                   _norm(prev_text[-window:], unicode_fold))
    if sel.suffix and sides in ("both", "suffix"):
        bonus += weight * Q._ratio(_norm(sfx, unicode_fold),
                                   _norm(next_text[:window], unicode_fold))
    return bonus


def anchors_variant(document: str, *, store_whole_neighbour: bool = False,
                    window: int = Q.CONTEXT_CHARS, **_ignored) -> list[dict]:
    """What a producer STORES, under the same mutation vocabulary.

    Separate from `resolve_variant` because the two corpora answer different
    questions and a producer defect can be invisible to the resolve one: with the
    match-time guard above, an implementation storing whole neighbour blocks
    resolves exactly like a conforming one. §9 constrains the stored field, so
    the `anchors` category is where that mutation is caught."""
    blocks = [b for b in L.parse_document(document) if b.index >= 0]
    out: list[dict] = []
    for i, b in enumerate(blocks):
        prev = blocks[i - 1].content if i > 0 else ""
        nxt = blocks[i + 1].content if i + 1 < len(blocks) else ""
        pfx, sfx = (prev, nxt) if store_whole_neighbour else (prev[-window:], nxt[:window])
        for mk in b.markers:
            if mk.id and not mk.malformed:
                out.append({"id": mk.id, "hash": L.body_hash(b.content),
                            "quote": b.content, "prefix": pfx, "suffix": sfx})
    return out


def resolve_variant(before: str, after: str, threshold: float, margin: float, *,
                    rank: str = "aggregate", guard: str = "aggregate",
                    guard_clamp: bool = True, report_clamp: bool = True,
                    store_whole_neighbour: bool = False, window_stored: bool = True,
                    unclamp_exact_ties: bool = False,
                    containment_floor: bool = True,
                    min_candidates: int = 1, tie_order: str = "later",
                    threshold_op: str = ">=", margin_op: str = ">=",
                    context_sides: str = "both", window: int = Q.CONTEXT_CHARS,
                    hash_ambiguity: str = "fall-through",
                    unicode_fold: bool = False, bonus_weight: float = 0.05,
                    bonus_tiebreak_only: float | None = None,
                    normalize_sides: str = "both") -> dict:
    """The §9.1 ladder with each contested choice exposed as a parameter.

    Defaults reproduce the reference exactly; every non-default is a mutation.
    """
    anchors = R.build_anchors(before)
    if store_whole_neighbour:
        stored = {a["id"]: a for a in anchors_variant(before, store_whole_neighbour=True)}
        anchors = [
            R.Anchor(id=a.id, hash=a.hash,
                     selector=Q.Selector(quote=a.selector.quote,
                                         prefix=stored[a.id]["prefix"],
                                         suffix=stored[a.id]["suffix"]))
            for a in anchors
        ]
    after_blocks = [b for b in L.parse_document(after) if b.index >= 0]
    bodies = [b.content for b in after_blocks]

    surviving: dict[str, int] = {}
    for i, b in enumerate(after_blocks):
        for mk in b.markers:
            # SPEC.md §16: a marker carrying the exact `subhash` key is never the
            # stay of the block containing it, so MARKER-tier lookup must not see
            # it. Without this the ladder binds a child's id to its container: a
            # confident, silent bind to the wrong block, which is the failure the
            # rule is mandatory for. Block markers are still lexically present on
            # `b.markers`; the filter is about attribution, not retention.
            if mk.id and not mk.malformed and not mk.has_subhash:
                surviving.setdefault(mk.id, i)
    hash_to_idx: dict[str, list[int]] = {}
    for i, body in enumerate(bodies):
        hash_to_idx.setdefault(L.body_hash(body), []).append(i)

    ge = (lambda a, b: a >= b) if threshold_op == ">=" else (lambda a, b: a > b)
    ge_m = (lambda a, b: a >= b) if margin_op == ">=" else (lambda a, b: a > b)

    out: dict[str, dict] = {}
    for a in anchors:
        if a.id in surviving:
            out[a.id] = {"method": "marker", "target": surviving[a.id], "score": 1.0}
            continue
        hits = hash_to_idx.get(a.hash, [])
        # §9.1 tier 2 needs a UNIQUE hit; taking the first of several is the
        # reading that turns an ambiguous hash into a confident attachment.
        if len(hits) == 1 or (hits and hash_ambiguity == "first-hit"):
            out[a.id] = {"method": "hash", "target": hits[0], "score": 1.0}
            continue

        sel = a.selector
        body = [body_score_variant(sel.quote, c, containment_floor=containment_floor,
                                   unicode_fold=unicode_fold,
                                   normalize_sides=normalize_sides) for c in bodies]
        agg = []
        for i in range(len(bodies)):
            prev = bodies[i - 1] if i > 0 else ""
            nxt = bodies[i + 1] if i + 1 < len(bodies) else ""
            agg.append(body[i] + context_bonus_variant(
                sel, prev, nxt, sides=context_sides, window=window,
                unicode_fold=unicode_fold, weight=bonus_weight,
                window_stored=window_stored))
        if bonus_tiebreak_only is not None and body:
            # §9 says the bonus "breaks near-ties" and is "not a primary key".
            # Read literally, that licenses applying it ONLY where the body
            # scores are already within epsilon of the leader, rather than
            # additively to every candidate as the reference does.
            top = max(body)
            agg = [agg[i] if abs(bs - top) <= bonus_tiebreak_only else bs
                   for i, bs in enumerate(body)]

        if not agg or len(agg) < min_candidates:
            out[a.id] = {"method": "detached", "target": None,
                         "score": min(max(agg), 1.0) if agg else 0.0}
            continue

        def order(scores):
            pairs = [(s, i) for i, s in enumerate(scores)]
            # reverse-sorting (score, index) puts the LATER index first on an
            # exact tie, which conformance spec/score.json requires.
            pairs.sort(reverse=(tie_order == "later"))
            if tie_order != "later":
                pairs.sort(key=lambda p: (-p[0], p[1]))
            return pairs

        agg_order = order(agg)
        cap_r = (lambda x: min(x, 1.0)) if report_clamp else (lambda x: x)
        # §9 says the bonus breaks near-ties "between structurally identical
        # blocks". Read narrowly, that licenses lifting the clamp ONLY when the
        # body scores really are identical (an exact match, 1.0), which is where
        # the clamp provably defeats the mechanism, and keeping it everywhere else,
        # which is where lifting it turns a correct detach into a false attachment
        # on merely near-duplicate text.
        exact_tie = bool(body) and max(body) >= 1.0
        clamp_guard = guard_clamp and not (unclamp_exact_ties and exact_tie)
        cap_g = (lambda x: min(x, 1.0)) if clamp_guard else (lambda x: x)
        reported = cap_r(agg_order[0][0])

        gate = agg_order if guard == "aggregate" else order(body)
        idx = (agg_order if rank == "aggregate" else order(body))[0][1]
        best = cap_g(gate[0][0])
        runner = cap_g(gate[1][0]) if len(gate) > 1 else 0.0

        if ge(best, threshold) and ge_m(best - runner, margin):
            out[a.id] = {"method": "quote", "target": idx, "score": reported}
        else:
            out[a.id] = {"method": "detached", "target": None, "score": reported}
    return out


def check(vectors, *, default_threshold: float = R.DEFAULT_THRESHOLD,
          default_margin: float = R.DEFAULT_MARGIN, **kw) -> list[str]:
    """Run the corpus against one mutation; return the vectors it fails.

    A vector that omits `threshold`/`margin` asserts the implementation's own
    defaults, so those are exactly the vectors a wrong constant reaches."""
    failed = []
    for tier, v in vectors:
        t = v["threshold"] if "threshold" in v else default_threshold
        m = v["margin"] if "margin" in v else default_margin
        got = resolve_variant(v["before"], v["after"], t, m, **kw)
        want = v["resolutions"]
        ok = got.keys() == want.keys() and all(
            got[k]["method"] == want[k]["method"]
            and got[k]["target"] == want[k]["target"]
            and abs(got[k]["score"] - want[k]["score"]) < TOL
            for k in want)
        if not ok:
            failed.append(f"{tier}:{v['name']}")
    return failed


def load_score() -> list[tuple[str, dict]]:
    """The `context_bonus` vectors from the `score` category, which score a
    stored selector directly rather than through a document."""
    out = []
    for tier in ("spec", "gen"):
        path = HERE / tier / "score.json"
        if not path.exists():
            continue
        for v in json.loads(path.read_text())["vectors"]:
            if v.get("fn") == "context_bonus":
                out.append((tier, v))
    return out


def check_score(vectors, *, window: int = Q.CONTEXT_CHARS, unicode_fold: bool = False,
                context_sides: str = "both", bonus_weight: float = 0.05,
                window_stored: bool = True, **_ignored) -> list[str]:
    """Run the context-bonus vectors against one mutation.

    This is the only corpus that scores a selector the resolver did not build,
    so it is the only one that can see the match-time window on the stored side."""
    failed = []
    for tier, v in vectors:
        sel = Q.Selector(quote="q", prefix=v["prefix"], suffix=v["suffix"])
        got = context_bonus_variant(sel, v["prev"], v["next"], sides=context_sides,
                                    window=window, unicode_fold=unicode_fold,
                                    weight=bonus_weight, window_stored=window_stored)
        if abs(got - v["bonus"]) >= TOL:
            failed.append(f"{tier}:{v.get('name', 'context_bonus')}")
    return failed


def load_anchors() -> list[tuple[str, dict]]:
    """The `anchors` category, which asserts what a producer stores rather than
    what the resolver decides."""
    out = []
    for tier in ("spec", "gen"):
        path = HERE / tier / "anchors.json"
        if not path.exists():
            continue
        for v in json.loads(path.read_text())["vectors"]:
            out.append((tier, v))
    return out


def check_anchors(vectors, **kw) -> list[str]:
    """Run the anchors corpus against one mutation; return the vectors it fails.

    Mutations that only change the resolver are inert here by construction, and
    that asymmetry is the point: it is what lets the table below state which
    corpus catches which defect instead of implying one corpus catches all."""
    failed = []
    for tier, v in vectors:
        if anchors_variant(v["document"], **kw) != v["anchors"]:
            failed.append(f"{tier}:{v['name']}")
    return failed


MUTATIONS = [
    # --- what the commit rule reads ---------------------------------------
    ("gate the commit rule on body score, keeping aggregate ranking",
     {"guard": "body"}, "caught"),
    ("rank AND gate on body score, treating context as a later tiebreak",
     {"rank": "body", "guard": "body"}, "caught"),
    ("apply the guard to unclamped scores, still reporting a clamped one",
     {"guard_clamp": False}, "caught"),
    ("report the unclamped score, still guarding on a clamped one",
     {"report_clamp": False}, "caught"),
    # --- off-by-one on the boundaries -------------------------------------
    ("read the threshold as strictly greater than 0.5", {"threshold_op": ">"}, "caught"),
    ("read the margin as strictly greater than 0.05", {"margin_op": ">"}, "caught"),
    ("break exact ties toward the earlier candidate", {"tie_order": "earlier"}, "caught"),
    # --- the selector ------------------------------------------------------
    # NOTE: a "store the whole neighbour block" row used to sit here, inverted:
    # through v1.2 the reference stored whole blocks and windowing the stored
    # side was the mutation, recorded as a known nonconformance rather than as a
    # wrong reading. The reference now conforms, so that mutation moved to
    # PRODUCER_MUTATIONS below, where it demonstrates something this table
    # cannot: the resolve corpus alone can no longer catch it.
    # §9 caps the bonus at "<= 0.05 each" without saying the weight IS 0.05, so
    # a compliant-looking implementation could scale by 0.025 and read the cap as
    # satisfied. The corpus pins 0.05, which is the intended reading (the bonus is
    # 0.05 times a ratio in [0,1], hence "<= 0.05"), but the prose does not say so.
    ("scale the context bonus by 0.025 per side, satisfying §9's '<= 0.05' cap",
     {"bonus_weight": 0.025}, "caught"),
    # §9 also says the bonus "breaks near-ties" and is "not a primary key", which
    # licenses applying it only within epsilon of the leading body score instead
    # of additively to every candidate.
    ("apply the bonus only to candidates within 0.01 of the best body score",
     {"bonus_tiebreak_only": 0.01}, "caught"),
    # The surviving candidate from the 2026-08 clamp re-pricing (SPEC_DECISIONS.md).
    # Unlike `guard_clamp: False` it leaves `near-dup-margin-guard-detaches` alone,
    # so the only vectors it reaches are the two about genuinely identical twins. It
    # is a mutation here, not the reference, because adopting it would change a
    # normative vector and therefore needs a v1.3 argument of its own.
    ("lift the clamp only where the body scores are exactly tied",
     {"unclamp_exact_ties": True}, "caught"),
    ("score only the prefix side of the context", {"context_sides": "prefix"}, "caught"),
    ("score only the suffix side of the context", {"context_sides": "suffix"}, "caught"),
    ("fold with Unicode casefold and \\s instead of §9's ASCII fold",
     {"unicode_fold": True}, "caught"),
    # `body_score` normalizes both sides; normalizing only one is the easy slip,
    # because the stored quote arrives already-normalized-looking and the candidate
    # comes straight off the document.
    ("normalize the stored quote but not the candidate body",
     {"normalize_sides": "quote"}, "caught"),
    ("normalize the candidate body but not the stored quote",
     {"normalize_sides": "candidate"}, "caught"),
    # --- the ladder --------------------------------------------------------
    ("take the first of several hash hits instead of falling through to QUOTE",
     {"hash_ambiguity": "first-hit"}, "caught"),
    ("refuse to commit when there is only one candidate",
     {"min_candidates": 2}, "caught"),
    # --- the constants -----------------------------------------------------
    ("compile in threshold 0.6", {"default_threshold": 0.6}, "caught"),
    ("compile in threshold 0.4", {"default_threshold": 0.4}, "caught"),
    ("compile in margin 0.04", {"default_margin": 0.04}, "caught"),
    ("compile in margin 0.06", {"default_margin": 0.06}, "caught"),
    # --- proved inert ------------------------------------------------------
    # §9 specifies a containment floor "so a surviving half of a split block does
    # not score arbitrarily low". Under containment the Ratcliff/Obershelp ratio
    # is 2s/(s+l) and the floor is s/l, and 2s/(s+l) > s/l for every l > s; l == s
    # with containment means the strings are equal, which body_score has already
    # returned 1.0 for. So the floor cannot raise a score and no vector can catch
    # its removal. That is a fact about §9, not a hole: the guarantee the floor
    # exists to provide is already delivered by the metric.
    ("drop the containment floor", {"containment_floor": False}, "inert"),
    ("use a 47-character context window instead of 48", {"window": 47}, "caught"),
]

# Mutations the resolve corpus CANNOT catch, with the category that can. Kept in
# its own table because the claim being checked has two halves: the named corpus
# catches it, and `resolve` does not. Asserting only the first would let a reader
# assume resolve coverage it does not have, which is how the stored-context
# defect survived four releases of a corpus that looked comprehensive.
PRODUCER_MUTATIONS = [
    ("store the whole neighbour block instead of §9's 48 characters",
     {"store_whole_neighbour": True}, "anchors"),
    ("drop the match-time window on the stored side, so an over-long stored "
     "selector is scored against a windowed candidate",
     {"window_stored": False}, "score"),
]


# --- SPEC.md §3.3, the fenced-code mask (v1.5) ------------------------------
#
# The same question as above, asked of the rule most likely to be re-implemented
# slightly differently. §3.3 is a *line* rule with several named boundaries (how
# many leading spaces, which whitespace may follow a closer, whether a longer
# opener contains a shorter one), and the spec names each of them precisely
# because three implementations picking three readings is how the rule fails
# quietly: the divergence is a §8 hash disagreement between languages, with no
# error anywhere.
#
# The seam is `fence_state` itself: every §3.3 consumer reads the rule through it,
# so patching it reaches parse, lint and the write path at once, and a mutation
# here is what a second implementation getting that function subtly wrong looks
# like. `strip_markers_outside_code` is patched alongside it for the one mutation
# that is about *applying* the mask rather than computing it.
#
# `_paths_by_line` in the canonical linter used to be a second recogniser, tracking
# fences itself off the same two regexes, and the two disagreed: a marker followed by
# a fence run on one line was a bare opener to it and no fence at all to §3.3. It now
# reads `code_lines`, so it is on this seam and a mutation here does reach it. What
# is still true is that nothing below *measures* it: heading paths are §9 recovery
# evidence, no parse/lint/stamp vector exercises them, and the canonical linter's own
# unit tests are what hold that derivation to the rule.

FENCE_OPEN = re.compile(r"^(?P<indent>[ \t]*)(?P<run>`{3,}|~{3,})(?P<info>.*)$")
# The loose regex a parser might ship: three or more of EITHER character, mixed.
FENCE_OPEN_MIXED = re.compile(r"^(?P<indent>[ \t]*)(?P<run>[`~]{3,})(?P<info>.*)$")
# Everything Python, ECMAScript or Rust would call whitespace, which is the set
# §3.3 declines to use and names its reason for declining.
_ALL_WS = " \t\n\r\x0b\x0c\x1c\x1d\x1e\x1f\x85\xa0\u1680\u2000\u2001\u2002\u2003\u2004\u2005"\
          "\u2006\u2007\u2008\u2009\u200a\u2028\u2029\u202f\u205f\u3000\ufeff"


def fence_state_variant(text: str, *, indent: str = "0-3-spaces",
                        info_backtick: bool = True, closer_trailing: str = "space-tab",
                        closer_length: str = "at-least", closer_char: str = "same",
                        unclosed: str = "to-eof", fence_lines: str = "inside",
                        blockquote: bool = False, line_base: int = 1,
                        run_chars: str = "same", closer_indent: str = "own"):
    """§3.3's line rule, with each named boundary as a knob. Defaults are the spec."""
    def opener(line: str, want_indent: int | None = None):
        if blockquote and line.lstrip(" ").startswith(">"):
            line = line.lstrip(" ")[1:].lstrip(" ")
        m = (FENCE_OPEN_MIXED if run_chars == "mixed" else FENCE_OPEN).match(line)
        if m is None:
            return None
        pad = m.group("indent")
        if indent == "0-3-spaces" and (len(pad) > 3 or "\t" in pad):
            return None
        if indent == "0-3-any-ws" and len(pad) > 3:
            return None
        if indent == "none" and pad:
            return None
        # §3.3 gives the opener and the closer the same 0-3 allowance and does not
        # tie them together. Reading "at most three leading spaces" as "the same
        # leading spaces" is the misreading this knob expresses.
        if want_indent is not None and closer_indent == "match" and len(pad) != want_indent:
            return None
        return m.group("run"), m.group("info"), len(pad)

    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    inside: set[int] = set()
    open_after: set[int] = set()
    fence = None
    fence_pad = 0
    for num, line in enumerate(lines, line_base):
        if fence is None:
            op = opener(line)
            if op is None or (info_backtick and op[0][0] == "`" and "`" in op[1]):
                continue
            fence, fence_pad = op[0], op[2]
            if fence_lines == "inside":
                inside.add(num)
            open_after.add(num)
            continue
        inside.add(num)
        cl = opener(line, fence_pad)
        closes = cl is not None
        if closes:
            run, rest, _pad = cl
            if closer_char == "same" and run[0] != fence[0]:
                closes = False
            if closer_length == "at-least" and len(run) < len(fence):
                closes = False
            if closer_length == "exact" and len(run) != len(fence):
                closes = False
            if closer_trailing == "space-tab" and rest.strip(" \t"):
                closes = False
            if closer_trailing == "all-ws" and rest.strip(_ALL_WS):
                closes = False
            if closer_trailing == "none" and rest:
                closes = False
        if closes:
            if fence_lines != "inside":
                inside.discard(num)
            fence = None
        else:
            open_after.add(num)
    if fence is not None and unclosed == "ignore":
        # An implementer who reads "it closes at the first later line" as
        # requiring a closer: an unterminated fence is then not a fence at all.
        first = min(open_after) if open_after else None
        if first is not None:
            inside = {n for n in inside if n < first}
            open_after = {n for n in open_after if n < first}
    return inside, open_after


def strip_outside_variant(text, code, line_offset=0, *, judge_by="open"):
    """§3.3 judges a marker by the line it OPENS on. `judge_by="close"` is the
    other reading available to an implementer: a marker crossing a fence boundary
    is then classified by where it ends."""
    if not code:
        # The canonical linter keeps this one private (`_strip_markers`) and the
        # package exports it; the empty-code fast path must call the SAME function
        # the reference does, or the unmutated baseline stops reproducing the
        # corpus for reasons that have nothing to do with §3.3.
        strip_all = getattr(L, "strip_markers", None) or L._strip_markers
        return strip_all(text)
    out, prev = [], 0
    for m in L.COMBINED_MARKER.finditer(text):
        at = m.start() if judge_by == "open" else m.end()
        if line_offset + text.count("\n", 0, at) + 1 in code:
            continue
        out.append(text[prev:m.start()])
        prev = m.end()
    out.append(text[prev:])
    return "".join(out)


def judge_marker_variant(marker, code, *, judge_by="open"):
    """§3.3 judges a marker by the line it OPENS on. `judge_by="close"` is the
    other reading available to an implementer: a marker crossing a fence boundary
    is then classified by where it ends.

    This is the seam every reference asks through: the strip, the write-path
    rewrite, row refusal, block attachment, and the lexical diagnostics. Patching
    it flips all five at once, which the earlier strip-only patch could not do
    once attachment stopped routing through the strip."""
    if not code:
        return True
    line = marker.line
    if judge_by == "close":
        # `raw` is the marker's own bytes, so its newlines are its span.
        line += marker.raw.count("\n")
    return line not in code


# Each row is a reading of §3.3 an implementer could arrive at honestly, and the
# corpus must catch every one. Where a row's misreading is the *inverse* of a
# boundary (accepting more than §3.3 does), it is what the negative vectors exist
# for: those cannot be caught by removing the rule, only by over-applying it.
FENCE_MUTATIONS = [
    # --- how far a fence may be indented -----------------------------------
    ("accept a fence at any indent, so an indented code block is masked too",
     {"indent": "any"}),
    ("count a tab as one of the three leading spaces",
     {"indent": "0-3-any-ws"}),
    ("require a fence to start at column 0",
     {"indent": "none"}),
    # --- the info string ----------------------------------------------------
    ("let a backtick fence's info string contain a backtick (CommonMark 4.5)",
     {"info_backtick": False}),
    # --- what closes a fence -------------------------------------------------
    ("let any trailing text close a fence, not just spaces and tabs",
     {"closer_trailing": "any"}),
    ("require a bare closing run with nothing after it, not even a space",
     {"closer_trailing": "none"}),
    # The misreading §3.3 names outright: "the whitespace set is named rather than
    # left to 'whitespace', because three implementations picking three sets is the
    # way this rule fails quietly." This row sits BETWEEN "space-tab" and "any", so
    # the `x`-after-the-run vector above cannot catch it.
    ("let anything the runtime calls whitespace close a fence (JS `\\s`, Rust "
     "`is_whitespace`, Python `.strip()`), not just space and tab",
     {"closer_trailing": "all-ws"}),
    ("require the closing run to match the opener's length exactly, so a longer "
     "opener cannot contain a shorter run",
     {"closer_length": "exact"}),
    ("let a tilde run close a backtick fence",
     {"closer_char": "any"}),
    ("read the opening run as `[`~]{3,}`, so a mixed run opens a fence",
     {"run_chars": "mixed"}),
    # --- the edges of the span ------------------------------------------------
    ("treat an unclosed fence as not a fence at all",
     {"unclosed": "ignore"}),
    ("exclude the fence lines themselves, so a marker in an info string is a marker",
     {"fence_lines": "exclude"}),
    ("see a fence through a blockquote prefix, which needs the container the "
     "line rule deliberately does not have",
     {"blockquote": True}),
    # --- the arithmetic --------------------------------------------------------
    ("index the mask from line 0 rather than line 1",
     {"line_base": 0}),
    ("require the closing run's indent to match the opener's, reading §3.3's "
     "'at most three leading spaces' on both as 'the same leading spaces'",
     {"closer_indent": "match"}),
]

# --- SPEC.md §5.6 row recognition -----------------------------------------
#
# The §3.3 battery above proved that reverting a rule catches a POSITIVE vector
# but can never move a NEGATIVE one, and §5.6 is mostly negative: rules 1 to 5
# are refusals. So these mutations are written the way §3.3's were, as readings
# an implementer could arrive at honestly, and each has to be caught by a named
# vector in the optional `rows` profile.
#
# The seam is three named functions that BOTH Python references spell
# identically (`_row_cells`, `_table_candidates`, `_table_spans_by_container`),
# so one patch reaches the canonical linter's read path and the package's write
# path together. Patching the read path alone would leave the stamp vectors
# reporting a coverage hole that is really a patching bug, which is the mistake
# `_fence_modules` above documents and which this file has already made once.


def row_cells_variant(line, *, outer_pipes="required", trim="ascii"):
    """§5.6 rule 1 plus the cell rule, with the two readings that change what a
    row IS. `outer_pipes="optional"` is GFM's own rule, which §5.6 deliberately
    refuses; `trim="unicode"` is what `str.strip()` does when nobody names the
    whitespace set, and `trim="space"` is the narrower miss of reading step 3
    as "padding" and trimming only the space character."""
    leading = len(line) - len(line.lstrip(" "))
    if leading > 3:
        return None
    working = line[leading:].rstrip(" \t\f\v")
    if not working:
        return None
    spans = L._line_marker_spans(working)
    if L._spans_overlap(spans):
        return None

    delimiters, backslashes, pos, span_index = [], 0, 0, 0
    while pos < len(working):
        if span_index < len(spans) and pos == spans[span_index][0]:
            pos = spans[span_index][1]
            span_index += 1
            backslashes = 0
            continue
        char = working[pos]
        if char == "\\":
            backslashes += 1
            pos += 1
            continue
        if char == "|" and backslashes % 2 == 0:
            delimiters.append(pos)
        backslashes = 0
        pos += 1
    if outer_pipes == "required":
        if len(delimiters) < 2:
            return None
        if delimiters[0] != 0 or delimiters[-1] != len(working) - 1:
            return None
        bounds = delimiters
    else:
        # GFM's rule, which §5.6 refuses: a missing outer pipe is a VIRTUAL
        # boundary at the line edge, so `a | b` is a two-cell row. Requiring two
        # literal delimiters here instead would make the mutant agree with the
        # reference on exactly the single-delimiter lines the boundary vector is
        # built from, and a mutation that cannot differ cannot be caught.
        if not delimiters:
            return None
        bounds = list(delimiters)
        if bounds[0] != 0:
            bounds.insert(0, -1)
        if bounds[-1] != len(working) - 1:
            bounds.append(len(working))

    cells = []
    for start, end in zip(bounds, bounds[1:]):
        cell_spans = [
            (max(ms, start + 1) - (start + 1), min(me, end) - (start + 1))
            for ms, me in spans
            if start < ms and me <= end
        ]
        cell = L._remove_spans(working[start + 1 : end], cell_spans)
        if trim == "unicode":
            cells.append(cell.strip())
        elif trim == "space":
            cells.append(cell.strip(" "))
        else:
            cells.append(cell.strip(" \t\f\v"))
    return cells


# Captured before any binding is swapped, so the variant can delegate the
# list-item path without recursing into itself.
_REAL_CHILD_BODY = L.child_body


def child_body_variant(text, code=None, line_offset=0, kind="list",
                       markers_already_stripped=False, *, encode="escaped"):
    """§5.6 Body and hash steps 4 and 5, with the reading that drops the escape.

    `encode="none"` joins the trimmed cells with a bare `|` and skips step 4
    entirely. The spec names the collision this causes in its own prose: the two
    cells of `| a\\ | b |` and the one cell of `| a\\|b |` both become `a\\|b`,
    so two structurally different rows hash the same. Only the row path is
    mutated; a list item's body is left to the real implementation.
    """
    if kind != "row":
        return _REAL_CHILD_BODY(
            text, code, line_offset, kind, markers_already_stripped
        )
    cells = L._row_cells(text)
    if cells is None:
        return ""
    if encode == "none":
        return "|".join(cells)
    return "|".join(
        cell.replace("\\", "\\\\").replace("|", "\\|") for cell in cells
    )


def table_candidates_variant(
    text,
    code,
    provenance=None,
    *,
    delimiter_markers="refuse",
    header_is_row=False,
    ragged="accept",
    non_row="refuse",
):
    """§5.6 rules 2 to 5. Each keyword is one honest misreading of one rule."""
    lines = text.split("\n")
    refused_marker_lines = L._row_refused_marker_lines(text, code)
    candidates = []
    i = 0
    while i + 1 < len(lines):
        header = (
            None
            if i + 1 in code or i + 1 in refused_marker_lines
            else L._row_cells(lines[i])
        )
        delimiter_source = lines[i + 1]
        if delimiter_markers == "strip":
            # Deleting the marker BEFORE validating manufactures delimiter
            # syntax out of a line that did not have it, which is the one thing
            # §5.6 says the delimiter rule exists to prevent.
            delimiter_source = L._remove_spans(
                delimiter_source, L._line_marker_spans(delimiter_source)
            )
        delimiter = (
            None
            if i + 2 in code or i + 2 in refused_marker_lines
            else L._row_cells(delimiter_source)
        )
        delimiter_shaped = (
            delimiter is not None
            and bool(delimiter)
            and all(L._DELIMITER_CELL_RE.fullmatch(cell) for cell in delimiter)
        )
        if provenance is not None and header is not None and delimiter_shaped:
            provenance.update((i + 1, i + 2))
        if (
            header is None
            or delimiter is None
            or (
                delimiter_markers == "refuse"
                and bool(L._line_marker_spans(lines[i + 1]))
            )
            or "\f" in lines[i + 1]
            or "\v" in lines[i + 1]
            or len(header) != len(delimiter)
            or not delimiter_shaped
        ):
            i += 1
            continue

        rows = []
        if header_is_row:
            rows.append(L._ChildSpan(i + 1, i + 1, lines[i], i + 1, kind="row"))
        refused = False
        j = i + 2
        while j < len(lines):
            line_number = j + 1
            line = lines[j]
            if line_number in code or line_number in refused_marker_lines:
                if provenance is not None:
                    provenance.add(line_number)
                refused = True
                j += 1
                continue
            if line.strip(" \t\f\v") == "" or L._marker_only_line(line):
                break
            if provenance is not None:
                provenance.add(line_number)
            cells = L._row_cells(line)
            if cells is None or (ragged == "refuse" and len(cells) != len(header)):
                if non_row == "break":
                    break
                if non_row == "count":
                    # The ordinal-shifting reading: keep the refused line as a
                    # row so every later row's position moves by one.
                    rows.append(
                        L._ChildSpan(line_number, line_number, line, line_number,
                                     kind="row")
                    )
                else:
                    refused = True
            else:
                rows.append(
                    L._ChildSpan(line_number, line_number, line, line_number,
                                 kind="row")
                )
            j += 1
        if not refused:
            candidates.append(L._TableCandidate(i + 1, max(i + 2, j), rows))
        if j >= len(lines):
            break
        i = j + 1
    return candidates


def table_spans_variant(text, chunks, code, *, per_container="one"):
    """The post-scan filter. `per_container="all"` drops it, which is the
    reading that lets two ordinal-1 rows share one §9.2 container."""
    candidates_by_start = {}
    for candidate in L._table_candidates(text, code):
        for start, chunk in chunks:
            end = start + len(chunk.split("\n")) - 1
            if start <= candidate.header_line and candidate.end_line <= end:
                candidates_by_start.setdefault(start, []).append(candidate)
                break
    if per_container == "all":
        return {
            start: [span for candidate in candidates for span in candidate.rows]
            for start, candidates in candidates_by_start.items()
        }
    return {
        start: candidates[0].rows
        for start, candidates in candidates_by_start.items()
        if len(candidates) == 1
    }


ROW_MUTATIONS = [
    # --- rule 1: what a row line is ----------------------------------------
    ("accept a row without both outer pipes, which is GFM's own rule",
     {"cells": {"outer_pipes": "optional"}}),
    ("trim runtime Unicode whitespace instead of SP / HTAB / FF / VT",
     {"cells": {"trim": "unicode"}}),
    ("trim only spaces, leaving HTAB / FF / VT padding in the row body",
     {"cells": {"trim": "space"}}),
    # --- body and hash step 4: the escape that makes the join reversible ----
    ("join the cells without escaping, so `a\\ | b` and `a\\|b` collide",
     {"body": {"encode": "none"}}),
    # --- rule 2: what starts a candidate -----------------------------------
    ("delete a delimiter marker before validating the delimiter",
     {"candidates": {"delimiter_markers": "strip"}}),
    # --- what a body row is -------------------------------------------------
    ("treat a header row as a body row, so a header subhash addresses one",
     {"candidates": {"header_is_row": True}}),
    ("refuse a body row whose cell count differs from the header's, the way a "
     "GFM parser pads or truncates one",
     {"candidates": {"ragged": "refuse"}}),
    # --- rules 3 and 4: how a candidate ends -------------------------------
    ("end a candidate at its first non-row rather than refuse the whole candidate",
     {"candidates": {"non_row": "break"}}),
    ("count a refused line in later row ordinals instead of refusing the candidate",
     {"candidates": {"non_row": "count"}}),
    # --- the post-scan filter ----------------------------------------------
    ("expose both candidates in one selected container",
     {"spans": {"per_container": "all"}}),
]


_ROW_NAMES = {
    "child_body": "body",
    "_row_cells": "cells",
    "_table_candidates": "candidates",
    "_table_spans_by_container": "spans",
}


def _row_bindings():
    return [(m, n, kind) for m in _fence_modules()
            for n, kind in _ROW_NAMES.items() if hasattr(m, n)]


def check_rows(**kw) -> list[str]:
    """Run the optional `rows` profile with §5.6 mutated. Returns the failing
    vector names, which is what "the corpus catches this misreading" means."""
    import run_py

    cells_kw = kw.get("cells", {})
    cand_kw = kw.get("candidates", {})
    spans_kw = kw.get("spans", {})
    body_kw = kw.get("body", {})

    replacement = {
        "cells": lambda line: row_cells_variant(line, **cells_kw),
        "candidates": lambda text, code, provenance=None: table_candidates_variant(
            text, code, provenance, **cand_kw
        ),
        "spans": lambda text, chunks, code: table_spans_variant(
            text, chunks, code, **spans_kw
        ),
        "body": lambda text, code=None, line_offset=0, kind="list",
        markers_already_stripped=False: child_body_variant(
            text, code, line_offset, kind, markers_already_stripped, **body_kw
        ),
    }
    bindings = _row_bindings()
    saved = [(m, n, getattr(m, n)) for m, n, _ in bindings]
    try:
        for m, n, kind in bindings:
            setattr(m, n, replacement[kind])
        failed = []
        for path in sorted((HERE / "rows").glob("*.json")):
            data = json.loads(path.read_text())
            for v in data["vectors"]:
                try:
                    ok, _ = run_py.VERIFIERS["rows"](v)
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    failed.append(f"rows:{v.get('name', '?')}")
        return failed
    finally:
        for m, n, fn in saved:
            setattr(m, n, fn)


# --- §3.4: the carrier rule, and the readings of it that let a document through --
#
# The write path only, so these patch `markstay.stamp` rather than every module
# that spells a rule: no other implementation mints a child stay. Two seams, and
# they fail differently. `plain_text_state` decides what a carrier text may
# contain; `_carrier_prefix` decides WHICH bytes that is, and every scope defect
# in this rule's review history was the second one.
#
# §3.4's marker clause is deliberately absent. A conforming writer emits only an
# id and a digest at a carrier, so no corpus document can reach a mutation that
# permits more: the clause guards a caller that has not been written, and the
# eval's shape gate is where its counterexamples live.


def _write_module():
    """`markstay.stamp` through `sys.modules`, because the package re-exports a
    FUNCTION called `stamp` that shadows the submodule for a plain import."""
    import importlib

    importlib.import_module("markstay.stamp")
    return sys.modules["markstay.stamp"]


def plain_text_state_variant(text, marker="", syntax="html", flush=False, *,
                             capturing="all", mask="markers", flush_clause=True,
                             code_span_mask="list-only"):
    """§3.4's predicate with each of its decisions exposed as a parameter."""
    W = _write_module()

    if mask == "none":
        scanned = text
    elif mask == "comments":
        # The withdrawn reading: decide that a CLOSED comment is inert. `--!>`
        # closes one for an HTML parser and not for CommonMark, so this permits
        # `x<!-- note --!>` and everything behind it.
        scanned = re.sub(r"<!--.*?(?:-->|--!>)", lambda m: " " * len(m.group(0)),
                         text, flags=re.S)
    elif mask == "any-record":
        # Mask every §4 record, host closer or not, so a marker ending at `--!>`
        # is treated as closed.
        out = list(text)
        for record in L._scan_marker_records(text):
            for at in range(record.start, min(record.end, len(out))):
                out[at] = " "
        scanned = "".join(out)
    else:
        scanned = W._outside_markers(text, syntax)

    # v1.8: masking closed inline code spans is scoped to a non-flush (§5.5
    # list) carrier. `code_span_mask="always"` is the reading that applies it
    # to a flush (§5.6 row) carrier too, which is exactly what the row half of
    # the profile exists to refuse: GFM splits cells before inline parsing, so
    # a scan that pairs backticks across a `|` masks something a renderer does
    # not.
    if code_span_mask == "always" or (code_span_mask == "list-only" and not flush):
        scanned = W._inert_code_spans(scanned)

    characters = "<" if capturing == "angle-only" else W.CARRIER_CAPTURING[syntax]
    if any(character in scanned for character in characters):
        return False
    if flush_clause and flush and W._TRAILING_DELIMITER.search(scanned):
        return False
    return W.plain_marker(marker)


def carrier_prefix_variant(prefix_fn, lines, first_line0, marker_line0, kind, *,
                           scope="container"):
    """§3.4's carrier text, or the child-scoped reading it was corrected from.

    The unmutated function arrives as an argument rather than being looked up: by
    the time this runs it is what the module attribute points at, so reading it
    back off the module would call this variant again forever, and the baseline
    would fail every vector while reporting a coverage hole.
    """
    start = first_line0 if scope == "container" else marker_line0
    return prefix_fn(lines, start, marker_line0, kind)


CARRIER_MUTATIONS = [
    ("scan the carrier text with its own markers visible, so a stamped container "
     "refuses every child added to it afterwards",
     {"state": {"mask": "none"}}),
    ("treat any closed comment as inert, not just a complete marker",
     {"state": {"mask": "comments"}}),
    ("mask a §4 record that ends at HTML's `--!>`, which CommonMark does not "
     "recognise as a closer at all",
     {"state": {"mask": "any-record"}}),
    ("refuse on `<` alone, dropping the backslash and MDX brace conditions",
     {"state": {"capturing": "angle-only"}}),
    ("drop the flush clause, so a carrier landing against a delimiter run is "
     "written and the emphasis beside it stops rendering",
     {"state": {"flush_clause": False}}),
    ("scope the carrier text to the child rather than to its container",
     {"prefix": {"scope": "child"}}),
    ("apply v1.8's closed-code-span mask to a flush (row) carrier too, instead "
     "of scoping it to §5.5 list children",
     {"state": {"code_span_mask": "always"}}),
]


def check_carrier(**kw) -> list[str]:
    """Run the `rows` profile with §3.4 mutated, and report what fails."""
    import run_py

    W = _write_module()
    state_kw = kw.get("state", {})
    prefix_kw = kw.get("prefix", {})
    prefix_fn = W._carrier_prefix
    replacement = {
        "plain_text_state": lambda text, marker="", syntax="html", flush=False:
            plain_text_state_variant(text, marker, syntax, flush, **state_kw),
        "_carrier_prefix": lambda lines, first, last, kind:
            carrier_prefix_variant(prefix_fn, lines, first, last, kind, **prefix_kw),
    }
    saved = [(n, getattr(W, n)) for n in replacement]
    try:
        for name, fn in replacement.items():
            setattr(W, name, fn)
        failed = []
        for path in sorted((HERE / "rows").glob("*.json")):
            data = json.loads(path.read_text())
            for v in data["vectors"]:
                try:
                    ok, _ = run_py.VERIFIERS["rows"](v)
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    failed.append(f"rows:{v.get('name', '?')}")
        return failed
    finally:
        for name, fn in saved:
            setattr(W, name, fn)


# Applying the mask rather than computing it, so it takes the other seam.
FENCE_APPLY_MUTATIONS = [
    ("judge a marker by the line it closes on rather than the line it opens on",
     {"judge_by": "close"}),
]


# The two Python references spell the rule differently: the packaged one exports
# `fence_state` / `strip_markers_outside_code`, the canonical single-file linter
# keeps them private as `_fence_state` / `_strip_markers_outside_code`. Both are
# patched, because `run_py` verifies parse and lint through the canonical linter
# and the write path through the package.
_FENCE_NAMES = {
    "fence_state": "state", "_fence_state": "state",
    "code_lines": "lines",
    "strip_markers_outside_code": "strip", "_strip_markers_outside_code": "strip",
    "marker_outside_code": "judge", "_marker_outside_code": "judge",
}


def _fence_modules():
    """Every module that reads the rule through a name of its own. `stamp.py`
    imports the functions by name, so patching only `lint` would leave the write
    path unmutated and the write vectors would report a coverage hole that is
    really a patching bug. `markstay.stamp` is reached through `sys.modules`
    because the package re-exports a FUNCTION called `stamp`, which shadows the
    submodule for a plain `import markstay.stamp as ...`."""
    import importlib
    mods = [L, importlib.import_module("markstay.lint")]
    importlib.import_module("markstay.stamp")
    mods.append(sys.modules["markstay.stamp"])
    return mods


def _fence_bindings():
    return [(m, n, kind) for m in _fence_modules()
            for n, kind in _FENCE_NAMES.items() if hasattr(m, n)]


def check_fence(vectors, **kw) -> list[str]:
    """Run the parse/lint/stamp vectors with §3.3 mutated. Returns the names that
    fail, which is what "the corpus catches this misreading" means."""
    import run_py

    apply_kw = {k: kw.pop(k) for k in list(kw) if k == "judge_by"}

    def state(text):
        return fence_state_variant(text, **kw)

    def lines(text):
        return state(text)[0]

    def strip(text, code, line_offset=0):
        return strip_outside_variant(text, code, line_offset, **apply_kw)

    def judge(marker, code):
        return judge_marker_variant(marker, code, **apply_kw)

    replacement = {"state": state, "lines": lines, "strip": strip, "judge": judge}
    bindings = _fence_bindings()
    saved = [(m, n, getattr(m, n)) for m, n, _ in bindings]
    try:
        for m, n, kind in bindings:
            setattr(m, n, replacement[kind])
        failed = []
        for path in sorted((HERE / "spec").glob("*.json")) + sorted((HERE / "gen").glob("*.json")):
            data = json.loads(path.read_text())
            verify = run_py.VERIFIERS.get(data["category"])
            if verify is None or data["category"] not in ("parse", "lint", "stamp"):
                continue
            for v in data["vectors"]:
                try:
                    ok, _ = verify(v)
                except Exception:  # noqa: BLE001
                    ok = False
                if not ok:
                    failed.append(f"{data['tier']}/{data['category']}:{v.get('name', '?')}")
        return failed
    finally:
        for m, n, fn in saved:
            setattr(m, n, fn)


def differential(n: int = 400, seed: int = 20260816) -> list[str]:
    """Compare the UNMUTATED variant against `resolver.resolve` over generated
    document pairs, so agreement is tested beyond the frozen vectors."""
    rng = random.Random(seed)
    words = ["alpha", "bravo", "charlie", "delta", "echo", "retries", "stage",
             "queue", "payload", "three", "seven", "audit", "partner"]

    def para():
        return " ".join(rng.choice(words) for _ in range(rng.randint(3, 12))) + "."

    bad = []
    for case in range(n):
        blocks = [para() for _ in range(rng.randint(1, 6))]
        before = "\n\n".join(
            f"{b}\n<!-- stay:id{i} -->" if rng.random() < 0.8 else b
            for i, b in enumerate(blocks)) + "\n"
        kept = [b for b in blocks if rng.random() < 0.7]
        kept += [para() for _ in range(rng.randint(0, 2))]
        rng.shuffle(kept)
        after = "\n\n".join(kept) + "\n" if kept else ""
        t = rng.choice([0.3, 0.5, 0.7])
        m = rng.choice([0.0, 0.05, 0.2])
        got = resolve_variant(before, after, t, m)
        ref = R.resolve(R.build_anchors(before), after, threshold=t, margin=m)
        want = {k: {"method": v.method, "target": v.target, "score": v.score}
                for k, v in ref.items()}
        if got.keys() != want.keys() or any(
                got[k]["method"] != want[k]["method"]
                or got[k]["target"] != want[k]["target"]
                or abs(got[k]["score"] - want[k]["score"]) >= TOL for k in want):
            bad.append(f"case {case}: {got} != {want}")
    return bad


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    verbose = "--verbose" in argv or "-v" in argv
    vectors = load()
    print(f"resolve corpus: {len(vectors)} vectors\n")

    if "--differential" in argv:
        bad = differential()
        if bad:
            print(f"FAIL differential: {len(bad)} generated cases disagree with "
                  "resolver.resolve, so this file has drifted from the reference")
            for b in bad[:5]:
                print(f"       - {b}")
            return 1
        print("  ok   differential: 400 generated pairs match resolver.resolve")

    base = check(vectors)
    if base:
        print("FAIL baseline: the unmutated ladder disagrees with the corpus, so "
              "this file has drifted from the reference and every result below is "
              "meaningless.")
        for f in base:
            print(f"       - {f}")
        return 1
    print("  ok   baseline: unmutated ladder reproduces every vector")

    wrong = 0
    for label, kw, expect in MUTATIONS:
        failed = check(vectors, **kw)
        if expect == "inert":
            if failed:
                wrong += 1
                print(f"  ???  expected inert but {len(failed)} vectors fail: {label}")
                for f in failed:
                    print(f"         - {f}")
            else:
                print(f"  ok   inert as argued: {label}")
            continue
        if failed:
            print(f"  ok   caught ({len(failed)}): {label}")
            if verbose:
                for f in failed:
                    print(f"         - {f}")
        else:
            wrong += 1
            print(f"  HOLE uncaught: {label}")

    anchor_vectors = load_anchors()
    score_vectors = load_score()
    checkers = {"anchors": (check_anchors, anchor_vectors),
                "score": (check_score, score_vectors)}
    if anchor_vectors and score_vectors:
        print(f"\nproducer / scoring mutations (resolve corpus cannot catch these): "
              f"{len(anchor_vectors)} anchors vectors, {len(score_vectors)} "
              f"context-bonus vectors\n")
        for label, kw, category in PRODUCER_MUTATIONS:
            checker, vecs = checkers[category]
            caught = checker(vecs, **kw)
            by_resolve = check(vectors, **kw)
            if not caught:
                wrong += 1
                print(f"  HOLE uncaught by {category}: {label}")
            elif by_resolve:
                wrong += 1
                print(f"  ???  expected {category}-only but resolve also catches "
                      f"({len(by_resolve)}): {label}")
            else:
                print(f"  ok   caught by {category} only ({len(caught)}): {label}")
    else:
        wrong += 1
        print("  HOLE: the anchors or score corpus is missing, so the producer "
              "mutations below were not run at all")

    fence_vectors = check_fence([])  # unmutated: the baseline must be clean
    print(f"\n§3.3 fence mutations (parse + lint + stamp corpus)\n")
    if fence_vectors:
        wrong += 1
        print("  FAIL baseline: the unmutated variant disagrees with the corpus, so "
              "this battery has drifted from the reference and every row below is "
              "meaningless.")
        for f in fence_vectors[:5]:
            print(f"         - {f}")
    else:
        print("  ok   baseline: the unmutated §3.3 line rule reproduces every vector")
        for label, kw in FENCE_MUTATIONS + FENCE_APPLY_MUTATIONS:
            caught = check_fence([], **dict(kw))
            if caught:
                print(f"  ok   caught ({len(caught)}): {label}")
                if verbose:
                    for f in caught:
                        print(f"         - {f}")
            else:
                wrong += 1
                print(f"  HOLE uncaught: {label}")

    row_vectors = check_rows()  # unmutated: the baseline must be clean
    print(f"\n§5.6 row-recognition mutations (optional `rows` profile)\n")
    if row_vectors:
        wrong += 1
        print("  FAIL baseline: the unmutated variant disagrees with the corpus, so "
              "this battery has drifted from the reference and every row below is "
              "meaningless.")
        for f in row_vectors[:5]:
            print(f"         - {f}")
    else:
        n_rows = sum(
            len(json.loads(f.read_text())["vectors"])
            for f in sorted((HERE / "rows").glob("*.json"))
        )
        print("  ok   baseline: the unmutated §5.6 scan reproduces all "
              f"{n_rows} vectors")
        for label, kw in ROW_MUTATIONS:
            caught = check_rows(**kw)
            if caught:
                print(f"  ok   caught ({len(caught)}): {label}")
                if verbose:
                    for f in caught:
                        print(f"         - {f}")
            else:
                wrong += 1
                print(f"  HOLE uncaught: {label}")

    print(f"\n§3.4 carrier mutations (write path, `rows` profile)\n")
    if check_carrier():
        wrong += 1
        print("  BASELINE the unmutated carrier rule already fails the profile")
    else:
        for label, kw in CARRIER_MUTATIONS:
            caught = check_carrier(**kw)
            if caught:
                print(f"  ok   caught ({len(caught)}): {label}")
                if verbose:
                    for f in caught:
                        print(f"         - {f}")
            else:
                wrong += 1
                print(f"  HOLE uncaught: {label}")

    total_mutations = (len(MUTATIONS) + len(PRODUCER_MUTATIONS)
                       + len(FENCE_MUTATIONS) + len(FENCE_APPLY_MUTATIONS)
                       + len(ROW_MUTATIONS) + len(CARRIER_MUTATIONS))
    print(f"\n{total_mutations - wrong}/{total_mutations} mutations behaved as declared")
    if wrong:
        print("An uncaught mutation is a missing vector, not a bug in this file.")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main())
