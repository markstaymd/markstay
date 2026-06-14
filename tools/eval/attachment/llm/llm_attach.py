"""LLM-driven attachment-survival eval: the low-similarity regime.

The deterministic attachment eval (`../`) measures the resolution model under
edits whose block-to-block mapping is known exactly, but its hardest synthetic
rewrite (`heavy_paraphrase`) still keeps ~0.7 text similarity. The genuinely hard
case the spec's §9 quote tier exists for, a real agent rewriting prose down to
0.2-0.5 similarity, was untested. This module closes that gap with real LLM
rewrites while keeping ground truth judge-free.

The trick (judge-free ground truth from one generation)
-------------------------------------------------------
1. Annotate a clean doc: every block gets a `stay:` marker (`perturb.annotate`).
2. Ask an LLM to rewrite the prose, freely and aggressively, WITH the §11
   preservation instruction so it keeps every marker attached to the same block.
   The marker-survival eval showed an *instructed* rewrite keeps ~100% of markers,
   so the preserved marker placement is a trustworthy gold label for "where did
   this block's content go".
3. `lint_diff(before, after)` validates that label: any id the model dropped,
   duplicated, or relocated is excluded from scoring (no clean ground truth).
4. STRIP those markers from the exact same rewritten text. That stripped doc is
   the resolver's input, identical to what a *naive* rewrite (which drops markers,
   the real failure mode) would have produced. The resolver must now recover each
   original id from hash + quote alone, with no marker to lean on.
5. Score the resolver's recovered block against the gold block, and bucket every
   id by the *measured* before/after text similarity of its block.

The result the deterministic eval could not produce: recovery and false-attach
rate as a function of real rewrite similarity, down into the low-similarity regime
that stress-tests SPEC.md §9 (48-char context, threshold 0.5, margin 0.05).

No judge, no human: ground truth is the model's own preserved-marker placement,
validated deterministically by the linter. Dropped/duplicated ids are reported,
not guessed at.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

# attachment/ (resolver, quote, perturb) and eval/ (providers) on the path.
_ATTACH = Path(__file__).resolve().parents[1]
_EVAL = Path(__file__).resolve().parents[2]
for p in (str(_ATTACH), str(_EVAL)):
    if p not in sys.path:
        sys.path.insert(0, p)

import perturb as PB  # noqa: E402
import resolver as R  # noqa: E402
import markstay_lint as L  # noqa: E402  (path set up by resolver import)
from quote import normalize  # noqa: E402


# --- rewrite tasks: a spread of intensities to span the similarity range ----
# Each keeps blocks 1:1 (same set, same order) so the per-block similarity and
# the id->block ground truth stay clean; intensity drives how far the wording
# drifts. "restructure" is the point of the whole eval: low-similarity prose.
TASKS = {
    "copyedit": (
        "Lightly copy-edit the following Markdown document: fix grammar, "
        "awkward phrasing, and punctuation only. Keep the wording almost "
        "entirely intact."
    ),
    "rewrite": (
        "Rewrite the following Markdown document to be clearer and more "
        "concise. Rephrase sentences freely, but keep the same meaning."
    ),
    "restructure": (
        "Aggressively rewrite the following Markdown document. Reword every "
        "sentence substantially, change the phrasing and sentence order within "
        "each block, and use different vocabulary, while preserving the meaning "
        "of each block."
    ),
    "reword": (
        "Rewrite the following Markdown document in a formal, academic register. "
        "Replace as much of the everyday vocabulary as possible with more formal "
        "synonyms and recast every sentence's structure, so the wording differs "
        "as much as possible from the original while the meaning of each block is "
        "exactly preserved. Maximize lexical change."
    ),
}

STRUCTURE = (
    "\n\nKeep the document's block structure unchanged: the same blocks in the "
    "same order, one-to-one. Do not split, merge, add, reorder, or delete "
    "blocks, headings, lists, code blocks, or tables. Leave code blocks and "
    "tables exactly as they are."
)

# The SPEC.md §11 AI-editing contract, as an instruction. This is what makes the
# preserved markers a valid ground-truth label.
PRESERVE = (
    "\n\nThe document contains marker comments of the form "
    "`<!-- stay:ID hash=sha256:HEX -->` that identify each block. Preserve every "
    "marker exactly as written and keep it immediately after the same block it "
    "currently follows. Do not remove, alter, renumber, relocate, or add markers."
)

RETURN_ONLY = (
    "\n\nReturn only the resulting Markdown, with no commentary or code fences "
    "around the whole document."
)


def build_prompt(task_key: str, annotated_md: str) -> str:
    return (TASKS[task_key] + STRUCTURE + PRESERVE + RETURN_ONLY
            + "\n\n---\n\n" + annotated_md)


# --- output cleanup ---------------------------------------------------------

def strip_outer_fence(text: str) -> str:
    """Some models wrap the whole document in a ```markdown fence despite the
    instruction. Peel a single outer fence if the entire reply is one."""
    t = text.strip()
    if t.startswith("```"):
        first_nl = t.find("\n")
        if first_nl != -1 and t.endswith("```"):
            inner = t[first_nl + 1:-3]
            # only treat as an outer wrapper if the opener was a bare fence line
            if "\n" in t[:first_nl] or t[:first_nl].strip("`").isalpha() or t[:first_nl].strip() == "```":
                return inner.strip()
    return t


def strip_markers(md: str) -> str:
    """Remove every markstay marker token, leaving the prose. This reproduces the
    naive-rewrite output (markers dropped) from the instructed rewrite."""
    return L.MDX_MARKER.sub("", L.HTML_MARKER.sub("", md))


# --- ground truth from preserved markers ------------------------------------

@dataclass
class GroundTruth:
    id_to_idx: dict[str, int]       # gold: original id -> after content-block index
    dropped: set[str]               # ids the rewrite lost (no gold; excluded)
    duplicated: set[str]            # ids the rewrite duplicated (excluded)
    relocated: set[str]             # ids swapped onto other content (excluded)
    after_bodies: list[str]         # content-block bodies of the stripped after-doc


def ground_truth(before_md: str, after_with_markers: str) -> GroundTruth:
    """Build the gold id->block map from the markers the instructed rewrite kept,
    excluding any id the linter's regeneration diff flags as unsafe."""
    diff = L.lint_diff(before_md, after_with_markers)
    dropped = {f.id for f in diff if f.code == "DROPPED_ID" and f.id}
    duplicated = {f.id for f in diff if f.code == "DUPLICATED_ID" and f.id}
    relocated = {f.id for f in diff if f.code == "RELOCATED_ID" and f.id}
    bad = dropped | duplicated | relocated

    marked_blocks = [b for b in L.parse_document(after_with_markers) if b.index >= 0]
    id_to_idx: dict[str, int] = {}
    for b in marked_blocks:
        for mk in b.markers:
            if mk.id and not mk.malformed and mk.id not in bad:
                id_to_idx.setdefault(mk.id, b.index)

    # The resolver operates on the STRIPPED doc; its block indices must line up
    # with the marked parse. parse_document strips markers from Block.content, so
    # the content-block sequence is identical, assert it to catch any drift.
    stripped = strip_markers(after_with_markers)
    stripped_blocks = [b for b in L.parse_document(stripped) if b.index >= 0]
    assert len(stripped_blocks) == len(marked_blocks), (
        f"block-count mismatch after stripping markers: "
        f"{len(stripped_blocks)} vs {len(marked_blocks)}")
    for mb, sb in zip(marked_blocks, stripped_blocks):
        assert normalize(mb.content) == normalize(sb.content), \
            "stripped block content diverged from marked block content"

    return GroundTruth(id_to_idx, dropped, duplicated, relocated,
                       [b.content for b in stripped_blocks])


# --- similarity (same normalization the quote tier uses) --------------------

def similarity(a: str, b: str) -> float:
    na, nb = normalize(a), normalize(b)
    if not na or not nb:
        return 0.0
    return SequenceMatcher(None, na, nb, autojunk=False).ratio()


BANDS = [(0.0, 0.3), (0.3, 0.5), (0.5, 0.7), (0.7, 0.9), (0.9, 1.01)]


def band_label(s: float) -> str:
    for lo, hi in BANDS:
        if lo <= s < hi:
            top = "1.0" if hi > 1.0 else f"{hi:.1f}"
            return f"{lo:.1f}-{top}"
    return "1.0-1.0"


# --- scoring one rewritten document -----------------------------------------

@dataclass
class IdResult:
    id: str
    cat: str            # correct | wrong | missed | no_truth
    method: str         # marker | hash | quote | detached
    score: float        # resolver confidence
    sim: float          # measured before/after text similarity of the block
    target: int | None
    gold: int | None


def score_document(before_md: str, after_with_markers: str,
                   threshold: float = R.DEFAULT_THRESHOLD,
                   margin: float = R.DEFAULT_MARGIN) -> list[IdResult]:
    """Resolve every original id against the stripped rewrite and score it against
    the preserved-marker gold mapping. Ids the rewrite dropped/duplicated/relocated
    are returned as `no_truth` (excluded from recovery metrics by the aggregator)."""
    anchors = R.build_anchors(before_md)
    gt = ground_truth(before_md, after_with_markers)
    stripped = strip_markers(after_with_markers)
    resolutions = R.resolve(anchors, stripped, threshold=threshold, margin=margin)

    # original id -> its before-block body, for the similarity measurement.
    before_body = {a.id: a.selector.quote for a in anchors}

    out: list[IdResult] = []
    for a in anchors:
        res = resolutions[a.id]
        gold = gt.id_to_idx.get(a.id)
        if gold is None:
            out.append(IdResult(a.id, "no_truth", res.method, res.score, 0.0,
                                res.target, None))
            continue
        sim = similarity(before_body[a.id], gt.after_bodies[gold])
        if res.method == "detached":
            cat = "missed"            # gold block exists, resolver safely gave up
        elif res.target == gold:
            cat = "correct"
        else:
            cat = "wrong"            # false reattachment, the dangerous outcome
        out.append(IdResult(a.id, cat, res.method, res.score, sim,
                            res.target, gold))
    return out


# --- aggregation ------------------------------------------------------------

def recovery_falserate(cats: dict[str, int]) -> tuple[float, float, int]:
    """recovery = correct / scored; false-rate = wrong / scored. `scored` excludes
    no_truth ids. Returns (recovery, false_rate, scored_n)."""
    scored = cats.get("correct", 0) + cats.get("wrong", 0) + cats.get("missed", 0)
    if not scored:
        return 0.0, 0.0, 0
    return cats.get("correct", 0) / scored, cats.get("wrong", 0) / scored, scored


def tally(results: list[IdResult]) -> dict[str, int]:
    cats: dict[str, int] = {}
    for r in results:
        cats[r.cat] = cats.get(r.cat, 0) + 1
    return cats
