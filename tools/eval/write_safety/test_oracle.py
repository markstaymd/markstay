"""The oracle's own sanity cases.

Each real case is a three-line document that a write demonstrably changes, and each
safe case is one it must not flag. Six earlier versions of this oracle passed some
of these and failed others, every time by treating a layout difference (whitespace
left where a comment was removed, whitespace between two tags, whitespace before a
closing tag, a text node split in two by a removed comment) as a rendering change.
"""
import markstay as M

from render_oracle import rendered

REAL = {
    "list continuation becomes a code block":
        ("* `circular` -- boolean\n\n    Call `clone` with it.\n", {}, True, False),
    "marker inside a paired comment ends it early":
        ("<!-- a note\n\nmore note -->\n", {}, True, False),
    # SPEC.md §3.4 refuses this carrier, so the writer no longer produces the
    # damage and `stamp` cannot be used to reach it. The marker is written by hand
    # instead: the case is here to prove the ORACLE can still see the change, and
    # an oracle that stops seeing it because the writer stopped making it is a gate
    # that has quietly turned itself off.
    "row carrier escaped by a trailing backslash":
        ("| a | b |\n|---|---|\n| c | x\\ |\n",
         "| a | b |\n|---|---|\n| c | x\\<!-- stay:r subhash=sha256:dead --> |\n",
         True, True),
}

SAFE = {
    "plain paragraphs": ("Alpha.\n\nBeta.\n", {}),
    "tight list": ("- one\n- two\n", {"child_blocks": True}),
    "ordinary table row": ("| a | b |\n|---|---|\n| c | x |\n", {"child_blocks": True}),
    "cell ending in an even backslash run":
        ("| a | b |\n|---|---|\n| c | x\\\\ |\n", {"child_blocks": True}),
    "closed comment inside a cell":
        ("| a | b |\n|---|---|\n| c | <!-- n --> |\n", {"child_blocks": True}),
}


def changed(doc, mode, kw):
    """Does a write change the rendering? ``kw`` is stamp options, or the output.

    A literal output string is how a case reaches damage §3.4 now refuses to
    write: the document is the writer's input and the second value is what a
    writer without the rule would have produced.
    """
    out = kw if isinstance(kw, str) else M.stamp(doc, mode=mode, **kw).text
    return rendered(doc) != rendered(out)


def test_real_defects_are_seen():
    for name, (doc, kw, baseline, tree) in REAL.items():
        assert changed(doc, "blank-line", kw) is baseline, name
        assert changed(doc, "commonmark", kw) is tree, name


def test_safe_documents_are_not_flagged():
    for name, (doc, kw) in SAFE.items():
        assert not changed(doc, "blank-line", kw), name
        assert not changed(doc, "commonmark", kw), name


# --- SPEC.md §3.4's predicate: refuse on presence, not on meaning ---

from carrier_cost import (  # noqa: E402
    lexical_draft,
    outside_markers,
    plain_text_state,
)

# Every ending carrier_sweep.py measures as capturing the marker, under the pinned
# renderer. Keep this list and the sweep in step: an ending that moves from one list
# to the other without the sweep agreeing is the bug this file exists to catch.
UNSAFE_ENDINGS = ["<div", "\\", "x\\", "x\\\\\\",
                  "x<!--", "x<!-- c --!>", "x<!A", "x<!DOCTYPE",
                  "x<textarea>y", "x<title>y", "x<script>y", "x<style>y", "x<xmp>y",
                  "x<iframe>y", "x<noembed>y", "x<noframes>y", "x<plaintext>y"]

# Endings the rule still permits. Shorter than it was before round 5, on purpose:
# the rule refuses every `<` and every backslash without asking what it opens.
SAFE_ENDINGS = ["x", "", " ", "x  ", "x\t", "x*", "[x](y", "x&amp;", "`x`", "x`",
                "{/* c */}", "x{/*", "x*/"]

MARKER = "<!-- stay:i1 subhash=sha256:dead -->"
MARKER_WITH_EVIDENCE = "<!-- stay:i1 subhash=sha256:dead quote=\"c`d\" -->"


def test_predicate_refuses_every_measured_failure():
    for e in UNSAFE_ENDINGS:
        assert not plain_text_state(e), e


def test_predicate_allows_the_ordinary_endings():
    for e in SAFE_ENDINGS:
        assert plain_text_state(e), e


def test_it_refuses_on_presence_and_not_on_meaning():
    """The deliberate over-refusal. A `<` that opens nothing is still refused.

    This is the whole design: the round 4 predicate decided what each `<` meant and
    got eleven documents wrong doing it. Anything here that starts returning True is
    someone reintroducing that decision.

    v1.8 carved out ONE case, below, and the line between them is what this test is
    for. The clause never asks what a `<` is; it asks whether a code span opened and
    closed around it, which is a lexical question CommonMark answers by run length.
    Every case here still has a `<` whose meaning would have to be decided.
    """
    for text in ("a < b", "x<", "see <!-- shown`",
                 "x<a href=\"y>z\"", "x<plaintext>y</plaintext>"):
        assert not plain_text_state(text), text


def test_v18_masks_a_closed_code_span_at_a_child_carrier_only():
    """The one carve-out, and the two places it stops.

    A row keeps the presence rule, because GFM splits cells before inline parsing
    and a lexical scan pairs backticks across a `|` where a renderer does not. An
    unclosed run masks nothing, because it opens no span that closes here.
    """
    assert plain_text_state("`<style scoped>` in a code span")
    assert not plain_text_state("`<style scoped>` in a code span", flush=True)
    assert not plain_text_state("`<style scoped> unclosed")
    # ...and the withdrawn draft is the thing that let some of these through.
    assert lexical_draft("a < b") is False  # the draft called this one safe


def test_the_scan_does_not_pair_backticks_across_a_line_it_cannot_balance():
    """Pins the regression `51656e2` fixed, found by a dead review arm's probe
    direction rather than by the corpus (both corpora returned zero attributable
    changes for the commit this replaced).

    `ba297ac` paired backticks per line. CommonMark pairs runs sequentially across
    a paragraph, so a leftover run on an earlier line takes the next line's first
    run as its closer and shifts every pairing after it: this list item's stray
    backtick pairs with the comment's, masking the writer-refusing `<` behind a
    span that never closes in the rendered document. Reverting only the "stop at
    the first unbalanced line" behavior (keeping the rest of the v1.8 clause)
    still passes every other case in this module, which is what let it ship once.
    """
    assert not plain_text_state("- a `\n  b ` <!-- ` c")


def test_a_flush_carrier_refuses_a_trailing_emphasis_delimiter():
    """Not a capture: the insertion reclassifies the run it lands against."""
    row = "| a |\n|---|\n| *Hello!**"
    assert not plain_text_state(row, flush=True)
    assert plain_text_state(row)              # the same text, separated, is safe
    assert plain_text_state("| a |\n|---|\n| plain", flush=True)


def test_only_an_id_and_digest_marker_may_sit_at_a_carrier():
    """The marker's own bytes reach the same constructs its carrier text does."""
    assert plain_text_state("plain text", MARKER)
    assert not plain_text_state("plain text", MARKER_WITH_EVIDENCE)
    for evidence in ('<!-- stay:r subhash=sha256:79 quote="x|y" -->',
                     '<!-- stay:p hash=sha256:79 prefix="a b" -->',
                     "<!-- stay:p x-note=` -->"):
        assert not plain_text_state("plain text", evidence), evidence
    for plain in ("<!-- stay:i1 -->", "<!-- stay:i1 hash=sha256:abc -->",
                  "{/* stay:i1 subhash=sha256:abc */}"):
        assert plain_text_state("plain text", plain), plain


def test_mdx_adds_the_brace_and_html_does_not():
    assert not plain_text_state("x{", syntax="mdx")
    assert not plain_text_state("x{/* c */}", syntax="mdx")
    assert plain_text_state("x{", syntax="html")


def test_every_review_counterexample_is_refused():
    """Every document a review arm found, by its carrier text and marker."""
    import carrier_sweep as sweep
    found = 0
    for name, (_doc, _write, scope, marker, _tables) in sweep.SHAPES.items():
        if name.startswith(("R4 ", "R5 ", "R6 ", "R7 ")):
            flush = scope.lstrip().startswith("|")
            if name.endswith("is safe"):
                assert plain_text_state(scope, marker, flush=flush), name
                continue
            assert not plain_text_state(scope, marker, flush=flush), name
            found += 1
    assert found == 15, found



def test_the_derivation_and_the_writer_answer_alike():
    """Two copies of one rule are two rules the day they drift.

    `carrier_cost.plain_text_state` is the derivation SPEC.md §3.4 cites and
    `markstay.stamp.plain_text_state` is what a document actually meets. They are
    written separately on purpose, so the spec's number does not come from the
    implementation it is meant to price; this is what keeps that honest. The
    inputs are every ending and shape this file already measures, plus the marked
    carriers the corpus cannot contain.
    """
    import markstay.stamp as _unused  # noqa: F401
    import sys as _sys

    import carrier_sweep as sweep

    writer = _sys.modules["markstay.stamp"]
    marked = [
        "a <!-- stay:x -->",
        "a <!-- stay:x hash=sha256:dead -->",
        'a <!-- stay:x quote="`<textarea>" -->',
        'a <!-- stay:x quote="| <textarea>" -->',
        "a <!-- stay:hash=1 --!>",
        "a {/* stay:x */}",
        "a <!-- a note -->",
        "- a\n  ```\n  <!-- stay:fake -->\n  ```\n- b",
        "| a | <!-- stay:r subhash=sha256:dead --> | b",
    ]
    scopes = list(UNSAFE_ENDINGS) + list(SAFE_ENDINGS) + marked
    scopes += [scope for _n, (_d, _w, scope, _m, _t) in sweep.SHAPES.items()]
    for scope in scopes:
        for syntax in ("html", "mdx"):
            for flush in (False, True):
                for marker in ("", MARKER, MARKER_WITH_EVIDENCE):
                    assert plain_text_state(scope, marker, syntax, flush) is (
                        writer.plain_text_state(scope, marker, syntax, flush)
                    ), (scope, syntax, flush, marker)
        assert outside_markers(scope) == writer._outside_markers(scope), scope


def _main():
    """Run every case in this file, so `python test_oracle.py` is the whole gate."""
    ran = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            fn()
            ran += 1
    print(f"{ran} sanity cases pass")


if __name__ == "__main__":
    _main()
