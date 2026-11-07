"""The §9.1 ladder as spec v1.10 and package family 0.14.0 shipped it, frozen.

`resolver.py` is the live reference and changes with the spec. The evals that
compare arms, and the dated records they wrote, measured this ladder, so they read
it from here: an arm's control and a published number must not move because the
reference did. `excl_arms`, `heading_arms`, `twin_corpus`, `measure_context`,
`clamp_on_sections`, `llm/llm_attach`, `llm/run_llm_attach_eval` and `eval/replay`
import this module. `run_attach_eval`, `test_attach`, `llm/demo` and `conformance/*`
stay on `resolver.py`, because they describe what ships.

`resolve` and `_ambiguous_candidates` are `resolver.py`'s, and `resolve_variant` and
its scoring helpers (`body_score_variant`, `context_bonus_variant`, `anchors_variant`)
are `conformance/mutation_check.py`'s, byte for byte at the commit that froze them, the
default thresholds with them. The helpers are copied rather than imported because
`mutation_check.py` moves with the spec, and `twin_corpus`, `measure_context` and
`clamp_on_sections` price mutations through them. Do not fix anything here.

What is frozen is the ladder, not everything beneath it. `Anchor`, `Resolution` and
`build_anchors` are imported from `resolver.py`, parsing, hashing and quote
scoring come from the linter and `quote.py`, and the harnesses' edits from `perturb.py`; `heading_arms` also builds its cases
through the live `run_attach_eval.run_case`, passing this `resolve` in. A change in
any of those moves frozen outputs. Only `results_exclusivity.json` and
`results_context.json` are pinned by regeneration (`test_excl_arms.py`), and a change that only another harness reads,
such as stored heading evidence, passes that pin, so regenerate the affected
harness and compare when one of them changes.
"""

from __future__ import annotations

import re

import quote as Q
from quote import Candidate, rank_candidates
from resolver import L, Anchor, Resolution, build_anchors

__all__ = [
    "DEFAULT_HEADING_BONUS", "DEFAULT_MARGIN", "DEFAULT_THRESHOLD", "HEADING_MODES",
    "Anchor", "L", "Resolution", "build_anchors", "resolve", "resolve_variant",
]

DEFAULT_THRESHOLD = 0.5
DEFAULT_MARGIN = 0.05

HEADING_MODES = ("off", "bonus", "penalty", "filter")
DEFAULT_HEADING_BONUS = 0.12


def _ambiguous_candidates(ranked: list[Candidate], margin: float) -> list[Candidate]:
    """Return only candidates that participated in the failed margin.

    ``unmatched`` returns no sub-threshold candidates at all. For ``ambiguous``,
    the first candidate and every rival within the required margin explain why
    the resolver refused to commit, while lower-ranked noise does not.
    """
    if not ranked:
        return []
    best = ranked[0].score
    return [c for c in ranked if best - c.score < margin]


def resolve(
    anchors: list[Anchor],
    after_md: str,
    threshold: float = DEFAULT_THRESHOLD,
    margin: float = DEFAULT_MARGIN,
    mode: str = "blank-line",
    heading_path: str = "off",
    heading_bonus: float = DEFAULT_HEADING_BONUS,
    heading_gate: float | None = None,
    clamp: bool = True,
) -> dict[str, Resolution]:
    """Resolve every anchor id against the edited document via the evidence
    ladder. Returns id -> Resolution. `mode` selects the block segmenter and MUST
    match the mode `build_anchors` used (SPEC.md §5).

    The last four arguments are the heading-path experiment and the clamp axis it
    is measured against. Defaults reproduce the shipped resolver exactly.
    `heading_path` is 'off' | 'bonus' | 'penalty' | 'filter'; `heading_gate`
    defaults to `threshold`, making the preference a tiebreaker among candidates
    that already clear the commit bar on body text alone (pass 0.0 for the
    ungated form)."""
    if heading_path not in HEADING_MODES:
        raise ValueError(f"unknown heading_path mode: {heading_path!r}")
    gate = threshold if heading_gate is None else heading_gate

    after_blocks = [b for b in L.parse_document(after_md, mode=mode) if b.index >= 0]
    bodies = [b.content for b in after_blocks]
    # The after-document needs its own paths: `best_match` compares an anchor's
    # stored path against where each *candidate* now sits, and candidates are
    # bare bodies with no structure attached.
    after_paths = (
        L.heading_paths(after_md, after_blocks) if heading_path != "off" else None
    )

    # Tier 1 lookup: ids whose marker is still attached, mapped to block index.
    surviving: dict[str, int] = {}
    for idx, b in enumerate(after_blocks):
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                surviving.setdefault(mk.id, idx)

    # Tier 2 lookup: full-body hash -> block indices (list, to detect ambiguity).
    hash_to_idx: dict[str, list[int]] = {}
    for idx, body in enumerate(bodies):
        hash_to_idx.setdefault(L.body_hash(body), []).append(idx)

    out: dict[str, Resolution] = {}
    for a in anchors:
        # Tier 1: marker survived.
        if a.id in surviving:
            out[a.id] = Resolution(a.id, "marker", surviving[a.id], 1.0)
            continue
        # Tier 2: body hash uniquely identifies a surviving block.
        hits = hash_to_idx.get(a.hash, [])
        if len(hits) == 1:
            out[a.id] = Resolution(a.id, "hash", hits[0], 1.0)
            continue
        # Tier 3: quote recovery, committed only on a clear winner.
        ranked = rank_candidates(
            a.selector,
            bodies,
            candidate_paths=after_paths,
            heading_bonus=heading_bonus if heading_path == "bonus" else 0.0,
            heading_penalty=heading_bonus if heading_path == "penalty" else 0.0,
            heading_filter=heading_path == "filter",
            heading_gate=gate,
            clamp=clamp,
        )
        idx = ranked[0].target if ranked else -1
        score = ranked[0].score if ranked else 0.0
        runner = ranked[1].score if len(ranked) > 1 else 0.0
        if idx >= 0 and score >= threshold and (score - runner) >= margin:
            out[a.id] = Resolution(a.id, "quote", idx, score, runner_up_score=runner)
        elif idx >= 0 and score >= threshold:
            out[a.id] = Resolution(
                a.id,
                "detached",
                None,
                score,
                reason="ambiguous",
                candidates=_ambiguous_candidates(ranked, margin),
                runner_up_score=runner,
            )
        else:
            # Deliberate policy: an unmatched result never returns sub-threshold
            # candidates. Listing them would make rejected noise look actionable.
            out[a.id] = Resolution(
                a.id,
                "detached",
                None,
                score,
                reason="unmatched",
                runner_up_score=runner,
            )
    return out


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
    anchors = build_anchors(before)
    if store_whole_neighbour:
        stored = {a["id"]: a for a in anchors_variant(before, store_whole_neighbour=True)}
        anchors = [
            Anchor(id=a.id, hash=a.hash,
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
