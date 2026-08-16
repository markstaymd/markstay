#!/usr/bin/env python3
"""Self-tests for markstay_lint. Runnable two ways:

    python test_lint.py        # plain asserts, no dependency
    pytest test_lint.py        # also works (functions are test_*)

No API credentials needed: the linter is fully local and deterministic.
"""

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
    assert findings == [], codes(findings)  # whole-list hash matches, no drift


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
        "\n".join(line for line in before.splitlines() if line != "<!-- stay:parent -->")
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
    assert sorted(codes(findings)) == ["HASH_DRIFT", "MALFORMED_MARKER"]
    hidden = L.render_text("doc", findings)
    shown = L.render_text("doc", findings, show_drift=True)
    for r in (hidden, shown):
        assert "1 error, 1 warn, 0 info" in r  # counts unchanged
        assert "MALFORMED_MARKER" in r  # the actionable line stays
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
    assert [b.content for b in L.parse_document(md)] == ["---", "# Heading", "Body para."]


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
    long_sibling = ("Ship the linter and then "
                    + "wait for the release train " * 3
                    + "wait for the release train")
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
    over_long, _, _ = L._best_match(
        "the target block body", long_prev, "", candidates
    )
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
        ("# Alpha", []),          # a heading is scoped by its parents, not itself
        ("One.", ["Alpha"]),
        ("## Beta", ["Alpha"]),
        ("Two.", ["Alpha", "Beta"]),
        ("# Gamma", []),          # level 1 pops Beta and Alpha both
        ("Three.", ["Gamma"]),
    ]


def test_heading_path_skipped_level_nests_rather_than_replaces():
    md = "# Alpha\n\n### Deep\n\nBody.\n\n## Mid\n\nAfter.\n"
    assert _paths(md) == [
        ("# Alpha", []),
        ("### Deep", ["Alpha"]),
        ("Body.", ["Alpha", "Deep"]),
        ("## Mid", ["Alpha"]),    # level 2 pops the level-3 sibling
        ("After.", ["Alpha", "Mid"]),
    ]


def test_heading_path_atx_closing_hashes_and_empty_title():
    md = "## Alpha ##\n\nOne.\n\n### Beta#\n\nTwo.\n\n#\n\nThree.\n"
    assert _paths(md) == [
        ("## Alpha ##", []),
        ("One.", ["Alpha"]),
        ("### Beta#", ["Alpha"]),   # no space before the hash: not a closer
        ("Two.", ["Alpha", "Beta#"]),
        ("#", []),
        ("Three.", [""]),           # an empty title is still a level
    ]


def test_heading_path_setext():
    md = "Alpha\n=====\n\nOne.\n\nBeta\n----\n\nTwo.\n"
    assert _paths(md) == [
        ("Alpha\n=====", []),
        ("One.", ["Alpha"]),
        ("Beta\n----", ["Alpha"]),   # `-` is level 2, so it nests under Alpha
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
