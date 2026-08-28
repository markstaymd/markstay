"""Quote / selector recovery for the attachment-survival eval.

When a markstay marker detaches (the AI-regeneration failure mode: the agent
rewrites the document and drops the `<!-- stay:... -->` comment), the id has to
be re-found from *evidence about the text*, not from the marker. The spec's
recovery evidence is a W3C `TextQuoteSelector`-style triple:

    quote   the block's own text (the exact selector)
    prefix  up to 48 characters of the block immediately before it
    suffix  up to 48 characters of the block immediately after it

This module scores how well a stored selector matches a candidate block in the
edited document. It is deliberately dependency-free (stdlib `difflib`) so the
eval has no install step, mirroring the linter and the marker-survival harness.

Design notes
------------
* The dominant signal is body similarity (`difflib.SequenceMatcher.ratio` over
  normalized text). It degrades gracefully: a small in-place paraphrase keeps a
  high ratio, a split keeps a partial ratio on the surviving half, an unrelated
  block scores near zero. That graded behaviour is exactly what lets a threshold
  sweep expose the precision/recall trade-off of the resolution model.
* prefix/suffix are a *tiebreaker*, not a primary key. Two structurally
  identical blocks (e.g. repeated boilerplate) are separated by which one's
  neighbours match the stored context. This is the W3C rationale for carrying
  context at all.
"""

from __future__ import annotations

import re
import string
import sys
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

# The heading-path experiment compares paths with the linter's
# `canonical_heading`, rather than re-deriving the rule here: one definition,
# same reason `resolver.py` reuses `parse_document` instead of reimplementing
# marker grammar.
_LINTER = Path(__file__).resolve().parents[2] / "linter"
if str(_LINTER) not in sys.path:
    sys.path.insert(0, str(_LINTER))
from markstay_lint import canonical_heading  # noqa: E402

# How much neighbour context to keep on each side. Short enough to stay cheap,
# long enough to disambiguate repeated blocks. SPEC.md §9 pins this value; the
# spec records the number this eval measured.
CONTEXT_CHARS = 48


def window_prefix(text: str) -> str:
    """The last CONTEXT_CHARS characters of a preceding neighbour (SPEC.md §9:
    prefix/suffix "carry up to 48 characters of the neighbour on each side").

    Applied on both sides of the comparison, and applied to the *raw* text before
    normalization, because the candidate side has always windowed raw text and the
    two sides must window identically to compare like with like. Windowing after
    normalization would let whitespace collapse change how much text survives."""
    return text[-CONTEXT_CHARS:]


def window_suffix(text: str) -> str:
    """The first CONTEXT_CHARS characters of a following neighbour. See
    `window_prefix` for why this runs on raw text."""
    return text[:CONTEXT_CHARS]

# §9 matching normalization is pinned to ASCII for exact cross-implementation
# agreement (SPEC.md §9, SPEC_DECISIONS.md): lowercase only ASCII A-Z and collapse
# only ASCII whitespace. Non-ASCII characters pass through unchanged and identical
# in every implementation. Recovery is evidence, not identity (§2.1), so an
# ASCII-only fold is sufficient and avoids the Unicode casefold / `\s` divergences
# between languages.
_ASCII_WS = " \t\n\r\f\v"
_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)


def normalize(text: str) -> str:
    """Lowercase ASCII letters and collapse ASCII whitespace runs to a single
    space, then trim (SPEC.md §9). Capitalization and reflowed line breaks (very
    common after an LLM edit) must not register as differences. ASCII-only so a
    second implementation reproduces it exactly without Unicode case data."""
    return re.sub(r"[ \t\n\r\f\v]+", " ", text.strip(_ASCII_WS)).translate(_ASCII_LOWER)


@dataclass
class Selector:
    """Recovery evidence stored for one block at annotation time."""
    quote: str            # the block body (the exact selector)
    prefix: str = ""      # trailing context of the previous block
    suffix: str = ""      # leading context of the next block
    # Experimental third contextual signal, measured but never specified: the
    # enclosing heading titles at annotation time. No spec field carries this;
    # it is here to be measured. Empty means "not stored", which every arm must
    # treat as "no heading evidence" rather than as "the empty path".
    heading_path: tuple[str, ...] = ()

    @property
    def nquote(self) -> str:
        return normalize(self.quote)


@dataclass(frozen=True)
class Evidence:
    """One non-normative explanation of a candidate's score."""

    code: str
    label: str
    contribution: float


@dataclass(frozen=True)
class Candidate:
    """A diagnostic candidate, ranked without implying an attachment."""

    target: int
    score: float
    evidence: tuple[Evidence, ...] = field(default_factory=tuple)
    provenance: str = "independent-per-anchor"


def _ratio(a: str, b: str) -> float:
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b, autojunk=False).ratio()


def body_score(sel: Selector, candidate: str) -> float:
    """Similarity of a stored selector's quote to a candidate block body, in
    [0, 1]. Exact containment (the candidate is verbatim inside the quote or vice
    versa, the split / merge case) floors the score at the length ratio of the
    shorter to the longer, so a surviving half of a split paragraph cannot score
    arbitrarily low just because half its text went elsewhere."""
    q, c = sel.nquote, normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    base = _ratio(q, c)
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if short and short in long:
        base = max(base, len(short) / len(long))
    return base


def context_bonus(sel: Selector, prev_text: str, next_text: str) -> float:
    """Small additive bonus in [0, ~0.1] when the candidate's neighbours match
    the stored prefix/suffix. Used only to break near-ties between candidates
    that score equally on body.

    Both sides are windowed to CONTEXT_CHARS. Windowing the stored side is a
    no-op for a selector this version built, since `build_anchors` already stores
    a windowed field; it matters for a selector built by an older version or
    assembled by a consumer, which would otherwise be scored against a windowed
    candidate and lose bonus purely to the asymmetry."""
    bonus = 0.0
    if sel.prefix:
        bonus += 0.05 * _ratio(normalize(window_prefix(sel.prefix)),
                               normalize(window_prefix(prev_text)))
    if sel.suffix:
        bonus += 0.05 * _ratio(normalize(window_suffix(sel.suffix)),
                               normalize(window_suffix(next_text)))
    return bonus


def canonical_path(path) -> tuple[str, ...]:
    """A heading path in compare form: `canonical_heading` per component.

    Compared component by component and never as a joined string: a join leaves
    the delimiter and its escaping unspecified, and lets `["a/b"]` collide with
    `["a", "b"]`."""
    return tuple(canonical_heading(p) for p in path)


def rank_candidates(
    sel: Selector,
    candidates: list[str],
    candidate_paths: list | None = None,
    heading_bonus: float = 0.0,
    heading_penalty: float = 0.0,
    heading_filter: bool = False,
    heading_gate: float = 0.0,
    clamp: bool = True,
    targets: list[int] | None = None,
    provenance: str = "independent-per-anchor",
) -> list[Candidate]:
    """Return every scored candidate in the resolver's exact historical order.

    Ranking deliberately remains ``(unclamped_score, candidate_index)``
    descending. The index tie-break is part of the shipped resolver's behaviour:
    equal scores choose the later candidate. ``targets`` lets callers scoring a
    subset retain document-global target indices without changing that order.

    The heading arguments retain the completed heading-path experiment's
    behaviour. Evidence codes and labels are diagnostics, not protocol or
    conformance data; their versioning belongs to the surface that serializes
    them.
    """
    if targets is not None and len(targets) != len(candidates):
        raise ValueError("targets and candidates must have the same length")
    # An anchor with no stored path has no heading evidence, so every heading
    # argument is inert for it. That is what keeps a bonus arm from rewarding
    # candidates for matching the empty path.
    spath = canonical_path(sel.heading_path) if sel.heading_path else None
    cpaths = (
        [canonical_path(p) for p in candidate_paths]
        if candidate_paths is not None and spath is not None
        else None
    )

    scored: list[tuple[float, int, tuple[Evidence, ...]]] = []
    for i, c in enumerate(candidates):
        s = body_score(sel, c)
        prev_text = candidates[i - 1] if i > 0 else ""
        next_text = candidates[i + 1] if i + 1 < len(candidates) else ""
        context = context_bonus(sel, prev_text, next_text)
        total = s + context
        evidence = [Evidence("body_similarity", "body similarity", s)]
        if sel.prefix:
            prefix = 0.05 * _ratio(
                normalize(window_prefix(sel.prefix)),
                normalize(window_prefix(prev_text)),
            )
            contextual = provenance != "independent-per-anchor"
            evidence.append(
                Evidence(
                    "candidate_prefix_context" if contextual else "prefix_context",
                    (
                        f"preceding candidate in {provenance.replace('-', ' ')}"
                        if contextual
                        else "preceding context"
                    ),
                    prefix,
                )
            )
        if sel.suffix:
            suffix = 0.05 * _ratio(
                normalize(window_suffix(sel.suffix)),
                normalize(window_suffix(next_text)),
            )
            contextual = provenance != "independent-per-anchor"
            evidence.append(
                Evidence(
                    "candidate_suffix_context" if contextual else "suffix_context",
                    (
                        f"following candidate in {provenance.replace('-', ' ')}"
                        if contextual
                        else "following context"
                    ),
                    suffix,
                )
            )
        if cpaths is not None:
            match = cpaths[i] == spath
            if heading_filter and not match:
                continue
            if s >= heading_gate:
                if heading_bonus and match:
                    total += heading_bonus
                    evidence.append(
                        Evidence("heading_path_bonus", "matching heading path", heading_bonus)
                    )
                if heading_penalty and not match:
                    total -= heading_penalty
                    evidence.append(
                        Evidence(
                            "heading_path_penalty",
                            "different heading path",
                            -heading_penalty,
                        )
                    )
        scored.append((total, i, tuple(evidence)))
    scored.sort(key=lambda row: (row[0], row[1]), reverse=True)
    return [
        Candidate(
            target=targets[i] if targets is not None else i,
            score=min(total, 1.0) if clamp else total,
            evidence=evidence,
            provenance=provenance,
        )
        for total, i, evidence in scored
    ]


def best_match(
    sel: Selector,
    candidates: list[str],
    candidate_paths: list | None = None,
    heading_bonus: float = 0.0,
    heading_penalty: float = 0.0,
    heading_filter: bool = False,
    heading_gate: float = 0.0,
    clamp: bool = True,
) -> tuple[int, float, float]:
    """Compatibility wrapper returning ``(index, score, runner-up score)``."""
    ranked = rank_candidates(
        sel,
        candidates,
        candidate_paths=candidate_paths,
        heading_bonus=heading_bonus,
        heading_penalty=heading_penalty,
        heading_filter=heading_filter,
        heading_gate=heading_gate,
        clamp=clamp,
    )
    if not ranked:
        return -1, 0.0, 0.0
    runner_up = ranked[1].score if len(ranked) > 1 else 0.0
    return ranked[0].target, ranked[0].score, runner_up
