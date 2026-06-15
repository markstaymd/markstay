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
    shape = lambda mode: [(b.content, [m.id for m in b.markers], b.index)
                          for b in L.parse_document(md, mode=mode)]
    assert shape("blank-line") == shape("commonmark")


def test_unknown_mode_rejected():
    try:
        L.parse_document("x\n", mode="bogus")
    except ValueError:
        return
    assert False, "unknown mode must raise ValueError"


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
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
