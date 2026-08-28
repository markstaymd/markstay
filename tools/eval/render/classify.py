"""Per-axis survival oracles for the render matrix (the core of decision 2).

A "renderer" is two different pipelines with two different correct outcomes, so
there is no single shared comparator. This module holds three classifiers:

- ``roundtrip_verdict``  md -> md: reuse the reference linter's ``lint_diff`` error
  set (DROPPED / DUPLICATED / RELOCATED) AND a marker-cleanliness check. A formatter
  that reflows a body drifts the §8 hash, which is *expected and not a failure*. The
  real failures are a marker dropped, relocated to the wrong block, or rewritten into
  a form that no longer reads as a clean marker (pandoc's `<!-- ... -->`{=html} code
  span). HASH_DRIFT never fails a cell. A marker that entered inside a **table row**
  gets one extra test the block-level oracle cannot make (ROW_ESCAPED): a table is a
  single block to every segmenter, so a marker hoisted out of its row, or pushed onto
  a continuation line by a writer that re-tables, still passes DROPPED/RELOCATED while
  the row identity it carried is gone.
- ``render_verdict``     md -> HTML: the output is HTML, so a {block -> stay} reparse
  is the wrong oracle. Measure two facts: is the marker visible in the rendered text
  (bad), and is the comment retained in the HTML source (informational). "Invisible"
  is the good default for a comment.
- ``sanitizer_verdict``  HTML -> HTML over rehype-stay's id= emit: does the `id`
  survive a sanitizer verbatim, survive renamed (GitHub's `user-content-` clobber,
  which breaks the `#id` deep link), or get stripped.

Parsing/hashing is reused from the reference linter (``markstay_lint``), never
re-derived, so the round-trip oracle is byte-identical to the shipped linter.
"""

from __future__ import annotations

import html
import re

import markstay_lint as L

# Decision 4: pin ONE segmenter for the whole matrix so a "relocated" verdict
# reflects the tool under test, not a blank-line/CommonMark segmenter mismatch.
PARSE_MODE = "blank-line"

_TAG_RE = re.compile(r"<[^>]+>")
_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


# --- the table-row carrier (SPEC.md §14) -----------------------------------
# A GFM row is one line, so the only position a row marker can take is inside the
# last cell, before the closing pipe. Nothing in the block-level oracle can see that
# placement break: the whole table is one block, so a marker that leaves its row for
# a neighbouring line is still "on the right block" and still parses. The helpers
# below measure the row instead: a marker is row-carried if it entered on a table
# row line, and it survived if it comes out on a line that still holds that row's
# other cell values. Association is measured, not pipe syntax, so a writer that emits
# a different table style (pandoc's simple tables) passes as long as the row stays
# one line.
#
# Two known limits, both narrower than the check itself. A GFM row written without its
# outer pipes (`a | b`) is not tracked at all, because a prose line containing a `|`
# would otherwise be scored as a row; read that as "no row test ran", not as a pass.
# And two rows with identical cell text are indistinguishable to this check, so a
# marker that swapped between them scores clean. The corpus uses the fully piped form
# with distinct rows.

_ROW_LINE_RE = re.compile(r"^\s*\|.*\|\s*$")
_DELIM_CELL_RE = re.compile(r"^:?-+:?$")


def _strip_markers(text: str) -> str:
    return L.MDX_MARKER.sub("", L.HTML_MARKER.sub("", text))


def _row_cells(line: str) -> list[str]:
    """The cell texts of a table row line, markers stripped, empties dropped."""
    inner = line.strip().strip("|")
    return [c for c in (" ".join(_strip_markers(cell).split())
                        for cell in re.split(r"(?<!\\)\|", inner)) if c]


def _row_carried(text: str) -> dict:
    """{id: [that row's other cell texts]} for every marker sitting in a table row."""
    carried = {}
    for line in text.splitlines():
        if not _ROW_LINE_RE.match(line):
            continue
        cells = _row_cells(line)
        if cells and all(_DELIM_CELL_RE.match(c) for c in cells):
            continue                                   # header delimiter row
        for m in L.find_markers(line):
            if m.id:
                carried[m.id] = cells
    return carried


def _marker_lines(text: str, mid: str) -> list[str]:
    """Every output line still mentioning ``mid``, mangled forms included. All of them,
    not the first: prose that names a marker id would otherwise be answered with, and
    fail, a line the marker never moved to."""
    pat = re.compile(r"stay:%s\b" % re.escape(mid))
    return [line for line in text.splitlines() if pat.search(line)]


def _still_on_its_row(line: str, cells: list[str]) -> bool:
    """Does ``line`` still carry the row this marker entered on?

    The marker is stripped out of the line first, and so are the backticks a writer
    may have wrapped it in. That is not cosmetic: a one-character cell value like `5`
    occurs inside every marker's own `sha256:` prefix, so an unstripped line would
    vouch for its own row. With no cell values to key on (a row whose other cells are
    all empty) there is nothing to match, and the weaker test is that the marker is at
    least still on a table row line."""
    text = _strip_markers(line.replace("`", ""))
    if not cells:
        return bool(_ROW_LINE_RE.match(line))
    return all(c in text for c in cells)


# --- round-trip (md -> md) -------------------------------------------------

def _clean_marker_present(out: str, mid: str) -> bool:
    """A free-standing marker for ``mid`` survives in ``out``: a `<!-- stay:mid -->`
    or `{/* stay:mid */}` whose opener is NOT directly preceded by a backtick (which
    is how pandoc's `markdown` writer rewrites a trailing marker into an inline code
    span: `` `<!-- stay:mid -->`{=html} ``). The negative lookbehind is the whole
    test: a backtick immediately before `<!--` means the marker is now code, not a
    comment."""
    esc = re.escape(mid)
    html_clean = re.search(r"(?<!`)<!--\s*stay:%s\b" % esc, out)
    mdx_clean = re.search(r"(?<!`)\{/\*\s*stay:%s\b" % esc, out)
    return bool(html_clean or mdx_clean)


def roundtrip_verdict(inp: str, res: dict) -> dict:
    if res["rc"] != 0:
        return {"verdict": "ERROR", "note": _first_line(res.get("err"))}
    out = res["out"]
    in_ids = [m.id for m in L.find_markers(inp) if m.id]
    findings = L.lint_diff(inp, out, mode=PARSE_MODE)
    codes = {f.code for f in findings}
    out_ids = {m.id for m in L.find_markers(out) if m.id}

    missing = [i for i in in_ids if i not in out_ids]
    # A marker that no longer parses but survives HTML-escaped (`&lt;!-- stay:id --&gt;`)
    # is mangled, not dropped: the bytes are still there, just broken. Distinguish it
    # from a marker removed outright.
    escaped = [i for i in missing if re.search(r"&lt;!--\s*stay:%s\b" % re.escape(i), out)]
    truly_dropped = [i for i in missing if i not in escaped]
    # Present-but-unclean (pandoc's `<!-- ... -->`{=html} code span) OR escaped.
    mangled = [i for i in in_ids if i in out_ids and not _clean_marker_present(out, i)] + escaped

    if truly_dropped:
        return {"verdict": "DROPPED", "note": "marker(s) lost: %s" % ", ".join(sorted(truly_dropped))}
    if "RELOCATED_ID" in codes:
        moved = sorted({f.id for f in findings if f.code == "RELOCATED_ID"})
        return {"verdict": "RELOCATED", "note": "marker(s) moved to the wrong block: %s" % ", ".join(moved)}
    if "DUPLICATED_ID" in codes:
        dup = sorted({f.id for f in findings if f.code == "DUPLICATED_ID"})
        return {"verdict": "DUPLICATED", "note": "marker(s) duplicated: %s" % ", ".join(dup)}
    # Row carriage: a marker that entered inside a table row must come out on a line
    # that still carries that row's other cells (see the helpers above).
    carried = _row_carried(inp)
    left_row = []
    for mid, cells in carried.items():
        if not any(_still_on_its_row(line, cells) for line in _marker_lines(out, mid)):
            left_row.append(mid)
    if left_row:
        return {"verdict": "ROW_ESCAPED",
                "note": "marker(s) no longer on their table row's line: %s"
                        % ", ".join(sorted(left_row))}

    if mangled:
        return {"verdict": "MANGLED",
                "note": "marker(s) rewritten to a non-comment form (code span / escaped): %s"
                        % ", ".join(sorted(set(mangled)))}
    drift = "HASH_DRIFT" in codes
    note = "clean; §8 hash drifts on reflow (expected)" if drift else "clean, no drift"
    if carried:
        note += "; %d in-cell row marker(s) still on their row" % len(carried)
    return {"verdict": "SURVIVES", "note": note}


# --- render-emit (md -> HTML) ---------------------------------------------

def _visible_text(html_out: str) -> str:
    """The text a reader actually sees: strip HTML comments, then tags, then
    unescape entities. A marker that was escaped to `&lt;!-- stay --&gt;` and placed
    in a `<p>` surfaces here as literal `<!-- stay -->` text (a visible leak); a
    marker kept as a real `<!-- ... -->` comment is removed first (invisible)."""
    return html.unescape(_TAG_RE.sub("", _COMMENT_RE.sub("", html_out)))


def render_verdict(inp: str, res: dict) -> dict:
    if res["rc"] != 0:
        return {"verdict": "ERROR", "note": _first_line(res.get("err"))}
    out = res["out"]
    in_ids = [m.id for m in L.find_markers(inp) if m.id]
    vis = _visible_text(out)
    leaked = [i for i in in_ids if ("stay:%s" % i) in vis]
    retained = [i for i in in_ids if re.search(r"<!--\s*stay:%s\b" % re.escape(i), out)]

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
    in_ids = [m.id for m in L.find_markers(inp) if m.id]
    rendered = [i for i in in_ids if re.search(r'"[^"]*stay:%s\b' % re.escape(i), out)]
    if rendered:
        return {"verdict": "LEAKED_VISIBLE",
                "note": "marker rendered as JSX text: %s" % ", ".join(sorted(rendered))}
    retained = [i for i in in_ids if ("stay:%s" % i) in out]
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
