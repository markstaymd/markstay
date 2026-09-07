"""Per-axis survival oracles for the render matrix (the core of decision 2).

A "renderer" is two different pipelines with two different correct outcomes, so
there is no single shared comparator. This module holds three classifiers:

- ``roundtrip_verdict``  md -> md: reuse the reference linter's ``lint_diff`` error
  set (DROPPED / DUPLICATED / RELOCATED) AND a marker-cleanliness check. A formatter
  that reflows a body drifts the §8 hash, which is *expected and not a failure*. The
  real failures are a marker dropped, relocated to the wrong block, or rewritten into
  a form that no longer reads as a clean marker (pandoc's `<!-- ... -->`{=html} code
  span). HASH_DRIFT never fails a cell. A marker that entered inside a **table row**
  gets one extra test the block-level oracle cannot make (ROW_ESCAPED). In the
  blank-surrounded fixture a marker hoisted out of its row, or pushed onto a
  continuation line by a writer that re-tables, can remain in the same selected §5
  block and pass DROPPED/RELOCATED while the row identity it carried is gone.
- ``render_verdict``     md -> HTML: the output is HTML, so a {block -> stay} reparse
  is the wrong oracle. Measure two facts: is the marker visible in the rendered text
  (bad), and is the comment retained in the HTML source (informational). "Invisible"
  is the good default for a comment.
- ``sanitizer_verdict``  HTML -> HTML over rehype-stay's id= emit: does the `id`
  survive a sanitizer verbatim, survive renamed (GitHub's `user-content-` clobber,
  which breaks the `#id` deep link), or get stripped.

Block parsing and hashing are reused from the reference linter (``markstay_lint``).
The row-association check adds the §5.6 candidate scan below and pins its marker
opacity, escape parity, candidate refusal, and cell boundaries in ``test_render.py``.
"""

from __future__ import annotations

import re
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from html.parser import HTMLParser

import markstay_lint as L
from markdown_it import MarkdownIt

# Decision 4: pin ONE segmenter for the whole matrix so a "relocated" verdict
# reflects the tool under test, not a blank-line/CommonMark segmenter mismatch.
PARSE_MODE = "blank-line"

_COMMONMARK = MarkdownIt("commonmark")


# --- the table-row carrier (SPEC.md §5.6) ----------------------------------
# A GFM row is one line. The canonical writer position is inside the last cell,
# before the closing pipe, while a reader accepts a marker anywhere on an accepted
# body-row source line. In the standalone fixture, the block-level oracle cannot see
# a placement break when a marker leaves its row but remains in the same selected §5
# block. The helpers below measure the row instead: a marker is
# row-carried if it entered on a table row line, and it survived if it comes out on a
# accepted §5.6 body row with the same exact cell signature. A non-pipe table style
# is no longer a §5.6 child-row carrier, even if its visible text resembles the row.
#
# Two known limits, both narrower than the check itself. A GFM row written without its
# outer pipes (`a | b`) is not tracked at all, because a prose line containing a `|`
# would otherwise be scored as a row; read that as "no row test ran", not as a pass.
# Identical rows inside one container remain indistinguishable. The paired fixture's
# identical rows sit in different containers whose bare table markers make a
# cross-container swap observable. Without a bare selected-container marker the
# oracle fails closed: table shape and position cannot prove container identity.

_DELIM_CELL_RE = re.compile(r"^:?-+:?$")
_ID_END = r'''(?=\s|$|-->|--&gt;|\*/|["'])'''
_MARKER_ID_RE = re.compile(r"[A-Za-z0-9_-]+")


@dataclass
class _Marker:
    """Strict §4 marker facts needed by the render-survival oracle.

    ``subhash`` retains the parsed digest, while ``attribute_keys`` retains exact
    key presence even when that key's value is quoted or is not a valid digest.
    §16 and §5.6 route on the latter fact.
    """

    id: str | None
    hash: str | None
    raw: str
    syntax: str
    line: int
    malformed: bool = False
    subhash: str | None = None
    attribute_keys: frozenset[str] = field(default_factory=frozenset)
_MARKER_KEY_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]*")
_MARKER_HASH_RE = re.compile(r"sha256:([0-9A-Fa-f]+)")


def _lf_lines(text: str) -> list[str]:
    """§5.6 lines: normalize CRLF/CR, then split only at LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def _normalize_lf_with_raw_boundaries(text: str) -> tuple[str, list[int]]:
    """Normalize line endings and map every normalized boundary to raw source."""
    normalized = []
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


def _same_line_offset(source: str, target: str, pos: int) -> int:
    """Map a boundary through frontmatter blanking, which preserves line count."""
    line = source.count("\n", 0, pos)
    line_start = source.rfind("\n", 0, pos) + 1
    column = pos - line_start
    target_start = 0
    for _ in range(line):
        target_start = target.index("\n", target_start) + 1
    return target_start + column


def _parse_marker_body(
    body: str, syntax: str,
) -> tuple[str, list[tuple[str, str, bool]]] | None:
    """Parse one complete §4 marker body, or reject the whole body.

    The host comment owns its closing delimiter, even inside marker quotes. This pass
    then requires a key, an adjacent ``=``, and a complete bare or quoted value;
    quoted values admit normalized LF plus §4's two escapes. A comment that merely
    starts with ``stay:`` is not a marker token and cannot vouch for a row.
    """
    if not body.startswith("stay:"):
        return None
    if syntax == "html" and ("-->" in body or "--!>" in body):
        return None
    if syntax == "mdx" and "*/" in body:
        return None
    pos = len("stay:")
    id_match = _MARKER_ID_RE.match(body, pos)
    if id_match is None:
        return None
    marker_id = id_match.group(0)
    pos = id_match.end()
    if pos < len(body) and body[pos] not in " \t":
        return None

    attributes = []
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
            value = []
            while pos < len(body) and body[pos] != '"':
                char = body[pos]
                if char == "\\":
                    if pos + 1 == len(body) or body[pos + 1] not in '\\"':
                        return None
                    value.extend((char, body[pos + 1]))
                    pos += 2
                    continue
                codepoint = ord(char)
                # §3.3 explicitly assigns ownership when a marker span crosses a
                # fence boundary. Recognition has already normalized CRLF/CR to LF;
                # §5.6 refuses every row line the span touches before tokenization.
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


def _incomplete_marker_prefix_id(body: str) -> str | None:
    """Return the id when ``body`` is a valid but incomplete HTML marker prefix.

    A browser can close an HTML comment at ``--!>`` while a quoted marker value is
    still open. The bytes that follow are not a leak unless the tokenizer actually
    emits them as visible data, but a complete marker body followed by ordinary prose
    must not arm that check at all. This small prefix parser distinguishes those two
    states without treating an arbitrary malformed ``stay:`` comment as evidence.
    """
    body = body.lstrip(" \t")
    if _parse_marker_body(body, "html") is not None or not body.startswith("stay:"):
        return None

    pos = len("stay:")
    id_match = _MARKER_ID_RE.match(body, pos)
    if id_match is None:
        return None
    marker_id = id_match.group(0)
    pos = id_match.end()
    if pos < len(body) and body[pos] not in " \t":
        return None

    while pos < len(body):
        separator_start = pos
        while pos < len(body) and body[pos] in " \t":
            pos += 1
        if pos == len(body):
            return None
        if pos == separator_start:
            return None

        key_match = _MARKER_KEY_RE.match(body, pos)
        if key_match is None:
            return None
        pos = key_match.end()
        if pos == len(body):
            return marker_id
        if body[pos] != "=":
            return None
        pos += 1
        if pos == len(body):
            return marker_id

        if body[pos] == '"':
            pos += 1
            while pos < len(body):
                char = body[pos]
                if char == '"':
                    pos += 1
                    break
                if char == "\\":
                    if pos + 1 == len(body):
                        return marker_id
                    if body[pos + 1] not in '\\"':
                        return None
                    pos += 2
                    continue
                codepoint = ord(char)
                if char != "\n" and not (0x20 <= codepoint <= 0x7E):
                    return None
                pos += 1
            else:
                return marker_id
        else:
            value_start = pos
            while pos < len(body) and body[pos] not in " \t":
                codepoint = ord(body[pos])
                if body[pos] == '"' or not (0x21 <= codepoint <= 0x7E):
                    return None
                pos += 1
            if pos == value_start:
                return None

    return None


def _scan_marker_records(text: str) -> list[tuple[int, int, _Marker]]:
    """Scan complete §4 markers, stopping at the host comment's first closer.

    The reference linter's current grammar regex is intentionally not reused here:
    this eval is the oracle for a new carrier and validates the complete body. Each
    opener is scanned independently so nested HTML/MDX marker spans still overlap and
    trigger §5.6's fail-closed rule.
    """
    found = []
    for opener in re.finditer(r"<!--|\{/\*", text):
        syntax = "html" if opener.group(0) == "<!--" else "mdx"
        pos = opener.end()
        while pos < len(text) and text[pos] in " \t":
            pos += 1
        if not text.startswith("stay:", pos):
            continue

        body_start = pos
        search_start = pos + len("stay:")
        if syntax == "html":
            html_closers = [
                (at, closer)
                for closer in ("-->", "--!>")
                if (at := text.find(closer, search_start)) >= 0
            ]
            if not html_closers:
                continue
            close_start, closer = min(html_closers, key=lambda item: item[0])
            # `--!>` terminates an HTML comment but cannot complete the §4 ABNF.
            if closer != "-->":
                continue
            end = close_start + len(closer)
        else:
            close_start = text.find("*/", search_start)
            if close_start < 0 or not text.startswith("}", close_start + 2):
                continue
            end = close_start + 3
        body = text[body_start:close_start]
        parsed = _parse_marker_body(body, syntax)
        if parsed is None:
            continue
        marker_id, attributes = parsed
        block_hash = None
        child_hash = None
        for key, value, quoted_value in attributes:
            hash_match = None if quoted_value else _MARKER_HASH_RE.fullmatch(value)
            if key == "hash" and hash_match is not None and block_hash is None:
                block_hash = hash_match.group(1).lower()
            if key == "subhash" and hash_match is not None and child_hash is None:
                child_hash = hash_match.group(1).lower()
        marker = _Marker(
            id=marker_id,
            hash=block_hash,
            subhash=child_hash,
            raw=text[opener.start():end],
            syntax=syntax,
            line=text.count("\n", 0, opener.start()) + 1,
            malformed=False,
            attribute_keys=frozenset(key for key, _, _ in attributes),
        )
        found.append((opener.start(), end, marker))
    return found


def _scan_markers(text: str) -> list[_Marker]:
    return [marker for _, _, marker in _scan_marker_records(text)]


def _has_exact_attribute(marker: L.Marker | _Marker, key: str) -> bool | None:
    """Return exact parsed key presence, or ``None`` when strict parsing fails.

    Blocks come from the shipped linter and therefore carry ``L.Marker`` records,
    whose digest fields cannot distinguish an absent key from an invalid-valued one.
    Reparse their preserved raw bytes through this eval's complete §4 scanner. An
    unknown result must fail closed rather than turn a child-looking marker into bare
    selected-container evidence.
    """
    if isinstance(marker, _Marker):
        return key in marker.attribute_keys
    records = _scan_marker_records(marker.raw)
    if len(records) != 1:
        return None
    start, end, strict = records[0]
    if start != 0 or end != len(marker.raw):
        return None
    return key in strict.attribute_keys


def _raw_marker_spans(
    text: str, excluded_open_lines: set[int] | None = None
) -> list[tuple[int, int]]:
    excluded = excluded_open_lines or set()
    return [
        (start, end)
        for start, end, marker in _scan_marker_records(text)
        if marker.line not in excluded
    ]


def _overlapping_marker_spans(text: str) -> bool:
    spans = _raw_marker_spans(text)
    return any(
        start < previous_end
        for (_, previous_end), (start, _) in zip(spans, spans[1:])
    )


def _marker_spans(text: str) -> list[tuple[int, int]]:
    spans = _raw_marker_spans(text)
    merged = []
    for start, end in spans:
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    return merged


def _refused_marker_lines(
    text: str, excluded_open_lines: set[int] | None = None
) -> set[int]:
    """Lines touched by a real multiline or overlapping document marker.

    §3.3 judges a marker by the line where it opens. A span opening on a fenced line
    is content even if it closes later outside the fence; a span opening outside is a
    marker in full even if some of its later bytes lie on fenced lines.
    """
    spans = []
    for start, end in _raw_marker_spans(text, excluded_open_lines):
        first_line = text.count("\n", 0, start) + 1
        last_line = text.count("\n", 0, max(start, end - 1)) + 1
        spans.append((start, end, first_line, last_line))

    refused = set()
    for index, (start, end, first_line, last_line) in enumerate(spans):
        if first_line != last_line:
            refused.update(range(first_line, last_line + 1))
        for other_start, other_end, other_first, other_last in spans[index + 1:]:
            if other_start >= end:
                break
            if other_end > start:
                refused.update(range(first_line, last_line + 1))
                refused.update(range(other_first, other_last + 1))
    return refused


def _strip_markers(text: str) -> str:
    spans = _marker_spans(text)
    return "".join(
        text[start:end]
        for start, end in zip(
            [0] + [span_end for _, span_end in spans],
            [span_start for span_start, _ in spans] + [len(text)],
        )
    )


def _row_cells(line: str) -> list[str] | None:
    """Return normalized cell evidence for a §5.6 row line, or ``None``.

    Marker spans are skipped as opaque non-pipe tokens during delimiter recognition,
    and a pipe is escaped only after an odd consecutive backslash run. Cell evidence
    is trimmed only with §5.6's named ASCII set; interior and Unicode whitespace stay
    exact. Empty cells stay in the signature so their positions cannot collide.
    """
    leading_spaces = len(line) - len(line.lstrip(" "))
    if leading_spaces > 3:
        return None
    working = line[leading_spaces:].rstrip(" \t\f\v")
    if not working:
        return None
    if _overlapping_marker_spans(working):
        return None
    spans = _marker_spans(working)

    delimiters = []
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

    if (len(delimiters) < 2 or delimiters[0] != 0
            or delimiters[-1] != len(working) - 1):
        return None

    cells = []
    for start, end in zip(delimiters, delimiters[1:]):
        cell = _strip_markers(working[start + 1:end])
        normalized = cell.strip(" \t\f\v")
        cells.append(normalized)
    return cells


def _container_evidence_by_marker(
    text: str,
) -> dict[str, dict]:
    """Map every marker to bare ids that independently identify its §5 block."""
    blocks = [
        block for block in L.parse_document(text, mode=PARSE_MODE)
        if block.index >= 0
    ]

    containers = {}
    for block in blocks:
        bare = frozenset(
            marker.id for marker in block.markers
            if marker.id and _has_exact_attribute(marker, "subhash") is False
        )
        for marker in block.markers:
            if marker.id:
                containers[marker.id] = {
                    "ids": bare,
                }
    return containers


def _marker_only_line(line: str) -> bool:
    """A nonblank line containing only complete marker spans and ASCII whitespace."""
    return (
        not _overlapping_marker_spans(line)
        and bool(_marker_spans(line))
        and _strip_markers(line).strip(" \t\f\v") == ""
    )


def _candidate_rows(text: str) -> list[tuple[int, list[str]]]:
    """Return (1-based line, cells) for body rows of accepted §5.6 candidates.

    This is the complete left-to-right scan, not a search for table-shaped lines.
    A failed header pair advances one line; a started candidate owns its full extent
    and yields no rows if any body line refuses it.
    """
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    scannable = L._blank_frontmatter(normalized)
    lines = scannable.split("\n")
    fenced = L.code_lines(scannable)
    marker_refused = _refused_marker_lines(scannable, fenced)
    candidates: list[tuple[int, list[tuple[int, list[str]]]]] = []
    i = 0
    while i + 1 < len(lines):
        header = (
            None
            if i + 1 in fenced or i + 1 in marker_refused
            else _row_cells(lines[i])
        )
        delimiter = (
            None
            if i + 2 in fenced or i + 2 in marker_refused
            else _row_cells(lines[i + 1])
        )
        delimiter_has_marker = bool(_marker_spans(lines[i + 1]))
        delimiter_has_forbidden_space = "\f" in lines[i + 1] or "\v" in lines[i + 1]
        if (
            header is None
            or delimiter is None
            or delimiter_has_marker
            or delimiter_has_forbidden_space
            or len(header) != len(delimiter)
            or not all(_DELIM_CELL_RE.fullmatch(cell) for cell in delimiter)
        ):
            i += 1
            continue

        candidate: list[tuple[int, list[str]]] = []
        refused = False
        j = i + 2
        while j < len(lines):
            line = lines[j]
            if j + 1 in fenced or j + 1 in marker_refused:
                refused = True
                j += 1
                continue
            if line.strip(" \t\f\v") == "" or _marker_only_line(line):
                break
            cells = _row_cells(line)
            if cells is None:
                refused = True
            else:
                candidate.append((j + 1, cells))
            j += 1
        if not refused:
            candidates.append((i, candidate))
        if j >= len(lines):
            break
        i = j + 1
    # §5.6 uses the selected §5 block as the recovery container. Under this eval's
    # pinned blank-line profile, multiple candidates in one maximal nonblank run
    # would share one container and duplicate their row ordinals. Fail closed for
    # every candidate in that run rather than inventing a table discriminator.
    def block_start(line_index: int) -> int:
        while (
            line_index > 0
            and lines[line_index - 1].strip(" \t\f\v") != ""
        ):
            line_index -= 1
        return line_index

    by_container = Counter(block_start(start) for start, _ in candidates)
    return [
        row
        for start, rows in candidates
        if by_container[block_start(start)] == 1
        for row in rows
    ]


def _row_carried(text: str) -> dict:
    """Map each row marker to exact cells and selected-container evidence."""
    carried = {}
    candidate_rows = _candidate_rows(text)
    containers = _container_evidence_by_marker(text)
    lines = _lf_lines(text)
    for line_number, cells in candidate_rows:
        line = lines[line_number - 1]
        for m in _scan_markers(line):
            if m.id and _has_exact_attribute(m, "subhash") is True:
                carried[m.id] = {
                    "cells": cells,
                    "container": containers.get(m.id),
                }
    return carried


# --- round-trip (md -> md) -------------------------------------------------

def _clean_marker_present(out: str, mid: str) -> bool:
    """A free-standing marker for ``mid`` survives in ``out``: a `<!-- stay:mid -->`
    or `{/* stay:mid */}` outside a CommonMark inline-code token. Pandoc's `markdown`
    writer rewrites a trailing marker into such a token, and padded code spans have
    the same meaning, so cleanliness uses the pinned CommonMark parser rather than a
    one-character lookbehind."""
    searchable = _document_text(out)
    code_marker_ids = {
        marker.id
        for token in _COMMONMARK.parse(searchable)
        for child in (token.children or [])
        if child.type == "code_inline"
        for marker in _scan_markers(child.content)
        if marker.id
    }
    if mid in code_marker_ids:
        return False
    esc = re.escape(mid)
    html_clean = re.search(r"(?<!`)<!--\s*stay:%s(?=\s|-->)" % esc, searchable)
    mdx_clean = re.search(r"(?<!`)\{/\*\s*stay:%s(?=\s|\*/\})" % esc, searchable)
    return bool(html_clean or mdx_clean)


def _document_markers(text: str) -> list[L.Marker]:
    """Markers recognized at document level, excluding frontmatter and fences."""
    _, _, records = _document_marker_records(text)
    return [marker for _, _, marker in records]


def _document_marker_records(
    text: str,
) -> tuple[str, set[int], list[tuple[int, int, L.Marker]]]:
    """Frontmatter-excluded source, fenced lines, and §3.3-owned markers.

    Recognition uses normalized LF, but each marker retains its exact original source
    bytes so §4's verbatim-preservation check can detect a line-ending rewrite.
    """
    normalized, raw_boundaries = _normalize_lf_with_raw_boundaries(text)
    scannable = L._blank_frontmatter(normalized)
    fenced = L.code_lines(scannable)
    records = []
    for start, end, marker in _scan_marker_records(scannable):
        if marker.line in fenced:
            continue
        normalized_start = _same_line_offset(scannable, normalized, start)
        normalized_end = _same_line_offset(scannable, normalized, end)
        marker.raw = text[
            raw_boundaries[normalized_start]:raw_boundaries[normalized_end]
        ]
        records.append((start, end, marker))
    return scannable, fenced, records


def _document_text(text: str) -> str:
    """Mask fenced content while retaining real markers that cross its boundary."""
    scannable, fenced, records = _document_marker_records(text)
    protected = [(start, end) for start, end, _ in records]
    out = []
    line_number = 1
    span_index = 0
    for pos, char in enumerate(scannable):
        while span_index < len(protected) and pos >= protected[span_index][1]:
            span_index += 1
        in_marker = (
            span_index < len(protected)
            and protected[span_index][0] <= pos < protected[span_index][1]
        )
        if char == "\n":
            out.append(char)
            line_number += 1
        elif line_number in fenced and not in_marker:
            out.append(" ")
        else:
            out.append(char)
    return "".join(out)


def _marker_raws(text: str) -> dict[str, Counter]:
    """Exact marker bytes by id, for §4's verbatim-preservation requirement."""
    raws = defaultdict(Counter)
    for marker in _document_markers(text):
        if marker.id:
            raws[marker.id][marker.raw] += 1
    return raws


def roundtrip_verdict(inp: str, res: dict) -> dict:
    if res["rc"] != 0:
        return {"verdict": "ERROR", "note": _first_line(res.get("err"))}
    out = res["out"]
    in_ids = [m.id for m in _document_markers(inp) if m.id]
    findings = L.lint_diff(inp, out, mode=PARSE_MODE)
    codes = {f.code for f in findings}
    out_ids = {m.id for m in _document_markers(out) if m.id}

    missing = [i for i in in_ids if i not in out_ids]
    # A marker that no longer parses but survives HTML-escaped (`&lt;!-- stay:id --&gt;`)
    # is mangled, not dropped: the bytes are still there, just broken. Distinguish it
    # from a marker removed outright.
    escaped = [i for i in missing if re.search(
        r"&lt;!--\s*stay:%s(?=\s|--&gt;)" % re.escape(i), _document_text(out)
    )]
    truly_dropped = [i for i in missing if i not in escaped]
    # Present-but-unclean (pandoc's `<!-- ... -->`{=html} code span) OR escaped.
    in_raws = _marker_raws(inp)
    out_raws = _marker_raws(out)
    changed = [i for i in in_ids if i in out_ids and in_raws[i] != out_raws[i]]
    mangled = (
        [i for i in in_ids if i in out_ids and not _clean_marker_present(out, i)]
        + escaped
        + changed
    )

    if truly_dropped:
        return {"verdict": "DROPPED", "note": "marker(s) lost: %s" % ", ".join(sorted(truly_dropped))}
    if "RELOCATED_ID" in codes:
        moved = sorted({f.id for f in findings if f.code == "RELOCATED_ID"})
        return {"verdict": "RELOCATED", "note": "marker(s) moved to the wrong block: %s" % ", ".join(moved)}
    if "DUPLICATED_ID" in codes:
        dup = sorted({f.id for f in findings if f.code == "DUPLICATED_ID"})
        return {"verdict": "DUPLICATED", "note": "marker(s) duplicated: %s" % ", ".join(dup)}
    # Row carriage: a `subhash` marker that entered on an accepted body row must come
    # out on an accepted body row with the same exact cell signature.
    carried = _row_carried(inp)
    out_carried = _row_carried(out)
    left_row = []
    wrong_container = []
    for mid, evidence in carried.items():
        same_row = (
            mid in out_carried
            and out_carried[mid]["cells"] == evidence["cells"]
        )
        expected_container = evidence["container"]
        actual_container = (
            out_carried[mid]["container"] if mid in out_carried else None
        )
        same_container = (
            actual_container is not None
            and expected_container is not None
            and bool(expected_container["ids"])
            and actual_container["ids"] == expected_container["ids"]
        )
        if not same_row:
            left_row.append(mid)
        if not same_container:
            wrong_container.append(mid)
    if left_row or wrong_container:
        notes = []
        if left_row:
            notes.append("marker(s) no longer on their accepted §5.6 body row: %s" % ", ".join(
                sorted(left_row)
            ))
        if wrong_container:
            notes.append("marker(s) no longer in their original selected container: %s"
                         % ", ".join(sorted(wrong_container)))
        if mangled:
            notes.append("marker(s) also rewritten or changed: %s" % ", ".join(
                sorted(set(mangled))
            ))
        return {"verdict": "ROW_ESCAPED", "note": "; ".join(notes)}

    if mangled:
        return {"verdict": "MANGLED",
                "note": "marker(s) rewritten (code span / escaped / attributes changed): %s"
                        % ", ".join(sorted(set(mangled)))}
    drift = "HASH_DRIFT" in codes
    note = "clean; §8 hash drifts on reflow (expected)" if drift else "clean, no drift"
    if carried:
        note += "; %d in-cell row marker(s) still on accepted rows" % len(carried)
    return {"verdict": "SURVIVES", "note": note}


# --- render-emit (md -> HTML) ---------------------------------------------

class _VisibleTextParser(HTMLParser):
    """Collect rendered text while preserving RCDATA and ignoring real comments."""

    _HIDDEN = frozenset({"script", "style", "template"})

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts = []
        self.hidden_depth = 0
        self.early_closed_marker_ids = set()
        self.pending_early_marker_id = None

    def parse_comment(self, i, report=True):
        """Arm a leak check when `--!>` interrupts a valid marker prefix."""
        pending = None
        match = re.search(r"--!?>", self.rawdata[i + 4:])
        if match is not None:
            start = i + 4 + match.start()
            body = self.rawdata[i + 4:start]
            if not self.hidden_depth and match.group(0) == "--!>":
                pending = _incomplete_marker_prefix_id(body)
        result = super().parse_comment(i, report=report)
        self.pending_early_marker_id = pending
        return result

    def _clear_pending(self):
        self.pending_early_marker_id = None

    def handle_starttag(self, tag, attrs):
        self._clear_pending()
        if tag.lower() in self._HIDDEN:
            self.hidden_depth += 1

    def handle_endtag(self, tag):
        self._clear_pending()
        if tag.lower() in self._HIDDEN and self.hidden_depth:
            self.hidden_depth -= 1

    def handle_data(self, data):
        pending = self.pending_early_marker_id
        self._clear_pending()
        if not self.hidden_depth:
            self.parts.append(data)
            if pending is not None and data:
                self.early_closed_marker_ids.add(pending)

    def handle_decl(self, decl):
        self._clear_pending()

    def handle_pi(self, data):
        self._clear_pending()

    def unknown_decl(self, data):
        self._clear_pending()


def _visible_result(html_out: str) -> tuple[str, set[str]]:
    """The text a reader sees, with HTML comments interpreted in context.

    Real comments disappear, while the same bytes inside an RCDATA element such as
    `textarea` are data and remain visible. Escaped marker syntax in ordinary text is
    decoded as well.
    """
    parser = _VisibleTextParser()
    parser.feed(html_out)
    parser.close()
    return "".join(parser.parts), parser.early_closed_marker_ids


def _visible_text(html_out: str) -> str:
    return _visible_result(html_out)[0]


def render_verdict(inp: str, res: dict) -> dict:
    if res["rc"] != 0:
        return {"verdict": "ERROR", "note": _first_line(res.get("err"))}
    out = res["out"]
    in_ids = [m.id for m in _document_markers(inp) if m.id]
    vis, early_closed = _visible_result(out)
    visible_marker_ids = {m.id for m in _scan_markers(vis) if m.id}
    visible_marker_ids.update(
        match.group(1)
        for match in re.finditer(
            r"(?:<!--|\{/\*)[ \t]*stay:([A-Za-z0-9_-]+)(?=\s|-->|--!>|\*/|$)",
            vis,
        )
    )
    leaked = [i for i in in_ids if i in visible_marker_ids or i in early_closed]
    retained = [i for i in in_ids if re.search(
        r"<!--\s*stay:%s(?=\s|-->)" % re.escape(i), out
    )]

    if leaked:
        return {"verdict": "LEAKED_VISIBLE",
                "note": "marker(s) rendered as visible text: %s" % ", ".join(sorted(leaked))}
    note = ("comment retained in HTML source (invisible)" if retained
            else "comment dropped from output (invisible)")
    return {"verdict": "INVISIBLE", "note": note}


def mdx_verdict(inp: str, res: dict) -> dict:
    """MDX compiles to a JS module, not HTML, so it needs its own classifier.

    An HTML-comment marker is INVALID MDX and the compile fails (rc != 0): that is
    the documented reason §3.2 exists, recorded as ERROR with the §3.2 remediation.
    A §3.2 `{/* stay:id */}` marker compiles; at block position MDX hoists it to a
    bare `/*stay:id*/` JS comment and leaves an empty `{}` expression in the JSX, so
    it renders to nothing (invisible). A marker that instead showed up inside a
    rendered string literal would be a visible leak."""
    if res["rc"] != 0:
        return {"verdict": "ERROR",
                "note": "HTML-comment marker is invalid MDX (use the §3.2 {/* */} form)"}
    out = res["out"]
    in_ids = [m.id for m in _document_markers(inp) if m.id]
    string_markers = {
        marker.id
        for string in re.finditer(r'"(?:\\.|[^"\\])*"', out)
        for marker in _scan_markers(string.group(0))
        if marker.id
    }
    rendered = [i for i in in_ids if i in string_markers]
    if rendered:
        return {"verdict": "LEAKED_VISIBLE",
                "note": "marker rendered as JSX text: %s" % ", ".join(sorted(rendered))}
    retained = [i for i in in_ids if re.search(
        r"/\*\s*stay:%s%s.*?\*/" % (re.escape(i), _ID_END), out
    )]
    note = ("compiles; marker hoisted to a JS comment, renders as an empty expression"
            if retained else "compiles; marker dropped, renders to nothing")
    return {"verdict": "INVISIBLE", "note": note}


# --- sanitizer (HTML -> HTML over rehype-stay's id= emit) ------------------

def sanitizer_verdict(emit_html: str, res: dict) -> dict:
    if res["rc"] != 0:
        return {"verdict": "ERROR", "note": _first_line(res.get("err"))}
    out = res["out"]
    emit_ids = re.findall(r'id="([^"]+)"', emit_html)
    if not emit_ids:
        return {"verdict": "ERROR", "note": "emit produced no id= to test"}
    survived, prefixed, stripped = [], [], []
    for eid in emit_ids:
        if re.search(r'id="%s"' % re.escape(eid), out):
            survived.append(eid)
        elif re.search(r'id="[^"]*%s"' % re.escape(eid), out):
            prefixed.append(eid)
        else:
            stripped.append(eid)
    if stripped:
        return {"verdict": "ID_STRIPPED",
                "note": "anchor id removed: %s" % ", ".join(stripped)}
    if prefixed:
        return {"verdict": "ID_PREFIXED",
                "note": "id kept but renamed (e.g. user-content-): #id deep link breaks"}
    return {"verdict": "ID_SURVIVES", "note": "id preserved verbatim"}


# --- helpers ---------------------------------------------------------------

def _first_line(s):
    if not s:
        return ""
    return s.strip().splitlines()[0] if s.strip() else ""


# Severity order per axis: the cell verdict is the WORST across a tool's fixtures.
SEVERITY = {
    # Order matches the order roundtrip_verdict tests them, so the worst-across-fixtures
    # cell verdict and a single fixture's verdict cannot disagree about which is worse.
    "roundtrip": ["DROPPED", "RELOCATED", "DUPLICATED", "ROW_ESCAPED", "MANGLED",
                  "ERROR", "SURVIVES"],
    "render": ["LEAKED_VISIBLE", "ERROR", "INVISIBLE"],
    "sanitize": ["ID_STRIPPED", "ID_PREFIXED", "ERROR", "ID_SURVIVES"],
}


def worst(axis: str, verdicts: list[str]) -> str:
    order = SEVERITY[axis]
    return min(verdicts, key=lambda v: order.index(v) if v in order else 99)
