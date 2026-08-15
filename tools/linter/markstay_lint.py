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
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path

# --- marker grammar -------------------------------------------------------

# A marker body always begins with the `stay:` namespace. We capture the body
# lazily up to the closing delimiter, then pull id/hash out of it. Capturing the
# whole body (rather than a fixed attribute order) tolerates reordered or extra
# attributes, which the spec's free-order attribute grammar allows (SPEC.md §4).
HTML_MARKER = re.compile(r"<!--\s*(?P<body>stay:.*?)\s*-->", re.DOTALL)
MDX_MARKER = re.compile(r"\{/\*\s*(?P<body>stay:.*?)\s*\*/\}", re.DOTALL)

# The id is positional: the first token right after the `stay:` namespace
# (`stay:8f24`). A first token that contains `=` (a bare k=v with no id) leaves
# the marker without an id, which is malformed.
ID_RE = re.compile(r"stay:\s*(?P<id>[A-Za-z0-9_-]+)(?=\s|$)")
HASH_RE = re.compile(r"\bhash\s*=\s*sha256:(?P<hash>[0-9a-fA-F]+)")
SUBHASH_RE = re.compile(r"\bsubhash\s*=\s*sha256:(?P<hash>[0-9a-fA-F]+)")

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


def find_markers(text: str, line_offset: int = 0) -> list[Marker]:
    """All markstay markers in `text`, ordered by position. `line_offset` is the
    0-based line index where `text` begins in the full document."""
    raw = []
    for pat, syntax in ((HTML_MARKER, "html"), (MDX_MARKER, "mdx")):
        for m in pat.finditer(text):
            raw.append((m.start(), m.group(0), syntax, m.group("body")))
    raw.sort(key=lambda t: t[0])
    out = []
    for start, full, syntax, body in raw:
        line = line_offset + text[:start].count("\n") + 1
        # `.match` anchors the id to the FIRST token after `stay:` (SPEC.md §4:
        # the id is positional). `.search` would rescue a later `stay:ID` in a
        # body whose first token is a bare `k=v` (e.g. `stay:note=hello stay:ok`),
        # wrongly reading it as well-formed; the first token containing `=` is
        # malformed and the marker has no id.
        idm = ID_RE.match(body)
        hm = HASH_RE.search(body)
        shm = SUBHASH_RE.search(body)
        out.append(
            Marker(
                # Hex is stored canonically lowercase: SPEC.md §8 makes hash
                # comparison case-insensitive, so `hash=sha256:ABCD` must not read
                # as drift against a lowercase computed digest.
                id=idm.group("id") if idm else None,
                hash=hm.group("hash").lower() if hm else None,  # see ID_RE.match note
                subhash=shm.group("hash").lower() if shm else None,
                raw=full,
                syntax=syntax,
                line=line,
                malformed=idm is None,
            )
        )
    return out


def _strip_markers(text: str) -> str:
    return MDX_MARKER.sub("", HTML_MARKER.sub("", text))


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


def child_body(text: str) -> str:
    clean = _strip_markers(text)
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


def _restricted_child_spans(chunk: str, start: int) -> list[_ChildSpan]:
    """Fail-closed profile: flat, tight, single-paragraph list items."""
    lines = chunk.split("\n")
    items: list[tuple[int, int, str]] = []
    item_start: int | None = None
    item_lines: list[str] = []
    content_indent = 0
    saw_parent_marker = False
    signature: tuple[str, str] | None = None
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
            current = (
                ("ordered", marker[-1]) if marker[0].isdigit() else ("bullet", marker)
            )
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
    if mode == "commonmark":
        chunks = _segment_commonmark(text)
    elif mode == "blank-line":
        chunks = _segment_blank_line(text)
    else:
        raise ValueError(
            f"unknown parse mode: {mode!r} (use 'blank-line' or 'commonmark')"
        )

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

    blocks: list[Block] = []
    cidx = 0
    child_idx = 0
    for start, chunk in chunks:
        markers = find_markers(chunk, line_offset=start - 1)
        content = _strip_markers(chunk).strip(
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
                for ordinal, span in enumerate(child_spans.get(start, []), 1):
                    owned = [
                        mk
                        for mk in markers
                        if mk.subhash is not None
                        and span.start_line <= mk.line <= span.end_line
                        and mk.line not in span.excluded_lines
                    ]
                    child_marker_ids.update(id(mk) for mk in owned)
                    children.append(
                        ChildBlock(
                            content=child_body(span.text),
                            markers=owned,
                            line=span.start_line,
                            index=child_idx,
                            ordinal=ordinal,
                            parent_index=cidx,
                            marker_line=span.marker_line,
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


# --- checks ---------------------------------------------------------------


def lint_document(
    md: str, mode: str = "blank-line", child_blocks: bool = False
) -> tuple[list[Block], list[Finding]]:
    """Well-formedness and intra-document invariants for a single file."""
    blocks = parse_document(md, mode=mode, child_blocks=child_blocks)
    findings: list[Finding] = []
    seen: dict[str, int] = {}

    def check_marker(mk: Marker, body: str, orphan: bool = False, child: bool = False):
        if mk.malformed:
            findings.append(
                Finding(
                    "error",
                    "MALFORMED_MARKER",
                    f"marker has no parseable id: {mk.raw!r}",
                    line=mk.line,
                )
            )
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
        stored = mk.subhash if child else mk.hash
        if stored and body:
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
            has_parent = any(
                mk.id and not mk.malformed and mk.subhash is None for mk in b.markers
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
            if mk.id and not mk.malformed:
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
                _match_normalize(prefix), _match_normalize(prev[-48:])
            )
        if suffix:
            nxt = candidates[i + 1] if i + 1 < len(candidates) else ""
            score += 0.05 * _match_ratio(
                _match_normalize(suffix), _match_normalize(nxt[:48])
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
                if mk.id and not mk.malformed and mk.subhash is None
            ),
            None,
        )
        for ci, child in enumerate(block.children):
            digest = body_hash(child.content)
            for mk in child.markers:
                if mk.id and not mk.malformed:
                    anchors.append(
                        _ChildAnchor(
                            id=mk.id,
                            hash=digest,
                            quote=child.content,
                            prefix=block.children[ci - 1].content if ci > 0 else "",
                            suffix=(
                                block.children[ci + 1].content
                                if ci + 1 < len(block.children)
                                else ""
                            ),
                            ordinal=child.ordinal,
                            parent_id=parent.id if parent else None,
                            parent_hash=body_hash(block.content),
                            parent_quote=block.content,
                            parent_prefix=blocks[bi - 1].content if bi > 0 else "",
                            parent_suffix=(
                                blocks[bi + 1].content if bi + 1 < len(blocks) else ""
                            ),
                            sibling_hash_count=sum(
                                1
                                for candidate in block.children
                                if body_hash(candidate.content) == digest
                            ),
                            document_hash_count=doc_counts[digest],
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
            if any(mk.id == pid and not mk.malformed for mk in block.markers):
                out[pid] = (idx, "marker")
                claimed.add(idx)
                break

    for pid, anchor in reps.items():
        if pid in out:
            continue
        hits = [
            idx
            for idx, block in enumerate(blocks)
            if body_hash(block.content) == anchor.parent_hash and idx not in claimed
        ]
        if len(hits) == 1:
            out[pid] = (hits[0], "hash")
            claimed.add(hits[0])

    # Quote claims run last and in descending score order, so the best-supported
    # parent picks from the unclaimed blocks first rather than whichever anchor
    # happened to be enumerated first.
    pending = []
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
            pending.append((score, pid, candidates[idx]))
    for _, pid, target in sorted(pending, key=lambda row: -row[0]):
        if target in claimed:
            continue
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

    parents = _resolve_parents(anchors, blocks)
    out: dict[str, tuple[str, int | None]] = {}
    claimed: set[int] = set()

    # Tier 1 runs ahead of the parent gate, not behind it. A surviving child
    # marker is stored identity; where the parent lives is an inference about
    # its container. Letting a failed container inference discard the marker
    # would make the commonest LLM edit shape unrecoverable: the parent's
    # block-level marker sits on its own line and is easy to drop, while the
    # child markers ride inline inside the bullet text being rewritten.
    for anchor in anchors:
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

    for anchor in anchors:
        if anchor.id in out or _gated(anchor):
            continue
        parent = _parent_of(anchor)
        if parent is not None:
            ordinal = anchor.ordinal - 1
            if (
                body_hash(parent.content) == anchor.parent_hash
                and 0 <= ordinal < len(parent.children)
                and not parent.children[ordinal].markers
                and parent.children[ordinal].index not in claimed
            ):
                out[anchor.id] = ("parent-hash", parent.children[ordinal].index)
                claimed.add(parent.children[ordinal].index)
                continue
            sibling_hits = [
                child
                for child in parent.children
                if body_hash(child.content) == anchor.hash
                and child.index not in claimed
            ]
            if len(sibling_hits) == 1 and anchor.sibling_hash_count == 1:
                out[anchor.id] = ("hash", sibling_hits[0].index)
                claimed.add(sibling_hits[0].index)
                continue
        doc_hits = [
            child for child in hashes.get(anchor.hash, []) if child.index not in claimed
        ]
        if len(doc_hits) == 1 and anchor.document_hash_count == 1:
            out[anchor.id] = ("document-hash", doc_hits[0].index)
            claimed.add(doc_hits[0].index)

    # Quote scoring runs only over what no stronger tier took.
    for anchor in anchors:
        if anchor.id in out or _gated(anchor):
            continue
        parent = _parent_of(anchor)
        if parent is None or anchor.sibling_hash_count != 1:
            continue
        candidates = [
            child for child in parent.children if child.index not in claimed
        ]
        idx, score, runner = _best_match(
            anchor.quote,
            anchor.prefix,
            anchor.suffix,
            [child.content for child in candidates],
        )
        if idx >= 0 and score >= 0.5 and score - runner >= 0.05:
            out[anchor.id] = ("quote", candidates[idx].index)
            claimed.add(candidates[idx].index)

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
