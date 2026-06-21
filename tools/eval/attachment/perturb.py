"""Deterministic block-level perturbations with known ground truth.

The marker-survival eval used real LLM edits, where "which output block is
original block 3?" is itself a fuzzy judgement. To measure the *resolution
model* we instead need edits whose block-to-block mapping is known exactly, so a
resolver's answer can be scored as right or wrong without a human or a judge in
the loop. These operators provide that: each transforms a list of identified
blocks and reports, per original id, which resulting block(s) are the correct
home (or that the block was deleted and the id must come back DETACHED).

Every operator is deterministic (no randomness) so the eval is reproducible.

The operators model the edit classes the spec's failure-mode list calls out:
reorder (moves), edit-in-place (drift), split, merge, delete (detachment), and
insert (distractors that must not lure a false re-attachment). Any operator can
be composed with marker stripping, which is the AI-regeneration case where the
resolver can no longer lean on the id token and must recover from hash + quote.
"""

from __future__ import annotations

import hashlib
import sys
from dataclasses import dataclass, field
from pathlib import Path

_LINTER = Path(__file__).resolve().parents[2] / "linter"
if str(_LINTER) not in sys.path:
    sys.path.insert(0, str(_LINTER))
import markstay_lint as L  # noqa: E402


@dataclass
class PBlock:
    """A content block carrying the original id(s) attached to it."""
    text: str
    ids: list[str] = field(default_factory=list)


def _h(s: str, n: int = 4) -> str:
    return hashlib.sha256(L.normalize_body(s).encode("utf-8")).hexdigest()[:n]


def block_id(index: int, text: str) -> str:
    """Deterministic, distinct, greppable id, e.g. 'b3-6484'. The hyphen is
    inside the linter's id charset, so these parse as well-formed markers."""
    return f"b{index}-{_h(text)}"


# --- block kinds (for choosing realistic edit targets) --------------------

def kind(text: str) -> str:
    t = text.lstrip()
    if t.startswith("#"):
        return "heading"
    if t.startswith("```"):
        return "code"
    if t.startswith("|"):
        return "table"
    first = t.splitlines()[0] if t.splitlines() else t
    if first[:2] in ("- ", "* ") or (first[:1].isdigit() and first[1:2] in (".", ")")):
        return "list"
    return "para"


def is_para(pb: PBlock) -> bool:
    return kind(pb.text) == "para"


# --- annotation -----------------------------------------------------------

def annotate(base_md: str) -> tuple[str, list[PBlock]]:
    """Assign an id to every block of a clean document and return the annotated
    baseline (markers inline) plus the PBlock list the operators mutate."""
    blocks = [b for b in L.parse_document(base_md) if b.index >= 0]
    pblocks = [PBlock(text=b.content, ids=[block_id(i, b.content)])
               for i, b in enumerate(blocks)]
    return serialize(pblocks, strip=False), pblocks


def serialize(pblocks: list[PBlock], strip: bool) -> str:
    """Render PBlocks back to a Markdown document. With `strip`, markers are
    omitted entirely (the AI-regeneration case); otherwise each id's marker,
    carrying a freshly computed hash, trails its block."""
    parts = []
    for pb in pblocks:
        if strip or not pb.ids:
            parts.append(pb.text)
        else:
            markers = "\n".join(
                f"<!-- stay:{mid} hash=sha256:{_h(pb.text)} -->" for mid in pb.ids)
            parts.append(pb.text + "\n" + markers)
    return "\n\n".join(parts) + "\n"


# --- ground truth ---------------------------------------------------------

def default_truth(pblocks: list[PBlock]) -> dict:
    """id -> {'accept': {positions}, 'preferred': position}. The default is that
    an id's only correct home is the block it now sits on; operators override
    this for splits (two acceptable children) and deletes (must detach)."""
    t: dict[str, dict] = {}
    for pos, pb in enumerate(pblocks):
        for mid in pb.ids:
            t[mid] = {"accept": {pos}, "preferred": pos}
    return t


# --- operators ------------------------------------------------------------
# Each returns (new_pblocks, adjustments). `adjustments` overrides ground truth
# for specific ids; the harness merges it over default_truth.

def reorder(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Reverse the block order. A full positional change with no content change:
    once markers are stripped, only the body hash (Tier 2) can recover this."""
    return list(reversed(pblocks)), {}


def edit_in_place(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Paraphrase every other paragraph: append a clause and change a word. The
    id stays put but its stored hash no longer matches, forcing quote recovery
    under genuine content drift."""
    out = []
    for i, pb in enumerate(pblocks):
        if is_para(pb) and i % 2 == 1:
            edited = pb.text.replace("the ", "each ", 1)
            edited = edited.rstrip() + " This sentence was added by an editor."
            out.append(PBlock(text=edited, ids=list(pb.ids)))
        else:
            out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, {}


def split(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Split the first multi-sentence paragraph into two blocks. The first child
    keeps the id; the second is new. Both children descend from the original, so
    either is an acceptable home (the spec has not decided which child wins);
    the id-keeping child is the stricter 'preferred' target."""
    out: list[PBlock] = []
    adj: dict = {}
    split_ids: list[str] = []
    for pb in pblocks:
        if not split_ids and is_para(pb) and ". " in pb.text and pb.ids:
            head, _, tail = pb.text.partition(". ")
            out.append(PBlock(text=head + ".", ids=list(pb.ids)))   # id-keeping child
            out.append(PBlock(text=tail, ids=[]))                   # new child
            split_ids = list(pb.ids)
        else:
            out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    if split_ids:
        first = next(p for p, pb in enumerate(out) if set(split_ids) & set(pb.ids))
        children = {first, first + 1}
        for mid in split_ids:
            adj[mid] = {"accept": children, "preferred": first}
    return out, adj


def merge(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Merge the first adjacent pair of paragraphs into one block carrying both
    ids. After stripping, neither original hash matches the merged body, so both
    ids must recover by quote onto the same merged block."""
    out: list[PBlock] = []
    i = 0
    merged = False
    while i < len(pblocks):
        a = pblocks[i]
        b = pblocks[i + 1] if i + 1 < len(pblocks) else None
        if not merged and b is not None and is_para(a) and is_para(b) and a.ids and b.ids:
            out.append(PBlock(text=a.text.rstrip() + " " + b.text.lstrip(),
                              ids=list(a.ids) + list(b.ids)))
            merged = True
            i += 2
        else:
            out.append(PBlock(text=a.text, ids=list(a.ids)))
            i += 1
    return out, {}


def delete(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Delete the second paragraph block. Its id has no home and the only correct
    resolution is DETACHED, the spec's 'surface, don't silently reattach'."""
    out: list[PBlock] = []
    adj: dict = {}
    seen_para = 0
    for pb in pblocks:
        if is_para(pb) and pb.ids:
            seen_para += 1
            if seen_para == 2:
                for mid in pb.ids:
                    adj[mid] = {"accept": None, "preferred": None}
                continue
        out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, adj


# Deterministic aggressive reword: synonym swaps + light restructuring. Drops
# text similarity well below the gentle edit_in_place edit while keeping the block
# the *same* logical content, which is the realistic AI-rewrite case and the real
# stress test for the quote tier.
_SYN = {
    "messages": "records", "message": "record", "order": "request",
    "orders": "requests", "pipeline": "workflow", "validate": "check",
    "validation": "checking", "partner": "vendor", "product": "catalogue",
    "pricing": "price", "error": "fault", "errors": "faults", "stage": "step",
    "stages": "steps", "queue": "buffer", "backup": "archive", "data": "information",
    "configuration": "config", "files": "documents", "drive": "disk",
    "remote": "offsite", "repository": "repo", "repositories": "repos",
    "checklist": "list", "restore": "recovery", "coverage": "breadth",
    "confidence": "assurance", "persist": "store", "persistence": "storage",
    "downstream": "later", "consumers": "clients",
}
import re as _re  # noqa: E402


def _paraphrase(text: str) -> str:
    def sub(m):
        w = m.group(0)
        return _SYN.get(w.lower(), w)
    out = _re.sub(r"[A-Za-z]+", sub, text)
    out = out.replace(", ", " and ", 1)
    return out.rstrip() + " (revised)"


def heavy_paraphrase(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Aggressively reword every paragraph (synonym swaps + restructuring), so no
    paragraph's hash survives and the quote tier alone must recover them. Headings,
    code, and tables are left to hash-match. This is the realistic 'agent rewrote
    the prose' case and the hardest honest test of recovery."""
    out = []
    for pb in pblocks:
        if is_para(pb) and pb.ids:
            out.append(PBlock(text=_paraphrase(pb.text), ids=list(pb.ids)))
        else:
            out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, {}


def decoy(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Insert a paraphrased near-duplicate of the first paragraph right after it,
    AND lightly edit the original so neither hash-matches the anchor. The resolver
    must now discriminate the (lightly drifted) true block from a (heavily drifted)
    look-alike. A confident pick of the decoy would be a false reattachment; the
    correct answer is the edited original."""
    out: list[PBlock] = []
    placed = False
    for pb in pblocks:
        if not placed and is_para(pb) and pb.ids:
            original = PBlock(text=pb.text.rstrip() + " A small clarifying note.",
                              ids=list(pb.ids))
            look_alike = PBlock(text=_paraphrase(pb.text), ids=[])
            out.append(original)
            out.append(look_alike)
            placed = True
        else:
            out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, {}


def clone(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Insert an *exact* copy of the first paragraph right after it (a real
    copy-paste duplication) and leave the original untouched. With the marker
    stripped there is genuinely no evidence to tell the identical twins apart, so
    the spec-correct outcome is to DETACH (surface as outdated) rather than guess.
    Scored as a 'missed' because the block did survive, but the point is that it
    must NOT become a false attachment."""
    out: list[PBlock] = []
    placed = False
    for pb in pblocks:
        out.append(PBlock(text=pb.text, ids=list(pb.ids)))
        if not placed and is_para(pb) and pb.ids:
            out.append(PBlock(text=pb.text, ids=[]))   # identical twin, no id
            placed = True
    return out, {}


def insert(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Insert two new distractor paragraphs (no ids) near the top and middle.
    Existing ids must stay on their own blocks and must not be lured onto the new
    text. Tests the false-attraction failure mode."""
    distractor_a = PBlock(
        text="This is an entirely new paragraph inserted by a later editor, "
             "describing unrelated background that did not exist before.", ids=[])
    distractor_b = PBlock(
        text="Another new paragraph was added here to pad the document with "
             "additional context that no original marker should ever match.", ids=[])
    out = list(pblocks)
    mid = len(out) // 2
    out = out[:1] + [distractor_a] + out[1:mid] + [distractor_b] + out[mid:]
    return out, {}


OPERATORS = {
    "reorder": reorder,
    "edit_in_place": edit_in_place,
    "heavy_paraphrase": heavy_paraphrase,
    "split": split,
    "merge": merge,
    "delete": delete,
    "insert": insert,
    "decoy": decoy,
    "clone": clone,
}
