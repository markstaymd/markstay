"""The markstay attachment resolver.

The marker-survival eval answered "does the *id token* survive an LLM edit?".
This answers the harder question the spec actually rests on: after an edit that
moves, splits, merges, edits, or deletes blocks, can a tool re-attach each
original id to the *correct* block, and does it refuse to guess when it cannot?

The resolution model is the three-field split from SPEC.md §2.1:

    id     stable identity (answers *which block*)
    hash   drift detection (answers *did the body change*)
    quote  recovery evidence (answers *where did it go* when the marker is lost)

The resolver applies them as a priority ladder, strongest evidence first, and
assigns exclusively (SPEC.md §9.1 from v1.11). Every stay still unresolved is
evaluated at a tier before any commit at that tier takes effect, and a block
committed at a tier is *claimed* for the weaker tiers:

    1. MARKER  the id's marker is still present in the edited doc -> trust it.
               On two or more blocks, resolve among those carriers only: the
               one whose body hash is the stored hash if exactly one is, else
               §9's commit rule over the carriers, else DETACHED. A duplicated
               id never reaches the weaker tiers.
    2. HASH    no marker; the stored hash was recorded by exactly one stay and
               exactly one unclaimed block has it -> the content survived
               verbatim, just lost its marker.
    3. QUOTE   rank every block, claimed or not. The target is the best
               unclaimed block, the runner-up the best other block, claimed or
               not, and only a *clear* winner commits (score over threshold AND
               a margin over the runner-up). Stays selecting one target all
               commit if their quotes occupy disjoint places in it (a clean
               merge), and all go DETACHED (`contested`) otherwise, or when
               there are more than 16 of them.

DETACHED is a first-class, correct outcome: the spec says a marker that cannot
be confidently placed must be surfaced as outdated, never silently reattached to
a nearby block. The eval scores a confident wrong attachment as the worst result
and a DETACHED-when-truly-gone as correct.

Marker parsing and hashing are reused from the reference linter, not
reimplemented (per the handover): `parse_document`, `body_hash`, `normalize_body`.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the reference linter's parser/hasher rather than re-deriving marker
# grammar. The linter lives two dirs up under linter/.
_LINTER = Path(__file__).resolve().parents[2] / "linter"
if str(_LINTER) not in sys.path:
    sys.path.insert(0, str(_LINTER))
import markstay_lint as L  # noqa: E402

from quote import (  # noqa: E402
    Candidate,
    Selector,
    normalize,
    rank_candidates,
    window_prefix,
    window_suffix,
)

# Default thresholds for the QUOTE tier. A recovery is committed only when the
# best candidate clears `threshold` AND beats the runner-up by `margin`.
DEFAULT_THRESHOLD = 0.5
DEFAULT_MARGIN = 0.05


HEADING_MODES = ("off", "bonus", "penalty", "filter")
# revdown's constant, kept as the default so the arms start where the borrowed
# design sits. Phase 3 sweeps it rather than trusting it.
DEFAULT_HEADING_BONUS = 0.12


@dataclass
class Anchor:
    """Everything stored about one original block at annotation time. In a real
    markstay tool this is what the marker plus a side index would carry."""

    id: str
    hash: str  # full sha256 of the normalized body
    selector: Selector  # quote + prefix/suffix recovery evidence

    @property
    def heading_path(self) -> tuple[str, ...]:
        """The enclosing section at annotation time, carried on the selector
        because it is recovery evidence of the same kind as prefix/suffix."""
        return self.selector.heading_path


@dataclass
class Resolution:
    id: str
    method: str  # 'marker' | 'hash' | 'quote' | 'detached'
    target: int | None  # content-block index in the after-doc, or None
    score: float  # confidence in [0, 1] (1.0 for marker/hash)
    reason: str | None = None  # detached only: ambiguous | unmatched | contested
    candidates: list[Candidate] = field(default_factory=list)
    runner_up_score: float = 0.0


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


def build_anchors(before_md: str, mode: str = "blank-line") -> list[Anchor]:
    """Extract anchors from an annotated baseline document. Each non-orphan block
    with a well-formed marker contributes one anchor carrying the block's hash
    and a quote selector built from the block and its neighbours.

    `mode` selects the block segmenter (SPEC.md §5): 'blank-line' (default) or
    'commonmark' (§5.2, whole loose lists / blank-line fences). It MUST match the
    mode passed to `resolve`."""
    blocks = [b for b in L.parse_document(before_md, mode=mode) if b.index >= 0]
    # Experimental third contextual signal, stored whether or not any caller
    # asks for it: an anchor built with `--heading-path off` and one built with
    # it on must be the same anchor, or the arms would differ by what was
    # recorded rather than by how it was used.
    paths = L.heading_paths(before_md, blocks)
    anchors: list[Anchor] = []
    for i, b in enumerate(blocks):
        prev_text = blocks[i - 1].content if i > 0 else ""
        next_text = blocks[i + 1].content if i + 1 < len(blocks) else ""
        # SPEC.md §9: the stored prefix/suffix carry up to 48 characters of the
        # neighbour on each side. Storing the whole block instead caps the
        # achievable ratio near 2*48/(len+48), because the candidate side is
        # windowed at match time, so a perfectly preserved long neighbour scored
        # well under the 0.05 it should.
        sel = Selector(
            quote=b.content,
            prefix=window_prefix(prev_text),
            suffix=window_suffix(next_text),
            heading_path=tuple(paths[i]),
        )
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                anchors.append(
                    Anchor(
                        id=mk.id,
                        hash=L.body_hash(b.content),
                        selector=sel,
                    )
                )
    return anchors


# SPEC.md §9.1: a merge exemption with more contenders than this fails. The
# subset search below is exponential in the count; at the defaults no more than
# four contenders can reach it (each needs a quote at least a quarter of the
# block's length), so the cap only binds at a caller's lower threshold, where it
# fails closed and lets every implementation agree without a big-integer mask.
MERGE_CONTENDER_CAP = 16


def disjoint_in(body: str, quotes: list[str]) -> bool:
    """SPEC.md §9.1's merge test: can every quote be placed verbatim inside
    `body` at its own half-open span, no two spans overlapping? Both sides are
    already normalized by §9. Two equal quotes need two occurrences.

    The cap and the length check come first. Then a dynamic programme over
    subsets of the contenders: `end[S]` is the smallest offset by which every
    quote in S fits, pairwise disjoint, inside `body[:end[S]]`; `end[{}]` is 0 and
    `end[S]` is the minimum over i in S of `find(q_i, end[S - {i}]) + len(q_i)`.
    Any disjoint placement reads left to right, and the earliest occurrence after
    the previous end never ends later than another choice, so the programme is
    exact, where a greedy first match depends on the order the contenders arrive
    in (`abcd` and `bcde` fit `abcdef abcd` only if `abcd` takes its second
    occurrence). Offsets are code points."""
    if len(quotes) > MERGE_CONTENDER_CAP:
        return False
    if not all(quotes):
        return False
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


def _commit_rule(
    a_id: str,
    ranked: list[Candidate],
    threshold: float,
    margin: float,
    method: str,
) -> Resolution:
    """§9's commit rule on a ranking whose first entry is the target and whose
    second is the runner-up. `method` names the tier a commit is reported under."""
    idx = ranked[0].target if ranked else -1
    score = ranked[0].score if ranked else 0.0
    runner = ranked[1].score if len(ranked) > 1 else 0.0
    if idx >= 0 and score >= threshold and (score - runner) >= margin:
        return Resolution(a_id, method, idx, score, runner_up_score=runner)
    if idx >= 0 and score >= threshold:
        return Resolution(
            a_id,
            "detached",
            None,
            score,
            reason="ambiguous",
            candidates=_ambiguous_candidates(ranked, margin),
            runner_up_score=runner,
        )
    # Deliberate policy: an unmatched result never returns sub-threshold
    # candidates. Listing them would make rejected noise look actionable.
    return Resolution(
        a_id, "detached", None, score, reason="unmatched", runner_up_score=runner
    )


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
    ladder, assigning exclusively (SPEC.md §9.1). Returns id -> Resolution.
    `mode` selects the block segmenter and MUST match the mode `build_anchors`
    used (SPEC.md §5).

    The last four arguments are the heading-path experiment and the clamp axis it
    is measured against. Defaults reproduce the specified resolver exactly; they
    change only how each block is scored, never the assignment rules.
    `heading_path` is 'off' | 'bonus' | 'penalty' | 'filter'; `heading_gate`
    defaults to `threshold`, making the preference a tiebreaker among candidates
    that already clear the commit bar on body text alone (pass 0.0 for the
    ungated form). The ladder as v1.10 shipped it is `ladder_v110.resolve`.

    Before tier 1 the anchors collapse to one per id, the last one read, so a
    baseline that repeats an id (a §7 error) resolves that anchor at every tier
    and "recorded by exactly one stay" counts distinct ids."""
    if heading_path not in HEADING_MODES:
        raise ValueError(f"unknown heading_path mode: {heading_path!r}")
    gate = threshold if heading_gate is None else heading_gate
    # One anchor per id before any tier, the last read, kept at the id's first
    # position. A baseline that repeats an id is a §7 error; without this, tier 2
    # would count one stay's hash twice and could commit an earlier anchor that
    # tier 1 and tier 3 never see.
    anchors = list({a.id: a for a in anchors}.values())

    after_blocks = [b for b in L.parse_document(after_md, mode=mode) if b.index >= 0]
    bodies = [b.content for b in after_blocks]
    # The after-document needs its own paths: `best_match` compares an anchor's
    # stored path against where each *candidate* now sits, and candidates are
    # bare bodies with no structure attached.
    after_paths = (
        L.heading_paths(after_md, after_blocks) if heading_path != "off" else None
    )

    def ranking(a: Anchor) -> list[Candidate]:
        """Every block ranked against the whole document, so context compares
        each candidate with its physical neighbours whatever is claimed."""
        return rank_candidates(
            a.selector,
            bodies,
            candidate_paths=after_paths,
            heading_bonus=heading_bonus if heading_path == "bonus" else 0.0,
            heading_penalty=heading_bonus if heading_path == "penalty" else 0.0,
            heading_filter=heading_path == "filter",
            heading_gate=gate,
            clamp=clamp,
        )

    # Tier 1 lookup: every block carrying each id's marker, in document order.
    carriers: dict[str, list[int]] = {}
    for idx, b in enumerate(after_blocks):
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                on = carriers.setdefault(mk.id, [])
                if idx not in on:
                    on.append(idx)

    out: dict[str, Resolution] = {}

    # Tier 1: the marker. A commit among several carriers is still tier 1: the
    # marker is the evidence that limits the pool, hash and quote only choose
    # within it. Claims do not apply here, since §5 lets one block carry several
    # stays, so the order anchors are visited in cannot matter.
    for a in anchors:
        on = carriers.get(a.id)
        if not on:
            continue
        if len(on) == 1:
            out[a.id] = Resolution(a.id, "marker", on[0], 1.0)
            continue
        hits = [i for i in on if L.body_hash(bodies[i]) == a.hash]
        if len(hits) == 1:
            out[a.id] = Resolution(a.id, "marker", hits[0], 1.0)
            continue
        among = set(on)
        out[a.id] = _commit_rule(
            a.id, [c for c in ranking(a) if c.target in among], threshold, margin,
            "marker",
        )
    claimed = {r.target for r in out.values() if r.target is not None}

    # Tier 2: a hash recorded by one stay, carried by one unclaimed block. Two
    # stays can never propose one block here, because both would have recorded
    # its hash, so this tier needs no contest.
    hash_to_idx: dict[str, list[int]] = {}
    for idx, body in enumerate(bodies):
        hash_to_idx.setdefault(L.body_hash(body), []).append(idx)
    recorded: dict[str, int] = {}
    for a in anchors:
        recorded[a.hash] = recorded.get(a.hash, 0) + 1
    hash_commits: dict[str, int] = {}
    for a in anchors:
        if a.id in out or recorded[a.hash] != 1:
            continue
        hits = [h for h in hash_to_idx.get(a.hash, []) if h not in claimed]
        if len(hits) == 1:
            hash_commits[a.id] = hits[0]
    for aid, t in hash_commits.items():
        out[aid] = Resolution(aid, "hash", t, 1.0)
        claimed.add(t)

    # Tier 3: quote recovery. The target must be unclaimed; a claimed block still
    # counts as the runner-up, so claiming a rival cannot open a margin.
    pending: dict[str, Resolution] = {}
    for a in anchors:
        if a.id in out:
            continue
        ranked = ranking(a)
        free = next((c for c in ranked if c.target not in claimed), None)
        if free is None:
            pending[a.id] = Resolution(a.id, "detached", None, 0.0, reason="unmatched")
            continue
        ranked = [free] + [c for c in ranked if c.target != free.target]
        pending[a.id] = _commit_rule(a.id, ranked, threshold, margin, "quote")

    by_target: dict[int, list[str]] = {}
    for aid, r in pending.items():
        if r.method == "quote":
            by_target.setdefault(r.target, []).append(aid)
    quotes = {a.id: a.selector.nquote for a in anchors}
    for t, aids in by_target.items():
        if len(aids) == 1 or disjoint_in(normalize(bodies[t]), [quotes[i] for i in aids]):
            continue
        for aid in aids:
            r = pending[aid]
            pending[aid] = Resolution(
                aid, "detached", None, r.score, reason="contested",
                runner_up_score=r.runner_up_score,
            )
    out.update(pending)
    return out
