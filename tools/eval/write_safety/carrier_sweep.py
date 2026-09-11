#!/usr/bin/env python3
"""Which text makes a mid-line marker unsafe? (SPEC.md §3.4)

Three rules put a marker on a line that already carries content: §5.5's child
carrier at the end of a list item's last paragraph, §5.6's row carrier inside a
row's last cell, and §5's permission for any block's marker to sit on the block's
last line. Everywhere else a marker gets a line of its own, where the bytes beside
it cannot change what it means.

This enumerates what can precede a marker, writes one, and reports where the
rendering changes. The point is to derive the refusal predicate from the failures
rather than to guess it and hope.

Two dimensions were added after round 3, because the endings table alone cannot see
them: a **shape** whose capturing text is not on the marker's own line, and a marker
whose **own bytes** do the capturing.

Numbers here are markdown-it-py version dependent. Run under the pin in
`requirements.txt` (4.2.0, CommonMark 0.31.2); under the pre-0.31 comment rule
(3.0.0) `x<!--` reads as safe, because the doubled `--` stops the merged span being
a comment at all.
"""
import sys

import markstay as M

from carrier_cost import plain_text_state
from render_oracle import rendered

ENDINGS = [
    "x", "", " ",
    # escapes
    "x\\", "x\\\\", "x\\\\\\", "\\",
    # host comment openers and closers
    "x<!--", "x-->", "x{/*", "x*/", "<!-- c -->", "{/* c */}", "x<!", "x<!-",
    "x<!-- c --!>",
    # HTML-shaped starts a marker could complete
    "x<", "x<a", "x<a href=\"y", "x<!A", "x<!DOCTYPE", "x<?", "x<![CDATA[",
    "x</", "x</a", "<div>", "<div", "<span>y",
    # raw-text elements: the tag is closed, the element is not
    "x<textarea>y", "x<title>y", "x<script>y", "x<style>y", "x<xmp>y",
    "x<iframe>y", "x<noembed>y", "x<noframes>y", "x<plaintext>y",
    "x<textarea>y</textarea>", "x<pre>y",
    # code spans, including the ones a README about HTML is full of
    "x`", "x``", "`x", "``x", "`x`", "x```",
    "x`<!--`", "x`<style scoped>`", "x`<div`", "x`<v4.8`", "x`a\\`",
    # inline emphasis and links
    "x*", "*x", "x_", "x[", "x![", "[x](y", "x&", "x&amp;", "x&#",
    # autolinks
    "<http://a", "<http://a>",
    # whitespace-significant endings
    "x  ", "x\t",
]

ROW = "| a | b |\n|---|---|\n| c | {} |\n"
ITEM = "- one\n- {}\n"

# Counterexamples the endings table cannot express: the capturing text is not on the
# marker's own line, or the marker's own bytes are what close the construct. Each is
# (document, write, carrier text the predicate sees, marker as written, render with
# GFM tables on).
#
# The block marked ROUND 4 REVIEW is the set the codex arm found on 2026-09-10, every
# one re-executed here. Each was a false accept under the lexical predicate of the day:
# it permitted them and the oracle saw the document change. They are the reason §3.4
# refuses on presence rather than on meaning, and they stay in the gate so any future
# rule has to answer them rather than be believed.
SHAPES = {
    "opener on an earlier line of the same paragraph": (
        "- text <!-- unclosed\n  more text\n", "stamp",
        "- text <!-- unclosed\n  more text", "", False),
    "opener on an earlier line, minimal": (
        "- <!-- x\n  y\n", "stamp", "- <!-- x\n  y", "", False),
    "opener in an earlier cell of the same row": (
        "| a | b |\n|---|---|\n| <!-- x | y |\n", "stamp",
        "| <!-- x | y ", "", False),
    "opener in an earlier cell, nothing else in it": (
        "| a | b |\n|---|---|\n| <!-- | x |\n", "stamp", "| <!-- | x ", "", False),
    "opener closed inside the same row": (
        "| a | b |\n|---|---|\n| <!-- x --> | y |\n", "stamp",
        "| <!-- x --> | y ", "", False),
    "code span closed by the marker's own quote evidence": (
        "- a `b\n",
        "- a `b <!-- stay:i1 subhash=sha256:dead quote=\"c`d\" -->\n",
        "- a `b", "<!-- stay:i1 subhash=sha256:dead quote=\"c`d\" -->", False),
    "same, with a marker carrying no backtick": (
        "- a `b\n",
        "- a `b <!-- stay:i1 subhash=sha256:dead -->\n",
        "- a `b", "<!-- stay:i1 subhash=sha256:dead -->", False),
    "ordinary block marker, flush after a trailing backslash": (
        "x\\\n", "x\\<!-- stay:p1 hash=sha256:dead -->\n",
        "x\\", "<!-- stay:p1 hash=sha256:dead -->", False),
    "ordinary block marker, a space after the same backslash": (
        "x\\\n", "x\\ <!-- stay:p1 hash=sha256:dead -->\n",
        "x\\ ", "<!-- stay:p1 hash=sha256:dead -->", False),
    "ordinary block marker on the block's last line, open comment": (
        "x<!--\n", "x<!-- <!-- stay:p2 hash=sha256:dead -->\n",
        "x<!-- ", "<!-- stay:p2 hash=sha256:dead -->", False),

    # --- ROUND 4 REVIEW (codex, 2026-09-10): every one a false accept ---
    "R4 generic carrier, opener on an earlier line of the paragraph": (
        "text <!-- unclosed\nmore text\n",
        "text <!-- unclosed\nmore text <!-- stay:p hash=sha256:dead -->\n",
        "text <!-- unclosed\nmore text ", "<!-- stay:p hash=sha256:dead -->", False),
    "R4 row, backticks paired across GFM cells": (
        "| a | b |\n|---|---|\n| ` | <!--` y |\n", "stamp",
        "| ` | <!--` y", "", True),
    "R4 code span loses to an earlier HTML tag opener": (
        "- x<a title=\"`\"> <!-- ` >\n", "stamp",
        "- x<a title=\"`\"> <!-- ` > ", "", False),
    "R4 a backslash-escaped backtick is not a code-span opener": (
        "- x\\`<!--` y\n", "stamp", "- x\\`<!--` y ", "", False),
    "R4 marker quote evidence closes a processing instruction": (
        "x<? \n", "x<? <!-- stay:p1 quote=\"?>\" -->\n",
        "x<? ", "<!-- stay:p1 quote=\"?>\" -->", False),
    "R4 marker quote evidence closes a CDATA section": (
        "x<![CDATA[ \n", "x<![CDATA[ <!-- stay:p1 quote=\"]]>\" -->\n",
        "x<![CDATA[ ", "<!-- stay:p1 quote=\"]]>\" -->", False),
    "R4 a > inside a quoted attribute does not close the tag": (
        "x<a title='>x \n", "x<a title='>x <!-- stay:p1 quote=' prefix=z-->\n",
        "x<a title='>x ", "<!-- stay:p1 quote=' prefix=z-->", False),
    "R4 </plaintext> does not end plaintext": (
        "- x<plaintext>y</plaintext>\n", "stamp",
        "- x<plaintext>y</plaintext> ", "", False),
    "R4 </ script> is not a valid end tag": (
        "- x<script>y</ script>\n", "stamp", "- x<script>y</ script> ", "", False),
    "R4 an end tag inside an attribute value is not an end tag": (
        "- x<script title=\"></script>\">y\n", "stamp",
        "- x<script title=\"></script>\">y ", "", False),

    # --- ROUND 5 REVIEW (codex, 2026-09-10) ---
    # Both are the marker's own bytes, not its carrier text. They are why §3.4 permits
    # only an id-and-digest marker at a carrier position and routes evidence to §4's
    # side index.
    "R5 marker quote evidence closes a link title": (
        '- ) [x](url "\n<!-- stay:p hash=sha256:4c077b1f2ef1 -->\n',
        '- ) [x](url " <!-- stay:i subhash=sha256:d5498f9d9b50 quote=") [x](url \\"" -->'
        '\n<!-- stay:p hash=sha256:4c077b1f2ef1 -->\n',
        '- ) [x](url " ',
        '<!-- stay:i subhash=sha256:d5498f9d9b50 quote=") [x](url \\"" -->', False),
    "R5 a pipe in row evidence splits the GFM cell": (
        "| a | b |\n|---|---|\n| x | y |\n",
        '| a | b |\n|---|---|\n| x | y<!-- stay:r subhash=sha256:791a886d455a'
        ' quote="x|y" --> |\n\n<!-- stay:table hash=sha256:8a2e294d70b7 -->\n',
        "| x | y |", '<!-- stay:r subhash=sha256:791a886d455a quote="x|y" -->', True),

    # --- ROUND 6 REVIEW (codex, 2026-09-10) ---
    # The capturing text is inside the container and outside the child, which is why
    # §3.4's carrier text is the container's source rather than the child's.
    "R6 a header's raw-text element captures a later row's carrier": (
        "| a | <textarea>b |\n|---|---|\n| x | y |\n| z | </textarea> |\n",
        "| a | <textarea>b |\n|---|---|\n"
        "| x | y<!-- stay:r subhash=sha256:791a886d455a --> |\n| z | </textarea> |\n",
        "| a | <textarea>b |\n|---|---|\n| x | y |",
        "<!-- stay:r subhash=sha256:791a886d455a -->", True),
    "R6 a preceding sibling item captures the next item's carrier": (
        "- <textarea>a\n- b\n- </textarea>\n", "stamp",
        "- <textarea>a\n- b", "", False),

    # --- ROUND 7 REVIEW (codex, 2026-09-10) ---
    # Not a capture. The flush insertion changes the character after a delimiter run
    # from whitespace to `<`, which flips the run from closing to neither, and the
    # emphasis stops rendering. No refused character appears anywhere in the document,
    # so no prefix can see it: only the insertion itself can.
    "R7 a flush carrier reclassifies the delimiter run before it": (
        "| a |\n|---|\n| *Hello!** |\n", "stamp",
        "| a |\n|---|\n| *Hello!**", "", True),
    "R7 the same body with a spaced child carrier is safe": (
        "- *Hello!**\n- x\n", "stamp", "- *Hello!** ", "", False),
}


def unsafe(doc, out, tables=False):
    if out == doc:
        return None  # nothing minted here, so nothing to judge
    return rendered(doc, tables=tables) != rendered(out, tables=tables)


def write_module():
    """`markstay.stamp`, whose name the package shadows with a function."""
    import sys as _sys

    import markstay.stamp  # noqa: F401
    return _sys.modules["markstay.stamp"]


def stamped(doc, mode, guard=False):
    """Stamp ``doc``, by default with §3.4 forced OPEN, which is the measurement.

    Every arm above asks "does an insertion at this carrier change the
    rendering", and the answer has to come from a writer that makes the
    insertion. Once the rule is implemented, asking the shipped writer instead
    measures the rule against itself: it refuses, the document does not change,
    and the endings and shapes the rule was derived FROM all report `ok`. That is
    a gate that can no longer fail. Measured: guarded, this file finds 22 unsafe
    endings and shapes where forcing the insertion finds 39.

    The mutation battery is unaffected either way, since it patches the writer's
    own seam and runs the corpus. ``guard=True`` is for the one arm that is about
    the shipped writer rather than about the rule.
    """
    module = write_module()
    saved = module.plain_text_state
    if not guard:
        module.plain_text_state = lambda *a, **kw: True
    try:
        return M.stamp(doc, mode=mode, child_blocks=True).text
    except Exception as exc:  # a refusal is not a rendering change
        return exc
    finally:
        module.plain_text_state = saved


def endings_table():
    print(f"{'ending':26s} {'row/blank':>10s} {'row/tree':>9s} "
          f"{'item/blank':>11s} {'item/tree':>10s}")
    failures = set()
    for e in ENDINGS:
        cells = []
        for template in (ROW, ITEM):
            for mode in ("blank-line", "commonmark"):
                doc = template.format(e)
                out = stamped(doc, mode)
                if isinstance(out, Exception):
                    cells.append(f"error:{type(out).__name__}")
                    continue
                r = unsafe(doc, out)
                cells.append("-" if r is None else ("UNSAFE" if r else "ok"))
                if r:
                    failures.add(e)
        print(f"{e!r:26s} {cells[0]:>10s} {cells[1]:>9s} "
              f"{cells[2]:>11s} {cells[3]:>10s}")
    print(f"\n{len(failures)} unsafe endings: {sorted(failures)}")
    return failures


def shapes_table():
    print(f"\n{'shape':58s} {'blank':>7s} {'tree':>7s} {'refused':>8s}")
    failures = []
    for name, (doc, write, scope, marker, tables) in SHAPES.items():
        cells = []
        for mode in ("blank-line", "commonmark"):
            out = stamped(doc, mode) if write == "stamp" else write
            if isinstance(out, Exception):
                cells.append(f"error:{type(out).__name__}")
                continue
            r = unsafe(doc, out, tables)
            cells.append("-" if r is None else ("UNSAFE" if r else "ok"))
        # A row carrier is written flush; every other position takes a separator.
        refused = not plain_text_state(scope, marker,
                                       flush=scope.lstrip().startswith("|"))
        print(f"{name[:58]:58s} {cells[0]:>7s} {cells[1]:>7s} "
              f"{'yes' if refused else 'no':>8s}")
        if "UNSAFE" in cells and not refused:
            failures.append(name)
    return failures


# §3.4's flush clause came out of four documents a review arm sent, which is thinner
# than every other condition here. These are the bodies that derive it properly: put
# each in the flush position and ask which trailing bytes actually matter.
FLUSH_BODIES = [
    "*Hello!**", "**Hello!*", "_foo!__", "*_**", "~~x~", "~x~~", "*a*", "**a**",
    "~~a~~", "a*", "a_", "a~", "*a", "_a", "~a", "a**", "a__", "a~~",
    "[a](b)", "[a]", "![a](b)", "[a][b]", "[a] ", "[a](b", "[a]:", "<b@c.d>",
    "<http://a>", "<b>x</b>", "&amp;", "&", "a\\", "a&#35;", "a  ", "a\t",
    "a\\\\", "`a`", "``a``", "`a` ", "a.", "a,", "a!", "a?", "a:", "a;", "a)",
    "a]", "a}", "a>", "a=", "a+", "a#", "a$", "a%", "a^", "a|", "a/", "a'", 'a"',
    "a-",
]


def flush_table():
    """Which trailing bytes make a flush carrier unsafe? (§3.4's flush clause)"""
    print(f"\n{'flush cell body':18s} {'changed':>8s} {'refused':>8s}")
    missed = []
    for body in FLUSH_BODIES:
        doc = f"| a |\n|---|\n| {body} |\n"
        out = stamped(doc, "commonmark")
        if isinstance(out, Exception) or out == doc:
            continue
        changed = rendered(doc, tables=True) != rendered(out, tables=True)
        scope = f"| a |\n|---|\n| {body}"
        refused = not plain_text_state(scope.rstrip() if body[-1:].isspace() else scope,
                                       flush=True)
        if changed and not refused:
            missed.append(body)
        if changed or not refused:
            print(f"{body!r:18s} {str(changed):>8s} {str(refused):>8s}")
    print(f"{len(FLUSH_BODIES)} bodies, {len(missed)} the clause misses: {missed}")
    return missed


# Documents whose input is the WRITER'S OWN OUTPUT. Every other gate in this file
# starts from unmarked text, which is exactly why none of them could see that §3.4
# refused a carrier because of a marker markstay itself wrote: a stamped container
# refused every child added to it afterwards, for good. These must be PERMITTED,
# and they are the reason the scan masks complete markers.
INCREMENTAL = {
    "a third item added to a stamped list": (
        "- one <!-- stay:c1 subhash=sha256:7692c3ad3540 -->\n"
        "- two <!-- stay:c2 subhash=sha256:3fc4ccfe7458 -->\n"
        "- three\n"
        "<!-- stay:ln hash=sha256:2086e2bdb07a -->\n", "c3", "list"),
    # The container digest is the refreshed one a `restamp` leaves behind, because
    # adding a row drifts it and `stamp` refuses a drifted container before §3.4
    # gets a say: a fixture with a stale digest tests the wrong refusal.
    "a row added to a stamped table": (
        "| h | v |\n|---|---|\n"
        "| a | 1<!-- stay:r1 subhash=sha256:df4504ce9250 --> |\n"
        "| b | 2 |\n"
        "<!-- stay:tb hash=sha256:791ff2d16630 -->\n", "r2", "row"),
    "a container stay on the line in front of its own rows": (
        "intro <!-- stay:p hash=sha256:e499e09ba226 -->\n"
        "| a | b |\n|---|---|\n| x | y |\n", "r1", "row"),
}


def incremental_table():
    """Can a writer stamp a child beside siblings it already stamped?"""
    print(f"\n{'writer output as input':56s} {'minted':>8s} {'refused':>8s}")
    failures = []
    for name, (doc, new_id, kind) in INCREMENTAL.items():
        # Guarded, unlike every other arm here: this one measures the shipped
        # writer's answer on documents the shipped writer produced.
        got = M.stamp(doc, child_blocks=True, new_id=lambda: new_id)
        minted = [entry["id"] for entry in got.minted]
        refused = [entry["kind"] for entry in got.refused_carriers]
        print(f"{name[:56]:56s} {str(minted):>8s} {str(refused):>8s}")
        if new_id not in minted or refused or got.refused is not None:
            failures.append(name)
    print(f"{len(INCREMENTAL)} documents, {len(failures)} the rule refuses: {failures}")
    return failures


def predicate_check(unsafe_endings):
    """Every measured failure refused, and the ordinary endings still permitted.

    An ending is judged at the row position, which is flush, since that is the stricter
    of the two and an ending permitted there is permitted anywhere.
    """
    accepted = sorted(e for e in unsafe_endings if plain_text_state(e, flush=True))
    print(f"\n§3.4 as specified, against the endings table:")
    print(f"  unsafe endings it permits (must be none): {accepted}")
    refused = sorted(e for e in ENDINGS
                     if e not in unsafe_endings and not plain_text_state(e, flush=True))
    print(f"  safe endings it refuses (the width it was priced for): {refused}")
    return accepted


def main():
    unsafe_endings = endings_table()
    shape_failures = shapes_table()
    flush_misses = flush_table()
    refused_own = incremental_table()
    accepted = predicate_check(unsafe_endings)
    if shape_failures:
        print(f"\nSHAPES the predicate permits and the oracle calls unsafe: "
              f"{shape_failures}")
    if refused_own:
        print(f"\nDOCUMENTS the writer produced and can no longer stamp: {refused_own}")
    return 1 if (accepted or shape_failures or flush_misses or refused_own) else 0


if __name__ == "__main__":
    sys.exit(main())
