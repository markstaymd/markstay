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
from dataclasses import dataclass
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
    # Experimental third contextual signal (PLAN_HEADING_PATH_EVIDENCE): the
    # enclosing heading titles at annotation time. No spec field carries this;
    # it is here to be measured. Empty means "not stored", which every arm must
    # treat as "no heading evidence" rather than as "the empty path".
    heading_path: tuple[str, ...] = ()

    @property
    def nquote(self) -> str:
        return normalize(self.quote)


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
    """Rank candidate block bodies against a selector.

    Returns (best_index, best_score, runner_up_score). The runner-up is returned
    so the resolver can require a margin: a confident recovery needs not just a
    high score but a *clear winner*, which is how "surface, don't guess" is
    enforced for genuinely ambiguous re-attachment.

    The heading arguments are the experiment (`../../PLAN_HEADING_PATH_EVIDENCE`
    in the umbrella). With `candidate_paths=None` and the defaults this is
    bit-identical to the shipped resolver.

    `heading_bonus`  added to a candidate whose heading path equals the stored
                     one, alongside the existing prefix/suffix context bonus.
    `heading_penalty` the same preference expressed the other way up: subtracted
                     from a candidate whose path *differs*. The two differ by a
                     constant only in the ranking, and that constant is the
                     whole point. A bonus raises scores, so on a document where
                     every candidate matches (a single-section document, the
                     negative control) it is not a no-op: it pushes matched
                     scores into the 1.0 ceiling, collapses the margin, and
                     detaches. A penalty can only lower a *mismatched*
                     candidate, so it cannot move a document with one section,
                     cannot lift anything over the commit threshold, and cannot
                     reach the clamp's ceiling.
    `heading_gate`   minimum *body* score before the heading bonus applies. Set
                     to the commit threshold it makes the bonus a pure
                     tiebreaker: it can reorder candidates that already clear
                     the bar on their own text and can never lift a weak body
                     match over it. At 0.0 the bonus is ungated, which is the
                     form the cross-section audit measured.
    `heading_filter` revdown's hard gate: only equal-path candidates compete.
                     Cheap to run and unshippable as written, since SPEC.md §2.2
                     requires a stay to survive movement within a document.
    `clamp`          the shipped behaviour: clamp the best and runner-up score
                     individually to 1.0 *before* the caller's margin test.
                     Ranking is unaffected either way (clamping is monotonic);
                     what changes is the margin, and a collapsed margin detaches.
    """
    # An anchor with no stored path has no heading evidence, so every heading
    # argument is inert for it. That is what keeps a bonus arm from rewarding
    # candidates for matching the empty path.
    spath = canonical_path(sel.heading_path) if sel.heading_path else None
    cpaths = (
        [canonical_path(p) for p in candidate_paths]
        if candidate_paths is not None and spath is not None
        else None
    )

    scored = []
    for i, c in enumerate(candidates):
        s = body_score(sel, c)
        prev_text = candidates[i - 1] if i > 0 else ""
        next_text = candidates[i + 1] if i + 1 < len(candidates) else ""
        total = s + context_bonus(sel, prev_text, next_text)
        if cpaths is not None:
            match = cpaths[i] == spath
            if heading_filter and not match:
                continue
            if s >= heading_gate:
                if heading_bonus and match:
                    total += heading_bonus
                if heading_penalty and not match:
                    total -= heading_penalty
        scored.append((total, i))
    if not scored:
        return -1, 0.0, 0.0
    scored.sort(reverse=True)
    best_score, best_index = scored[0]
    runner_up = scored[1][0] if len(scored) > 1 else 0.0
    if not clamp:
        return best_index, best_score, runner_up
    # Clamp the context bonus back out of the reported score's ceiling at 1.0.
    return best_index, min(best_score, 1.0), min(runner_up, 1.0)
