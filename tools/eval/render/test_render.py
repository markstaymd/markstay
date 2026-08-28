#!/usr/bin/env python3
"""Classifier self-tests: prove the per-axis oracle on hand-labelled cases before
the matrix is trusted (the plan's "parser-verified, not grep'd" acceptance gate).

Each case feeds a classifier a known input/output pair and asserts the verdict, so
a regression in `classify.py` (a missed relocation, a mangle read as survival, a
sanitizer rename read as a strip) is caught here, not silently in the matrix. Run
standalone (`./.venv/bin/python test_render.py`) or via `run.py`, which calls
`run_self_tests()` first and refuses to build the matrix if it raises.
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "linter"))

import classify


def ok(res):
    return {"out": res, "err": None, "rc": 0}


def err(msg):
    return {"out": "", "err": msg, "rc": 1}


# --- round-trip cases ------------------------------------------------------

ROUNDTRIP = [
    # (name, input, output_result, expected_verdict)
    ("survives_identity",
     "Apple sentence.\n\n<!-- stay:a1 -->\n",
     ok("Apple sentence.\n\n<!-- stay:a1 -->\n"),
     "SURVIVES"),
    ("survives_with_hash_drift",
     "Apple sentence here.\n\n<!-- stay:a1 hash=sha256:dead -->\n",
     ok("Apple sentence here, now reflowed.\n\n<!-- stay:a1 hash=sha256:dead -->\n"),
     "SURVIVES"),  # body edited -> §8 drift, but marker on its block: not a failure
    ("dropped",
     "Apple sentence.\n\n<!-- stay:a1 -->\n",
     ok("Apple sentence.\n"),
     "DROPPED"),
    ("relocated_swap",
     "Apple here.\n\n<!-- stay:a1 -->\n\nBanana there.\n\n<!-- stay:b1 -->\n",
     ok("Banana there.\n\n<!-- stay:a1 -->\n\nApple here.\n\n<!-- stay:b1 -->\n"),
     "RELOCATED"),
    ("duplicated",
     "Apple here.\n\n<!-- stay:a1 -->\n",
     ok("Apple here.\n\n<!-- stay:a1 -->\n\nApple twin.\n\n<!-- stay:a1 -->\n"),
     "DUPLICATED"),
    ("mangled_pandoc_codespan",
     "First paragraph. <!-- stay:p2 -->\n",
     ok("First paragraph. `<!-- stay:p2 -->`{=html}\n"),
     "MANGLED"),  # id still parses, but it is now an inline code span, not a comment
    ("mangled_escaped",
     "First paragraph.\n\n<!-- stay:p2 -->\n",
     ok("First paragraph.\n\n&lt;!-- stay:p2 --&gt;\n"),
     "MANGLED"),  # escaped: find_markers won't match -> not 'clean' and id present? see note

    # --- the table-row carrier: a marker inside the last cell of a one-line row.
    # A table is ONE block to every segmenter, so none of the cases above can tell a
    # row marker that held from one that slid off its row; these four are the whole
    # difference between "the bytes survived" and "the row is still addressed".
    ("row_survives_realigned",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("| a      | b                                    |\n"
        "| ------ | ------------------------------------ |\n"
        "| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "SURVIVES"),  # column padding moves the marker's column, not its row
    ("row_survives_restyled_table",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 --> |\n",
     ok("  a        b\n  -------- -----------------------\n"
        "  apples   3 <!-- stay:r1 -->\n"),
     "SURVIVES"),  # a non-pipe table style still keeps the row on one line
    ("row_escaped_hoisted",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 --> |\n",
     ok("<!-- stay:r1 -->\n\n| a | b |\n|---|---|\n| apples | 3 |\n"),
     "ROW_ESCAPED"),  # still on the right BLOCK, and the row it addressed is gone
    ("row_escaped_short_cells_not_vouched_by_marker",
     "| a | b |\n|---|---|\n| 3 | 5 <!-- stay:r1 subhash=sha256:5e6f --> |\n",
     ok("<!-- stay:r1 subhash=sha256:5e6f -->\n\n| a | b |\n|---|---|\n| 3 | 5 |\n"),
     "ROW_ESCAPED"),  # `3` and `5` both occur inside the marker's own sha256: prefix
    ("row_survives_prose_names_the_id",
     "| apples | 3 <!-- stay:r1 --> |\n",
     ok("see stay:r1 below\n\n| apples | 3 <!-- stay:r1 --> |\n"),
     "SURVIVES"),  # every line mentioning the id is tried, not just the first
    ("row_survives_all_empty_siblings",
     "| | |\n|---|---|\n| | <!-- stay:r1 --> |\n",
     ok("| | |\n|---|---|\n| | <!-- stay:r1 --> |\n"),
     "SURVIVES"),  # no cell text to key on: the weaker test is "still on a row line"
    ("row_escaped_all_empty_siblings",
     "| | |\n|---|---|\n| | <!-- stay:r1 --> |\n",
     ok("| | |\n|---|---|\n| | |\n<!-- stay:r1 -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_continuation_line",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 --> |\n",
     ok("  a        b\n  -------- ------------\n  apples   3\n"
        "           <!-- stay:r1 -->\n"),
     "ROW_ESCAPED"),  # pandoc's writer wrapping a cell splits marker from row
]


# --- render cases ----------------------------------------------------------

RENDER = [
    ("invisible_retained",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A para.</p>\n<!-- stay:a1 -->\n"),
     "INVISIBLE"),
    ("invisible_dropped",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A para.</p>\n"),
     "INVISIBLE"),
    ("leaked_escaped",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A para.</p>\n<p>&lt;!-- stay:a1 --&gt;</p>\n"),
     "LEAKED_VISIBLE"),
]


# --- MDX cases -------------------------------------------------------------

MDX = [
    ("mdx_html_comment_rejected",
     "A para.\n\n<!-- stay:a1 -->\n",
     err("Unexpected character `!` ... to create a comment in MDX, use `{/* text */}`"),
     "ERROR"),
    ("mdx_profile_invisible",
     "A para.\n\n{/* stay:x1 */}\n",
     ok("/*stay:x1*/\nfunction _createMdxContent(props){return <><_c.p>{\"A para.\"}</_c.p>{}</>;}"),
     "INVISIBLE"),
]


# --- sanitizer cases -------------------------------------------------------

SANITIZE = [
    ("id_survives",
     '<p id="a1">A</p>',
     ok('<p id="a1">A</p>'),
     "ID_SURVIVES"),
    ("id_prefixed",
     '<p id="a1">A</p>',
     ok('<p id="user-content-a1">A</p>'),
     "ID_PREFIXED"),
    ("id_stripped",
     '<p id="a1">A</p>',
     ok('<p>A</p>'),
     "ID_STRIPPED"),
]


def run_self_tests(verbose=False):
    failures = []

    for name, inp, res, want in ROUNDTRIP:
        got = classify.roundtrip_verdict(inp, res)["verdict"]
        _check("roundtrip", name, want, got, failures)
    for name, inp, res, want in RENDER:
        got = classify.render_verdict(inp, res)["verdict"]
        _check("render", name, want, got, failures)
    for name, inp, res, want in MDX:
        got = classify.mdx_verdict(inp, res)["verdict"]
        _check("mdx", name, want, got, failures)
    for name, emit, res, want in SANITIZE:
        got = classify.sanitizer_verdict(emit, res)["verdict"]
        _check("sanitize", name, want, got, failures)

    total = len(ROUNDTRIP) + len(RENDER) + len(MDX) + len(SANITIZE)
    if failures:
        for f in failures:
            print("FAIL:", f, file=sys.stderr)
        raise AssertionError("%d/%d classifier self-tests failed" % (len(failures), total))
    print("classifier self-tests: %d/%d passed" % (total, total), file=sys.stderr)
    return total


def _check(axis, name, want, got, failures):
    if got != want:
        failures.append("[%s] %s: want %s, got %s" % (axis, name, want, got))


if __name__ == "__main__":
    run_self_tests(verbose=True)
