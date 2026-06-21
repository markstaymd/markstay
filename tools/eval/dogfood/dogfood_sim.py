"""Dogfood simulation: does a real 'update this document' LLM pass silently drop a
seeded section, and does markstay's §11 regeneration diff catch it?

This extends eval/ from synthetic fixtures (eval/docs/*.md) to a real Markdown
corpus that has been seeded with stays (e.g. sampled FastAPI docs and Rust Book
chapters). For every (doc, task, model, arm) cell it:

  1. reads the seeded doc (markers already minted) as `before`,
  2. asks a model to perform a realistic document update and return the whole doc,
  3. runs the linter's regeneration diff (lint_diff) `before` -> `after`, the exact
     catch the pre-commit hook uses,
  4. classifies every DROPPED_ID as a *content drop* (the heading/section is gone,
     a true positive the catch earns its keep on) or a *marker strip* (the content
     survived, only the `stay:` marker was lost, a false-positive nag).

It answers the three questions simulation-on-synthetic-fixtures can't: how often a
realistic update drops a real section (drop propensity), what the catch's
true-positive vs nag split is, and how much of the friction is pure marker-strip.

The content drop / marker strip split is decided by an LLM judge, not a string
heuristic. A textual best-match wrongly reads a deleted section as surviving when a
textually similar sibling is still present (and vocabulary-overlap fails the same
way on generic shared words); the judge reads the whole edited document and decides
whether the removed section's *information* genuinely survives (reworded / merged /
moved) or is gone.

PRIVACY: this module reads docs from disk but returns only metrics, finding codes,
and opaque stay ids, never document text or model output, so it runs unchanged over
a private corpus. The runner anonymizes doc names (doc01..) in the committed report.

Marker parsing, hashing, and the regeneration diff are reused from the reference
linter, not re-derived.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

# Reuse the reference linter (lives two dirs up under linter/), same convention as
# eval/attachment/resolver.py.
_LINTER = Path(__file__).resolve().parents[2] / "linter"
if str(_LINTER) not in sys.path:
    sys.path.insert(0, str(_LINTER))
import markstay_lint as L  # noqa: E402


# --- realistic document-update tasks, ordered low -> high churn ---------------

TASKS = {
    # Low churn: the routine "log what happened" edit. A drop here is a pure
    # accident, the organic base rate.
    "append": (
        "Update this living tracking document by recording a new development: "
        "add a short dated entry under the most appropriate existing section "
        "noting that the related work has progressed since the last update. "
        "Keep everything else as it is."
    ),
    # Medium churn: status maintenance across the whole doc.
    "status": (
        "Bring this living tracking document up to date: mark resolved items as "
        "done, refresh any stale status lines, and tighten wording where it has "
        "gotten verbose. Keep the document's structure and all its sections."
    ),
    # High churn: the dangerous regeneration. This is where a section goes missing.
    "consolidate": (
        "This tracking document has grown long and messy. Consolidate and tidy it: "
        "merge overlapping sections, fold short stale notes into nearby sections, "
        "drop content that is clearly resolved or no longer relevant, and tighten "
        "the prose throughout. Produce a clean, well-organized version."
    ),
}

# Naive arm says nothing about markers (models an uninstructed session). Instructed
# arm appends the real PRESERVE.md guidance (models a session with the active §11
# preservation instruction, the deferred half of the pilot).
RETURN_ONLY = (
    "\n\nReturn only the full resulting Markdown document, with no commentary and "
    "no code fences around it."
)


def build_prompt(task_key: str, doc_md: str, preserve_text: str | None) -> str:
    parts = [TASKS[task_key]]
    if preserve_text:
        parts.append("\n\n" + preserve_text.strip())
    parts.append(RETURN_ONLY)
    parts.append("\n\n---\n\n" + doc_md)
    return "".join(parts)


_FENCE_RE = re.compile(r"^```[a-zA-Z]*\n(.*)\n```$", re.DOTALL)


def strip_outer_fence(text: str) -> str:
    t = text.strip()
    m = _FENCE_RE.match(t)
    return m.group(1) if m else t


# --- per-cell structural classification --------------------------------------
# lint_diff reports a DROPPED_ID whenever an id vanishes, but it cannot tell
# "the whole section was deleted" (a true positive the catch earns its keep on)
# from "the section is still here, the model just stripped its marker" (a
# false-positive nag). That split is decided downstream by the judge (below);
# classify_structural only extracts what the linter knows for certain.

@dataclass
class CellMetrics:
    n_stays: int = 0
    dropped: list = field(default_factory=list)        # ids reported DROPPED
    content_drops: list = field(default_factory=list)  # judge: section gone (TP)
    marker_strips: list = field(default_factory=list)  # judge: content survived (FP)
    judge_unknown: list = field(default_factory=list)  # judge gave no clear verdict
    relocated: int = 0
    duplicated: int = 0
    hash_drift: int = 0
    new_ids: int = 0
    caught: bool = False        # would the pre-commit hook block (any error finding)?
    block_reason: list = field(default_factory=list)   # distinct error codes
    # Was the block a true guard (caught a real content drop) or pure nag
    # (blocked only on surviving content: marker strips / relocations)?
    is_guard: bool = False
    is_nag: bool = False

    def to_dict(self):
        d = dict(self.__dict__)
        d["n_dropped"] = len(self.dropped)
        d["n_content_drops"] = len(self.content_drops)
        d["n_marker_strips"] = len(self.marker_strips)
        return d


def classify_structural(before_md: str, after_md: str, mode: str = "blank-line"):
    """Run the §11 catch. Returns (metrics, dropped_content) where dropped_content
    maps each DROPPED id -> the content of the block it was anchored to, for the
    judge to rule survived/deleted on. Guard/nag is left for finalize()."""
    before_by_id = {}
    for b in L.parse_document(before_md, mode=mode):
        for mk in b.markers:
            if mk.id and not mk.malformed:
                before_by_id.setdefault(mk.id, b)

    findings = L.lint_diff(before_md, after_md, mode=mode)
    m = CellMetrics(n_stays=len(before_by_id))
    dropped_content = {}
    for f in findings:
        if f.code == "DROPPED_ID":
            m.dropped.append(f.id)
            blk = before_by_id.get(f.id)
            dropped_content[f.id] = blk.content if blk is not None else ""
        elif f.code == "RELOCATED_ID":
            m.relocated += 1
        elif f.code == "DUPLICATED_ID":
            m.duplicated += 1
        elif f.code == "HASH_DRIFT":
            m.hash_drift += 1
        elif f.code == "NEW_ID":
            m.new_ids += 1
    m.caught = L.has_errors(findings)
    m.block_reason = sorted({f.code for f in findings if f.level == "error"})
    return m, dropped_content


def finalize(m: CellMetrics, verdicts: dict) -> CellMetrics:
    """Apply the judge's per-dropped-id verdicts and settle guard vs nag.

    verdicts: id -> 'SURVIVED' | 'DELETED' | 'UNKNOWN'. A guard requires at least
    one genuinely deleted section; otherwise a blocked commit is a nag. UNKNOWN
    verdicts are reported but never counted as a deletion, so guard is a lower
    bound (conservative against overstating the catch's value)."""
    for mid in m.dropped:
        v = verdicts.get(mid, "UNKNOWN")
        if v == "DELETED":
            m.content_drops.append(mid)
        elif v == "SURVIVED":
            m.marker_strips.append(mid)
        else:
            m.judge_unknown.append(mid)
    if m.caught:
        m.is_guard = len(m.content_drops) > 0
        m.is_nag = not m.is_guard
    return m


# --- the survival judge ------------------------------------------------------
# Batched: one call per cell-with-drops sends the edited document once plus all
# removed sections, and gets one verdict line per section. Far cheaper than a call
# per id, and the judge sees the whole document so a section merged into another
# counts as SURVIVED.

_JUDGE_HEAD = (
    "An editor rewrote a Markdown document. Below is the EDITED document, then a "
    "numbered list of sections that were present BEFORE the edit. For each numbered "
    "section decide whether its substantive information still survives anywhere in "
    "the edited document (even if reworded, shortened, merged into another section, "
    "or moved) or whether it was genuinely removed.\n\n"
    "Reply with exactly one line per numbered section, in order, formatted as "
    "`<n>: SURVIVED` or `<n>: DELETED`. No other text."
)


def build_judge_prompt(after_md: str, items: list[tuple[str, str]]) -> str:
    """items: list of (id, block_content) in stable order. The id is not shown to
    the judge (it numbers the sections); the caller maps numbers back to ids."""
    parts = [_JUDGE_HEAD, "\n\n=== EDITED DOCUMENT ===\n", after_md,
             "\n\n=== SECTIONS FROM BEFORE THE EDIT ===\n"]
    for i, (_id, content) in enumerate(items, 1):
        body = (content or "").strip() or "(empty / non-textual block)"
        parts.append(f"\n[{i}]\n{body}\n")
    return "".join(parts)


_VERDICT_RE = re.compile(r"^\s*\[?(\d+)\]?\s*[:.\-)]\s*(SURVIVED|DELETED)\b",
                         re.IGNORECASE | re.MULTILINE)


def parse_judge(raw: str, items: list[tuple[str, str]]) -> dict:
    """Map the judge's numbered verdicts back to ids. Missing/garbled -> UNKNOWN."""
    by_num = {}
    for m in _VERDICT_RE.finditer(raw or ""):
        by_num[int(m.group(1))] = m.group(2).upper()
    out = {}
    for i, (mid, _content) in enumerate(items, 1):
        out[mid] = by_num.get(i, "UNKNOWN")
    return out


# --- within-collection items (the catch's blind spot) ------------------------
# A stay sits on a top-level block, so a table is one stay and a list is one stay.
# A row or bullet dropped from inside that block leaves the stay in place and only
# drifts the block hash (HASH_DRIFT, non-blocking), so the §11 catch cannot see it.
# To measure how much real content that blind spot loses, we extract the individual
# rows/bullets and judge their survival directly, independent of any stay.

_BULLET_RE = re.compile(r"^\s*[-*+]\s+(\S.*)$")
_TABLE_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_TABLE_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")  # the |---|:--| divider row


def extract_items(md: str) -> list[dict]:
    """Every table data-row and list bullet, each a within-collection unit whose
    identity a stay does NOT protect. Markers stripped. Table header rows (the line
    directly above a `|---|` divider) and the divider itself are excluded; what
    remains is the data a real update can silently prune."""
    lines = L._strip_markers(md).split("\n")
    n = len(lines)
    items: list[dict] = []
    for i, ln in enumerate(lines):
        if _TABLE_ROW_RE.match(ln):
            if _TABLE_SEP_RE.match(ln):
                continue  # divider
            if i + 1 < n and _TABLE_SEP_RE.match(lines[i + 1]):
                continue  # header (sits right above the divider)
            text = ln.strip().strip("|").strip()
            if text:
                items.append({"kind": "row", "text": text})
            continue
        m = _BULLET_RE.match(ln)
        if m:
            text = m.group(1).strip()
            if text:
                items.append({"kind": "bullet", "text": text})
    return items


_ITEM_JUDGE_HEAD = (
    "An editor rewrote a Markdown document. Below is the EDITED document, then a "
    "numbered list of individual entries (table rows and list bullets) that were "
    "present BEFORE the edit. For each numbered entry decide whether its substantive "
    "information still survives anywhere in the edited document (even if reworded, "
    "moved to another table/list, or merged into another entry) or whether it was "
    "genuinely removed.\n\n"
    "Reply with exactly one line per numbered entry, in order, formatted as "
    "`<n>: SURVIVED` or `<n>: DELETED`. No other text."
)


def build_item_judge_prompt(after_md: str, items: list[tuple[str, str]]) -> str:
    """items: list of (key, item_text) in stable order; key is not shown."""
    parts = [_ITEM_JUDGE_HEAD, "\n\n=== EDITED DOCUMENT ===\n", after_md,
             "\n\n=== ENTRIES FROM BEFORE THE EDIT ===\n"]
    for i, (_key, text) in enumerate(items, 1):
        parts.append(f"\n[{i}] {text}\n")
    return "".join(parts)
