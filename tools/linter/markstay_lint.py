#!/usr/bin/env python3
"""markstay reference linter.

Checks that markstay markers in a Markdown document are well-formed and, given a
baseline version, that no ids were silently dropped, duplicated, or relocated by
an edit. This is the post-edit safety net the marker-survival eval
(../eval/FINDINGS.md) showed is mandatory: a regenerating agent that is not told
about markstay strips nearly every marker, so silent loss has to become a caught
error rather than a quiet break of every downstream reference.

Scope: the canonical HTML-comment marker

    <!-- stay:ID [hash=sha256:HEX] [k=v ...] -->

and the MDX profile

    {/* stay:ID [hash=sha256:HEX] [k=v ...] */}

(SPEC.md §3). Markers attach to the block immediately above them (after-block
placement, SPEC.md §5). A chunk that is *only* markers attaches to the previous
content block; a marker with no preceding block is an orphan.

Hash normalization is SPEC.md §8. `normalize_body` implements that rule, and the
linter always compares at the precision recorded in the marker, so it never
reports drift merely because a freshly computed hash is longer than a short
stored one.

What it does NOT do: detect block split/merge relocations where content only
partially moved. Exact-content marker swaps are caught (RELOCATED_ID); partial
relocation is the domain of the attachment-survival eval (quote/selector
recovery), not this deterministic linter.

Usage:
    markstay_lint.py FILE [FILE ...]          # well-formedness + intra-doc checks
    markstay_lint.py --before OLD.md NEW.md     # regeneration diff
    markstay_lint.py --json ...                 # machine-readable findings

Exit status is non-zero when any error-level finding is reported, so it can gate
a commit hook or an agent's post-edit step.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import string
import sys
from dataclasses import dataclass, field, replace
from difflib import SequenceMatcher
from pathlib import Path

# --- marker grammar -------------------------------------------------------

# These compatibility regexes describe the old permissive surface. Core discovery,
# stripping, and rewriting all use the strict host-first scanner below. They remain
# exported for one development-only mutation harness that is migrated in Phase 3.
HTML_MARKER = re.compile(r"<!--\s*(?P<body>stay:.*?)\s*-->", re.DOTALL)
MDX_MARKER = re.compile(r"\{/\*\s*(?P<body>stay:.*?)\s*\*/\}", re.DOTALL)
COMBINED_MARKER = re.compile(
    r"<!--\s*(?P<html>stay:.*?)\s*-->|\{/\*\s*(?P<mdx>stay:.*?)\s*\*/\}", re.DOTALL
)

_MARKER_OPEN_RE = re.compile(r"<!--|\{/\*")
_MARKER_ID_RE = re.compile(r"[A-Za-z0-9_-]+")
_MARKER_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_MARKER_HASH_RE = re.compile(r"sha256:([0-9A-Fa-f]+)")

LEVELS = {"error": 0, "warn": 1, "info": 2}


# --- data model -----------------------------------------------------------


@dataclass
class Marker:
    id: str | None
    hash: str | None
    raw: str
    syntax: str  # 'html' | 'mdx'
    line: int
    malformed: bool = False
    subhash: str | None = None
    # Exact parsed key presence, independent of whether its value is a digest.
    # §16 routes on this bit: `subhash=bogus` is a child-looking marker while
    # `x-subhash=bogus` is not.
    has_subhash: bool = False


@dataclass
class Block:
    content: str  # marker(s) removed, normalized for display only
    markers: list = field(default_factory=list)
    line: int = 0  # 1-based start line of the content
    index: int = -1  # content-block index; -1 means an orphan marker chunk
    children: list = field(default_factory=list)


@dataclass
class ChildBlock:
    content: str
    markers: list = field(default_factory=list)
    line: int = 0
    index: int = -1
    ordinal: int = 0
    parent_index: int = -1
    marker_line: int = 0
    kind: str = "list"  # `list` (§5.5) or `row` (§5.6)


@dataclass
class Finding:
    level: str  # 'error' | 'warn' | 'info'
    code: str
    message: str
    id: str | None = None
    line: int | None = None

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if v is not None}


# --- hashing (SPEC.md §8) -------------------------------------------------


def normalize_body(text: str) -> str:
    """Normalization for hashing (SPEC.md §8): LF endings, per-line trailing
    ASCII whitespace stripped, leading/trailing blank lines dropped. Markers are
    excluded upstream (they are stripped before a block's content is hashed).

    The trailing-whitespace set is ASCII (space, tab, form feed, vertical tab),
    not Python's Unicode `str.rstrip()`, so a second implementation reproduces the
    hash exactly without an ICU table (SPEC.md §8; see SPEC_DECISIONS.md)."""
    t = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [ln.rstrip(" \t\f\v") for ln in t.split("\n")]
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def body_hash(text: str, length: int | None = None) -> str:
    h = hashlib.sha256(normalize_body(text).encode("utf-8")).hexdigest()
    return h[:length] if length else h


# --- parsing --------------------------------------------------------------


@dataclass
class _MarkerRecord:
    start: int
    end: int
    marker: Marker


def _normalize_lf_with_raw_boundaries(text: str) -> tuple[str, list[int]]:
    """Normalize line endings and map normalized boundaries to raw offsets."""
    normalized: list[str] = []
    raw_boundaries = [0]
    pos = 0
    while pos < len(text):
        if text[pos] == "\r":
            pos += 2 if pos + 1 < len(text) and text[pos + 1] == "\n" else 1
            normalized.append("\n")
        else:
            normalized.append(text[pos])
            pos += 1
        raw_boundaries.append(pos)
    return "".join(normalized), raw_boundaries


def _parse_marker_body(
    body: str, syntax: str
) -> tuple[str, list[tuple[str, str, bool]]] | None:
    """Parse one complete normalized-LF §4 marker body."""
    if not body.startswith("stay:"):
        return None
    pos = len("stay:")
    id_match = _MARKER_ID_RE.match(body, pos)
    if id_match is None:
        return None
    marker_id = id_match.group(0)
    pos = id_match.end()
    if pos < len(body) and body[pos] not in " \t":
        return None

    attributes: list[tuple[str, str, bool]] = []
    while pos < len(body):
        separator_start = pos
        while pos < len(body) and body[pos] in " \t":
            pos += 1
        if pos == len(body):
            break
        if pos == separator_start:
            return None
        key_match = _MARKER_KEY_RE.match(body, pos)
        if key_match is None:
            return None
        key = key_match.group(0)
        pos = key_match.end()
        if pos == len(body) or body[pos] != "=":
            return None
        pos += 1
        if pos == len(body):
            return None

        quoted = body[pos] == '"'
        if quoted:
            pos += 1
            value: list[str] = []
            while pos < len(body) and body[pos] != '"':
                char = body[pos]
                if char == "\\":
                    if pos + 1 == len(body) or body[pos + 1] not in '\\"':
                        return None
                    value.extend((char, body[pos + 1]))
                    pos += 2
                    continue
                codepoint = ord(char)
                if char != "\n" and not (0x20 <= codepoint <= 0x7E):
                    return None
                value.append(char)
                pos += 1
            if pos == len(body):
                return None
            pos += 1
            attribute_value = "".join(value)
        else:
            value_start = pos
            while pos < len(body) and body[pos] not in " \t":
                codepoint = ord(body[pos])
                if body[pos] == '"' or not (0x21 <= codepoint <= 0x7E):
                    return None
                pos += 1
            if pos == value_start:
                return None
            attribute_value = body[value_start:pos]
        attributes.append((key, attribute_value, quoted))
    return marker_id, attributes


def _malformed_key_first(body: str) -> bool:
    """Whether §4 still requires a no-positional-id diagnostic for this body."""
    if not body.startswith("stay:"):
        return False
    key = _MARKER_KEY_RE.match(body, len("stay:"))
    return key is not None and key.end() < len(body) and body[key.end()] == "="


def _scan_marker_records(text: str, line_offset: int = 0) -> list[_MarkerRecord]:
    """Discover every complete §4 marker using the host comment's first close.

    Openers are independent. A rejected opener therefore cannot swallow a later
    valid marker. Recognition uses normalized LF, while offsets and ``raw`` map
    back to the caller's exact source bytes.
    """
    normalized, raw_boundaries = _normalize_lf_with_raw_boundaries(text)
    records: list[_MarkerRecord] = []
    for opener in _MARKER_OPEN_RE.finditer(normalized):
        syntax = "html" if opener.group(0) == "<!--" else "mdx"
        pos = opener.end()
        while pos < len(normalized) and normalized[pos] in " \t":
            pos += 1
        if not normalized.startswith("stay:", pos):
            continue
        body_start = pos
        search_start = pos + len("stay:")
        if syntax == "html":
            closers = [
                (at, closer)
                for closer in ("-->", "--!>")
                if (at := normalized.find(closer, search_start)) >= 0
            ]
            if not closers:
                continue
            close_start, closer = min(closers, key=lambda item: item[0])
            normalized_end = close_start + len(closer)
            valid_host_close = closer == "-->"
        else:
            close_start = normalized.find("*/", search_start)
            if close_start < 0:
                continue
            valid_host_close = normalized.startswith("}", close_start + 2)
            normalized_end = close_start + (3 if valid_host_close else 2)

        body = normalized[body_start:close_start]
        parsed = _parse_marker_body(body, syntax) if valid_host_close else None
        malformed = parsed is None and _malformed_key_first(body)
        if parsed is None and not malformed:
            continue

        attributes = parsed[1] if parsed is not None else []
        block_hash = None
        child_hash = None
        for key, value, quoted in attributes:
            digest = None if quoted else _MARKER_HASH_RE.fullmatch(value)
            if key == "hash" and digest is not None and block_hash is None:
                block_hash = digest.group(1).lower()
            if key == "subhash" and digest is not None and child_hash is None:
                child_hash = digest.group(1).lower()

        raw_start = raw_boundaries[opener.start()]
        raw_end = raw_boundaries[normalized_end]
        records.append(
            _MarkerRecord(
                raw_start,
                raw_end,
                Marker(
                    id=parsed[0] if parsed is not None else None,
                    hash=block_hash,
                    subhash=child_hash,
                    has_subhash=any(key == "subhash" for key, _, _ in attributes),
                    raw=text[raw_start:raw_end],
                    syntax=syntax,
                    line=line_offset + normalized.count("\n", 0, opener.start()) + 1,
                    malformed=malformed,
                ),
            )
        )
    records.sort(key=lambda record: (record.start, record.end))
    return records


def find_markers(text: str, line_offset: int = 0) -> list[Marker]:
    """All markstay markers in `text`, ordered by position. `line_offset` is the
    0-based line index where `text` begins in the full document.

    A raw grammar-level primitive, and deliberately code-blind: it answers "is
    this a well-formed marker" for a string with no document around it, which is
    what the conformance corpus needs. SPEC.md §3.3 (a marker inside a fenced
    code block is content) is a *document*-level rule and cannot be applied here,
    because this function is handed chunks in about fifty places and a chunk that
    begins inside a fence carries no opener. Callers that segment a whole
    document filter the result against `code_lines`."""
    return [record.marker for record in _scan_marker_records(text, line_offset)]


def _strip_markers(text: str) -> str:
    """Remove every marker-shaped string. A raw grammar-level primitive: it is
    code-blind, so a caller that must honour SPEC.md §3.3 passes a document-level
    mask to `_strip_markers_outside_code` instead."""
    records = [
        record for record in _scan_marker_records(text) if not record.marker.malformed
    ]
    return _strip_record_ranges(text, records)


def _merged_record_ranges(
    records: list[_MarkerRecord], start: int = 0, end: int | None = None
) -> list[tuple[int, int]]:
    limit = (
        max((record.end for record in records), default=start) if end is None else end
    )
    merged: list[tuple[int, int]] = []
    for record in records:
        left = max(start, record.start)
        right = min(limit, record.end)
        if left >= right:
            continue
        if merged and left < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], right))
        else:
            merged.append((left, right))
    return merged


def _strip_record_ranges(
    text: str, records: list[_MarkerRecord], *, source_start: int = 0
) -> str:
    spans = _merged_record_ranges(records, source_start, source_start + len(text))
    if not spans:
        return text
    out: list[str] = []
    previous = source_start
    for start, end in spans:
        out.append(text[previous - source_start : start - source_start])
        previous = end
    out.append(text[previous - source_start :])
    return "".join(out)


# --- fenced code blocks (SPEC.md §3.3, v1.5) ------------------------------

# An opening fence may carry an info string; a *closing* fence may not, and a
# backtick fence's info string may not contain a backtick (CommonMark 4.5).
_FENCE_OPEN_RE = re.compile(r"^ {0,3}(?P<run>`{3,}|~{3,})(?P<info>.*)$")
_FENCE_CLOSE_RE = re.compile(r"^ {0,3}(?P<run>`{3,}|~{3,})[ \t]*$")


def _fence_state(text: str) -> tuple[set[int], set[int]]:
    """Fence geometry for one document (SPEC.md §3.3, v1.5): the 1-based line
    numbers that lie inside a fenced code block, and the 1-based line numbers a
    fence is still open *after*.

    The second set is what the write path needs and it is not derivable from the
    first: a marker appended after line L lands on a new line inside the fence
    exactly when a fence is open at the end of L, and an unclosed fence runs to
    the end of the document, where there is no later line to test.

    Recognition is line-based and deliberately narrow, so both segmenters (§5)
    and every tool agree on it without a block parser:

    * the scan runs on LF-split lines, so a CRLF document and its LF twin give
      the same answer (§8);
    * an opening fence has at most three leading **spaces** and then three or
      more backticks or tildes. A tab is not one of the three: CommonMark
      expands it to the next four-column stop, which needs a column model this
      rule deliberately does not have. A backtick fence's info string may not
      contain a backtick;
    * it closes at the first later line with at most three leading spaces that
      is a run of the **same** character, **at least as long** as the opener,
      followed by nothing but spaces and tabs. A longer opener is what lets a
      fence contain a shorter one, and the whitespace set is named rather than
      left to "whitespace" because three implementations picking three sets is
      the way this rule fails quietly;
    * an unclosed fence runs to the end of the document.

    The fence lines themselves are inside the block, deliberately rather than as
    an edge case: a marker-shaped string can sit in an opening fence's info
    string, where before §3.3 it was read as a marker and bound to whatever block
    preceded it."""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    inside: set[int] = set()
    open_after: set[int] = set()
    fence: str | None = None
    for num, line in enumerate(lines, 1):
        if fence is None:
            opener = _FENCE_OPEN_RE.match(line)
            if opener is None or (
                opener.group("run")[0] == "`" and "`" in opener.group("info")
            ):
                continue
            fence = opener.group("run")
            inside.add(num)
            open_after.add(num)
            continue
        inside.add(num)
        closer = _FENCE_CLOSE_RE.match(line)
        if (
            closer
            and closer.group("run")[0] == fence[0]
            and len(closer.group("run")) >= len(fence)
        ):
            fence = None
        else:
            open_after.add(num)
    return inside, open_after


def code_lines(text: str) -> set[int]:
    """The 1-based line numbers inside a fenced code block (SPEC.md §3.3). Text
    there is content: a marker-shaped string on one of these lines identifies no
    block, is hashed with the body (§8), and does not make its block stamped."""
    return _fence_state(text)[0]


def _marker_outside_code(marker: Marker, code: set[int] | None) -> bool:
    """Whether SPEC.md §3.3's fenced-code mask leaves `marker` active.

    §3.3 judges a marker by the line it *opens* on, which is the only line a
    reader can see it start on; the grammar is DOTALL, so one marker can span
    lines and close inside a fence it opened outside. Every path that separates
    active markers from marker-shaped content asks here, so the reading is one
    decision rather than a copy of the same expression at each seam."""
    return not code or marker.line not in code


def _strip_markers_outside_code(text: str, code: set[int], line_offset: int = 0) -> str:
    """Remove markers from `text`, leaving marker-shaped strings inside a fenced
    code block in place (SPEC.md §3.3: they are content, and §8 hashes them with
    the body). `line_offset` is the 0-based line index at which `text` begins in
    the document `code` was computed over.

    A marker is judged by the line it *opens* on, which is the only line a reader
    can see it start on; the grammar is DOTALL, so one can span lines."""
    if not code:
        return _strip_markers(text)
    records = [
        record
        for record in _scan_marker_records(text, line_offset)
        if not record.marker.malformed and _marker_outside_code(record.marker, code)
    ]
    return _strip_record_ranges(text, records)


_FRONTMATTER_OPEN_RE = re.compile(r"^---[ \t]*$")
_FRONTMATTER_CLOSE_RE = re.compile(r"^(?:---|\.\.\.)[ \t]*$")
# One payload line that could only be YAML, never Markdown prose: a mapping key or
# a list item. Used to tell real frontmatter from a leading thematic break that
# happens to be followed by another one. A YAML comment (`# ...`) is deliberately
# NOT accepted: it is byte-identical to an ATX heading, so accepting it lets
# `---` / `# Heading` / `---` be read as frontmatter and silently destroys the
# heading. Comment-only frontmatter therefore is not skipped, which is the safe
# direction to be wrong in.
#
# `[^\x00-\x20\x7f]` is "not an ASCII control character and not a space", written
# out rather than as `\S`. Whitespace is ASCII-pinned here exactly as it is for
# hashing (§8) and matching (§9), because Python, ECMAScript and Rust each define
# Unicode whitespace differently: U+001C is whitespace to Python only, U+0085 to
# Python and Rust only, U+00A0 to Python and ECMAScript only, U+FEFF to ECMAScript
# only. A `\S` here therefore makes four conforming implementations skip different
# spans, which for a rule that DELETES a span from the document is the one kind of
# divergence that loses data.
_YAMLISH_LINE_RE = re.compile(
    r"^[ \t]*(?:-[ \t]+[^\x00-\x20\x7f]|[^\x00-\x20\x7f:#][^:]*:(?:[ \t]|$))"
)


def _blank_frontmatter(text: str) -> str:
    """Blank a leading YAML frontmatter block so neither segmenter sees it as
    content (SPEC.md §5).

    Frontmatter is document metadata, not a block: it carries no prose to identify,
    and hashing it makes a metadata edit (`status: draft` -> `status: done`) drift a
    content hash. It also has to be removed *before* segmentation rather than
    filtered after, because the two segmenters disagree about what it is , the
    baseline reads the whole fenced span as one block, while CommonMark reads the
    opening `---` as a thematic break and the closing one as a setext underline,
    turning the metadata into an H2. Leaving it in puts a document that is inside
    §5.4's agreement subset outside the set the two segmenters actually agree on.

    Recognition is deliberately conservative, because `---` is also a thematic break
    and a setext underline, so a loose rule silently eats real content. All four
    must hold:

    1. line 1 is exactly `---`;
    2. a later line is exactly `---` or `...` (the closing fence). Without one the
       opener is an ordinary thematic break;
    3. the payload between the fences is non-empty and contains **no blank line**.
       This is what stops `---` / blank / `Intro.` / blank / `---` , two thematic
       breaks around a paragraph , from being read as frontmatter that swallows the
       paragraph;
    4. at least one payload line is unambiguously YAML (a `key:` or a `- item`).
       This is what stops `---` / `Title` / `---` , a thematic break followed by a
       setext heading , from being read as frontmatter. A YAML comment does not
       count, because `# x` is also an ATX heading and accepting it would swallow
       `---` / `# Heading` / `---`.

    Conditions 3 and 4 confine the ambiguity rather than removing it. Any blank-free
    payload that reads as YAML is *also* ordinary Markdown: `---` / `- Keep this` /
    `---` is a list between two thematic breaks, `---` / `title: v` / `---` is a
    setext heading under one. Both satisfy all four conditions and their content *is*
    excluded. Frontmatter wins, the same call every mainstream site generator makes.
    A document that fails any of the four conditions falls through to ordinary
    Markdown, where the worst case is that frontmatter is not skipped (a hash-drift
    warning) rather than content being silently discarded.

    Lines are replaced one-for-one with empty lines, so every line number the caller
    reports is unchanged."""
    lines = text.split("\n")
    if not lines or not _FRONTMATTER_OPEN_RE.match(lines[0]):
        return text
    for i in range(1, len(lines)):
        if _FRONTMATTER_CLOSE_RE.match(lines[i]):
            payload = lines[1:i]
            if not payload or any(ln.strip(" \t\f\v") == "" for ln in payload):
                return text
            if not any(_YAMLISH_LINE_RE.match(ln) for ln in payload):
                return text
            return "\n".join([""] * (i + 1) + lines[i + 1 :])
    return text


def _segment_blank_line(text: str) -> list[tuple[int, str]]:
    """Baseline segmenter (SPEC.md §5): a block is a maximal run of non-blank
    lines bounded by blank lines or the document edges. Dependency-free. Returns
    (start_line_1based, chunk_text) spans in document order."""
    chunks: list[tuple[int, str]] = []
    cur, start = [], None
    for idx, ln in enumerate(text.split("\n")):
        if ln.strip(" \t\f\v") == "":  # blank = only ASCII whitespace (SPEC.md §5)
            if cur:
                chunks.append((start, "\n".join(cur)))
                cur, start = [], None
        else:
            if not cur:
                start = idx + 1
            cur.append(ln)
    if cur:
        chunks.append((start, "\n".join(cur)))
    return chunks


def _segment_commonmark(text: str) -> list[tuple[int, str]]:
    """CommonMark-tree segmenter (SPEC.md §5.2, v1.1): a block is a node of the
    CommonMark block tree, so a loose list, a fence with internal blank lines, or
    a blockquote with internal blank lines is one span regardless of the blank
    lines inside it. A marker on its own line is its own (html_block) span, which
    the caller folds into the preceding content block exactly as it folds a
    blank-line marker-only chunk, so the attach layer above is identical.

    markdown-it-py is imported lazily so the default blank-line path keeps the
    linter dependency-free; CommonMark mode is the optional extra."""
    from markdown_it import MarkdownIt  # lazy: optional extra, see SPEC.md §5.2

    lines = text.split("\n")
    chunks: list[tuple[int, str]] = []
    for t in MarkdownIt("commonmark").parse(text):
        # Top-level block tokens carry a source line `map`; container openers
        # (nesting=1) span the whole container, self-contained tokens (nesting=0)
        # span themselves. Skip close tokens (nesting<0) and nested children
        # (level>0) so each block contributes exactly one span.
        if t.level == 0 and t.nesting >= 0 and t.map is not None:
            s, e = t.map
            chunks.append((s + 1, "\n".join(lines[s:e])))
    return chunks


_LIST_PREFIX_RE = re.compile(
    r"^(?P<indent> {0,3})(?P<marker>(?:[*+-]|[0-9]{1,9}[.)]))(?P<gap>[ \t]+)(?=\S)"
)
_THEMATIC_RE = re.compile(
    r"^ {0,3}(?:(?:\*[ \t]*){3,}|(?:-[ \t]*){3,}|(?:_[ \t]*){3,})$"
)
_UNSAFE_ITEM_BODY_RE = re.compile(
    r"^(?:#{1,6}(?:[ \t]|$)|>|```|~~~|(?:[*+-]|[0-9]{1,9}[.)])[ \t]+)"
)


@dataclass
class _ChildSpan:
    start_line: int
    end_line: int
    text: str
    marker_line: int
    excluded_lines: set[int] = field(default_factory=set)
    kind: str = "list"


def child_body(
    text: str,
    code: set[int] | None = None,
    line_offset: int = 0,
    kind: str = "list",
    markers_already_stripped: bool = False,
) -> str:
    """The hashed body of one child block (SPEC.md §5.5): the item's own text with
    its list prefix and continuation indent removed.

    ``code`` is the SPEC.md §3.3 mask for the document ``text`` was sliced from,
    and ``line_offset`` the 0-based line index at which the slice begins. Without
    them the strip is code-blind, which lets a fenced example inside a list item be
    removed from the child's body while the container that holds the same fence
    keeps it: one document, two §8 answers. Only the CommonMark child profile can
    reach that shape, since the dependency-free profile refuses any item carrying a
    fence, but the parameter is threaded from both."""
    if kind == "row":
        cells = _row_cells(text)
        if cells is None:
            return ""
        return "|".join(
            cell.replace("\\", "\\\\").replace("|", "\\|") for cell in cells
        )
    if kind != "list":
        raise ValueError(f"unknown child kind: {kind!r}")

    clean = (
        text
        if markers_already_stripped
        else (
            _strip_markers(text)
            if not code
            else _strip_markers_outside_code(text, code, line_offset)
        )
    )
    lines = clean.split("\n")
    if lines:
        match = _LIST_PREFIX_RE.match(lines[0])
        if match:
            prefix = match.group(0)
            width = 0
            for char in prefix:
                width = width + 1 if char != "\t" else width + (4 - width % 4)
            lines[0] = lines[0][len(prefix) :]
            for i in range(1, len(lines)):
                col = 0
                cut = 0
                for cut, char in enumerate(lines[i], 1):
                    if char == " ":
                        col += 1
                    elif char == "\t":
                        col += 4 - col % 4
                    else:
                        cut = 0
                        break
                    if col >= width:
                        break
                if col == width:
                    lines[i] = lines[i][cut:]
    return "\n".join(lines).strip(" \t\n\r\f\v")


_DELIMITER_CELL_RE = re.compile(r"^:?-+:?$")


def _line_marker_spans(line: str) -> list[tuple[int, int]]:
    return [
        (record.start, record.end)
        for record in _scan_marker_records(line)
        if not record.marker.malformed
    ]


def _spans_overlap(spans: list[tuple[int, int]]) -> bool:
    return any(
        start < previous_end for (_, previous_end), (start, _) in zip(spans, spans[1:])
    )


def _remove_spans(text: str, spans: list[tuple[int, int]]) -> str:
    out: list[str] = []
    previous = 0
    for start, end in spans:
        out.append(text[previous:start])
        previous = end
    out.append(text[previous:])
    return "".join(out)


def _row_cells(line: str) -> list[str] | None:
    """Return §5.6 cells after fixing boundaries around opaque marker tokens."""
    leading_spaces = len(line) - len(line.lstrip(" "))
    if leading_spaces > 3:
        return None
    working = line[leading_spaces:].rstrip(" \t\f\v")
    if not working:
        return None
    spans = _line_marker_spans(working)
    if _spans_overlap(spans):
        return None

    delimiters: list[int] = []
    backslashes = 0
    pos = 0
    span_index = 0
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
    if len(delimiters) < 2 or delimiters[0] != 0 or delimiters[-1] != len(working) - 1:
        return None

    cells: list[str] = []
    for start, end in zip(delimiters, delimiters[1:]):
        cell_spans = [
            (
                max(marker_start, start + 1) - (start + 1),
                min(marker_end, end) - (start + 1),
            )
            for marker_start, marker_end in spans
            if start < marker_start and marker_end <= end
        ]
        cell = _remove_spans(working[start + 1 : end], cell_spans)
        cells.append(cell.strip(" \t\f\v"))
    return cells


def _marker_only_line(line: str) -> bool:
    spans = _line_marker_spans(line)
    return (
        bool(spans)
        and not _spans_overlap(spans)
        and _remove_spans(line, spans).strip(" \t\f\v") == ""
    )


def _row_refused_marker_lines(text: str, code: set[int]) -> set[int]:
    records = [
        record
        for record in _scan_marker_records(text)
        if not record.marker.malformed and _marker_outside_code(record.marker, code)
    ]
    refused: set[int] = set()
    spans: list[tuple[int, int, int, int]] = []
    for record in records:
        first = text.count("\n", 0, record.start) + 1
        last = text.count("\n", 0, max(record.start, record.end - 1)) + 1
        spans.append((record.start, record.end, first, last))
        if first != last:
            refused.update(range(first, last + 1))
    for index, (start, end, first, last) in enumerate(spans):
        for other_start, other_end, other_first, other_last in spans[index + 1 :]:
            if other_start >= end:
                break
            if other_end > start:
                refused.update(range(first, last + 1))
                refused.update(range(other_first, other_last + 1))
    return refused


@dataclass
class _TableCandidate:
    header_line: int
    end_line: int
    rows: list[_ChildSpan]


def _table_candidates(
    text: str, code: set[int], provenance: set[int] | None = None
) -> list[_TableCandidate]:
    """Complete document-level §5.6 scan before selected-container filtering."""
    lines = text.split("\n")
    refused_marker_lines = _row_refused_marker_lines(text, code)
    candidates: list[_TableCandidate] = []
    i = 0
    while i + 1 < len(lines):
        header = (
            None
            if i + 1 in code or i + 1 in refused_marker_lines
            else _row_cells(lines[i])
        )
        delimiter = (
            None
            if i + 2 in code or i + 2 in refused_marker_lines
            else _row_cells(lines[i + 1])
        )
        delimiter_shaped = (
            delimiter is not None
            and bool(delimiter)
            and all(_DELIMITER_CELL_RE.fullmatch(cell) for cell in delimiter)
        )
        if provenance is not None and header is not None and delimiter_shaped:
            provenance.update((i + 1, i + 2))
        if (
            header is None
            or delimiter is None
            or bool(_line_marker_spans(lines[i + 1]))
            or "\f" in lines[i + 1]
            or "\v" in lines[i + 1]
            or len(header) != len(delimiter)
            or not delimiter_shaped
        ):
            i += 1
            continue

        rows: list[_ChildSpan] = []
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
            if line.strip(" \t\f\v") == "" or _marker_only_line(line):
                break
            if provenance is not None:
                provenance.add(line_number)
            cells = _row_cells(line)
            if cells is None:
                refused = True
            else:
                rows.append(
                    _ChildSpan(
                        line_number,
                        line_number,
                        line,
                        line_number,
                        kind="row",
                    )
                )
            j += 1
        if not refused:
            candidates.append(_TableCandidate(i + 1, max(i + 2, j), rows))
        if j >= len(lines):
            break
        i = j + 1
    return candidates


def _table_spans_by_container(
    text: str, chunks: list[tuple[int, str]], code: set[int]
) -> dict[int, list[_ChildSpan]]:
    """Map accepted candidates to §5 blocks, then enforce one per container."""
    candidates_by_start: dict[int, list[_TableCandidate]] = {}
    for candidate in _table_candidates(text, code):
        for start, chunk in chunks:
            end = start + len(chunk.split("\n")) - 1
            if start <= candidate.header_line and candidate.end_line <= end:
                candidates_by_start.setdefault(start, []).append(candidate)
                break
    return {
        start: candidates[0].rows
        for start, candidates in candidates_by_start.items()
        if len(candidates) == 1
    }


def _restricted_child_spans(chunk: str, start: int) -> list[_ChildSpan]:
    """Fail-closed profile: flat, tight, single-paragraph list items."""
    lines = chunk.split("\n")
    items: list[tuple[int, int, str]] = []
    item_start: int | None = None
    item_lines: list[str] = []
    content_indent = 0
    saw_parent_marker = False
    signature: tuple[tuple[str, str], str] | None = None
    for off, raw in enumerate(lines):
        clean = _strip_markers(raw).strip(" \t\r\f\v")
        markers = find_markers(raw, line_offset=start + off - 1)
        if clean == "" and markers:
            saw_parent_marker = True
            continue
        if saw_parent_marker or _THEMATIC_RE.match(_strip_markers(raw)):
            return []
        m = _LIST_PREFIX_RE.match(_strip_markers(raw))
        if m:
            prefix = m.group(0)
            body = _strip_markers(raw)[len(prefix) :]
            if "\t" in prefix or _UNSAFE_ITEM_BODY_RE.match(body):
                return []
            if item_start is not None:
                items.append((item_start, off - 1, "\n".join(item_lines)))
            marker = m.group("marker")
            kind = (
                ("ordered", marker[-1]) if marker[0].isdigit() else ("bullet", marker)
            )
            # The marker's own indentation is part of the signature: an indented
            # `  - Nested` matches _LIST_PREFIX_RE as happily as a top-level one
            # and would be emitted as a *sibling* of the item containing it, a
            # child block SPEC.md §5.5 says does not exist, shifting every later
            # ordinal so the two segmenters disagree about which item a child
            # stay addresses.
            current = (kind, m.group("indent"))
            if signature is None:
                signature = current
            elif signature != current:
                return []
            item_start, item_lines, content_indent = off, [raw], len(prefix)
            continue
        clean_raw = _strip_markers(raw)
        indent = " " * content_indent
        if (
            item_start is None
            or not clean_raw.startswith(indent)
            or clean_raw[len(indent) :].startswith(" ")
            or _UNSAFE_ITEM_BODY_RE.match(clean_raw[len(indent) :])
        ):
            return []
        item_lines.append(raw)
    if item_start is not None:
        items.append(
            (item_start, item_start + len(item_lines) - 1, "\n".join(item_lines))
        )
    return (
        [
            _ChildSpan(start + first, start + last, raw, start + last)
            for first, last, raw in items
        ]
        if items
        else []
    )


def _commonmark_child_spans(chunk: str, start: int) -> list[_ChildSpan]:
    from markdown_it import MarkdownIt

    tokens = MarkdownIt("commonmark").parse(chunk)
    roots = [
        t
        for t in tokens
        if t.level == 0
        and t.nesting == 1
        and t.map is not None
        and t.type in ("bullet_list_open", "ordered_list_open")
    ]
    if len(roots) != 1:
        return []
    raw_lines = chunk.split("\n")
    spans: list[_ChildSpan] = []
    for t in tokens:
        if t.type != "list_item_open" or t.level != 1 or t.map is None:
            continue
        s, e = t.map
        excluded: set[int] = set()
        for nested in tokens:
            if (
                nested.type == "list_item_open"
                and nested.level > 1
                and nested.map is not None
                and s <= nested.map[0] < nested.map[1] <= e
            ):
                excluded.update(range(start + nested.map[0], start + nested.map[1]))
        marker_line = 0
        paragraph_ends = [
            x.map[1]
            for x in tokens
            if (
                x.type == "paragraph_open"
                and x.level == 2
                and x.map is not None
                and s <= x.map[0] < x.map[1] <= e
            )
        ]
        if paragraph_ends:
            marker_line = start + paragraph_ends[-1] - 1
        spans.append(
            _ChildSpan(
                start + s,
                start + e - 1,
                "\n".join(raw_lines[s:e]),
                marker_line,
                excluded,
            )
        )
    return spans


def segment_child_items(chunk: str, start_line: int, mode: str) -> list[_ChildSpan]:
    if mode == "commonmark":
        return _commonmark_child_spans(chunk, start_line)
    if mode == "blank-line":
        return _restricted_child_spans(chunk, start_line)
    raise ValueError(f"unknown parse mode: {mode!r} (use 'blank-line' or 'commonmark')")


def _line_starts(text: str) -> list[int]:
    starts = [0]
    starts.extend(match.end() for match in re.finditer("\n", text))
    return starts


def _document_marker_records(md: str, text: str) -> list[_MarkerRecord]:
    """Normalized/frontmatter-blanked records retaining exact caller bytes."""
    normalized = md.replace("\r\n", "\n").replace("\r", "\n")
    normalized_lines = normalized.split("\n")
    blanked_lines = text.split("\n")
    frontmatter_lines = {
        line
        for line, (source, blanked) in enumerate(
            zip(normalized_lines, blanked_lines), 1
        )
        if source != blanked
    }
    raw_records = [
        record
        for record in _scan_marker_records(md)
        if record.marker.line not in frontmatter_lines
    ]
    normalized_records = _scan_marker_records(text)

    def facts(record: _MarkerRecord) -> tuple:
        marker = record.marker
        return (
            marker.line,
            marker.syntax,
            marker.id,
            marker.hash,
            marker.subhash,
            marker.has_subhash,
            marker.malformed,
        )

    if [facts(record) for record in raw_records] != [
        facts(record) for record in normalized_records
    ]:
        return normalized_records
    return [
        _MarkerRecord(
            normalized_record.start,
            normalized_record.end,
            replace(normalized_record.marker, raw=raw_record.marker.raw),
        )
        for normalized_record, raw_record in zip(normalized_records, raw_records)
    ]


def _record_line_bounds(text: str, record: _MarkerRecord) -> tuple[int, int]:
    """Inclusive source lines occupied by one complete marker record."""
    return (
        record.marker.line,
        text.count("\n", 0, max(record.start, record.end - 1)) + 1,
    )


def _record_belongs_to_child(
    text: str, record: _MarkerRecord, span: _ChildSpan
) -> bool:
    first, last = _record_line_bounds(text, record)
    return (
        span.start_line <= first
        and last <= span.end_line
        and not any(line in span.excluded_lines for line in range(first, last + 1))
    )


def parse_document(
    md: str, mode: str = "blank-line", child_blocks: bool = False
) -> list[Block]:
    """Parse into content blocks with their attached markers.

    `mode='blank-line'` (default, dependency-free) splits on blank lines (SPEC.md
    §5). `mode='commonmark'` (v1.1, needs markdown-it-py) splits on the CommonMark
    block tree so loose lists and blank-line-containing fences attach as one block
    (SPEC.md §5.2). The two agree on every document in SPEC.md §5.4's agreement
    subset. In both modes a leading YAML frontmatter
    block is metadata rather than content and is skipped before segmentation (see
    `_blank_frontmatter`, without which frontmatter is a counterexample to that
    agreement), and a chunk that is only markers attaches to the previous content
    block."""
    text = _blank_frontmatter(md.replace("\r\n", "\n").replace("\r", "\n"))
    # SPEC.md §3.3: text inside a fenced code block is content. The rule is
    # computed once over the whole document and threaded, on the
    # `_blank_frontmatter` precedent, because neither segmenter has a concept of
    # a fence and `find_markers` is handed chunks. Blanking preserves line
    # numbers, so this mask indexes the caller's text as well as `text`.
    code = code_lines(text)
    if mode == "commonmark":
        chunks = _segment_commonmark(text)
    elif mode == "blank-line":
        chunks = _segment_blank_line(text)
    else:
        raise ValueError(
            f"unknown parse mode: {mode!r} (use 'blank-line' or 'commonmark')"
        )

    document_records = _document_marker_records(md, text)
    active_records = [
        record
        for record in document_records
        if _marker_outside_code(record.marker, code)
    ]
    removable_records = [
        record for record in active_records if not record.marker.malformed
    ]
    line_starts = _line_starts(text)

    child_spans: dict[int, list[_ChildSpan]] = {}
    if child_blocks:
        for start, chunk in chunks:
            child_spans[start] = segment_child_items(chunk, start, mode)
        if mode == "blank-line":
            run: list[int] = []
            for start, _ in chunks + [(-1, "")]:
                if start >= 0 and child_spans.get(start):
                    run.append(start)
                    continue
                if len(run) > 1:
                    for loose_start in run:
                        child_spans[loose_start] = []
                run = []
        table_spans = _table_spans_by_container(text, chunks, code)
        for start, spans in table_spans.items():
            # Row ownership wins when a table sits inside a direct list item.
            # The two child kinds retain separate ordinals and sibling scopes.
            child_spans.setdefault(start, []).extend(spans)
        for spans in child_spans.values():
            spans.sort(
                key=lambda span: (span.start_line, 0 if span.kind == "row" else 1)
            )

    blocks: list[Block] = []
    cidx = 0
    child_idx = 0
    for start, chunk in chunks:
        chunk_start = line_starts[start - 1]
        chunk_end = chunk_start + len(chunk)
        chunk_records = [
            record
            for record in active_records
            if chunk_start <= record.start < chunk_end
        ]
        markers = [record.marker for record in chunk_records]
        record_by_marker = {id(record.marker): record for record in chunk_records}
        content = _strip_record_ranges(
            chunk, removable_records, source_start=chunk_start
        ).strip(
            " \t\n\r\f\v"
        )  # ASCII strip (SPEC.md §5/§8)
        if content == "":
            # marker-only chunk: attach to the previous content block if any
            if blocks and blocks[-1].index >= 0:
                blocks[-1].markers.extend(markers)
            else:
                blocks.append(Block(content="", markers=markers, line=start, index=-1))
        else:
            children: list[ChildBlock] = []
            child_marker_ids: set[int] = set()
            if child_blocks:
                ordinals: dict[str, int] = {}
                row_marker_ids = {
                    id(mk)
                    for span in child_spans.get(start, [])
                    if span.kind == "row"
                    for mk in markers
                    if mk.has_subhash
                    and _record_belongs_to_child(text, record_by_marker[id(mk)], span)
                }
                for span in child_spans.get(start, []):
                    ordinals[span.kind] = ordinals.get(span.kind, 0) + 1
                    owned = [
                        mk
                        for mk in markers
                        if mk.has_subhash
                        and id(mk) not in child_marker_ids
                        and (span.kind == "row" or id(mk) not in row_marker_ids)
                        and _record_belongs_to_child(
                            text, record_by_marker[id(mk)], span
                        )
                    ]
                    child_marker_ids.update(id(mk) for mk in owned)
                    span_text = span.text
                    if span.kind == "list":
                        # Strip using full-document record ranges so a marker
                        # crossing an item boundary does not leave a dangling
                        # opener or closer in either child's hash. Ownership is
                        # still stricter: only a record wholly contained in one
                        # direct item can address it.
                        span_text = _strip_record_ranges(
                            span_text,
                            removable_records,
                            source_start=line_starts[span.start_line - 1],
                        )
                    children.append(
                        ChildBlock(
                            content=child_body(
                                span_text,
                                code,
                                span.start_line - 1,
                                span.kind,
                                markers_already_stripped=span.kind == "list",
                            ),
                            markers=owned,
                            line=span.start_line,
                            index=child_idx,
                            ordinal=ordinals[span.kind],
                            parent_index=cidx,
                            marker_line=span.marker_line,
                            kind=span.kind,
                        )
                    )
                    child_idx += 1
            blocks.append(
                Block(
                    content=content,
                    markers=[mk for mk in markers if id(mk) not in child_marker_ids],
                    line=start,
                    index=cidx,
                    children=children,
                )
            )
            cidx += 1
    return blocks


# --- heading paths (experimental, not spec behaviour) ---------------------
#
# The enclosing section a block sits in, as an ordered list of heading titles.
# This is candidate recovery evidence for the QUOTE tier (SPEC.md §9), being
# measured before any of it is proposed for the spec; nothing in the linter's
# published checks consumes it. See eval/attachment/ for the experiment.
#
# Derived from the document's **source lines**, never from `Block.content`.
# Content has already lost the leading indent that separates an indented code
# block from a heading (`    # deploy` is code, `# deploy` is a section), and it
# has had markers removed, so a derivation reading it cannot tell those cases
# apart. Blocks come in only to map a line's path onto the block that starts
# there.

# Fence recognition is shared with §3.3 (`_fence_state` above), so heading paths
# and the marker mask never disagree about where a code block is.
# The opening `#` run must be followed by whitespace or end the line: `#Foo` is a
# paragraph, not a heading (CommonMark 4.2). Indent is at most 3 spaces; 4 makes
# it an indented code block.
_ATX_RE = re.compile(r"^ {0,3}(?P<hashes>#{1,6})(?:[ \t]+(?P<title>.*?))?[ \t]*$")
# A closing `#` run only closes when whitespace precedes it, so `## foo#` keeps
# its trailing hash and `## foo #` does not.
_ATX_CLOSE_RE = re.compile(r"(?:^|[ \t])#+[ \t]*$")
_SETEXT_RE = re.compile(r"^ {0,3}(?P<run>=+|-+)[ \t]*$")
# Lines that cannot be the paragraph a setext underline applies to. Blockquote
# and list openers put following lines in a container (their continuations are
# lazy, so they are not document-level paragraph text either); an indented line
# with no paragraph open is code; a link reference definition is consumed by the
# parser and emits no paragraph at all.
_CONTAINER_RE = re.compile(r"^ {0,3}(?:>|(?:[*+-]|[0-9]{1,9}[.)])(?:[ \t]|$))")
_INDENTED_RE = re.compile(r"^(?: {4}|\t)")
_LINKDEF_RE = re.compile(r"^ {0,3}\[[^\]]*\]:")
# HTML blocks (CommonMark 4.6). Types 1 to 5 close on their own end condition,
# type 6 on a blank line. Type 7 (any complete tag alone on a line) is
# deliberately not recognised: it cannot interrupt a paragraph, it is the rarest
# of the seven, and treating an arbitrary custom tag as a block opener would
# swallow real headings after it.
_HTML_TAGS_6 = (
    "address|article|aside|base|basefont|blockquote|body|caption|center|col|"
    "colgroup|dd|details|dialog|dir|div|dl|dt|fieldset|figcaption|figure|"
    "footer|form|frame|frameset|h1|h2|h3|h4|h5|h6|head|header|hr|html|iframe|"
    "legend|li|link|main|menu|menuitem|nav|noframes|ol|optgroup|option|p|param|"
    "search|section|summary|table|tbody|td|tfoot|th|thead|title|tr|track|ul"
)
_HTML_OPEN = (
    (
        re.compile(r"^ {0,3}<(?:script|pre|style|textarea)(?:[ \t>]|$)", re.I),
        re.compile(r"</(?:script|pre|style|textarea)>", re.I),
    ),
    (re.compile(r"^ {0,3}<!--"), re.compile(r"-->")),
    (re.compile(r"^ {0,3}<\?"), re.compile(r"\?>")),
    (re.compile(r"^ {0,3}<![A-Za-z]"), re.compile(r">")),
    (re.compile(r"^ {0,3}<!\[CDATA\["), re.compile(r"\]\]>")),
    (re.compile(rf"^ {{0,3}}</?(?:{_HTML_TAGS_6})(?:[ \t/>]|$)", re.I), None),
)

# Inline markup removed before the §9 fold, matched as *pairs* only. A blanket
# strip of `*`, backtick and `~` collides section titles that differ by literal
# punctuation (`*.py` with `.py`, `~/.config` with `/.config`, `A * B` with
# `A B`), which is a worse failure than missing an unpaired delimiter.
_INLINE_RES = (
    (re.compile(r"!?\[(?P<text>[^\]]*)\]\([^()]*\)"), r"\g<text>"),  # inline link
    (re.compile(r"!?\[(?P<text>[^\]]*)\]\[[^\]]*\]"), r"\g<text>"),  # ref link
    (re.compile(r"`+(?P<text>[^`]+)`+"), r"\g<text>"),  # code span
    (re.compile(r"\*\*(?=\S)(?P<text>.+?)(?<=\S)\*\*"), r"\g<text>"),
    (
        re.compile(r"(?<![0-9A-Za-z_])__(?=\S)(?P<text>.+?)(?<=\S)__(?![0-9A-Za-z_])"),
        r"\g<text>",
    ),
    (re.compile(r"~~(?=\S)(?P<text>.+?)(?<=\S)~~"), r"\g<text>"),
    (re.compile(r"\*(?=\S)(?P<text>.+?)(?<=\S)\*"), r"\g<text>"),
    # `_` opens or closes emphasis only at a word boundary: intraword underscores
    # are literal, so `sync_corpus.sh` keeps its underscore while `_Rollback_`
    # loses its delimiters.
    (
        re.compile(r"(?<![0-9A-Za-z_])_(?=\S)(?P<text>.+?)(?<=\S)_(?![0-9A-Za-z_])"),
        r"\g<text>",
    ),
)


def canonical_heading(title: str) -> str:
    """Compare-form of one heading title.

    SPEC.md §9's fold (lowercase ASCII, collapse ASCII whitespace runs, trim)
    plus a heading-specific step the fold does not do: paired inline emphasis,
    code spans and link syntax come out first. A heading is short enough that one
    emphasis span is a large fraction of the string, so `## **Rollback**` and
    `## Rollback` folding differently would break the signal on a purely cosmetic
    edit, which is what an LLM rewrite does to headings. Only *paired*
    delimiters are removed, so a title that merely contains `*`, `` ` `` or `~`
    keeps it."""
    out = title
    for pattern, repl in _INLINE_RES:
        out = pattern.sub(repl, out)
    return re.sub(r"[ \t\n\r\f\v]+", " ", out.strip(" \t\n\r\f\v")).translate(
        _ASCII_LOWER
    )


def _paths_by_line(md: str) -> list[list[str]]:
    """The enclosing heading titles for every 0-indexed source line.

    A heading line carries its *parents*: the stack is popped for the incoming
    level before the line's path is recorded, so `## Prod` under `# Deploy`
    records `["Deploy"]` rather than the path of the sibling section above it.
    A setext title line is rescoped the same way once its underline is read."""
    text = _blank_frontmatter(md.replace("\r\n", "\n").replace("\r", "\n"))
    # SPEC.md §3.3 fence geometry, computed once over the document by
    # `_fence_state` and threaded here on the `parse_document` precedent, rather
    # than re-derived below. A second recogniser is a second answer: this one used
    # to run over the marker-stripped lines, so a marker whose line ended in a
    # backtick run became a bare fence opener to it and no fence at all to §3.3,
    # and every heading after it was swallowed by a fence that never closed.
    # Blanking preserves line numbers, so the mask indexes `lines` directly.
    code = code_lines(text)
    # Markers are stripped per line rather than document-wide: a multi-line
    # marker would otherwise take its newlines with it and shift every line
    # number after it.
    lines = [_strip_markers(raw) for raw in text.split("\n")]
    stack: list[tuple[int, str]] = []
    out: list[list[str]] = []
    html_close: re.Pattern | None = None
    html_blank_ends = False
    para: list[int] = []  # line indices of an open paragraph (a setext candidate)
    container = False  # inside a blockquote or list item, until a blank line

    def pop_to(level: int) -> None:
        while stack and stack[-1][0] >= level:
            stack.pop()

    for line_no, line in enumerate(lines, 1):
        blank = line.strip(" \t\f\v") == ""

        # An open HTML block is tested first, so it can still close on a
        # fence-shaped line: §3.3's line scan has no concept of an HTML block, so
        # letting the mask short-circuit here would leave the block open to the end
        # of the document and lose every heading under it. Once it closes, the mask
        # below still applies, so a line either recogniser calls code contributes no
        # heading.
        if html_close is not None or html_blank_ends:
            if (html_blank_ends and blank) or (
                html_close is not None and html_close.search(line)
            ):
                html_close, html_blank_ends = None, False
            out.append([t for _, t in stack])
            para = []
            continue

        if line_no in code:
            # Fence lines included: a heading cannot open inside a fenced block,
            # and a fenced line is not a lazy continuation of an open container.
            out.append([t for _, t in stack])
            para, container = [], False
            continue

        atx = _ATX_RE.match(line)
        if atx:
            level = len(atx.group("hashes"))
            title = _ATX_CLOSE_RE.sub("", atx.group("title") or "").strip(" \t")
            pop_to(level)
            out.append([t for _, t in stack])
            stack.append((level, title))
            para, container = [], False
            continue

        setext = _SETEXT_RE.match(line)
        if setext and para:
            level = 1 if setext.group("run")[0] == "=" else 2
            title = " ".join(lines[i].strip(" \t") for i in para)
            pop_to(level)
            parents = [t for _, t in stack]
            for i in para:  # the title lines belong to the heading, not above it
                out[i] = parents
            stack.append((level, title))
            out.append([t for _, t in stack])
            para, container = [], False
            continue

        out.append([t for _, t in stack])
        if blank:
            para, container = [], False
        elif _CONTAINER_RE.match(line):
            # Everything up to the next blank line belongs to the blockquote or
            # list item, including lines that look like top-level paragraph text
            # (they are lazy continuations of the container's paragraph).
            para, container = [], True
        elif container:
            para = []
        elif para:
            para.append(len(out) - 1)  # continuation of the open paragraph
        elif _INDENTED_RE.match(line) or _LINKDEF_RE.match(line):
            para = []
        elif any(op.match(line) for op, _ in _HTML_OPEN):
            for op, close in _HTML_OPEN:
                if op.match(line):
                    if close is None:
                        html_blank_ends = True
                    elif not close.search(line):
                        html_close = close
                    break
        else:
            para = [len(out) - 1]
    return out


def heading_paths(md: str, blocks: list[Block]) -> list[list[str]]:
    """The enclosing heading titles for each block, parallel to `blocks`.

    `md` is the same source `parse_document` was given; `blocks` is what it
    returned, in either segmentation mode. A block takes the path of the source
    line it starts on, so the rules are:

    * **A block is scoped by the headings that precede it**, and a heading never
      appears in its own path. A block opening with a heading gets that
      heading's parents.
    * A heading the segmenter glued to the body after it (`# H` with no blank
      line before `Body.`, one block under blank-line segmentation and two under
      CommonMark, SPEC.md §5.4) is recognised either way, and scopes the blocks
      that *follow* the block containing it.
    * All six ATX levels and both setext levels count, held as a stack popped on
      `level >= incoming`, so a skipped level nests rather than replacing.
    * Fenced code, indented code, HTML blocks, blockquotes and list items cannot
      contribute a heading, and a link reference definition or a lazy
      continuation line cannot become a setext title.
    * **Fenced code is SPEC.md §3.3's geometry exactly**, read from `_fence_state`
      rather than re-derived here, so there is one fence recogniser in this module
      and not two. That makes it narrower than CommonMark where the two part
      company: a fence opened inside an HTML block is open, and an unclosed fence
      runs to the end of the document. Agreeing with §3.3 is the point, since a
      second reading of the same lines is what let a marker sitting before a
      backtick run open a fence nothing else could see.

    Titles come back as written; use `canonical_heading` to compare them.
    Experimental: no spec text defines this yet (see eval/attachment/)."""
    by_line = _paths_by_line(md)
    if not by_line:
        return [[] for _ in blocks]
    return [by_line[max(0, min(len(by_line) - 1, b.line - 1))] for b in blocks]


# --- checks ---------------------------------------------------------------


def lint_document(
    md: str, mode: str = "blank-line", child_blocks: bool = False
) -> tuple[list[Block], list[Finding]]:
    """Well-formedness and intra-document invariants for a single file."""
    blocks = parse_document(md, mode=mode, child_blocks=child_blocks)
    findings: list[Finding] = []
    seen: dict[str, int] = {}

    # Malformed and duplicate checks are lexical and document-global. Run them
    # once in source order before attachment separates block and child markers.
    normalized = md.replace("\r\n", "\n").replace("\r", "\n")
    scannable = _blank_frontmatter(normalized)
    code = code_lines(scannable)
    table_scan_lines: set[int] = set()
    _table_candidates(scannable, code, table_scan_lines)
    for record in _document_marker_records(md, scannable):
        mk = record.marker
        if not _marker_outside_code(mk, code):
            continue
        if mk.malformed:
            findings.append(
                Finding(
                    "error",
                    "MALFORMED_MARKER",
                    f"marker has no parseable id: {mk.raw!r}",
                    line=mk.line,
                )
            )
            continue
        if mk.id in seen:
            findings.append(
                Finding(
                    "error",
                    "DUPLICATE_ID",
                    f"id {mk.id} appears more than once (first at line {seen[mk.id]})",
                    id=mk.id,
                    line=mk.line,
                )
            )
        else:
            seen[mk.id] = mk.line

    def check_marker(mk: Marker, body: str, orphan: bool = False, child: bool = False):
        if mk.malformed:
            return
        if orphan:
            findings.append(
                Finding(
                    "error",
                    "ORPHAN_MARKER",
                    f"marker {mk.id} has no preceding block to attach to",
                    id=mk.id,
                    line=mk.line,
                )
            )
            # An orphan has no body to attribute or hash. Exact `subhash`
            # presence excludes containing-block attribution (§16), but does
            # not waive the required orphan diagnostic (§5).
            return
        if mk.has_subhash and not child:
            return
        stored = mk.subhash if child else mk.hash
        if stored and (child or body):
            now = body_hash(body, len(stored))
            if now != stored:
                key = "subhash" if child else "hash"
                findings.append(
                    Finding(
                        "warn",
                        "HASH_DRIFT",
                        f"id {mk.id}: stored {key}=sha256:{stored} != current "
                        f"sha256:{now} (content edited since the hash was written)",
                        id=mk.id,
                        line=mk.line,
                    )
                )

    for b in blocks:
        orphan = b.index == -1
        for mk in b.markers:
            check_marker(mk, b.content, orphan=orphan)
        if child_blocks and b.index >= 0:
            # SPEC.md §5.5: a `subhash` marker that no child block owns addresses
            # nothing. It reaches here from an item nested inside another item,
            # which v1.3 does not address, and it is not the container's stay
            # either. Reporting it is the SHOULD in §5.5: silence is
            # indistinguishable from a marker that resolved.
            for mk in b.markers:
                if mk.has_subhash and mk.id and not mk.malformed:
                    if mk.line in table_scan_lines:
                        target = "table row"
                        why = "the complete §5.6 scan did not accept this as a body row"
                    else:
                        target = "list item"
                        why = (
                            "nested items are not child blocks in v1.3"
                            if any(child.kind == "list" for child in b.children)
                            else "this segmenter emitted no list child blocks for the block"
                        )
                    findings.append(
                        Finding(
                            "warn",
                            "CHILD_UNADDRESSED",
                            f"child id {mk.id} addresses no {target} ({why})",
                            id=mk.id,
                            line=mk.line,
                        )
                    )
            has_parent = any(
                mk.id and not mk.malformed and not mk.has_subhash for mk in b.markers
            )
            for child in b.children:
                for mk in child.markers:
                    check_marker(mk, child.content, child=True)
                    if not has_parent and mk.id and not mk.malformed:
                        findings.append(
                            Finding(
                                "warn",
                                "ORPHAN_CHILD",
                                f"child id {mk.id} has no stayed parent container",
                                id=mk.id,
                                line=mk.line,
                            )
                        )
    return blocks, findings


def _id_index(blocks: list[Block]) -> dict[str, list[Block]]:
    out: dict[str, list[Block]] = {}
    for b in blocks:
        if b.index < 0:
            continue
        for mk in b.markers:
            if mk.id and not mk.malformed and not mk.has_subhash:
                out.setdefault(mk.id, []).append(b)
    return out


def _child_id_index(blocks: list[Block]) -> dict[str, list[ChildBlock]]:
    out: dict[str, list[ChildBlock]] = {}
    for b in blocks:
        if b.index < 0:
            continue
        for child in b.children:
            for mk in child.markers:
                if mk.id and not mk.malformed:
                    out.setdefault(mk.id, []).append(child)
    return out


_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)

# SPEC.md §9: a stored prefix/suffix carries up to this many characters of the
# neighbour on each side. Both the stored and the candidate side are windowed to
# it, on raw text before normalization, so the two sides compare like with like.
_CONTEXT_CHARS = 48


def _match_normalize(text: str) -> str:
    return re.sub(r"[ \t\n\r\f\v]+", " ", text.strip(" \t\n\r\f\v")).translate(
        _ASCII_LOWER
    )


def _match_ratio(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0.0


def _body_score(quote: str, candidate: str) -> float:
    q, c = _match_normalize(quote), _match_normalize(candidate)
    if not q or not c:
        return 0.0
    if q == c:
        return 1.0
    score = _match_ratio(q, c)
    short, long = (q, c) if len(q) <= len(c) else (c, q)
    if short in long:
        score = max(score, len(short) / len(long))
    return score


def _best_match(
    quote: str, prefix: str, suffix: str, candidates: list[str]
) -> tuple[int, float, float]:
    scored: list[tuple[float, int]] = []
    for i, candidate in enumerate(candidates):
        score = _body_score(quote, candidate)
        if prefix:
            prev = candidates[i - 1] if i > 0 else ""
            score += 0.05 * _match_ratio(
                _match_normalize(prefix[-_CONTEXT_CHARS:]),
                _match_normalize(prev[-_CONTEXT_CHARS:]),
            )
        if suffix:
            nxt = candidates[i + 1] if i + 1 < len(candidates) else ""
            score += 0.05 * _match_ratio(
                _match_normalize(suffix[:_CONTEXT_CHARS]),
                _match_normalize(nxt[:_CONTEXT_CHARS]),
            )
        scored.append((score, i))
    if not scored:
        return -1, 0.0, 0.0
    scored.sort(reverse=True)
    best, idx = scored[0]
    runner = scored[1][0] if len(scored) > 1 else 0.0
    return idx, min(best, 1.0), min(runner, 1.0)


@dataclass
class _ChildAnchor:
    id: str
    hash: str
    quote: str
    prefix: str
    suffix: str
    ordinal: int
    parent_id: str | None
    parent_hash: str
    parent_quote: str
    parent_prefix: str
    parent_suffix: str
    sibling_hash_count: int
    document_hash_count: int
    kind: str


def _build_child_anchors(md: str, mode: str) -> list[_ChildAnchor]:
    blocks = [
        b for b in parse_document(md, mode=mode, child_blocks=True) if b.index >= 0
    ]
    doc_counts: dict[str, int] = {}
    for block in blocks:
        for child in block.children:
            digest = body_hash(child.content)
            doc_counts[digest] = doc_counts.get(digest, 0) + 1
    anchors: list[_ChildAnchor] = []
    for bi, block in enumerate(blocks):
        parent = next(
            (
                mk
                for mk in block.markers
                if mk.id and not mk.malformed and not mk.has_subhash
            ),
            None,
        )
        for child in block.children:
            siblings = [
                candidate
                for candidate in block.children
                if candidate.kind == child.kind
            ]
            ci = siblings.index(child)
            digest = body_hash(child.content)
            for mk in child.markers:
                if mk.id and not mk.malformed:
                    anchors.append(
                        _ChildAnchor(
                            id=mk.id,
                            hash=digest,
                            quote=child.content,
                            prefix=(
                                siblings[ci - 1].content[-_CONTEXT_CHARS:]
                                if ci > 0
                                else ""
                            ),
                            suffix=(
                                siblings[ci + 1].content[:_CONTEXT_CHARS]
                                if ci + 1 < len(siblings)
                                else ""
                            ),
                            ordinal=child.ordinal,
                            parent_id=parent.id if parent else None,
                            parent_hash=body_hash(block.content),
                            parent_quote=block.content,
                            parent_prefix=(
                                blocks[bi - 1].content[-_CONTEXT_CHARS:]
                                if bi > 0
                                else ""
                            ),
                            parent_suffix=(
                                blocks[bi + 1].content[:_CONTEXT_CHARS]
                                if bi + 1 < len(blocks)
                                else ""
                            ),
                            sibling_hash_count=sum(
                                1
                                for candidate in siblings
                                if body_hash(candidate.content) == digest
                            ),
                            document_hash_count=doc_counts[digest],
                            kind=child.kind,
                        )
                    )
    return anchors


def _resolve_parents(
    anchors: list[_ChildAnchor], blocks: list[Block]
) -> dict[str, tuple[int, str]]:
    """Resolve every distinct parent stay at once, assigning exclusively.

    Resolving each parent in isolation lets two anchors claim the same block: a
    deleted list whose near-duplicate sibling survives scores a large quote
    margin against it, because the only rival that would have contested the
    match is the one the edit removed. Running the tiers as global passes and
    consuming a block when a stronger tier claims it removes that whole class of
    wrong-parent recovery, and with it the child cascade underneath.
    """

    reps: dict[str, _ChildAnchor] = {}
    for anchor in anchors:
        if anchor.parent_id is not None:
            reps.setdefault(anchor.parent_id, anchor)

    out: dict[str, tuple[int, str]] = {}
    claimed: set[int] = set()

    for pid in reps:
        for idx, block in enumerate(blocks):
            if any(
                mk.id == pid and not mk.malformed and not mk.has_subhash
                for mk in block.markers
            ):
                out[pid] = (idx, "marker")
                claimed.add(idx)
                break

    hash_proposals: dict[str, int] = {}
    for pid, anchor in reps.items():
        if pid in out:
            continue
        hits = [
            idx
            for idx, block in enumerate(blocks)
            if body_hash(block.content) == anchor.parent_hash and idx not in claimed
        ]
        if len(hits) == 1:
            hash_proposals[pid] = hits[0]
    hash_counts: dict[int, int] = {}
    for target in hash_proposals.values():
        hash_counts[target] = hash_counts.get(target, 0) + 1
    for pid, target in hash_proposals.items():
        if hash_counts[target] == 1:
            out[pid] = (target, "hash")
            claimed.add(target)

    # Every parent scores against one tier-start snapshot. A target reached by
    # two stays at this tier goes to neither (§9.2), rather than to the higher
    # score or whichever parent happened to be enumerated first.
    quote_proposals: dict[str, tuple[int, float]] = {}
    for pid, anchor in reps.items():
        if pid in out:
            continue
        candidates = [idx for idx in range(len(blocks)) if idx not in claimed]
        idx, score, runner = _best_match(
            anchor.parent_quote,
            anchor.parent_prefix,
            anchor.parent_suffix,
            [blocks[i].content for i in candidates],
        )
        if idx >= 0 and score >= 0.5 and score - runner >= 0.05:
            quote_proposals[pid] = (candidates[idx], score)
    quote_counts: dict[int, int] = {}
    for target, _ in quote_proposals.values():
        quote_counts[target] = quote_counts.get(target, 0) + 1
    for pid, (target, _) in quote_proposals.items():
        if quote_counts[target] == 1:
            out[pid] = (target, "quote")
            claimed.add(target)
    return out


def _resolve_children(
    anchors: list[_ChildAnchor], after_md: str, mode: str
) -> dict[str, tuple[str, int | None]]:
    blocks = [
        b
        for b in parse_document(after_md, mode=mode, child_blocks=True)
        if b.index >= 0
    ]
    all_children = [child for block in blocks for child in block.children]
    marked: dict[str, ChildBlock] = {}
    hashes: dict[str, list[ChildBlock]] = {}
    for child in all_children:
        hashes.setdefault(body_hash(child.content), []).append(child)
        for mk in child.markers:
            if mk.id and not mk.malformed:
                marked.setdefault(mk.id, child)

    # SPEC.md §5.5: a `subhash` marker that no direct child owns addresses
    # nothing, and "nobody's stay" is not a licence to recover the id from
    # weaker evidence. The marker is still in the document, so a tool honouring
    # the reader rule reports it unaddressed (`CHILD_UNADDRESSED`) while a
    # resolver walking the ladder would bind the same id to a *different* item:
    # the two halves of one implementation disagreeing about one document, which
    # is the §13 failure the rule exists to prevent. Reaches here from an item
    # nested inside another item, and from a segmenter that emitted no children
    # for the block at all. Both fail closed.
    # Narrower than "a `subhash` marker sits block-level somewhere": an id whose
    # marker is *also* owned by a direct child still has a marker doing its job,
    # and a stray nested copy of it is a §7 duplicate for the linter to report
    # (`DUPLICATE_ID`), not a reason to lose an anchor that never moved.
    unaddressed: set[str] = {
        mk.id
        for block in blocks
        for mk in block.markers
        if mk.has_subhash and mk.id and not mk.malformed
    } - set(marked)

    parents = _resolve_parents(anchors, blocks)
    out: dict[str, tuple[str, int | None]] = {}
    claimed: set[int] = set()

    for anchor in anchors:
        if anchor.id in unaddressed:
            out[anchor.id] = ("detached", None)

    # Tier 1 runs ahead of the parent gate, not behind it. A surviving child
    # marker is stored identity; where the parent lives is an inference about
    # its container. Letting a failed container inference discard the marker
    # would make the commonest LLM edit shape unrecoverable: the parent's
    # block-level marker sits on its own line and is easy to drop, while the
    # child markers ride inline inside the bullet text being rewritten.
    for anchor in anchors:
        if anchor.id in out:
            continue
        hit = marked.get(anchor.id)
        if hit is not None:
            out[anchor.id] = ("marker", hit.index)
            claimed.add(hit.index)

    def _parent_of(anchor: _ChildAnchor) -> Block | None:
        info = parents.get(anchor.parent_id) if anchor.parent_id else None
        return blocks[info[0]] if info is not None else None

    def _gated(anchor: _ChildAnchor) -> bool:
        """A child whose parent stay exists but could not be found has no
        sibling scope, so every structural tier below is unavailable to it."""
        return anchor.parent_id is not None and anchor.parent_id not in parents

    def _commit(tier: str, proposals: dict[str, int]) -> None:
        counts: dict[int, int] = {}
        for target in proposals.values():
            counts[target] = counts.get(target, 0) + 1
        for anchor_id, target in proposals.items():
            if counts[target] == 1:
                out[anchor_id] = (tier, target)
                claimed.add(target)

    ordinal_proposals: dict[str, int] = {}
    for anchor in anchors:
        if anchor.id in out or _gated(anchor):
            continue
        parent = _parent_of(anchor)
        if parent is None or body_hash(parent.content) != anchor.parent_hash:
            continue
        siblings = [child for child in parent.children if child.kind == anchor.kind]
        ordinal = anchor.ordinal - 1
        if not 0 <= ordinal < len(siblings):
            continue
        candidate = siblings[ordinal]
        if candidate.markers or candidate.index in claimed:
            continue
        ordinal_proposals[anchor.id] = candidate.index
    _commit("parent-hash", ordinal_proposals)

    sibling_proposals: dict[str, int] = {}
    for anchor in anchors:
        if anchor.id in out or _gated(anchor):
            continue
        parent = _parent_of(anchor)
        if parent is None or anchor.sibling_hash_count != 1:
            continue
        hits = [
            child
            for child in parent.children
            if child.kind == anchor.kind
            and body_hash(child.content) == anchor.hash
            and child.index not in claimed
        ]
        if len(hits) == 1:
            sibling_proposals[anchor.id] = hits[0].index
    _commit("hash", sibling_proposals)

    document_proposals: dict[str, int] = {}
    for anchor in anchors:
        if anchor.id in out or _gated(anchor) or anchor.document_hash_count != 1:
            continue
        hits = [
            child for child in hashes.get(anchor.hash, []) if child.index not in claimed
        ]
        if len(hits) == 1:
            document_proposals[anchor.id] = hits[0].index
    _commit("document-hash", document_proposals)

    # Quote scoring uses the tier-start snapshot too. Contested candidates go to
    # neither stay and fall through to DETACHED.
    quote_proposals: dict[str, int] = {}
    for anchor in anchors:
        if anchor.id in out or _gated(anchor):
            continue
        parent = _parent_of(anchor)
        if parent is None:
            continue
        candidates = [
            child
            for child in parent.children
            if child.kind == anchor.kind and child.index not in claimed
        ]
        idx, score, runner = _best_match(
            anchor.quote,
            anchor.prefix,
            anchor.suffix,
            [child.content for child in candidates],
        )
        if idx >= 0 and score >= 0.5 and score - runner >= 0.05:
            quote_proposals[anchor.id] = candidates[idx].index
    _commit("quote", quote_proposals)

    for anchor in anchors:
        out.setdefault(anchor.id, ("detached", None))
    return out


# --- within-collection items (SPEC.md §5.1): the opt-in COLLECTION_SHRANK check --
# A stay binds a whole block, so a table is one stay and a list is one stay. A row
# or bullet dropped from inside that block leaves the stay in place and only drifts
# the block hash (a non-blocking warning). When lint_diff is asked to check
# collections, it counts the table data-rows + list bullets a kept block carries
# before vs after and reports a blocking COLLECTION_SHRANK when that count falls, so
# a silently pruned row/bullet is caught the way a dropped block already is.

_ROW_RE = re.compile(r"^\s*\|.*\|\s*$")
_ROW_SEP_RE = re.compile(r"^\s*\|[\s:|-]+\|\s*$")  # the |---|:--| divider row
_BULLET_RE = re.compile(r"^\s*[-*+]\s+\S")


def _item_count(content: str) -> int:
    """Count the table data-rows + list bullets in a block's content. The table
    header (the line directly above a ``|---|`` divider) and the divider itself are
    excluded; what remains is the within-collection data an edit can prune. Markers
    are already stripped from ``Block.content``, so a per-item marker line never
    counts."""
    lines = content.split("\n")
    n = len(lines)
    count = 0
    for i, ln in enumerate(lines):
        if _ROW_RE.match(ln):
            if _ROW_SEP_RE.match(ln):
                continue
            if i + 1 < n and _ROW_SEP_RE.match(lines[i + 1]):
                continue  # header row sits directly above the divider
            if ln.strip().strip("|").strip():
                count += 1
        elif _BULLET_RE.match(ln):
            count += 1
    return count


def lint_diff(
    before_md: str,
    after_md: str,
    mode: str = "blank-line",
    check_collections: bool = False,
    child_blocks: bool = False,
) -> list[Finding]:
    """Regeneration diff: what an edit did to the ids. Catches the AI-rewrite
    failure mode (dropped markers) plus duplication and exact-content relocation.

    With ``check_collections=True`` it additionally reports a blocking
    COLLECTION_SHRANK when a kept stay's block lost table rows or list bullets
    (SPEC.md §5.1: a stay binds the whole table/list, so a pruned row/bullet is
    otherwise only a non-blocking hash drift). Off by default, so existing callers
    and the conformance corpus are unaffected."""
    before_blocks = parse_document(before_md, mode=mode, child_blocks=child_blocks)
    after_blocks = parse_document(after_md, mode=mode, child_blocks=child_blocks)
    before = {
        mid: blks[0] for mid, blks in _id_index(before_blocks).items() if len(blks) == 1
    }
    after = _id_index(after_blocks)
    findings: list[Finding] = []

    for mid in before:
        if mid not in after:
            findings.append(
                Finding(
                    "error",
                    "DROPPED_ID",
                    f"id {mid} was in the baseline but is gone after the edit (silent loss)",
                    id=mid,
                )
            )

    for mid, blks in after.items():
        if len(blks) > 1:
            findings.append(
                Finding(
                    "error",
                    "DUPLICATED_ID",
                    f"id {mid} appears {len(blks)} times after the edit "
                    f"(copy without re-mint, or a regeneration collision)",
                    id=mid,
                )
            )

    for mid in after:
        if mid not in before:
            findings.append(
                Finding(
                    "info", "NEW_ID", f"id {mid} is new (not in the baseline)", id=mid
                )
            )

    # content-keyed before index, for exact-swap relocation detection
    before_by_content = {}
    for mid, b in before.items():
        if b.content:
            before_by_content.setdefault(body_hash(b.content), mid)

    for mid, blks in after.items():
        if mid not in before or len(blks) != 1:
            continue
        a, b0 = blks[0], before[mid]
        if not a.content or not b0.content:
            continue
        if body_hash(a.content) == body_hash(b0.content):
            continue  # unchanged
        moved_from = before_by_content.get(body_hash(a.content))
        if moved_from and moved_from != mid:
            findings.append(
                Finding(
                    "error",
                    "RELOCATED_ID",
                    f"id {mid} now sits on content that previously carried id "
                    f"{moved_from} (markers look swapped or relocated)",
                    id=mid,
                )
            )
        else:
            findings.append(
                Finding(
                    "warn",
                    "HASH_DRIFT",
                    f"id {mid}: content changed between versions (edited in place)",
                    id=mid,
                )
            )

    if check_collections:
        for mid, blks in after.items():
            if mid not in before or len(blks) != 1:
                continue
            n0 = _item_count(before[mid].content)
            n1 = _item_count(blks[0].content)
            if n0 > 0 and n1 < n0:
                findings.append(
                    Finding(
                        "error",
                        "COLLECTION_SHRANK",
                        f"id {mid}: collection shrank from {n0} to {n1} items "
                        f"(a table row or list bullet was dropped from inside the block)",
                        id=mid,
                    )
                )
    if child_blocks:
        before_children = _child_id_index(before_blocks)
        after_children = _child_id_index(after_blocks)
        resolved = _resolve_children(
            _build_child_anchors(before_md, mode), after_md, mode
        )
        for mid, children in before_children.items():
            if len(children) != 1:
                continue
            if resolved.get(mid, ("detached", None))[0] == "detached":
                findings.append(
                    Finding(
                        "error",
                        "CHILD_DROPPED",
                        f"child id {mid} could not be recovered after the edit "
                        f"(the item was dropped or its remaining evidence is ambiguous)",
                        id=mid,
                    )
                )
        for mid, children in after_children.items():
            if len(children) > 1:
                findings.append(
                    Finding(
                        "error",
                        "DUPLICATED_ID",
                        f"child id {mid} appears {len(children)} times after the edit",
                        id=mid,
                    )
                )
            elif mid not in before_children:
                findings.append(
                    Finding(
                        "info",
                        "NEW_ID",
                        f"child id {mid} is new (not in the baseline)",
                        id=mid,
                    )
                )
    return findings


# --- reporting ------------------------------------------------------------


def sort_findings(findings: list[Finding]) -> list[Finding]:
    return sorted(findings, key=lambda f: (LEVELS.get(f.level, 9), f.line or 0, f.code))


def has_errors(findings: list[Finding]) -> bool:
    return any(f.level == "error" for f in findings)


def render_text(label: str, findings: list[Finding], show_drift: bool = False) -> str:
    """Human render. HASH_DRIFT is the dominant, non-actionable line in normal use
    (it never blocks; it only ever says "you edited things"), so it is hidden by
    default and collapsed to one discoverable line. `show_drift=True` lists it.
    The structured channel (`--json`, the return tuples) is unaffected, drift is
    always carried there. The error/warn/info summary counts the real totals
    either way, so a hidden drift is still counted as a warn that happened."""
    if not findings:
        return f"{label}: clean (no findings)"
    out = [f"{label}:"]
    shown = findings if show_drift else [f for f in findings if f.code != "HASH_DRIFT"]
    n_drift_hidden = len(findings) - len(shown)
    for f in sort_findings(shown):
        where = f"L{f.line}" if f.line else "-"
        out.append(f"  [{f.level:5}] {f.code:16} {where:>5}  {f.message}")
    if n_drift_hidden:
        noun = "finding" if n_drift_hidden == 1 else "findings"
        out.append(
            f"  -> {n_drift_hidden} hash-drift {noun} hidden (--show-drift to list)"
        )
    n_err = sum(1 for f in findings if f.level == "error")
    n_warn = sum(1 for f in findings if f.level == "warn")
    n_info = sum(1 for f in findings if f.level == "info")
    out.append(f"  -> {n_err} error, {n_warn} warn, {n_info} info")
    return "\n".join(out)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="markstay reference linter")
    ap.add_argument("files", nargs="+", help="Markdown file(s) to lint")
    ap.add_argument(
        "--before",
        metavar="OLD.md",
        help="baseline version; runs a regeneration diff against the "
        "single FILE given (dropped/duplicated/relocated ids)",
    )
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument(
        "--show-drift",
        action="store_true",
        dest="show_drift",
        help="list HASH_DRIFT findings in the text output (hidden by "
        "default; --json always carries them)",
    )
    ap.add_argument(
        "--check-collections",
        action="store_true",
        dest="check_collections",
        help="with --before, also block when a kept stay's table or list "
        "lost rows/bullets (COLLECTION_SHRANK); off by default",
    )
    ap.add_argument(
        "--child-blocks",
        action="store_true",
        dest="child_blocks",
        help="enable experimental direct list-item identity; the "
        "dependency-free mode fails closed outside flat tight "
        "single-paragraph lists",
    )
    ap.add_argument(
        "--commonmark",
        action="store_true",
        help="segment blocks over the CommonMark tree (SPEC.md §5.2, "
        "v1.1): loose lists and blank-line fences attach as one "
        "block. Needs markdown-it-py; the default is the "
        "dependency-free blank-line model",
    )
    args = ap.parse_args(argv)
    mode = "commonmark" if args.commonmark else "blank-line"

    if args.commonmark:
        # The one optional dependency. A missing parser is a setup answer, not a
        # stack trace out of the segmenter. The hint names the parser rather than
        # the packaged extra (`pip install 'markstay[commonmark]'`, which is what
        # the CLI in impl/py prints), because this file runs as a standalone
        # script whose user need not have the package installed at all.
        # find_spec rather than an import: it answers "is it installed" without
        # executing the module, so a parser that is present but broken still
        # raises its own error instead of being reported as absent.
        import importlib.util

        if importlib.util.find_spec("markdown_it") is None:
            print(
                "error: --commonmark needs the CommonMark parser.\n"
                "       install it with:  pip install markdown-it-py",
                file=sys.stderr,
            )
            return 2

    results = []  # (label, findings)
    if args.before:
        if len(args.files) != 1:
            ap.error("--before takes exactly one NEW file")
        before_md = Path(args.before).read_text()
        after_md = Path(args.files[0]).read_text()
        results.append(
            (
                f"{args.before} -> {args.files[0]}",
                lint_diff(
                    before_md,
                    after_md,
                    mode=mode,
                    check_collections=args.check_collections,
                    child_blocks=args.child_blocks,
                ),
            )
        )
    else:
        for f in args.files:
            _, findings = lint_document(
                Path(f).read_text(), mode=mode, child_blocks=args.child_blocks
            )
            results.append((f, findings))

    if args.json:
        payload = {
            label: [x.to_dict() for x in sort_findings(fs)] for label, fs in results
        }
        print(json.dumps(payload, indent=2))
    else:
        print(
            "\n".join(
                render_text(label, fs, show_drift=args.show_drift)
                for label, fs in results
            )
        )

    return 1 if any(has_errors(fs) for _, fs in results) else 0


if __name__ == "__main__":
    sys.exit(main())
