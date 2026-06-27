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
