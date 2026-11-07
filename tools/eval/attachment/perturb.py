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
from difflib import SequenceMatcher
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


# --- section-structure operators -------------------------------------------
# The operators above all act *within* whatever section they find themselves in,
# because the fixtures they were written for carry a single heading each. These
# four move the document's heading structure instead, which is the only way to
# price a resolver that treats section position as evidence: the ones that keep a
# block's content while changing its section are its *cost*, not its benefit.
#
# Kept in a separate registry on purpose. Adding them to OPERATORS would change
# every published number in `results.md`, which is a blast radius that belongs to
# a deliberate re-measurement rather than to adding a fixture.

_ATX_H = _re.compile(r"^ {0,3}(#{1,6})\s")
_SETEXT_RULE = _re.compile(r"^ {0,3}(=+|-+)\s*$")


def heading_level(text: str) -> int:
    """ATX or setext heading level, or 0 for a non-heading block.

    `kind()` above reports setext headings as paragraphs (it only looks for a
    leading `#`), which is harmless for the within-section operators but would
    make a section operator walk straight past `Appendix\\n--------`."""
    lines = text.strip("\n").split("\n")
    m = _ATX_H.match(lines[0])
    if m:
        return len(m.group(1))
    if len(lines) == 2 and lines[0].strip() and _SETEXT_RULE.match(lines[1]):
        return 1 if lines[1].strip()[0] == "=" else 2
    return 0


def _heading_positions(pblocks: list[PBlock]) -> list[int]:
    return [i for i, pb in enumerate(pblocks) if heading_level(pb.text)]


def cross_section_move(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Move one paragraph out of its section and into a later one, leaving its
    near-duplicate siblings behind.

    This is the case `SPEC.md` §2.2 names outright: a stay MUST survive movement
    within a document. A resolver that filters candidates by stored heading path
    cannot recover this block at all, and one that merely favours the stored path
    is pulled toward whichever twin stayed put. Correct answer is unchanged: the
    id belongs to the block that moved."""
    heads = _heading_positions(pblocks)
    if len(heads) < 2:
        return list(pblocks), {}
    # first paragraph under the second heading
    src = next((i for i in range(heads[1] + 1, len(pblocks))
                if not heading_level(pblocks[i].text) and pblocks[i].ids), None)
    if src is None:
        return list(pblocks), {}
    out = list(pblocks)
    moved = out.pop(src)
    out.insert(len(out) - 1, moved)   # into the document's last section
    return out, {}


def cross_section_move_edit(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Move the document's most *distinctive* paragraph into a later section and
    drift its text, so it must be recovered by quote from another section.

    This is the operator that prices a structural signal, and `cross_section_move`
    is not, which took running the arms to notice: a block whose text survives
    verbatim is recovered at the hash tier, so the quote tier never sees it and a
    heading filter never gets the chance to exclude it. Drift alone is not enough
    either. If the moved block has a byte-identical twin that stayed behind, every
    arm detaches on the margin and the arms cannot be told apart.

    So the block is chosen for being unlike every other block: content evidence
    alone identifies it, the shipped resolver recovers it, and any arm that
    *requires* the stored section cannot, which is exactly the guarantee
    `SPEC.md` §2.2 makes and a filter cannot keep."""
    heads = _heading_positions(pblocks)
    if len(heads) < 2:
        return list(pblocks), {}
    norm = [_re.sub(r"\s+", " ", pb.text.strip().lower()) for pb in pblocks]

    def rival(i: int) -> float:
        return max((SequenceMatcher(None, norm[i], norm[j], autojunk=False).ratio()
                    for j in range(len(pblocks)) if j != i), default=0.0)

    candidates = [i for i in range(heads[1] + 1, len(pblocks))
                  if not heading_level(pblocks[i].text) and pblocks[i].ids]
    if not candidates:
        return list(pblocks), {}
    src = min(candidates, key=rival)
    out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
    moved = out.pop(src)
    edited = moved.text.replace("the ", "each ", 1)
    edited = edited.rstrip() + " This sentence was added by an editor."
    out.insert(len(out) - 1, PBlock(text=edited, ids=list(moved.ids)))
    return out, {}


def section_move(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Relocate a whole section (its heading and everything under it, up to the
    next heading of the same or higher level) to the end of the document. Every
    id keeps its block; only the order changes, so this is the structural
    analogue of `reorder` and every arm must survive it intact."""
    heads = _heading_positions(pblocks)
    if len(heads) < 3:
        return list(pblocks), {}
    start = heads[1]
    level = heading_level(pblocks[start].text)
    end = next((i for i in heads if i > start
                and heading_level(pblocks[i].text) <= level), len(pblocks))
    section = pblocks[start:end]
    out = pblocks[:start] + pblocks[end:] + section
    return [PBlock(text=pb.text, ids=list(pb.ids)) for pb in out], {}


def heading_rename(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Reword every second heading, keeping its level and its body blocks.

    The realistic way an LLM breaks a stored heading path: it tidies the section
    titles while leaving the prose alone. Every id still belongs exactly where it
    was, so any arm that loses one here has been misled by structure."""
    out: list[PBlock] = []
    seen = 0
    for pb in pblocks:
        lvl = heading_level(pb.text)
        if lvl and seen % 2 == 1:
            lines = pb.text.strip("\n").split("\n")
            m = _ATX_H.match(lines[0])
            if m:
                title = lines[0][m.end():].strip().rstrip("#").strip()
                out.append(PBlock(text=f"{m.group(1)} {_paraphrase(title)}",
                                  ids=list(pb.ids)))
            else:  # setext: reword the title line, keep the underline
                out.append(PBlock(text=f"{_paraphrase(lines[0])}\n{lines[1]}",
                                  ids=list(pb.ids)))
            seen += 1
            continue
        if lvl:
            seen += 1
        out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, {}


def heading_delete(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Delete the second heading, merging its section into the one above.

    Two things happen at once and both need to be right: the heading's own id has
    no home and MUST come back DETACHED, and every block that sat under it now
    reports a different section while being otherwise untouched. A path-filtering
    arm loses that whole section; a path-bonus arm merely stops being helped."""
    heads = _heading_positions(pblocks)
    if len(heads) < 2:
        return list(pblocks), {}
    victim = heads[1]
    out: list[PBlock] = []
    adj: dict = {}
    for i, pb in enumerate(pblocks):
        if i == victim:
            for mid in pb.ids:
                adj[mid] = {"accept": None, "preferred": None}
            continue
        out.append(PBlock(text=pb.text, ids=list(pb.ids)))
    return out, adj


SECTION_OPERATORS = {
    "cross_section_move": cross_section_move,
    "cross_section_move_edit": cross_section_move_edit,
    "section_move": section_move,
    "heading_rename": heading_rename,
    "heading_delete": heading_delete,
}


# --- identity-boundary operators --------------------------------------------
# These price the rules that decide *which* block keeps an id when content says
# two candidates fit: a replacement in the same slot, two neighbours that trade
# places while drifting, and a pasted copy that may carry the original's marker.
# They exist for the exclusivity arms (`excl_arms.py`) and sit in their own
# registry for the same reason SECTION_OPERATORS do: adding them to OPERATORS
# would move every published number in `results.md`.

_UNRELATED = ("A completely different statement now occupies this slot, written "
              "later about an unrelated subject that shares nothing with the text "
              "it displaced.")


def _nth_marked_para(pblocks: list[PBlock], n: int) -> int | None:
    seen = 0
    for i, pb in enumerate(pblocks):
        if is_para(pb) and pb.ids:
            seen += 1
            if seen == n:
                return i
    return None


def _drift(text: str) -> str:
    """The same light edit `edit_in_place` makes."""
    return text.replace("the ", "each ", 1).rstrip() + " This sentence was added by an editor."


def replace(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Put unrelated text in the second paragraph's slot. SPEC.md §2.2 says a
    replacement earns a new stay, so the old id has no home and MUST detach.
    This is the case a position-based aligner gets wrong by construction."""
    out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
    i = _nth_marked_para(out, 2)
    if i is None:
        return out, {}
    adj = {mid: {"accept": None, "preferred": None} for mid in out[i].ids}
    out[i] = PBlock(text=_UNRELATED, ids=[])
    return out, adj


def replace_related(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Replace the second paragraph with a same-topic statement that withdraws
    its claim: the first half of its words kept, the assertion reversed.

    Ground truth is DETACH under §2.2, but that truth is semantic rather than
    lexical. Half the words survive, so no similarity threshold can separate
    this from an edit, and an arm that misattaches here is approximating the
    rule rather than breaking it. Reported apart from `replace` for that reason."""
    out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
    i = _nth_marked_para(out, 2)
    if i is None:
        return out, {}
    adj = {mid: {"accept": None, "preferred": None} for mid in out[i].ids}
    words = out[i].text.split()
    half = " ".join(words[: max(4, len(words) // 2)])
    out[i] = PBlock(text=half + " is no longer true and has been withdrawn entirely.",
                    ids=[])
    return out, adj


def swap_edit(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Swap the first pair of adjacent marked paragraphs and drift both. A
    position aligner sees two in-place edits; identity says each id follows its
    own text, and neither hash survives, so both must recover at the quote tier."""
    out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
    paras = [i for i, pb in enumerate(out) if is_para(pb) and pb.ids]
    for a, b in zip(paras, paras[1:]):
        if b == a + 1:
            first, second = out[a], out[b]
            out[a] = PBlock(text=_drift(second.text), ids=list(second.ids))
            out[b] = PBlock(text=_drift(first.text), ids=list(first.ids))
            break
    return out, {}


def edit_into_twin(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
    """Rewrite one marked paragraph into another's exact text, each keeping its
    own id. Run with alternate ids stripped, this is the one shape that reaches
    exclusive tier 2's claimed filter: the stripped id's hash now names two blocks,
    and one of them is claimed at tier 1 by the marker that stayed.

    The rewritten paragraph is the first one after the second marked paragraph an
    odd number of stays away, so the two ids always fall on opposite parities and
    one parity of a partly-marked run has the shape. The source's hash has to be
    unique among the stored stays, or historical uniqueness refuses it first."""
    out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
    marked = [i for i, pb in enumerate(out) if pb.ids]
    hashes = [L.body_hash(pb.text) for pb in out if pb.ids]
    paras = [i for i in marked if is_para(out[i])]
    for src in paras[1:]:
        if hashes.count(L.body_hash(out[src].text)) > 1:
            continue
        for dst in paras:
            if dst > src and (marked.index(dst) - marked.index(src)) % 2:
                out[dst] = PBlock(text=out[src].text, ids=list(out[dst].ids))
                return out, {}
    return out, {}


def _copy(where: str, edit: str | None):
    """Build a copy operator: paste the second marked paragraph, marker and all,
    at `where` (`above` / `below` the original, or the document's `start` /
    `end`), then optionally drift the `copy` or the `original`.

    SPEC.md §7 says a copy mints a fresh stay, so the id belongs to the original
    in every variant. With markers kept the id appears on two blocks, which is
    what prices §9.1 tier 1 for a duplicated id; with markers stripped the copy
    is an unmarked twin, which is `clone` at a chosen distance."""

    def op(pblocks: list[PBlock]) -> tuple[list[PBlock], dict]:
        out = [PBlock(text=pb.text, ids=list(pb.ids)) for pb in pblocks]
        i = _nth_marked_para(out, 2)
        if i is None:
            return out, {}
        src = out[i]
        cp = PBlock(text=_drift(src.text) if edit == "copy" else src.text,
                    ids=list(src.ids))
        if edit == "original":
            out[i] = src = PBlock(text=_drift(src.text), ids=list(src.ids))
        if where == "above":
            out.insert(i, cp)
            orig = i + 1
        elif where == "below":
            out.insert(i + 1, cp)
            orig = i
        elif where == "start":
            out.insert(0, cp)
            orig = i + 1
        else:
            out.append(cp)
            orig = i
        return out, {mid: {"accept": {orig}, "preferred": orig} for mid in src.ids}

    op.__name__ = f"copy_{where}" + (f"_edit_{edit}" if edit else "")
    op.__doc__ = _copy.__doc__
    return op


COPY_OPERATORS = {
    f"copy_{where}" + (f"_edit_{edit}" if edit else ""): _copy(where, edit)
    for edit in (None, "copy", "original")
    for where in ("above", "below", "start", "end")
}

EXCL_OPERATORS = {
    "replace": replace,
    "replace_related": replace_related,
    "swap_edit": swap_edit,
    **COPY_OPERATORS,
}

# Kept apart from EXCL_OPERATORS, whose published sweeps would otherwise move.
TWIN_EDIT_OPERATORS = {"edit_into_twin": edit_into_twin}
