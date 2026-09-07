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
    ("mangled_padded_codespan",
     "First paragraph. <!-- stay:p2 -->\n",
     ok("First paragraph. ` <!-- stay:p2 --> `\n"),
     "MANGLED"),
    ("mangled_escaped",
     "First paragraph.\n\n<!-- stay:p2 -->\n",
     ok("First paragraph.\n\n&lt;!-- stay:p2 --&gt;\n"),
     "MANGLED"),  # escaped: find_markers won't match -> not 'clean' and id present? see note
    ("fenced_only_marker_removed_is_not_dropped",
     "```md\n<!-- stay:a1 -->\n```\n",
     ok("```md\n```\n"),
     "SURVIVES"),
    ("fenced_only_marker_changed_is_not_mangled",
     "```md\n<!-- stay:a1 x-note=old -->\n```\n",
     ok("```md\n<!-- stay:a1 x-note=new -->\n```\n"),
     "SURVIVES"),
    ("real_marker_dropped_despite_fenced_duplicate",
     "Body.\n\n<!-- stay:a1 -->\n\n```md\n<!-- stay:a1 -->\n```\n",
     ok("Body.\n\n```md\n<!-- stay:a1 -->\n```\n"),
     "DROPPED"),
    ("frontmatter_only_marker_removed_is_not_dropped",
     "---\nnote: <!-- stay:a1 -->\n---\n\nBody.\n",
     ok("---\nnote:\n---\n\nBody.\n"),
     "SURVIVES"),
    ("fenced_escaped_marker_is_not_mangle_evidence",
     "Body.\n\n<!-- stay:a1 -->\n",
     ok("Body.\n\n```md\n&lt;!-- stay:a1 --&gt;\n```\n"),
     "DROPPED"),
    ("marker_opens_outside_fence_and_closes_inside_is_real",
     'Body.\n<!-- stay:a1 quote="\n```md\n" -->\n```\n',
     ok("Body.\n```\n"),
     "DROPPED"),
    ("marker_opens_inside_fence_and_closes_outside_is_content",
     '```md\n<!-- stay:fake quote="\n```\nTail" -->\n',
     ok('```md\n<!-- stay:changed quote="\n```\nTail" -->\n'),
     "SURVIVES"),
    ("quoted_attribute_survives_verbatim",
     'Body.\n\n<!-- stay:a1 quote="x-- > y" x-acme=v1 -->\n',
     ok('Body.\n\n<!-- stay:a1 quote="x-- > y" x-acme=v1 -->\n'),
     "SURVIVES"),
    ("attribute_after_quoted_value_is_exact",
     'Body.\n\n<!-- stay:a1 quote="x-- > y" x-acme=v1 -->\n',
     ok('Body.\n\n<!-- stay:a1 quote="x-- > y" x-acme=v2 -->\n'),
     "MANGLED"),
    ("multiline_marker_crlf_bytes_survive_verbatim",
     'Body.\n\n<!-- stay:a1 quote="x\r\ny" -->\n',
     ok('Body.\n\n<!-- stay:a1 quote="x\r\ny" -->\n'),
     "SURVIVES"),
    ("multiline_marker_crlf_to_lf_is_mangled",
     'Body.\n\n<!-- stay:a1 quote="x\r\ny" -->\n',
     ok('Body.\n\n<!-- stay:a1 quote="x\ny" -->\n'),
     "MANGLED"),
    ("multiline_marker_cr_to_lf_is_mangled",
     'Body.\n\n<!-- stay:a1 quote="x\ry" -->\n',
     ok('Body.\n\n<!-- stay:a1 quote="x\ny" -->\n'),
     "MANGLED"),
    ("multiline_marker_raw_mapping_survives_frontmatter_blanking",
     '---\r\ntitle: x\r\n---\r\n\r\nBody.\r\n'
     '<!-- stay:a1 quote="x\r\ny" -->\r\n',
     ok('---\r\ntitle: x\r\n---\r\n\r\nBody.\r\n'
        '<!-- stay:a1 quote="x\r\ny" -->\r\n'),
     "SURVIVES"),

    # --- the table-row carrier: a `subhash` marker inside an accepted body row.
    # In this blank-surrounded fixture the block-level checks cannot tell a row marker
    # that held from one that slid elsewhere inside the same selected §5 block.
    ("row_survives_realigned",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     ok("| a      | b                                    |\n"
        "| ------ | ------------------------------------ |\n"
        "| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n"
        "<!-- stay:t1 -->\n"),
     "SURVIVES"),
    ("row_survives_pipe_inside_marker_attribute",
     '| a | b |\n|---|---|\n| apples | 3<!-- stay:r1 subhash=sha256:1a2b quote="a|b" --> |\n'
     '<!-- stay:t1 -->\n',
     ok('| a | b |\n|---|---|\n| apples | 3<!-- stay:r1 subhash=sha256:1a2b quote="a|b" --> |\n'
        '<!-- stay:t1 -->\n'),
     "SURVIVES"),
    ("row_escaped_restyled_as_nonpipe_table",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  a        b\n  -------- -----------------------\n"
        "  apples   3 <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_hoisted",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("<!-- stay:r1 subhash=sha256:1a2b -->\n\n| a | b |\n|---|---|\n| apples | 3 |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_short_cells_not_vouched_by_marker",
     "| a | b |\n|---|---|\n| 3 | 5 <!-- stay:r1 subhash=sha256:5e6f --> |\n",
     ok("<!-- stay:r1 subhash=sha256:5e6f -->\n\n| a | b |\n|---|---|\n| 3 | 5 |\n"),
     "ROW_ESCAPED"),
    ("row_survives_prose_names_the_id",
     "| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     ok("see stay:r1 below\n\n| h1 | h2 |\n|---|---|\n"
        "| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n"
        "<!-- stay:t1 -->\n"),
     "SURVIVES"),
    ("row_survives_all_empty_siblings",
     "| | |\n|---|---|\n| | <!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     ok("| | |\n|---|---|\n| | <!-- stay:r1 subhash=sha256:1a2b --> |\n"
        "<!-- stay:t1 -->\n"),
     "SURVIVES"),
    ("row_escaped_all_empty_siblings",
     "| | |\n|---|---|\n| | <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("| | |\n|---|---|\n| | |\n<!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_continuation_line",
     "| a | b |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  a        b\n  -------- ------------\n  apples   3\n"
        "           <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_substring_collision",
     "| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n| applesauce | 13 |\n",
     ok("| h1 | h2 |\n|---|---|\n| apples | 3 |\n"
        "| applesauce | 13 <!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_empty_row_to_header",
     "| h1 | h2 |\n|---|---|\n| | <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("| h1 | h2 <!-- stay:r1 subhash=sha256:1a2b --> |\n|---|---|\n| | |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_invalid_subhash_key_moves_between_rows",
     "| h1 | h2 |\n|---|---|\n"
     "| a | b<!-- stay:r1 subhash=bogus --> |\n| c | d |\n"
     "<!-- stay:t1 -->\n",
     ok("| h1 | h2 |\n|---|---|\n| a | b |\n"
        "| c | d<!-- stay:r1 subhash=bogus --> |\n"
        "<!-- stay:t1 -->\n"),
     "ROW_ESCAPED"),
    ("row_invalid_subhash_container_evidence_fails_closed",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=bogus --> |\n"
     "<!-- stay:t1 subhash=bogus -->\n",
     ok("| h |\n|---|\n| a<!-- stay:r1 subhash=bogus --> |\n"
        "<!-- stay:t1 subhash=bogus -->\n"),
     "ROW_ESCAPED"),
    ("row_x_subhash_container_evidence_stays_bare",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=bogus --> |\n"
     "<!-- stay:t1 x-subhash=bogus -->\n",
     ok("| h |\n|---|\n| a<!-- stay:r1 subhash=bogus --> |\n"
        "<!-- stay:t1 x-subhash=bogus -->\n"),
     "SURVIVES"),
    ("row_escaped_identical_body_crosses_container",
     "| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n\n"
     "<!-- stay:t1 -->\n\n"
     "| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r2 subhash=sha256:1a2b --> |\n\n"
     "<!-- stay:t2 -->\n",
     ok("| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r2 subhash=sha256:1a2b --> |\n\n"
        "<!-- stay:t1 -->\n\n"
        "| h1 | h2 |\n|---|---|\n| apples | 3 <!-- stay:r1 subhash=sha256:1a2b --> |\n\n"
        "<!-- stay:t2 -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_identical_body_crosses_unstamped_container",
     "| h |\n|---|\n| same<!-- stay:r1 subhash=sha256:1a2b --> |\n\n"
     "Between.\n\n"
     "| h |\n|---|\n| same |\n",
     ok("| h |\n|---|\n| same |\n\n"
        "Between.\n\n"
        "| h |\n|---|\n| same<!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_unstamped_container_relocation_fails_closed",
     "Alpha unique.\n| h |\n|---|\n"
     "| same<!-- stay:r1 subhash=sha256:1a2b --> |\n\nBeta unique.\n",
     ok("Alpha unique.\n\nBeta unique.\n| h |\n|---|\n"
        "| same<!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_empty_cell_positions_do_not_collide",
     "| h1 | h2 | h3 |\n|---|---|---|\n"
     "| a | | b <!-- stay:r1 subhash=sha256:1a2b --> |\n| a | b | |\n",
     ok("| h1 | h2 | h3 |\n|---|---|---|\n"
        "| a | | b |\n| a | b <!-- stay:r1 subhash=sha256:1a2b --> | |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_interior_space_does_not_collapse",
     "| h1 | h2 |\n|---|---|\n"
     "| a  b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n| a b | x |\n",
     ok("| h1 | h2 |\n|---|---|\n"
        "| a  b | x |\n| a b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_unicode_space_does_not_collapse",
     "| h1 | h2 |\n|---|---|\n"
     "| a\u00a0b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n| a b | x |\n",
     ok("| h1 | h2 |\n|---|---|\n"
        "| a\u00a0b | x |\n| a b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_escaped_private_use_text_is_not_a_token",
     "| h1 | h2 |\n|---|---|\n"
     "| a\ue000b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n| ab | x |\n",
     ok("| h1 | h2 |\n|---|---|\n"
        "| a\ue000b | x |\n| ab | x <!-- stay:r1 subhash=sha256:1a2b --> |\n"),
     "ROW_ESCAPED"),
    ("row_survives_id_ending_hyphen",
     "| h1 | h2 |\n|---|---|\n| a | b <!-- stay:r- subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     ok("| h1 | h2 |\n|---|---|\n| a | b <!-- stay:r- subhash=sha256:1a2b --> |\n"
        "<!-- stay:t1 -->\n"),
     "SURVIVES"),
    ("row_escaped_nonpipe_reversed_cells",
     "| h1 | h2 |\n|---|---|\n| alpha | beta <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  beta alpha <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_nonpipe_empty_positions_are_unprovable",
     "| h1 | h2 | h3 |\n|---|---|---|\n"
     "| a | | b <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  a b <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_nonpipe_preserves_exact_space",
     "| h1 | h2 |\n|---|---|\n"
     "| a  b | x <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  a b x <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_nonpipe_hyphen_boundary",
     "| h1 | h2 |\n|---|---|\n"
     "| bar | x <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("  foo-bar x <!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_escaped_malformed_id_mention_is_not_evidence",
     "| h1 | h2 |\n|---|---|\n| a | b <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     ok("| h1 | h2 |\n|---|---|\n| a | b <!-- stay:r1. --> |\n"
        "<!-- stay:r1 subhash=sha256:1a2b -->\n"),
     "ROW_ESCAPED"),
    ("row_mangled_subhash_changed",
     "| h1 | h2 |\n|---|---|\n| a | b<!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     ok("| h1 | h2 |\n|---|---|\n| a | b<!-- stay:r1 subhash=sha256:ffff --> |\n"
        "<!-- stay:t1 -->\n"),
     "MANGLED"),
    ("row_mangled_extension_attribute_changed",
     "| h1 | h2 |\n|---|---|\n"
     "| a | b<!-- stay:r1 subhash=sha256:1a2b x-acme=v1 --> |\n"
     "<!-- stay:t1 -->\n",
     ok("| h1 | h2 |\n|---|---|\n"
        "| a | b<!-- stay:r1 subhash=sha256:1a2b x-acme=v2 --> |\n"
        "<!-- stay:t1 -->\n"),
     "MANGLED"),
]


# Direct §5.6 row-scan boundaries. These make the association oracle fail if it
# regresses to a negative-lookbehind split or scans marker attributes as table text.
ROW_CELLS = [
    ("marker_pipe_is_opaque",
     '| a | b<!-- stay:r1 quote="x|y" --> |',
     ["a", "b"]),
    ("html_host_closer_in_quote_does_not_hide_pipe",
     '| a | b<!-- stay:r1 subhash=sha256:ab quote="x--> | y" --> |',
     ["a", 'b<!-- stay:r1 subhash=sha256:ab quote="x-->', 'y" -->']),
    ("html_bang_host_closer_in_quote_does_not_hide_pipe",
     '| a | b<!-- stay:r1 subhash=sha256:ab quote="x--!> | y" --> |',
     ["a", 'b<!-- stay:r1 subhash=sha256:ab quote="x--!>', 'y" -->']),
    ("mdx_host_closer_in_quote_does_not_hide_pipe",
     '| a | b{/* stay:r1 subhash=sha256:ab quote="x*/} | y" */} |',
     ["a", 'b{/* stay:r1 subhash=sha256:ab quote="x*/}', 'y" */}']),
    ("mdx_comment_close_without_brace_is_still_forbidden",
     '| a | b{/* stay:r1 subhash=sha256:ab quote="x*/ | y" */} |',
     ["a", 'b{/* stay:r1 subhash=sha256:ab quote="x*/', 'y" */}']),
    ("rejected_mdx_opener_does_not_swallow_later_marker",
     '| a | b{/* stay:bad quote="x*/ tail {/* stay:r1 quote="x|y" */} |',
     ["a", 'b{/* stay:bad quote="x*/ tail']),
    ("html_may_carry_mdx_close_text",
     '| a | b<!-- stay:r1 quote="x*/ | y" --> |',
     ["a", "b"]),
    ("mdx_may_carry_html_close_text",
     '| a | b{/* stay:r1 quote="x--> | y" */} |',
     ["a", "b"]),
    ("invalid_quoted_escape_does_not_hide_pipe",
     r'| a | b<!-- stay:r1 quote="x\q|y" --> |',
     ["a", r'b<!-- stay:r1 quote="x\q', 'y" -->']),
    ("odd_marker_backslash_keeps_quote_escaped",
     r'| a | b<!-- stay:r1 quote="x\" | y" --> |',
     ["a", "b"]),
    ("even_marker_backslashes_close_quote",
     r'| a | b<!-- stay:r1 quote="x\\" | y" --> |',
     ["a", r'b<!-- stay:r1 quote="x\\"', 'y" -->']),
    ("overlapping_marker_spans_refuse_row",
     '| a<!-- stay:r1 quote="{/* stay:nested */}" --> | '
     'b<!-- stay:r2 quote="x|y" --> |',
     None),
    ("inline_code_marker_is_still_opaque",
     '| a | `<!-- stay:r1 quote="x|y" -->` |',
     ["a", "``"]),
    ("odd_backslash_escapes_pipe",
     r"| a\|b | c |",
     [r"a\|b", "c"]),
    ("even_backslashes_leave_delimiter",
     r"| a\\| b |",
     [r"a\\", "b"]),
    ("marker_breaks_backslash_run",
     r"| a | x\<!-- stay:r1 -->|",
     ["a", "x\\"]),
    ("outer_pipes_required", "a | b | c", None),
    ("empty_cell_positions_preserved", "| a | | b |", ["a", "", "b"]),
    ("interior_ascii_space_preserved", "| a  b | x |", ["a  b", "x"]),
    ("unicode_space_preserved", "| a\u00a0b | x |", ["a\u00a0b", "x"]),
    ("private_use_text_preserved", "| a\ue000b | x |", ["a\ue000b", "x"]),
]


# Complete §5.6 candidate-scan cases. Expected values include only real row stays:
# markers with `subhash` on accepted body rows.
ROW_CARRIED = [
    ("accepted_at_eof",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |",
     {"r1": ["a"]}),
    ("accepted_before_blank",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n\nTail.\n",
     {"r1": ["a"]}),
    ("accepted_before_marker_only_line",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n",
     {"r1": ["a"]}),
    ("standalone_row_excluded",
     "| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {}),
    ("header_subhash_excluded_body_included",
     "| h<!-- stay:rh subhash=sha256:1a2b --> |\n|---|\n"
     "| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {"r1": ["a"]}),
    ("marked_delimiter_pair_fails_then_releases_scan",
     "| h |\n|---<!-- stay:bad subhash=sha256:1a2b -->|\n"
     "| h2 |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {"r1": ["a"]}),
    ("marker_pipe_does_not_rescue_delimiter",
     '| h |\n|---<!-- stay:bad quote="a|b" -->|\n'
     "| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {}),
    ("form_feed_delimiter_rejected",
     "| h |\n|\f---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {}),
    ("vertical_tab_after_delimiter_rejected",
     "| h |\n|---|\v\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {}),
    ("bare_body_marker_excluded",
     "| h |\n|---|\n| a<!-- stay:r1 --> |\n",
     {}),
    ("empty_quoted_value_does_not_hide_subhash",
     '| h |\n|---|\n'
     '| a<!-- stay:r1 quote="" subhash=sha256:1a2b --> |\n',
     {"r1": ["a"]}),
    ("invalid_subhash_value_still_routes_as_child",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=bogus --> |\n",
     {"r1": ["a"]}),
    ("quoted_subhash_value_still_routes_as_child",
     '| h |\n|---|\n| a<!-- stay:r1 subhash="sha256:1a2b" --> |\n',
     {"r1": ["a"]}),
    ("x_subhash_does_not_route_as_child",
     "| h |\n|---|\n| a<!-- stay:r1 x-subhash=bogus --> |\n",
     {}),
    ("invalid_quoted_escape_is_not_row_evidence",
     '| h |\n|---|\n'
     r'| a<!-- stay:r1 subhash=sha256:1a2b quote="x\q" --> |' "\n",
     {}),
    ("attribute_without_equals_is_not_row_evidence",
     "| h |\n|---|\n"
     "| a<!-- stay:r1 subhash=sha256:1a2b nonsense --> |\n",
     {}),
    ("whitespace_around_equals_is_not_row_evidence",
     "| h |\n|---|\n"
     "| a<!-- stay:r1 subhash = sha256:1a2b --> |\n",
     {}),
    ("invalid_body_refuses_every_row",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "not a row\n| b<!-- stay:r2 subhash=sha256:1a2b --> |\n\n",
     {}),
    ("fenced_table_excluded",
     "```md\n| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n```\n",
     {}),
    ("fence_inside_body_refuses",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "```md\ninside\n```\n\n",
     {}),
    ("marker_opening_inside_fence_does_not_poison_later_row",
     "```md\n<!-- stay:fake\n```\n\n"
     "| h |\n|---|\n| a --> <!-- stay:r1 subhash=sha256:1a2b --> |\n",
     {"r1": ["a -->"]}),
    ("overlapping_marker_span_in_body_refuses",
     "| h |\n|---|\n"
     '| a<!-- stay:outer quote="{/* stay:inner subhash=sha256:1a2b */}" --> |\n\n',
     {}),
    ("multiline_overlapping_marker_span_refuses",
     '| h<!-- stay:outer quote="x |\n'
     "|---|\n"
     '| a{/* stay:r1 subhash=sha256:1a2b */} y" --> |\n',
     {}),
    ("inline_code_row_marker_is_addressable",
     "| h1 | h2 |\n|---|---|\n"
     '| a | `<!-- stay:r1 subhash=sha256:1a2b quote="x|y" -->` |\n',
     {"r1": ["a", "``"]}),
    ("frontmatter_table_excluded",
     "---\ntitle: x\n| h |\n|---|\n"
     "| a<!-- stay:r1 subhash=sha256:1a2b --> |\n---\n",
     {}),
    ("cr_and_crlf_normalize",
     "| h |\r|---|\r\n| a<!-- stay:r1 subhash=sha256:1a2b --> |",
     {"r1": ["a"]}),
    ("unicode_line_separator_is_not_lf",
     "| h |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\u0085tail\n\n",
     {}),
    ("two_candidates_in_one_container_refused",
     "| h1 |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n"
     "<!-- stay:t1 -->\n"
     "| h2 |\n|---|\n| b<!-- stay:r2 subhash=sha256:1a2b --> |\n",
     {}),
    ("two_candidates_in_separate_containers_accepted",
     "| h1 |\n|---|\n| a<!-- stay:r1 subhash=sha256:1a2b --> |\n\n"
     "<!-- stay:t1 -->\n\n"
     "| h2 |\n|---|\n| b<!-- stay:r2 subhash=sha256:1a2b --> |\n",
     {"r1": ["a"], "r2": ["b"]}),
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
    ("naked_id_in_prose_is_not_a_leak",
     "Prose says stay:a1 below.\n\n<!-- stay:a1 -->\n",
     ok("<p>Prose says stay:a1 below.</p>\n<!-- stay:a1 -->\n"),
     "INVISIBLE"),
    ("rcdata_marker_is_visible",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<textarea><!-- stay:a1 --></textarea>"),
     "LEAKED_VISIBLE"),
    ("html_bang_terminator_leaks_marker_tail",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok('<p>A <!-- stay:a1 quote="x--!> LEAK" --> Z</p>'),
     "LEAKED_VISIBLE"),
    ("html_bang_terminator_without_tail_stays_invisible",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A para.</p><!-- stay:a1 --!>"),
     "INVISIBLE"),
    ("html_bang_terminator_ignores_later_comment_closer",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A.</p><!-- stay:a1 --!><!-- ordinary -->"),
     "INVISIBLE"),
    ("html_bang_terminator_without_normal_closer_leaks_visible_tail",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok('<p>A <!-- stay:a1 quote="x--!> LEAK</p>'),
     "LEAKED_VISIBLE"),
    ("html_bang_complete_body_followed_by_prose_is_not_tail",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok("<p>A.</p><!-- stay:a1 --!>ordinary prose"),
     "INVISIBLE"),
    ("html_bang_incomplete_prefix_without_tail_stays_invisible",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok('<p>A.</p><!-- stay:a1 quote="x--!>'),
     "INVISIBLE"),
    ("html_bang_terminator_inside_template_stays_hidden",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok('<template><!-- stay:a1 quote="x--!> LEAK" --></template>'),
     "INVISIBLE"),
    ("rcdata_bang_marker_is_visible",
     "A para.\n\n<!-- stay:a1 -->\n",
     ok('<textarea><!-- stay:a1 quote="x--!> LEAK" --></textarea>'),
     "LEAKED_VISIBLE"),
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
    ("mdx_naked_id_in_text_is_not_a_leak",
     "Prose says stay:x1.\n\n{/* stay:x1 */}\n",
     ok("/*stay:x1*/\nfunction _createMdxContent(props){return <_c.p>{\"Prose says stay:x1.\"}</_c.p>;}"),
     "INVISIBLE"),
    ("mdx_complete_marker_in_text_leaks",
     "A para.\n\n{/* stay:x1 */}\n",
     ok('function _createMdxContent(props){return <_c.p>{"{/* stay:x1 */}"}</_c.p>;}'),
     "LEAKED_VISIBLE"),
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
    for name, line, want in ROW_CELLS:
        got = classify._row_cells(line)
        _check("row-cells", name, want, got, failures)
    for name, inp, want in ROW_CARRIED:
        got = {
            mid: evidence["cells"]
            for mid, evidence in classify._row_carried(inp).items()
        }
        _check("row-candidates", name, want, got, failures)
    for name, inp, res, want in RENDER:
        got = classify.render_verdict(inp, res)["verdict"]
        _check("render", name, want, got, failures)
    for name, inp, res, want in MDX:
        got = classify.mdx_verdict(inp, res)["verdict"]
        _check("mdx", name, want, got, failures)
    for name, emit, res, want in SANITIZE:
        got = classify.sanitizer_verdict(emit, res)["verdict"]
        _check("sanitize", name, want, got, failures)

    total = (
        len(ROUNDTRIP) + len(ROW_CELLS) + len(ROW_CARRIED)
        + len(RENDER) + len(MDX) + len(SANITIZE)
    )
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
