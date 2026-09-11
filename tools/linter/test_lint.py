#!/usr/bin/env python3
"""Self-tests for markstay_lint. Runnable two ways:

    python test_lint.py        # plain asserts, no dependency
    pytest test_lint.py        # also works (functions are test_*)

No API credentials needed: the linter is fully local and deterministic.
"""

import random

import markstay_lint as L


def codes(findings):
    return sorted(f.code for f in findings)


def test_clean_doc_with_correct_hash():
    body = "The order pipeline ingests messages and normalizes them."
    h = L.body_hash(body, 4)
    md = (
        f"{body}\n<!-- stay:8f24 hash=sha256:{h} -->\n\n"
        "A second paragraph that is also identified.\n<!-- stay:a1b2 -->\n"
    )
    _, findings = L.lint_document(md)
    assert findings == [], codes(findings)
    assert not L.has_errors(findings)


def test_hash_uppercase_hex_no_drift():
    # SPEC.md §8: hex comparison is case-insensitive. A marker storing the hash
    # in uppercase must not be reported as drifted against the lowercase digest.
    body = "Users authenticate with an API key in the Authorization header."
    h = L.body_hash(body, 4).upper()
    md = f"{body}\n<!-- stay:8f24 hash=sha256:{h} -->\n"
    _, findings = L.lint_document(md)
    assert codes(findings) == [], codes(findings)
    assert not L.has_errors(findings)


def test_marker_no_blank_line_attaches_to_block():
    md = "Just one paragraph.\n<!-- stay:p1 -->\n"
    blocks = L.parse_document(md)
    assert len(blocks) == 1
    assert blocks[0].content == "Just one paragraph."
    assert [m.id for m in blocks[0].markers] == ["p1"]


def test_marker_only_chunk_attaches_to_previous():
    md = "Some content.\n\n<!-- stay:x -->\n"
    blocks = L.parse_document(md)
    assert len(blocks) == 1
    assert blocks[0].content == "Some content."
    assert [m.id for m in blocks[0].markers] == ["x"]


def test_duplicate_id():
    md = "Block one.\n<!-- stay:dup -->\n\nBlock two.\n<!-- stay:dup -->\n"
    _, findings = L.lint_document(md)
    assert "DUPLICATE_ID" in codes(findings)
    assert L.has_errors(findings)


def test_malformed_marker():
    md = "A paragraph.\n<!-- stay:note=hello -->\n"
    _, findings = L.lint_document(md)
    assert "MALFORMED_MARKER" in codes(findings)


def test_marker_parser_is_complete_host_first_and_resumes_at_later_openers():
    invalid = [
        "<!-- stay:bad broken -->",
        '<!-- stay:bad x="a\\q" -->',
        '<!-- stay:bad x="a-->b" -->',
        '<!-- stay:bad x="a--!>b" -->',
        '{/* stay:bad x="a*/b" */}',
        "<!-- stay:bad\nhash=sha256:dead -->",
    ]
    for raw in invalid:
        assert L.find_markers(raw) == [], raw
        assert L._strip_markers(raw) == raw

    text = (
        '<!-- stay:bad x="a--!>b" -->\n'
        '{/* stay:bad x="a*/b" */}\n'
        "<!-- stay:good hash=sha256:BEEF -->"
    )
    markers = L.find_markers(text)
    assert [(mk.id, mk.hash) for mk in markers] == [("good", "beef")]


def test_marker_parser_normalizes_quoted_line_endings_but_preserves_raw():
    raw = '<!-- stay:a quote="one\r\ntwo\rthree" subhash="bogus" -->'
    marker = L.find_markers(raw)[0]
    assert marker.raw == raw
    assert marker.id == "a"
    assert marker.subhash is None
    assert marker.has_subhash is True
    parsed = L.parse_document("Body.\r\n" + raw + "\r\n")
    assert parsed[0].markers[0].raw == raw


def test_malformed_no_id_is_diagnostic_but_not_a_stripped_marker():
    raw = "<!-- stay:note=hello -->"
    marker = L.find_markers(raw)[0]
    assert marker.malformed is True
    assert L._strip_markers(raw) == raw
    for rejected in (
        "<!-- stay:note=hello --!>",
        "{/* stay:note=hello */x",
    ):
        markers = L.find_markers(rejected)
        assert len(markers) == 1 and markers[0].malformed
        assert markers[0].raw == (
            rejected if rejected.endswith(("--!>", "*/")) else rejected[:-1]
        )
        assert L._strip_markers(rejected) == rejected
        assert codes(L.lint_document(rejected)[1]) == ["MALFORMED_MARKER"]


def test_subhash_presence_is_lexical_for_duplicates_but_not_a_block_stay():
    md = (
        "Body.\n"
        "<!-- stay:child subhash=bogus hash=sha256:dead -->\n"
        '<!-- stay:child subhash="bogus" -->\n'
        "<!-- stay:parent -->\n"
    )
    blocks, findings = L.lint_document(md)
    assert [mk.has_subhash for mk in blocks[0].markers] == [True, True, False]
    assert codes(findings) == ["DUPLICATE_ID"]
    assert list(L._id_index(blocks)) == ["parent"]
    assert (
        L.lint_diff(
            md, md.replace("<!-- stay:child subhash=bogus hash=sha256:dead -->\n", "")
        )
        == []
    )


def test_orphan_subhash_is_reported_without_block_attribution_or_hash_drift():
    for value in ("sha256:dead", "bogus", '"sha256:dead"'):
        _, findings = L.lint_document(
            f"<!-- stay:child subhash={value} hash=sha256:dead -->"
        )
        assert [(finding.code, finding.id) for finding in findings] == [
            ("ORPHAN_MARKER", "child")
        ]
    _, control = L.lint_document("<!-- stay:block x-subhash=bogus -->")
    assert codes(control) == ["ORPHAN_MARKER"]


def test_hashed_orphan_has_no_body_to_report_as_drifted():
    _, findings = L.lint_document("<!-- stay:x hash=sha256:dead -->\n")
    assert [(finding.code, finding.id) for finding in findings] == [
        ("ORPHAN_MARKER", "x")
    ]


def test_duplicate_order_stays_lexical_when_child_ownership_is_enabled():
    docs = [
        ("- item <!-- stay:x subhash=bogus -->\n<!-- stay:x -->\n", 1),
        (
            "| h |\n|---|\n| item<!-- stay:x subhash=bogus --> |\n" "<!-- stay:x -->\n",
            3,
        ),
    ]
    for md, first_line in docs:
        duplicate = next(
            finding
            for finding in L.lint_document(md, child_blocks=True)[1]
            if finding.code == "DUPLICATE_ID"
        )
        assert duplicate.line > first_line
        assert f"first at line {first_line}" in duplicate.message


def test_multiline_quoted_marker_crosses_blank_segment_without_disappearing():
    md = 'Body.\n<!-- stay:a quote="one\n\ntwo" -->\n'
    for mode in ("blank-line", "commonmark"):
        blocks, findings = L.lint_document(md, mode=mode)
        assert findings == []
        assert [mk.id for block in blocks for mk in block.markers] == ["a"]
        assert [block.content for block in blocks if block.index >= 0] == ["Body."]


def test_multiline_child_marker_must_fit_wholly_inside_one_item():
    crossing = (
        '- one <!-- stay:c subhash=sha256:dead x-note="bogus\n'
        '- two" -->\n'
        "<!-- stay:p -->\n"
    )
    contained = (
        '- one <!-- stay:c subhash=sha256:dead x-note="bogus\n'
        '  continued" -->\n'
        "- two\n"
        "<!-- stay:p -->\n"
    )
    for mode in ("blank-line", "commonmark"):
        blocks, findings = L.lint_document(crossing, mode=mode, child_blocks=True)
        assert [child.content for child in blocks[0].children] == ["one", ""]
        assert all(not child.markers for child in blocks[0].children)
        assert [(finding.code, finding.id) for finding in findings] == [
            ("CHILD_UNADDRESSED", "c")
        ]

        blocks, findings = L.lint_document(contained, mode=mode, child_blocks=True)
        assert [child.content for child in blocks[0].children] == ["one", "two"]
        assert [marker.id for marker in blocks[0].children[0].markers] == ["c"]
        assert all(not child.markers for child in blocks[0].children[1:])
        assert [finding.code for finding in findings] == ["HASH_DRIFT"]


def test_crossing_marker_does_not_erase_unrelated_list_child_ownership():
    for key in ("subhash=bogus", "x-note=block"):
        md = (
            f'- one <!-- stay:c {key} x-note="cross\n'
            '- two" --> text<!-- stay:d subhash=bogus -->\n'
            "<!-- stay:p -->\n"
        )
        for mode in ("blank-line", "commonmark"):
            blocks, findings = L.lint_document(md, mode=mode, child_blocks=True)
            assert [child.content for child in blocks[0].children] == ["one", "text"]
            assert [marker.id for marker in blocks[0].children[1].markers] == ["d"]
            if key == "subhash=bogus":
                assert [(finding.code, finding.id) for finding in findings] == [
                    ("CHILD_UNADDRESSED", "c")
                ]
            else:
                assert findings == []


def test_multiline_child_strip_keeps_later_fenced_marker_as_content():
    md = (
        '- one <!-- stay:c subhash=bogus x-note="a\n'
        "  b\n"
        '  c" -->\n\n'
        "  ```\n"
        "  <!-- stay:example -->\n"
        "  ```\n"
        "<!-- stay:p -->\n"
    )
    blocks = L.parse_document(md, mode="commonmark", child_blocks=True)
    child = blocks[0].children[0]
    assert [marker.id for marker in child.markers] == ["c"]
    assert "<!-- stay:example -->" in child.content


def test_x_subhash_remains_a_block_level_extension_key():
    md = "Body.\n<!-- stay:block x-subhash=bogus -->\n"
    blocks, findings = L.lint_document(md)
    assert findings == []
    assert blocks[0].markers[0].has_subhash is False
    assert list(L._id_index(blocks)) == ["block"]


def test_orphan_marker_at_top():
    md = "<!-- stay:loose -->\n\nReal content below.\n"
    _, findings = L.lint_document(md)
    assert "ORPHAN_MARKER" in codes(findings)


def test_hash_drift_intradoc():
    md = "Edited content.\n<!-- stay:z9 hash=sha256:dead -->\n"
    _, findings = L.lint_document(md)
    assert codes(findings) == ["HASH_DRIFT"]
    assert not L.has_errors(findings)  # drift is a warning, not an error


def test_mdx_marker_parsed():
    md = "An MDX block.\n{/* stay:mdx1 hash=sha256:abcd */}\n"
    blocks = L.parse_document(md)
    assert blocks[0].markers[0].id == "mdx1"
    assert blocks[0].markers[0].syntax == "mdx"


def test_diff_dropped():
    before = "A.\n<!-- stay:a -->\n\nB.\n<!-- stay:b -->\n"
    after = "A.\n<!-- stay:a -->\n\nB rewritten without its marker.\n"
    findings = L.lint_diff(before, after)
    dropped = [f for f in findings if f.code == "DROPPED_ID"]
    assert [f.id for f in dropped] == ["b"]
    assert L.has_errors(findings)


def test_diff_duplicated():
    before = "A.\n<!-- stay:a -->\n"
    after = "A.\n<!-- stay:a -->\n\nCopy of A.\n<!-- stay:a -->\n"
    findings = L.lint_diff(before, after)
    assert "DUPLICATED_ID" in codes(findings)


def test_diff_new_id_is_info():
    before = "A.\n<!-- stay:a -->\n"
    after = "A.\n<!-- stay:a -->\n\nBrand new block.\n<!-- stay:c -->\n"
    findings = L.lint_diff(before, after)
    new = [f for f in findings if f.code == "NEW_ID"]
    assert [f.id for f in new] == ["c"]
    assert not L.has_errors(findings)  # a new id alone is informational


def test_diff_relocation_swap():
    before = "Alpha content.\n<!-- stay:aaa -->\n\nBeta content.\n<!-- stay:bbb -->\n"
    after = "Beta content.\n<!-- stay:aaa -->\n\nAlpha content.\n<!-- stay:bbb -->\n"
    findings = L.lint_diff(before, after)
    reloc = sorted(f.id for f in findings if f.code == "RELOCATED_ID")
    assert reloc == ["aaa", "bbb"]
    assert L.has_errors(findings)


def test_diff_inplace_edit_is_drift_not_relocation():
    before = "Alpha content.\n<!-- stay:aaa -->\n"
    after = "Alpha content, now revised.\n<!-- stay:aaa -->\n"
    findings = L.lint_diff(before, after)
    assert codes(findings) == ["HASH_DRIFT"]
    assert not L.has_errors(findings)


# --- CommonMark-tree attachment (SPEC.md §5.2, v1.1) ----------------------
# These contrast the default blank-line segmenter (where loose lists and
# blank-line fences split into several blocks, the §5.2 limit) with commonmark
# mode (where each is one block carrying the stay). commonmark mode needs
# markdown-it-py; the default path stays dependency-free.


def _content_blocks(md, mode):
    return [b for b in L.parse_document(md, mode=mode) if b.index >= 0]


def test_commonmark_loose_list_is_one_block():
    md = "- item one\n\n- item two\n\n- item three\n<!-- stay:mylist -->\n"
    # baseline: blank lines split the loose list, marker binds the last item only
    bl = _content_blocks(md, "blank-line")
    assert len(bl) == 3
    assert "item three" in bl[-1].content and "item one" not in bl[-1].content
    assert [m.id for m in bl[-1].markers] == ["mylist"]
    # commonmark: the whole loose list is one block carrying the stay
    cm = _content_blocks(md, "commonmark")
    assert len(cm) == 1
    assert all(x in cm[0].content for x in ("item one", "item two", "item three"))
    assert [m.id for m in cm[0].markers] == ["mylist"]


def test_commonmark_blank_line_fence_is_one_block():
    md = "```\ncode line 1\n\ncode line 2\n```\n<!-- stay:fence -->\n"
    # baseline: the internal blank line splits the fence into >1 block
    assert len(_content_blocks(md, "blank-line")) > 1
    # commonmark: the whole fence is one block carrying the stay
    cm = _content_blocks(md, "commonmark")
    assert len(cm) == 1
    assert "code line 1" in cm[0].content and "code line 2" in cm[0].content
    assert [m.id for m in cm[0].markers] == ["fence"]


def test_commonmark_blockquote_with_blank_is_one_block():
    md = "> quoted line 1\n>\n> quoted line 2\n<!-- stay:bq -->\n"
    cm = _content_blocks(md, "commonmark")
    assert len(cm) == 1
    assert [m.id for m in cm[0].markers] == ["bq"]


def test_commonmark_loose_list_lint_clean_with_hash():
    body = "- item one\n\n- item two\n\n- item three"
    h = L.body_hash(body, 4)
    md = f"{body}\n<!-- stay:mylist hash=sha256:{h} -->\n"
    _, findings = L.lint_document(md, mode="commonmark")
    # A loose list is §5.4 case 2, so the §13 subset advisory is expected here and
    # is the only finding: the whole-list hash matches, so nothing drifted.
    assert codes(findings) == ["OUTSIDE_SUBSET"], codes(findings)


def test_commonmark_agrees_with_blank_line_on_simple_doc():
    # No loose lists / blank-line fences -> both modes produce identical blocks.
    md = "Para one.\n<!-- stay:a -->\n\nPara two.\n<!-- stay:b -->\n"
    shape = lambda mode: [
        (b.content, [m.id for m in b.markers], b.index)
        for b in L.parse_document(md, mode=mode)
    ]
    assert shape("blank-line") == shape("commonmark")


def test_unknown_mode_rejected():
    try:
        L.parse_document("x\n", mode="bogus")
    except ValueError:
        return
    assert False, "unknown mode must raise ValueError"


# --- COLLECTION_SHRANK: opt-in within-collection loss check (SPEC.md §5.1) -----
# A stay binds the whole table/list, so a dropped row/bullet is normally only a
# non-blocking HASH_DRIFT. check_collections=True turns net item loss into a
# blocking finding; it is off by default so existing callers are unaffected.

_TBL = (
    "| Item | State |\n|------|-------|\n"
    "| auth | done |\n| orders | wip |\n<!-- stay:tbl -->\n"
)
_LST = "- alpha\n- beta\n- gamma\n<!-- stay:lst -->\n"


def test_collection_shrank_table_row_drop():
    after = _TBL.replace("| orders | wip |\n", "")
    on = L.lint_diff(_TBL, after, check_collections=True)
    assert "COLLECTION_SHRANK" in codes(on)
    assert L.has_errors(on)
    # off by default: the same row drop is only a non-blocking hash drift
    off = L.lint_diff(_TBL, after)
    assert "COLLECTION_SHRANK" not in codes(off)
    assert not L.has_errors(off)


def test_collection_shrank_bullet_drop():
    after = _LST.replace("- beta\n", "")
    on = L.lint_diff(_LST, after, check_collections=True)
    assert "COLLECTION_SHRANK" in codes(on)
    assert L.has_errors(on)


def test_collection_shrank_silent_on_inplace_edit_and_growth():
    edited = _TBL.replace("| orders | wip |", "| orders | done |")
    grown = _TBL.replace("| orders | wip |\n", "| orders | wip |\n| billing | todo |\n")
    for after in (edited, grown):
        on = L.lint_diff(_TBL, after, check_collections=True)
        assert "COLLECTION_SHRANK" not in codes(on)
        assert not L.has_errors(on)  # only HASH_DRIFT, a warning


def test_collection_shrank_fires_on_consolidation_known_fp():
    # Merging two rows into one is intended pruning, but a net-count drop trips the
    # check: a documented false positive (churn-driven, like the section catch).
    after = _TBL.replace(
        "| auth | done |\n| orders | wip |\n", "| auth+orders | done |\n"
    )
    assert "COLLECTION_SHRANK" in codes(
        L.lint_diff(_TBL, after, check_collections=True)
    )


def test_collection_shrank_distinct_from_dropped_block():
    # Dropping the whole table removes its stay -> DROPPED_ID (existing rule), not
    # SHRANK (which is specifically "block kept, items lost").
    after = "Some replacement paragraph.\n<!-- stay:other -->\n"
    cs = codes(L.lint_diff(_TBL, after, check_collections=True))
    assert "DROPPED_ID" in cs
    assert "COLLECTION_SHRANK" not in cs


# --- experimental direct list-item identity ---------------------------------


def _child_marker(mid, body):
    return f"<!-- stay:{mid} subhash=sha256:{L.body_hash(body, 12)} -->"


def _child_doc():
    return (
        f"- Ship the linter {_child_marker('a', 'Ship the linter')}\n"
        f"- Document the command {_child_marker('b', 'Document the command')}\n"
        f"- Publish package {_child_marker('c', 'Publish package')}\n"
        "<!-- stay:parent -->\n"
    )


def _child_anchors(md, mode="blank-line"):
    return {a.id: a for a in L._build_child_anchors(md, mode)}.values()


def test_child_parse_and_orphan_warning_are_opt_in():
    md = f"- Alpha {_child_marker('child', 'Alpha')}\n"
    legacy, legacy_findings = L.lint_document(md)
    assert legacy[0].children == [] and legacy_findings == []
    blocks, findings = L.lint_document(md, child_blocks=True)
    assert [c.content for c in blocks[0].children] == ["Alpha"]
    assert [(f.code, f.level) for f in findings] == [("ORPHAN_CHILD", "warn")]


def test_table_rows_are_children_with_canonical_bodies_in_both_modes():
    row_body = r"a\\\|b||tail\\"
    digest = L.body_hash(row_body, 12)
    md = (
        "| one | two | three |\n"
        "|---|---|---|\n"
        rf"| a\|b | | tail\<!-- stay:r1 subhash=sha256:{digest} --> |"
        "\n"
        "<!-- stay:table -->\n"
    )
    for mode in ("blank-line", "commonmark"):
        blocks, findings = L.lint_document(md, mode=mode, child_blocks=True)
        rows = [child for child in blocks[0].children if child.kind == "row"]
        assert [(row.ordinal, row.content) for row in rows] == [(1, row_body)]
        assert [marker.id for marker in rows[0].markers] == ["r1"]
        assert findings == []


def test_empty_table_row_body_still_checks_subhash_drift():
    md = (
        "| h |\n"
        "|---|\n"
        "|<!-- stay:r subhash=sha256:dead -->|\n"
        "<!-- stay:table -->\n"
    )
    blocks, findings = L.lint_document(md, child_blocks=True)
    assert [(child.kind, child.content) for child in blocks[0].children] == [
        ("row", "")
    ]
    drift = [finding for finding in findings if finding.code == "HASH_DRIFT"]
    assert [(finding.id, "sha256:e3b0" in finding.message) for finding in drift] == [
        ("r", True)
    ]


def test_table_row_scan_accepts_ragged_rows_and_refuses_unsafe_candidates():
    ragged = (
        "| h1 | h2 |\n|---|---|\n"
        "| one | two | three<!-- stay:r subhash=bogus --> |\n"
        "<!-- stay:t -->\n"
    )
    rows = L.parse_document(ragged, child_blocks=True)[0].children
    assert [(row.kind, row.content) for row in rows] == [("row", "one|two|three")]

    opaque = (
        "| h |\n|---|\n"
        '| a\\<!-- stay:r subhash=bogus x-note="|" -->|\n'
        "<!-- stay:t -->\n"
    )
    opaque_row = L.parse_document(opaque, child_blocks=True)[0].children[0]
    assert opaque_row.content == "a\\\\"
    assert [marker.id for marker in opaque_row.markers] == ["r"]

    refused = [
        "| h |\n|---|\n| ok<!-- stay:r subhash=bogus --> |\nnot a row\n",
        "| h |\n|---<!-- stay:d -->|\n| ok<!-- stay:r subhash=bogus --> |\n",
        (
            "| h |\n|---|\n| one<!-- stay:r1 subhash=bogus --> |\n"
            "<!-- stay:split -->\n| h |\n|---|\n"
            "| two<!-- stay:r2 subhash=bogus --> |\n"
        ),
        (
            "| h |\n|---|\n"
            '| one<!-- stay:r subhash=bogus x-note="two\n'
            'three" --> |\n'
        ),
        (
            "| h |\n|---|\n"
            "| one<!-- stay:outer subhash=bogus x=<!--stay:inner --> |\n"
        ),
    ]
    for md in refused:
        assert not [
            child
            for block in L.parse_document(md, child_blocks=True)
            for child in block.children
            if child.kind == "row"
        ]


def test_table_header_subhash_is_lexical_but_unaddressed():
    md = (
        "| h<!-- stay:header subhash=bogus --> |\n"
        "|---|\n"
        "| body |\n"
        "<!-- stay:table -->\n"
    )
    blocks, findings = L.lint_document(md, child_blocks=True)
    assert [child.content for child in blocks[0].children] == ["body"]
    assert "header" not in L._id_index(blocks)
    assert [(finding.code, finding.id) for finding in findings] == [
        ("CHILD_UNADDRESSED", "header")
    ]
    assert "complete §5.6 scan" in findings[0].message


def test_unaddressed_reason_uses_scan_provenance_not_a_pipe_heuristic():
    nested = (
        "- outer\n"
        "  - nested text | still a list <!-- stay:kid subhash=bogus -->\n"
        "<!-- stay:parent -->\n"
    )
    nested_finding = next(
        finding
        for finding in L.lint_document(nested, mode="commonmark", child_blocks=True)[1]
        if finding.code == "CHILD_UNADDRESSED"
    )
    assert "nested items" in nested_finding.message

    refused = (
        "| h |\n|---|\n"
        "not a row <!-- stay:kid subhash=bogus -->\n"
        "<!-- stay:parent -->\n"
    )
    refused_finding = next(
        finding
        for finding in L.lint_document(refused, child_blocks=True)[1]
        if finding.code == "CHILD_UNADDRESSED"
    )
    assert "complete §5.6 scan" in refused_finding.message

    delimiter = (
        "| h |\n"
        "|---<!-- stay:kid subhash=bogus -->|\n"
        "| body |\n"
        "<!-- stay:parent -->\n"
    )
    delimiter_finding = next(
        finding
        for finding in L.lint_document(delimiter, child_blocks=True)[1]
        if finding.code == "CHILD_UNADDRESSED"
    )
    assert "complete §5.6 scan" in delimiter_finding.message

    prose = (
        "| prose |\n"
        "| also prose <!-- stay:kid subhash=bogus --> |\n"
        "<!-- stay:parent -->\n"
    )
    prose_finding = next(
        finding
        for finding in L.lint_document(prose, child_blocks=True)[1]
        if finding.code == "CHILD_UNADDRESSED"
    )
    assert "complete §5.6 scan" not in prose_finding.message


def test_list_and_row_children_keep_separate_ordinals_and_ownership():
    md = (
        "- item\n"
        "  | h |\n"
        "  |---|\n"
        "  | value<!-- stay:row subhash=bogus --> |\n"
        "<!-- stay:parent -->\n"
    )
    block = L.parse_document(md, mode="commonmark", child_blocks=True)[0]
    assert [(child.kind, child.ordinal) for child in block.children] == [
        ("list", 1),
        ("row", 1),
    ]
    row = next(child for child in block.children if child.kind == "row")
    assert [marker.id for marker in row.markers] == ["row"]
    list_child = next(child for child in block.children if child.kind == "list")
    assert list_child.markers == []


def test_row_anchors_use_row_ordinals_and_row_sibling_context_only():
    md = (
        "- list one <!-- stay:l1 subhash=bogus -->\n"
        "- list two <!-- stay:l2 subhash=bogus -->\n"
        "  | h |\n"
        "  |---|\n"
        "  | row one<!-- stay:r1 subhash=bogus --> |\n"
        "  | row two<!-- stay:r2 subhash=bogus --> |\n"
        "<!-- stay:p -->\n"
    )
    anchors = {anchor.id: anchor for anchor in L._build_child_anchors(md, "commonmark")}
    assert [(anchors[mid].kind, anchors[mid].ordinal) for mid in ("l1", "l2")] == [
        ("list", 1),
        ("list", 2),
    ]
    assert [(anchors[mid].kind, anchors[mid].ordinal) for mid in ("r1", "r2")] == [
        ("row", 1),
        ("row", 2),
    ]
    assert anchors["r1"].prefix == ""
    assert anchors["r1"].suffix == "row two"
    assert anchors["r2"].prefix == "row one"
    assert anchors["r2"].suffix == ""


def test_markerless_row_recovers_by_parent_hash_and_document_hash():
    row_marker = _child_marker("r", "Move row")
    table = (
        "| h |\n"
        "|---|\n"
        f"| Move row{row_marker} |\n"
        "| Keep row<!-- stay:k subhash=bogus --> |\n"
    )
    parent_hash = L.body_hash(L.parse_document(table, child_blocks=True)[0].content, 12)
    before = table + f"<!-- stay:p hash=sha256:{parent_hash} -->\n"
    after = before.replace(row_marker, "")
    anchor = next(
        anchor
        for anchor in L._build_child_anchors(before, "blank-line")
        if anchor.id == "r"
    )
    assert L._resolve_children([anchor], after, "blank-line")["r"][0] == "parent-hash"

    first = "| h |\n|---|\n" f"| Move row{row_marker} |\n" "<!-- stay:p1 -->\n"
    second = (
        "| h |\n|---|\n"
        "| Stable<!-- stay:s subhash=bogus --> |\n"
        "<!-- stay:p2 -->\n"
    )
    before_move = first + "\n" + second
    moved_line = f"| Move row{row_marker} |"
    after_move = before_move.replace(moved_line + "\n", "", 1).replace(
        "| Stable<!-- stay:s subhash=bogus --> |\n",
        "| Stable<!-- stay:s subhash=bogus --> |\n| Move row |\n",
        1,
    )
    anchor = next(
        anchor
        for anchor in L._build_child_anchors(before_move, "blank-line")
        if anchor.id == "r"
    )
    assert (
        L._resolve_children([anchor], after_move, "blank-line")["r"][0]
        == "document-hash"
    )


def test_row_quote_candidates_exclude_overlapping_list_children(monkeypatch):
    marker = _child_marker("r", "target original")
    before = (
        "- outer\n"
        "  | h |\n"
        "  |---|\n"
        f"  | target original{marker} |\n"
        "<!-- stay:p -->\n"
    )
    after = before.replace(f"target original{marker}", "target revised")
    anchor = next(
        anchor
        for anchor in L._build_child_anchors(before, "commonmark")
        if anchor.id == "r"
    )
    calls = []
    original = L._best_match

    def record_candidates(quote, prefix, suffix, candidates):
        calls.append(list(candidates))
        return original(quote, prefix, suffix, candidates)

    monkeypatch.setattr(L, "_best_match", record_candidates)
    assert L._resolve_children([anchor], after, "commonmark")["r"][0] == "quote"
    assert calls == [["target revised"]]


def test_child_boundaries_agree_inside_restricted_profile_and_fail_closed_outside():
    inside = "1. Alpha\n2. Beta\n"
    blank = L.parse_document(inside, child_blocks=True)
    common = L.parse_document(inside, mode="commonmark", child_blocks=True)
    assert [c.content for c in blank[0].children] == ["Alpha", "Beta"]
    assert [c.content for c in common[0].children] == ["Alpha", "Beta"]
    multiline = "- Alpha\n  continuation\n- Beta\n"
    assert [
        c.content for c in L.parse_document(multiline, child_blocks=True)[0].children
    ] == [
        c.content
        for c in L.parse_document(multiline, mode="commonmark", child_blocks=True)[
            0
        ].children
    ]
    lazy = "- Alpha\nlazy continuation\n- Beta\n"
    assert L.parse_document(lazy, child_blocks=True)[0].children == []
    loose = "- Alpha\n\n- Beta\n"
    assert all(not b.children for b in L.parse_document(loose, child_blocks=True))
    # SPEC.md §5.5: a nested list belongs to its ancestor item's body, so it is
    # never a sibling child. The restricted profile used to accept "  - Nested"
    # as an item of its own, which shifted every later ordinal away from what
    # CommonMark reports for the same document.
    nested = "- Alpha\n  - Nested\n- Beta\n"
    assert L.parse_document(nested, child_blocks=True)[0].children == []
    assert [
        c.content
        for c in L.parse_document(nested, mode="commonmark", child_blocks=True)[
            0
        ].children
    ] == ["Alpha\n- Nested", "Beta"]


def test_child_drop_blocks_but_markerless_reword_recovers():
    before = _child_doc()
    dropped = (
        "\n".join(
            line for line in before.splitlines() if not line.startswith("- Document")
        )
        + "\n"
    )
    assert "CHILD_DROPPED" in codes(L.lint_diff(before, dropped, child_blocks=True))
    reworded = (
        "\n".join(
            "- Document the CLI clearly" if line.startswith("- Document") else line
            for line in before.splitlines()
        )
        + "\n"
    )
    assert "CHILD_DROPPED" not in codes(
        L.lint_diff(before, reworded, child_blocks=True)
    )


def test_child_quote_context_can_separate_original_duplicate_hashes():
    before = (
        f"- Alpha {_child_marker('a', 'Alpha')}\n"
        f"- Shared task {_child_marker('s1', 'Shared task')}\n"
        f"- Beta {_child_marker('b', 'Beta')}\n"
        f"- Shared task {_child_marker('s2', 'Shared task')}\n"
        f"- Gamma {_child_marker('g', 'Gamma')}\n"
        "<!-- stay:parent -->\n"
    )
    after = (
        "- Alpha\n"
        "- Shared task revised\n"
        "- Beta\n"
        "- Shared task revised\n"
        "- Gamma\n"
        "<!-- stay:parent -->\n"
    )
    anchors = [
        anchor for anchor in _child_anchors(before) if anchor.quote == "Shared task"
    ]
    assert [anchor.sibling_hash_count for anchor in anchors] == [2, 2]

    resolved = L._resolve_children(anchors, after, "blank-line")
    assert [resolved[anchor.id] for anchor in anchors] == [
        ("quote", 1),
        ("quote", 3),
    ]


def test_child_duplicate_history_still_blocks_exact_hash_tiers():
    before = (
        "- Alpha\n"
        f"- Shared task {_child_marker('s1', 'Shared task')}\n"
        "- Beta\n"
        "- Shared task\n"
        "- Gamma\n"
        "<!-- stay:parent -->\n"
    )
    after = (
        "- Alpha\n"
        "- Shared task\n"
        "- Beta\n"
        "- Shared task revised\n"
        "- Gamma\n"
        "<!-- stay:parent -->\n"
    )
    anchors = [
        anchor for anchor in _child_anchors(before) if anchor.quote == "Shared task"
    ]
    assert len(anchors) == 1
    assert anchors[0].sibling_hash_count == 2
    assert anchors[0].document_hash_count == 2
    current_children = [
        child
        for block in L.parse_document(after, child_blocks=True)
        for child in block.children
    ]
    current_exact = sum(
        L.body_hash(child.content) == anchors[0].hash for child in current_children
    )
    assert current_exact == 1

    resolved = L._resolve_children(anchors, after, "blank-line")
    assert resolved[anchors[0].id] == ("quote", 1)


def test_child_surviving_marker_precedes_parent_hash_ordinal():
    before = _child_doc()
    lines = before.splitlines()
    marker_a = lines[0].split(" <!--", 1)[1]
    marker_b = lines[1].split(" <!--", 1)[1]
    after = "\n".join(
        [
            f"- Ship the linter <!--{marker_b}",
            f"- Document the command <!--{marker_a}",
            lines[2],
            lines[3],
            "",
        ]
    )
    findings = L.lint_diff(before, after, child_blocks=True)
    assert "CHILD_DROPPED" not in codes(findings)


def test_child_surviving_marker_outlives_an_unresolvable_parent():
    """The parent's block-level marker is a standalone line an edit drops
    easily, while child markers ride inline in the bullet text being rewritten.
    A failed inference about the container must not discard stored child ids."""

    before = _child_doc()
    after = (
        "\n".join(
            line for line in before.splitlines() if line != "<!-- stay:parent -->"
        )
        .replace("Ship the linter", "Roll out the ingestion pipeline")
        .replace("Document the command", "Smoke-test downstream consumers")
        .replace("Publish package", "Cut the release candidate")
        + "\n"
    )
    resolved = L._resolve_children(_child_anchors(before), after, "blank-line")
    assert [resolved[cid][0] for cid in ("a", "b", "c")] == ["marker"] * 3


def test_child_near_duplicate_parent_cannot_capture_a_deleted_sibling_list():
    """Exclusive assignment: the surviving list claims its own block by exact
    hash, so the deleted near-duplicate cannot quote-match onto it and drag its
    children along."""

    before = (
        f"- Deploy alpha service {_child_marker('a1', 'Deploy alpha service')}\n"
        f"- Verify alpha service {_child_marker('a2', 'Verify alpha service')}\n"
        "<!-- stay:pa -->\n\n"
        "Interlude.\n<!-- stay:mid -->\n\n"
        f"- Deploy beta service {_child_marker('b1', 'Deploy beta service')}\n"
        f"- Verify beta service {_child_marker('b2', 'Verify beta service')}\n"
        "<!-- stay:pb -->\n"
    )
    after = "Interlude.\n\n- Deploy beta service\n- Verify beta service\n"
    resolved = L._resolve_children(_child_anchors(before), after, "blank-line")
    assert [resolved[cid][0] for cid in ("a1", "a2")] == ["detached", "detached"]


def test_child_same_tier_contest_is_order_invariant_and_goes_to_neither():
    digest = L.body_hash(L.child_body("- Alpha"), 12)
    before = (
        f"- Alpha <!-- stay:a1 subhash=sha256:{digest} -->"
        f" <!-- stay:a2 subhash=sha256:{digest} -->\n"
        "- Beta\n<!-- stay:parent -->\n"
    )
    after = before.replace(f" <!-- stay:a1 subhash=sha256:{digest} -->", "").replace(
        f" <!-- stay:a2 subhash=sha256:{digest} -->", ""
    )
    anchors = L._build_child_anchors(before, "blank-line")
    forward = L._resolve_children(anchors, after, "blank-line")
    reverse = L._resolve_children(list(reversed(anchors)), after, "blank-line")
    for result in (forward, reverse):
        assert result["a1"] == ("detached", None)
        assert result["a2"] == ("detached", None)


def test_child_parent_quote_contest_goes_to_neither_in_both_orders():
    before = (
        f"- Deploy alpha service {_child_marker('a', 'Deploy alpha service')}\n"
        f"- Tail alpha {_child_marker('at', 'Tail alpha')}\n"
        "<!-- stay:pa -->\n\n"
        "Interlude.\n<!-- stay:mid -->\n\n"
        f"- Deploy beta service {_child_marker('b', 'Deploy beta service')}\n"
        f"- Tail beta {_child_marker('bt', 'Tail beta')}\n"
        "<!-- stay:pb -->\n"
    )
    after = "Interlude.\n\n- Deploy shared service\n- Tail shared\n"
    anchors = L._build_child_anchors(before, "blank-line")
    forward = L._resolve_children(anchors, after, "blank-line")
    reverse = L._resolve_children(list(reversed(anchors)), after, "blank-line")
    for result in (forward, reverse):
        assert result["a"] == ("detached", None)
        assert result["b"] == ("detached", None)


def test_child_parent_hash_contest_goes_to_neither_in_both_orders():
    before = (
        f"- Deploy shared service {_child_marker('a', 'Deploy shared service')}\n"
        f"- Tail shared {_child_marker('at', 'Tail shared')}\n"
        "<!-- stay:pa -->\n\n"
        "Interlude.\n<!-- stay:mid -->\n\n"
        f"- Deploy shared service {_child_marker('b', 'Deploy shared service')}\n"
        f"- Tail shared {_child_marker('bt', 'Tail shared')}\n"
        "<!-- stay:pb -->\n"
    )
    after = (
        "Interlude.\n<!-- stay:mid -->\n\n" "- Deploy shared service\n- Tail shared\n"
    )
    anchors = L._build_child_anchors(before, "blank-line")
    blocks = [
        block
        for block in L.parse_document(after, child_blocks=True)
        if block.index >= 0
    ]
    for ordered in (anchors, list(reversed(anchors))):
        parents = L._resolve_parents(ordered, blocks)
        assert "pa" not in parents
        assert "pb" not in parents


def test_child_markerless_cross_parent_move_uses_document_hash():
    before = (
        f"- Alpha {_child_marker('a', 'Alpha')}\n"
        f"- Move me {_child_marker('move', 'Move me')}\n"
        "<!-- stay:p1 -->\n\nInterlude.\n\n"
        f"- Gamma {_child_marker('g', 'Gamma')}\n"
        f"- Delta {_child_marker('d', 'Delta')}\n"
        "<!-- stay:p2 -->\n"
    )
    moved = next(line for line in before.splitlines() if line.startswith("- Move me"))
    lines = [line for line in before.splitlines() if line != moved]
    at = next(i for i, line in enumerate(lines) if line.startswith("- Delta")) + 1
    lines.insert(at, "- Move me")
    findings = L.lint_diff(before, "\n".join(lines) + "\n", child_blocks=True)
    assert not [f for f in findings if f.code == "CHILD_DROPPED" and f.id == "move"]


def test_child_demoted_to_a_nested_item_detaches_rather_than_moving():
    """SPEC.md §5.5: a `subhash` marker inside a nested item is nobody's stay.

    The marker survives the edit, so nothing here is a dropped marker; what is
    gone is the id's ability to address anything. The ladder must not recover it
    from weaker evidence, because the quote tier lands it on the *enclosing*
    direct item and the loss goes unreported. Alpha deliberately carries no
    child stay of its own: that is what leaves it unclaimed and reachable, and
    a shape where every sibling is stamped hides the defect.
    """
    before = (
        "- Alpha\n" f"- Beta {_child_marker('b', 'Beta')}\n" "<!-- stay:parent -->\n"
    )
    beta = next(line for line in before.splitlines() if line.startswith("- Beta"))
    after = before.replace(beta + "\n", "  " + beta + "\n", 1)
    resolved = L._resolve_children(
        L._build_child_anchors(before, "commonmark"), after, "commonmark"
    )
    assert resolved["b"] == ("detached", None)
    findings = L.lint_diff(before, after, child_blocks=True, mode="commonmark")
    assert "b" in [f.id for f in findings if f.code == "CHILD_DROPPED"]
    _, after_findings = L.lint_document(after, mode="commonmark", child_blocks=True)
    assert "b" in [f.id for f in after_findings if f.code == "CHILD_UNADDRESSED"]


def test_child_nested_copy_does_not_detach_the_marker_that_never_moved():
    """The unaddressed gate is about an id with nowhere to be, not an id with a
    stray copy. Paste a stayed bullet into a nested position elsewhere and the
    original marker is still exactly where it was, doing its job; the copy is a
    §7 duplicate for the linter to report. Detaching there would lose an anchor
    that never moved, which is the over-broad reading of §5.5 rule 2.
    """
    stayed = f"- Beta {_child_marker('b', 'Beta')}"
    before = (
        f"- Alpha\n{stayed}\n<!-- stay:p1 -->\n\nInterlude.\n\n"
        "- Gamma\n<!-- stay:p2 -->\n"
    )
    after = before.replace(
        "- Gamma\n<!-- stay:p2 -->", f"- Gamma\n  {stayed}\n<!-- stay:p2 -->", 1
    )
    resolved = L._resolve_children(
        L._build_child_anchors(before, "commonmark"), after, "commonmark"
    )
    assert resolved["b"] == ("marker", 1)
    _, after_findings = L.lint_document(after, mode="commonmark", child_blocks=True)
    codes = {f.code for f in after_findings if f.id == "b"}
    assert "DUPLICATE_ID" in codes


def test_child_identical_sibling_loss_detaches_safely():
    before = (
        f"- Done {_child_marker('d1', 'Done')}\n"
        f"- Done {_child_marker('d2', 'Done')}\n"
        f"- Pending {_child_marker('p', 'Pending')}\n"
        "<!-- stay:parent -->\n"
    )
    first = before.splitlines()[0]
    after = before.replace(first + "\n", "", 1)
    dropped = [
        f.id
        for f in L.lint_diff(before, after, child_blocks=True)
        if f.code == "CHILD_DROPPED"
    ]
    assert "d1" in dropped


# --- drift routing: quiet human render, intact structured channel ------------
# HASH_DRIFT is load-bearing in the structured channel (the RAG chunker treats it
# as fatal; the Plate contrast counts it) but noise in the default human render
# (it never blocks, only ever says "you edited things"). The render hides it by
# default behind --show-drift; the finding, its warn level, and --json are
# untouched.

import contextlib  # noqa: E402
import io  # noqa: E402
import os  # noqa: E402
import tempfile  # noqa: E402


def _tmp_md(text):
    fh = tempfile.NamedTemporaryFile("w", suffix=".md", delete=False, encoding="utf-8")
    fh.write(text)
    fh.close()
    return fh.name


def _run_cli(argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = L.main(argv)
    return rc, buf.getvalue()


def test_render_hides_drift_by_default_lists_with_flag():
    _, findings = L.lint_document("Edited.\n<!-- stay:z9 hash=sha256:dead -->\n")
    assert codes(findings) == ["HASH_DRIFT"]
    hidden = L.render_text("doc", findings)  # default show_drift=False
    shown = L.render_text("doc", findings, show_drift=True)
    assert "HASH_DRIFT" not in hidden  # drift line dropped
    assert "hash-drift" in hidden and "--show-drift" in hidden  # collapsed receipt
    assert "HASH_DRIFT" in shown  # listed on request
    assert "hidden (--show-drift" not in shown  # no collapsed line when shown
    # summary counts the real totals either way (drift is still a warn that happened)
    assert "0 error, 1 warn, 0 info" in hidden
    assert "0 error, 1 warn, 0 info" in shown


def test_render_keeps_real_findings_and_counts_with_mixed_set():
    md = (
        "Edited.\n<!-- stay:z9 hash=sha256:dead -->\n\n"
        "A para.\n<!-- stay:note=hello -->\n"
    )
    _, findings = L.lint_document(md)
    assert sorted(codes(findings)) == [
        "HASH_DRIFT", "MALFORMED_MARKER", "OUTSIDE_SUBSET"
    ]
    hidden = L.render_text("doc", findings)
    shown = L.render_text("doc", findings, show_drift=True)
    for r in (hidden, shown):
        assert "1 error, 1 warn, 1 info" in r  # counts unchanged
        assert "MALFORMED_MARKER" in r  # the actionable line stays
        assert "OUTSIDE_SUBSET" in r  # malformed comment remains content
    assert "HASH_DRIFT" not in hidden
    assert "1 hash-drift finding hidden" in hidden  # singular, collapsed


def test_json_byte_identical_with_and_without_show_drift():
    path = _tmp_md("Edited.\n<!-- stay:z9 hash=sha256:dead -->\n")
    try:
        _, a = _run_cli(["--json", path])
        _, b = _run_cli(["--json", "--show-drift", path])
        assert a == b  # structured channel untouched
        assert "HASH_DRIFT" in a  # drift still carried in --json
    finally:
        os.unlink(path)


def test_before_diff_text_path_hides_drift_by_default():
    before = _tmp_md("Alpha content.\n<!-- stay:aaa -->\n")
    after = _tmp_md("Alpha content, now revised.\n<!-- stay:aaa -->\n")
    try:
        _, hidden = _run_cli(["--before", before, after])
        _, shown = _run_cli(["--show-drift", "--before", before, after])
        assert "HASH_DRIFT" not in hidden
        assert "hash-drift" in hidden  # collapsed line on the diff path
        assert "HASH_DRIFT" in shown
    finally:
        os.unlink(before)
        os.unlink(after)


def test_hash_drift_stays_warn_in_return_tuples_guardrail():
    # Guardrail (the invariant the whole change hinges on): the structured channel
    # must keep HASH_DRIFT at warn, because the RAG chunker's fatal check and the
    # Plate contrast both read these tuples, not the printed text. Mirror in
    # impl/py/tests/test_unit.py for the packaged markstay.lint API the chunker imports.
    _, doc = L.lint_document("Edited.\n<!-- stay:z9 hash=sha256:dead -->\n")
    doc_drift = [f for f in doc if f.code == "HASH_DRIFT"]
    assert doc_drift and all(f.level == "warn" for f in doc_drift)
    diff = L.lint_diff(
        "Alpha.\n<!-- stay:a -->\n", "Alpha, revised.\n<!-- stay:a -->\n"
    )
    diff_drift = [f for f in diff if f.code == "HASH_DRIFT"]
    assert diff_drift and all(f.level == "warn" for f in diff_drift)


# --- leading YAML frontmatter is metadata, not a block (SPEC.md §5) -----------

_FM_DOC = "---\nstatus: active\nowner: tim\n---\n\n# Heading\n\nBody para.\n"


def _blocks(md, mode):
    return [(b.index, b.line, b.content) for b in L.parse_document(md, mode=mode)]


def test_frontmatter_is_not_a_block():
    blocks = L.parse_document(_FM_DOC)
    assert [b.content for b in blocks] == ["# Heading", "Body para."], [
        b.content for b in blocks
    ]
    assert not any("status: active" in b.content for b in blocks)


def test_frontmatter_does_not_shift_line_numbers():
    # blanking is line-for-line, so reported lines stay true to the source
    assert [(b.index, b.line) for b in L.parse_document(_FM_DOC)] == [(0, 6), (1, 8)]


def test_frontmatter_segmenters_agree():
    """The regression this whole change exists for: before the frontmatter skip,
    this document (no lists, no fences, squarely inside SPEC.md §5's stated
    agreement subset) segmented as 3 blocks under blank-line and 4 under
    CommonMark, because CommonMark reads the closing --- as a setext underline."""
    assert _blocks(_FM_DOC, "blank-line") == _blocks(_FM_DOC, "commonmark")


def test_frontmatter_metadata_edit_does_not_drift_a_hash():
    """A metadata-only edit must not read as a content edit. This is the noise the
    dogfood hit: flipping `status:` used to drift the frontmatter block's hash."""
    before = [L.body_hash(b.content) for b in L.parse_document(_FM_DOC)]
    after = [
        L.body_hash(b.content)
        for b in L.parse_document(_FM_DOC.replace("status: active", "status: complete"))
    ]
    assert before == after


def test_frontmatter_with_no_closing_fence_is_a_thematic_break():
    md = "---\n\n# Heading\n\nBody para.\n"
    assert [b.content for b in L.parse_document(md)] == [
        "---",
        "# Heading",
        "Body para.",
    ]


def test_frontmatter_does_not_swallow_two_thematic_breaks():
    """Regression, found by external review: a doc opening with a horizontal rule
    and containing another one later must not have everything between them read as
    frontmatter. The naive first-closing-fence rule silently ate `Intro.`"""
    md = "---\n\nIntro paragraph.\n\n---\n\nBody.\n"
    contents = [b.content for b in L.parse_document(md)]
    assert "Intro paragraph." in contents, contents
    assert contents == ["---", "Intro paragraph.", "---", "Body."], contents


def test_frontmatter_does_not_swallow_a_setext_heading():
    """Regression, found by external review: `---` / `Title` / `---` is a thematic
    break followed by a setext H2, not frontmatter with the payload `Title`. The
    payload has to look like YAML before the span is treated as metadata."""
    md = "---\nTitle\n---\n\nBody.\n"
    contents = [b.content for b in L.parse_document(md)]
    assert "Title" in "\n".join(contents), contents


def test_frontmatter_payload_with_a_blank_line_is_not_skipped():
    """Fails towards ordinary Markdown: not skipping is a hash-drift warning, while
    over-skipping silently destroys content."""
    md = "---\nstatus: active\n\nowner: tim\n---\n\nBody.\n"
    assert any("status: active" in b.content for b in L.parse_document(md))


def test_frontmatter_yamlish_forms_are_recognized():
    for payload in ("status: active", "- one\n- two", "empty:", "nested:\n  a: 1"):
        md = f"---\n{payload}\n---\n\nBody.\n"
        assert [b.content for b in L.parse_document(md)] == ["Body."], payload


def test_frontmatter_does_not_swallow_an_atx_heading():
    """Regression, found by external review: a YAML comment and an ATX heading are
    byte-identical, so `#` cannot be the evidence that a span is frontmatter. The
    cost is that comment-only frontmatter is not skipped, which is the safe
    direction: a stray hash-drift warning beats a destroyed heading."""
    md = "---\n# Heading\n---\nBody.\n"
    assert "# Heading" in "\n".join(b.content for b in L.parse_document(md))
    md_comment_only = "---\n# just a comment\n---\n\nBody.\n"
    assert "# just a comment" in "\n".join(
        b.content for b in L.parse_document(md_comment_only)
    )


def test_frontmatter_empty_payload_is_not_skipped():
    md = "---\n---\n\nBody.\n"
    assert any("---" in b.content for b in L.parse_document(md))


def test_frontmatter_closing_fence_tolerates_trailing_whitespace():
    md = "---\nkey: v\n---   \n\nBody.\n"
    assert [b.content for b in L.parse_document(md)] == ["Body."]


def test_frontmatter_crlf_normalizes_before_detection():
    md = "---\r\nkey: v\r\n---\r\n\r\n# H\r\n\r\nBody.\r\n"
    assert [b.content for b in L.parse_document(md)] == ["# H", "Body."]


def test_frontmatter_yamlish_whitespace_is_ascii_pinned():
    """Cross-language agreement, found by external review of the port: `\\S` means
    three different things in Python, ECMAScript and Rust, so the rule spells the
    ASCII set out. An ASCII control character is not a key start (the span stays
    ordinary Markdown); an exotic non-ASCII space is, exactly as for hashing (§8),
    where NBSP is content rather than whitespace."""
    # not a key start -> not frontmatter -> the span survives as content
    md = "---\n\x1ckey: v\n---\n\nBody.\n"
    assert any("key: v" in b.content for b in L.parse_document(md)), md

    # a key start -> frontmatter -> skipped. Each of these is Unicode whitespace to
    # at least one of the three runtimes and not to the others.
    for ch in ("\xa0", "\x85", "\ufeff"):
        md = f"---\n{ch}key: v\n---\n\nBody.\n"
        assert [b.content for b in L.parse_document(md)] == ["Body."], repr(ch)
        md_item = f"---\n- {ch}\n---\n\nBody.\n"
        assert [b.content for b in L.parse_document(md_item)] == ["Body."], repr(ch)


def test_marker_after_closing_fence_is_an_orphan():
    """The visible consequence for a doc stamped before this change: its
    frontmatter marker now has no block to attach to, and says so loudly."""
    _, findings = L.lint_document("---\nkey: v\n---\n<!-- stay:x -->\n\nBody.\n")
    assert "ORPHAN_MARKER" in codes(findings), codes(findings)


def test_marker_inside_frontmatter_payload_is_dropped():
    """Pins actual behaviour, flagged by external review: a marker *inside* the
    payload is blanked with the rest of the frontmatter and raises nothing. No tool
    puts a marker there (the stamper always writes after the block), so this is
    documented rather than defended. Change this test if that stops being true."""
    _, findings = L.lint_document("---\nkey: v\n<!-- stay:x -->\n---\n\nBody.\n")
    assert codes(findings) == [], codes(findings)


def test_frontmatter_only_at_document_start():
    md = "# Heading\n\n---\ntitle: not frontmatter\n---\n\nBody.\n"
    contents = [b.content for b in L.parse_document(md)]
    assert "title: not frontmatter" in "\n".join(contents), contents


def test_frontmatter_closed_by_yaml_end_marker():
    md = "---\ntitle: t\n...\n\n# Heading\n\nBody.\n"
    assert [b.content for b in L.parse_document(md)] == ["# Heading", "Body."]


def test_frontmatter_absent_document_is_unchanged():
    md = "# Heading\n\nBody para.\n\n- a\n- b\n"
    assert _blocks(md, "blank-line") == _blocks(md, "commonmark")
    assert [b.content for b in L.parse_document(md)] == [
        "# Heading",
        "Body para.",
        "- a\n- b",
    ]


def test_frontmatter_no_blank_line_before_content():
    """A doc with no blank line after the closing fence still splits correctly,
    which a filter-the-chunks-afterwards implementation would get wrong."""
    md = "---\ntitle: t\n---\n# Heading\n\nBody.\n"
    assert [b.content for b in L.parse_document(md)] == ["# Heading", "Body."]
    assert _blocks(md, "blank-line") == _blocks(md, "commonmark")


def test_commonmark_without_the_parser_is_an_error_not_a_traceback():
    """`--commonmark` is the one optional dependency. Missing it must exit 2 with
    an install line, not surface a ModuleNotFoundError out of the segmenter."""
    import contextlib
    import importlib.util
    import io
    import tempfile

    with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as fh:
        fh.write("Body.\n<!-- stay:a1b2 -->\n")
        path = fh.name

    real = importlib.util.find_spec
    importlib.util.find_spec = lambda name, *a, **k: (
        None if name == "markdown_it" else real(name, *a, **k)
    )
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            rc = L.main(["--commonmark", path])
    finally:
        importlib.util.find_spec = real

    assert rc == 2, rc
    assert "markdown-it-py" in err.getvalue(), err.getvalue()


def test_child_anchor_context_is_windowed_to_48_characters():
    """SPEC.md §9's 48-character limit, applied to the child ladder as well.

    The child path has NO conformance vectors (it is opt-in and its spec text is
    unmerged), so this is the only thing standing between it and the storage
    asymmetry corrected in the block path: whole neighbours stored against a
    candidate side windowed at match time, which caps a long neighbour's
    contribution well under the 0.05 §9 allows it."""
    long_sibling = (
        "Ship the linter and then "
        + "wait for the release train " * 3
        + "wait for the release train"
    )
    long_before = "A preceding block far longer than forty-eight characters, easily."
    long_after = "A following block also far longer than forty-eight characters here."
    md = (
        f"{long_before}\n\n"
        f"- {long_sibling} {_child_marker('a', long_sibling)}\n"
        f"- Document the command {_child_marker('b', 'Document the command')}\n\n"
        f"{long_after}\n"
    )
    anchors = {a.id: a for a in L._build_child_anchors(md, "blank-line")}
    b = anchors["b"]
    # Compare against the parsed sibling body, not the raw source line: the child
    # content is what the segmenter produced (markers stripped, edges trimmed).
    sibling_body = anchors["a"].quote
    assert len(b.prefix) == 48 and b.prefix == sibling_body[-48:]
    assert len(b.parent_prefix) == 48 and b.parent_prefix == long_before[-48:]
    assert len(b.parent_suffix) == 48 and b.parent_suffix == long_after[:48]
    # A short neighbour is stored whole: 48 is a cap, not a fixed width.
    assert anchors["a"].suffix == "Document the command"


def test_context_bonus_windows_an_over_long_stored_selector():
    """The match-time half of the same limit. A selector carrying more than §9
    allows (built by a pre-fix tool, or assembled by a consumer) must score the
    same as the conforming selector it windows down to, rather than losing bonus
    to the asymmetry."""
    long_prev = "Operators can override these retry defaults on a per-partner basis."
    candidates = [long_prev, "the target block body", "an unrelated block body"]
    over_long, _, _ = L._best_match("the target block body", long_prev, "", candidates)
    windowed_idx, windowed_score, _ = L._best_match(
        "the target block body", long_prev[-48:], "", candidates
    )
    _, over_long_score, _ = L._best_match(
        "the target block body", long_prev, "", candidates
    )
    assert over_long == windowed_idx == 1
    assert over_long_score == windowed_score


# --- heading paths (experimental, not spec behaviour) ---------------------
# Every rule below is a choice rather than a consequence, so each one is pinned
# here: the derivation is the half that would cost real money to change once a
# conformance category exists for it.


def _paths(md, mode="blank-line"):
    """(block content, its heading path) for every content block."""
    blocks = L.parse_document(md, mode=mode)
    return [
        (b.content, p)
        for b, p in zip(blocks, L.heading_paths(md, blocks))
        if b.index >= 0
    ]


def test_heading_path_atx_nests_by_level():
    md = "# Alpha\n\nOne.\n\n## Beta\n\nTwo.\n\n# Gamma\n\nThree.\n"
    assert _paths(md) == [
        ("# Alpha", []),  # a heading is scoped by its parents, not itself
        ("One.", ["Alpha"]),
        ("## Beta", ["Alpha"]),
        ("Two.", ["Alpha", "Beta"]),
        ("# Gamma", []),  # level 1 pops Beta and Alpha both
        ("Three.", ["Gamma"]),
    ]


def test_heading_path_skipped_level_nests_rather_than_replaces():
    md = "# Alpha\n\n### Deep\n\nBody.\n\n## Mid\n\nAfter.\n"
    assert _paths(md) == [
        ("# Alpha", []),
        ("### Deep", ["Alpha"]),
        ("Body.", ["Alpha", "Deep"]),
        ("## Mid", ["Alpha"]),  # level 2 pops the level-3 sibling
        ("After.", ["Alpha", "Mid"]),
    ]


def test_heading_path_atx_closing_hashes_and_empty_title():
    md = "## Alpha ##\n\nOne.\n\n### Beta#\n\nTwo.\n\n#\n\nThree.\n"
    assert _paths(md) == [
        ("## Alpha ##", []),
        ("One.", ["Alpha"]),
        ("### Beta#", ["Alpha"]),  # no space before the hash: not a closer
        ("Two.", ["Alpha", "Beta#"]),
        ("#", []),
        ("Three.", [""]),  # an empty title is still a level
    ]


def test_heading_path_setext():
    md = "Alpha\n=====\n\nOne.\n\nBeta\n----\n\nTwo.\n"
    assert _paths(md) == [
        ("Alpha\n=====", []),
        ("One.", ["Alpha"]),
        ("Beta\n----", ["Alpha"]),  # `-` is level 2, so it nests under Alpha
        ("Two.", ["Alpha", "Beta"]),
    ]


def test_heading_path_setext_needs_a_paragraph_above_it():
    """`---` opening a block is a thematic break, not a heading with no title."""
    md = "One.\n\n---\n\nTwo.\n"
    assert _paths(md) == [("One.", []), ("---", []), ("Two.", [])]


def test_heading_path_glued_heading_scopes_what_follows_not_itself():
    """`# H` with no blank line before the body is one block under blank-line
    segmentation and two under CommonMark (SPEC.md §5.4). The heading is
    recognised either way; what differs is only which block carries the body."""
    md = "# Alpha\nGlued body.\n\nAfter.\n"
    assert _paths(md, "blank-line") == [
        ("# Alpha\nGlued body.", []),
        ("After.", ["Alpha"]),
    ]
    assert _paths(md, "commonmark") == [
        ("# Alpha", []),
        ("Glued body.", ["Alpha"]),
        ("After.", ["Alpha"]),
    ]


def test_heading_path_fenced_code_is_not_a_heading():
    md = "# Alpha\n\n```sh\n# not a heading\n```\n\nBody.\n"
    assert _paths(md) == [
        ("# Alpha", []),
        ("```sh\n# not a heading\n```", ["Alpha"]),
        ("Body.", ["Alpha"]),
    ]


def test_heading_path_fence_state_survives_a_split_fence():
    """Blank-line segmentation cuts a fence containing a blank line into several
    blocks (SPEC.md §5.2's motivating case). Fence state has to carry across the
    boundary or the `#` line inside reads as a section."""
    md = "# Alpha\n\n```sh\necho one\n\n# not a heading\n```\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"], ["Alpha"]]


def test_heading_path_tilde_fence_is_not_closed_by_backticks():
    md = "~~~\n```\n# still code\n~~~\n\nBody.\n"
    assert _paths(md) == [("~~~\n```\n# still code\n~~~", []), ("Body.", [])]


def test_heading_path_blockquote_and_list_headings_do_not_escape():
    md = "# Alpha\n\n> # Quoted\n\n- # Listed\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"], ["Alpha"]]


def test_heading_path_document_with_no_headings():
    md = "One.\n\nTwo.\n\nThree.\n"
    assert [p for _, p in _paths(md)] == [[], [], []]


def test_heading_path_marker_on_the_heading_line():
    md = "## Alpha <!-- stay:h1 -->\n\nBody.\n<!-- stay:b1 -->\n"
    assert _paths(md) == [("## Alpha", []), ("Body.", ["Alpha"])]


def test_heading_path_is_parallel_to_blocks_including_orphans():
    md = "<!-- stay:orphan -->\n\n# Alpha\n\nBody.\n"
    blocks = L.parse_document(md)
    paths = L.heading_paths(md, blocks)
    assert len(paths) == len(blocks)
    assert blocks[0].index == -1 and paths[0] == []


def test_heading_path_indented_code_is_not_a_heading():
    """`Block.content` is whitespace-stripped, so a derivation reading it cannot
    tell `    # deploy` (code) from `# deploy` (a section). Deriving from the
    source lines is what keeps them apart."""
    md = "# Alpha\n\n    # not a heading\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"]]


def test_heading_path_html_block_is_not_a_heading():
    md = "# Alpha\n\n<script>\n# not a heading\n</script>\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"]]


def test_heading_path_html_block_closing_on_a_blank_line():
    """A CommonMark type-6 HTML block runs to the next blank line, which under
    blank-line segmentation is the end of the block anyway."""
    md = "# Alpha\n\n<div>\n# not a heading\n</div>\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"]]


def test_heading_path_link_reference_definition_is_not_a_setext_title():
    md = "# Alpha\n\n[label]: /url\n---\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"]]


def test_heading_path_lazy_continuation_is_not_a_setext_title():
    """`lazy` continues the blockquote's paragraph, so the `---` under it is a
    thematic break rather than a heading called "lazy"."""
    md = "# Alpha\n\n> quote\nlazy\n---\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"]]


def test_heading_path_multi_line_setext_title():
    md = "Alpha\nBeta\n=====\n\nBody.\n"
    assert _paths(md) == [("Alpha\nBeta\n=====", []), ("Body.", ["Alpha Beta"])]


def test_heading_path_backtick_fence_info_string_with_a_backtick():
    """A backtick fence's info string may not contain a backtick, so this line
    opens no fence and the heading under it is real (CommonMark 4.5)."""
    md = "``` bad`info\n\n# Alpha\n\nBody.\n"
    assert [p for _, p in _paths(md)] == [[], [], ["Alpha"]]


def test_heading_path_frontmatter_is_not_a_setext_heading():
    md = "---\ntitle: t\n---\n\n# Alpha\n\nBody.\n"
    assert _paths(md) == [("# Alpha", []), ("Body.", ["Alpha"])]


# The derivation reads SPEC.md §3.3 fence geometry from `_fence_state` rather than
# tracking fences itself. The four tests below pin that single-recogniser property,
# because a second recogniser is what this code shipped with and the two disagreed.


def test_heading_path_marker_line_ending_in_a_fence_run_opens_no_fence():
    """The derivation strips markers per line to keep line numbers stable, so a
    marker followed by a backtick run on the same line used to leave a bare fence
    opener behind and swallow every heading after it. §3.3 reads the raw line, where
    the leading `<!--` is not a fence, and the derivation now reads the same
    geometry."""
    md = (
        "# Alpha\n\n"
        "<!-- stay:AbCdEfGh hash=sha256:0123456789ab -->```\n\n"
        "# Later\n\nBody.\n"
    )
    assert not L.code_lines(md)
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], [], ["Later"]]


def test_heading_path_html_block_closes_on_a_line_inside_a_fence():
    """An open HTML block is tested before the fence mask, so its closer still
    counts when §3.3 calls that line code. Testing the mask first would leave the
    block open to the end of the document, which loses strictly more headings than
    the disagreement it would be avoiding."""
    md = "<script>\n```\n</script>\n```\n\n# Later\n\nBody.\n"
    assert sorted(L.code_lines(md)) == [2, 3, 4]
    assert [p for _, p in _paths(md)] == [[], [], ["Later"]]


def test_heading_path_unclosed_fence_in_an_html_block_masks_to_the_end():
    """§3.3's line scan has no concept of an HTML block, so a fence opened inside
    one is open, and an unclosed fence runs to the end of the document. The
    derivation agrees with it rather than second-guessing it: `# Later` is code, so
    it contributes no heading. Narrower than CommonMark on purpose, and it is the
    price of one recogniser."""
    md = "# Alpha\n\n<script>\n```\n</script>\n\n# Later\n\nBody.\n"
    assert sorted(L.code_lines(md)) == [4, 5, 6, 7, 8, 9, 10]
    assert [p for _, p in _paths(md)] == [[], ["Alpha"], ["Alpha"], ["Alpha"]]


def test_heading_path_a_marker_before_a_fence_run_kills_the_fence_for_both():
    """The defect class rather than the one document. A marker prepended to a fence
    opener leaves a line that §3.3 does not read as a fence, because the raw line
    opens with `<!--`, and the derivation has to reach the same answer or it swallows
    everything under a fence §3.3 says is not there. Run over four opener shapes,
    each with a heading below the run that must survive.

    Appending is the benign direction and is checked alongside: a marker after the
    run leaves a fence both recognisers still see, so the paths must not move at
    all."""
    marker = "<!-- stay:AbCdEfGh hash=sha256:0123456789ab -->"
    openers = ("```", "```sh", "~~~", "   ```")
    for opener in openers:
        md = f"# Alpha\n\n{opener}\n\n# Later\n\nBody.\n"
        assert L.code_lines(md), opener  # the fence is real without a marker
        assert [p for _, p in _paths(md)] == [
            [],
            ["Alpha"],
            ["Alpha"],
            ["Alpha"],
        ], opener  # the run swallows `# Later`, which is what a fence is for

        before = md.replace(opener, marker + opener, 1)
        assert not L.code_lines(before), opener
        assert [p for _, p in _paths(before)] == [[], ["Alpha"], [], ["Later"]], opener

        after = md.replace(opener, opener + marker, 1)
        assert L.code_lines(after) == L.code_lines(md), opener
        assert L._paths_by_line(after) == L._paths_by_line(md), opener


def test_heading_path_a_masked_line_is_not_a_lazy_container_continuation():
    """A masked line resets the open-container state as well as the paragraph, and
    that does real work rather than following from the fence opener having done it
    already: when the opener sits inside an HTML block, the HTML branch consumes it
    and the derivation reaches the interior lines without having seen an opener at
    all.

    Here §3.3 opens a fence on line 2 and closes it on line 5, so the `> quote` on
    line 4 is literal content and opens no blockquote, which leaves `text` / `====`
    outside the fence as a genuine setext H1. Reading line 4 as a container instead
    makes `text` a lazy continuation and loses the heading."""
    md = "<script>\n```\n</script>\n> quote\n```\ntext\n====\n"
    assert sorted(L.code_lines(md)) == [2, 3, 4, 5]
    assert L._paths_by_line(md)[-1] == ["text"]


def test_heading_path_agrees_with_the_code_mask_in_both_directions():
    """The single-recogniser property, over generated fence-edge documents rather
    than hand-written ones.

    The oracle is deliberately not a second copy of the derivation: over a grammar
    with no HTML block, container, setext underline or thematic break, a heading is
    just an ATX line that §3.3 does not call code, so `code_lines` is the only thing
    that can suppress one. Comparing the whole path list catches **both**
    directions, which is the point: a one-directional check that only asks whether a
    code line pushed a heading is blind to the defect this replaced, where a marker
    before a backtick run masked lines §3.3 says are not code at all.

    136 of these 1500 documents disagree with the oracle against the version that
    tracked fences itself, in both directions.
    """
    marker = "<!-- stay:AbCdEfGh hash=sha256:0123456789ab -->"
    frags = (
        "# Alpha",
        "## Beta",
        "### Gamma",
        "Body.",
        "",
        "```",
        "```sh",
        "~~~",
        "   ```",
        "    ```",
        marker + "```",
        "```" + marker,
        marker,
        "````",
        "~~~~",
        "``` bad`info",
    )

    def oracle(md):
        text = L._blank_frontmatter(md.replace("\r\n", "\n").replace("\r", "\n"))
        code = L.code_lines(text)
        stack, out = [], []
        for num, raw in enumerate(text.split("\n"), 1):
            atx = None if num in code else L._ATX_RE.match(L._strip_markers(raw))
            if atx is None:
                out.append([t for _, t in stack])
                continue
            level = len(atx.group("hashes"))
            title = L._ATX_CLOSE_RE.sub("", atx.group("title") or "").strip(" \t")
            while stack and stack[-1][0] >= level:
                stack.pop()
            out.append([t for _, t in stack])
            stack.append((level, title))
        return out

    rng = random.Random(20260829)
    for _ in range(1500):
        md = "\n".join(rng.choice(frags) for _ in range(rng.randint(3, 9))) + "\n"
        assert L._paths_by_line(md) == oracle(md), md


def test_heading_paths_agree_across_modes_inside_the_agreement_subset():
    """SPEC.md §5.4: the two segmenters draw the same boundaries only on the
    subset with a blank line at every boundary and no blank line inside a node.
    Scoped to that subset deliberately, since outside it the block lists differ
    and a path comparison would be comparing different things."""
    md = (
        "# Alpha\n\nOne.\n\n## Beta\n\nTwo.\n\nGamma\n-----\n\nThree.\n\n"
        "```sh\necho hi\n```\n\nFour.\n"
    )
    assert _paths(md, "blank-line") == _paths(md, "commonmark")


def test_canonical_heading_strips_emphasis_and_link_syntax():
    assert L.canonical_heading("**Rollback**") == L.canonical_heading("Rollback")
    assert L.canonical_heading("`api` Reference") == "api reference"
    assert L.canonical_heading("[Deploy](https://example.com/x)") == "deploy"
    assert L.canonical_heading("![Logo](a.png) Deploy") == "logo deploy"
    assert L.canonical_heading("~~Old~~ New") == "old new"
    assert L.canonical_heading("*Rollback*") == L.canonical_heading("_Rollback_")


def test_canonical_heading_keeps_unpaired_punctuation():
    """Only *paired* delimiters come out. Stripping every `*`, backtick and `~`
    collides section titles that differ by literal punctuation, which is worse
    than missing an unpaired delimiter: a glob and a path are real headings."""
    for a, b in (
        ("*.py", ".py"),
        ("operator*", "operator"),
        ("A * B", "A B"),
        ("foo*bar", "foobar"),
        ("~/.config", "/.config"),
    ):
        assert L.canonical_heading(a) != L.canonical_heading(b), a
    assert L.canonical_heading("*.py") == "*.py"


def test_canonical_heading_keeps_intraword_underscores():
    """`_` is only emphasis at a word boundary in CommonMark, and headings in
    this repo are full of `snake_case` identifiers."""
    assert L.canonical_heading("_heading_paths_") == "heading_paths"
    assert L.canonical_heading("Run   sync_corpus.sh\tnow") == "run sync_corpus.sh now"


def test_canonical_heading_folds_ascii_only():
    """SPEC.md §9's fold is ASCII-only so every implementation reproduces it
    without Unicode case data; `Ä` must survive uppercase."""
    assert L.canonical_heading("Ärger UPPER") == "Ärger upper"


# --- SPEC.md §3.3: a fenced code block is content (v1.5) -----------------


def test_code_lines_recognises_the_fences_the_line_rule_can_see():
    cases = [
        ("a\n```\ncode\n```\nb\n", {2, 3, 4}),
        ("a\n~~~\ncode\n~~~\nb\n", {2, 3, 4}),
        ("a\n   ```\ncode\n   ```\nb\n", {2, 3, 4}),  # three spaces still opens
        ("a\n    ```\ncode\n    ```\nb\n", set()),  # four is indented code
        ("a\n\t```\ncode\n\t```\nb\n", set()),  # a tab is not a space
        ("````\n```\ninner\n```\n````\n", {1, 2, 3, 4, 5}),  # longer contains shorter
        ("````\ncode\n```\nrest\n", {1, 2, 3, 4, 5}),  # shorter cannot close longer
        ("```\ncode\n~~~\nrest\n", {1, 2, 3, 4, 5}),  # nor a different character
        ("a\n```\ncode\n", {2, 3, 4}),  # unclosed runs to EOF
        ("```\ncode\n``` \nafter\n", {1, 2, 3}),  # trailing space still closes
        ("```\ncode\n```x\nrest\n", {1, 2, 3, 4, 5}),  # trailing anything else does not
        ("a\n```md `x`\nnope\n", set()),  # backtick in a backtick info string
        ("a\n~~~md `x`\ncode\n~~~\n", {2, 3, 4}),  # but not in a tilde one
        ("> ```\n> code\n> ```\n", set()),  # §3.3's stated limit
    ]
    for md, expected in cases:
        assert L.code_lines(md) == expected, repr(md)


def test_crlf_and_lf_twins_give_the_same_mask():
    lf = "a\n```\ncode\n```\nb\n"
    assert L.code_lines(lf.replace("\n", "\r\n")) == L.code_lines(lf)


def test_a_marker_in_a_fence_identifies_no_block_and_is_hashed_with_it():
    fence = "```md\nThe paragraph.\n<!-- stay:demo hash=sha256:7a9c -->\n```"
    (block,) = L.parse_document(fence + "\n")
    assert block.markers == []
    assert block.content == L.normalize_body(fence)


def test_two_fences_sharing_an_example_id_are_not_a_duplicate():
    md = (
        "```md\n<!-- stay:8f24 hash=sha256:7a9c -->\n```\n\n"
        "```mdx\n{/* stay:8f24 hash=sha256:7a9c */}\n```\n"
    )
    _, findings = L.lint_document(md)
    assert findings == [], codes(findings)


def test_a_marker_in_an_opening_fence_info_string_is_not_a_marker():
    blocks = L.parse_document("Intro.\n\n~~~md <!-- stay:demo -->\ncode\n~~~\n")
    assert [b.markers for b in blocks] == [[], []]


def test_an_inline_code_span_still_carries_a_marker():
    # §3.3 declines inline spans on purpose: a mangled marker a tool can still
    # see beats one that has silently stopped existing.
    (block,) = L.parse_document("A line showing `<!-- stay:demo -->` inline.\n")
    assert [mk.id for mk in block.markers] == ["demo"]


def test_a_fence_only_shifts_the_markers_inside_it():
    body = "Live content."
    md = (
        "```md\n<!-- stay:demo -->\n```\n\n"
        f"{body}\n<!-- stay:demo hash=sha256:{L.body_hash(body, 4)} -->\n"
    )
    _, findings = L.lint_document(md)
    assert findings == [], codes(findings)


def test_the_agreement_subset_ignores_marker_spans():
    """SPEC.md §5.4: marker spans are excluded from both sides of the comparison.

    Counted, they put every stamped document outside the subset: a trailing
    comment interrupts a paragraph in CommonMark while blank-line segmentation
    keeps the run whole, so `Body.` with a marker under it is one run and two
    nodes. The subset would then be empty exactly when the guarantee is wanted.
    """
    stamped = "Body.\n<!-- stay:x hash=sha256:521b25cc4586 -->\n"
    assert L.in_agreement_subset("Body.\n") is True
    assert L.in_agreement_subset(stamped) is True
    # Case 1 of the three §5.4 lists: a block boundary with no blank line at it.
    assert L.in_agreement_subset("# Heading\nBody.\n") is False
    # Case 2: a blank line inside one node, here a loose list.
    assert L.in_agreement_subset("- a\n\n- b\n") is False
    # Frontmatter is excluded (§5.3), so it does not read as a run of its own.
    assert L.in_agreement_subset("---\ntitle: x\n---\nBody.\n") is True


def test_a_document_outside_the_subset_is_reported_as_advice():
    """SPEC.md §13: a §5.2 linter SHOULD say so, one-directionally.

    `info` rather than `warn`: nothing about the document is wrong, and the
    signal only points one way. A §5.1 write is measurably more likely to change
    what such a document shows; being inside the subset is a better bet rather
    than a promise (§3.4).
    """
    _, findings = L.lint_document("# Heading\nBody.\n")
    advisory = [f for f in findings if f.code == "OUTSIDE_SUBSET"]
    assert [f.level for f in advisory] == ["info"]
    assert not L.has_errors(findings)

    _, clean = L.lint_document("# Heading\n\nBody.\n")
    assert [f for f in clean if f.code == "OUTSIDE_SUBSET"] == []


def test_a_marker_only_line_is_transparent_rather_than_blank():
    """SPEC.md §5.4, corrected in review round 10.

    Blanking a marker-only line manufactures a run boundary no segmenter draws:
    `foo` / marker / `bar` reads as two runs and two nodes, while the blank-line
    segmenter gives ONE block and the tree segmenter gives two. Deleting the line
    instead joins the runs each side of it and certifies the same document for the
    opposite reason.
    """
    assert L.in_agreement_subset("Body.\n<!-- stay:x hash=sha256:521b25cc4586 -->\n") is True
    assert L.in_agreement_subset("foo\n<!-- stay:s -->\nbar\n") is False
    # Transparent only AFTER content. A marker-only line that begins a run is
    # where the profiles part company: this one binds to `B.` under §5.1, whose
    # run starts at the marker line, and to `A.` under §5.2, where an html_block
    # folds into the block before it. Round 11 found this certified.
    assert L.in_agreement_subset("A.\n\n<!-- stay:m -->\nB.\n") is False
    assert L.in_agreement_subset("<!-- stay:m -->\nBody.\n") is False
    # Alone between blank lines it binds to `A.` under both, so it agrees.
    assert L.in_agreement_subset("A.\n\n<!-- stay:m -->\n\nB.\n") is True
    # A marker may span lines; the mask keeps the line endings so the accounting
    # sees the same lines the source has.
    crossing = 'a <!-- stay:x quote="one\n  two" -->\n# b\n'
    assert L.in_agreement_subset(crossing) is False


def test_malformed_diagnostics_remain_content_in_the_agreement_subset():
    for malformed in ("<!-- stay:hash=x -->", "<!-- stay:note=hello -->"):
        doc = f"A.\n{malformed}\n<!-- stay:m -->\n"

        def blocks(mode):
            return [
                (b.line, b.content, [m.id for m in b.markers if not m.malformed])
                for b in L.parse_document(doc, mode=mode)
                if b.index >= 0
            ]

        # The malformed comment remains a block in CommonMark, and the real
        # marker binds to it rather than to the baseline's combined paragraph.
        assert blocks("blank-line") == [(1, f"A.\n{malformed}", ["m"])]
        assert blocks("commonmark") == [(1, "A.", []), (2, malformed, ["m"])]
        assert L.in_agreement_subset(doc) is False

    # MDX-shaped malformed text stays paragraph content under both profiles.
    mdx = "A.\n{/* stay:hash=x */}\n<!-- stay:m -->\n"
    assert L.in_agreement_subset(mdx) is True


def test_the_subset_predicate_agrees_with_the_two_segmenters():
    """The property it is a predicate FOR, rather than its own reasoning.

    Checked here on the shapes that decide it and over the 2417-document corpus in
    `eval/write_safety` (0 certified that segment differently, 0 refused that
    segment identically).
    """
    for doc in (
        "Body.\n",
        "Body.\n<!-- stay:x hash=sha256:521b25cc4586 -->\n",
        "foo\n<!-- stay:s -->\nbar\n",
        "# Heading\nBody.\n",
        "- a\n\n- b\n",
        "A.\n\nB.\n",
        "---\ntitle: x\n---\nBody.\n",
        "Para.\n```\ncode\n```\n",
        "[label]: /url\nBody.\n",
        "A.\n\n<!-- stay:m -->\nB.\n",
        "A.\n\n<!-- stay:m -->\n\nB.\n",
        "<!-- stay:m -->\nBody.\n",
        "Body.\n<!-- stay:a -->\n<!-- stay:b -->\n",
        "A.\n\n<!-- stay:a -->\n<!-- stay:b -->\nB.\n",
    ):
        def blocks(mode):
            return [
                (b.line, b.content)
                for b in L.parse_document(doc, mode=mode)
                if b.index >= 0
            ]

        assert L.in_agreement_subset(doc) is (
            blocks("blank-line") == blocks("commonmark")
        ), doc


def test_a_line_of_unicode_whitespace_is_content_to_both_segmenters():
    """§5's blank line is ASCII-only, and so is this comparison.

    A bare `.strip()` folds U+00A0 in with the spaces, so a line holding one read
    as blank to the predicate and as content to both segmenters, and the document
    was certified while the baseline gave one block and the tree gave two.
    """
    nbsp = "A.\n<!-- stay:x -->\n\u00a0\n"
    assert L.in_agreement_subset(nbsp) is False


def _run_all():
    tests = [
        v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)
    ]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    import sys

    sys.exit(1 if _run_all() else 0)
