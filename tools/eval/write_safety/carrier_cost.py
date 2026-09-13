#!/usr/bin/env python3
"""The §3.4 plain-text-state predicate, and what it costs.

**The rule refuses on presence, not on meaning** (round 5, decided 2026-09-10). A carrier
text carrying any character that can begin a capture is refused, whatever that character
turns out to mean in context. It never asks what a `<` is, which is the point:
`lexical_draft()` below is the round 4 predicate that did ask, and `carrier_sweep.py`'s
`R4` shapes are the ten documents it got wrong. Deciding those correctly needs tag and
attribute state, per-element raw-text termination, PI and CDATA closers, inline
precedence and backslash escapes, which is an HTML tokenizer.

The predicate reads two things: the **carrier text**, which is the scope from its start up to the insertion point,
and the **marker as it will be written**. A marker's own bytes can capture it, since
a code span opened before the marker closes on a backtick inside a `quote=` value and
swallows the marker as displayed text.

`carrier_positions()` counts positions by **running the writer** and reading back
where it actually put each carrier. The first version of this file globbed table
cells and list-start lines with two regexes, which counted a six-cell row as six
positions where a writer has one, so its denominator described neither lost
addressability nor a bound on it.
"""
import re
import sys
from pathlib import Path

import markstay as M
from markstay.lint import _scan_marker_records
from markstay.stamp import _row_marker_position

# HTML's raw-text and escapable-raw-text elements, plus the legacy ones that behave
# the same way. Inside these a comment is text, so a marker after an unclosed one is
# displayed rather than hidden. Measured: every name here except `noscript` captures
# a carrier under markdown-it-py 4.2.0. `noscript` is raw text only when the consuming
# parser has scripting enabled, which a document cannot know, so it is refused too.
RAW_TEXT = ("script", "style", "textarea", "title", "xmp", "iframe", "noembed",
            "noframes", "noscript", "plaintext")

DECL = re.compile(r"<![A-Za-z][^>]*$")
TAG = re.compile(r"</?[A-Za-z][^>]*$")
START_TAG = re.compile(r"<([A-Za-z][A-Za-z0-9]*)(?:\s[^>]*)?>")
BACKTICKS = re.compile(r"`+")

COMMENT_SYNTAX = {"html": ("<!--", "-->"), "mdx": ("{/*", "*/}")}


def odd_trailing_backslashes(text):
    """`\\<` escapes the marker's opening bracket, so the marker is displayed."""
    n = 0
    for ch in reversed(text):
        if ch == "\\":
            n += 1
        else:
            break
    return n % 2 == 1


def unclosed_host_comment(text, syntax="html"):
    """A host comment opener the carrier text does not close.

    Left to right, not `rfind`: an earlier opener owns the first closer after it, so
    the last opener in the text is not necessarily the open one.

    Only `-->` closes an HTML comment here, though §4 records that an HTML *reader*
    also stops at `--!>`. The two disagree and the disagreement is measured: a
    CommonMark renderer does not recognise `--!>` at all, so `x<!-- c --!>` still
    captures a carrier. Refusing is the side of that disagreement a writer can afford.
    """
    opener, closer = COMMENT_SYNTAX[syntax]
    i = 0
    while True:
        o = text.find(opener, i)
        if o == -1:
            return False
        c = text.find(closer, o + len(opener))
        if c == -1:
            return True
        i = c + len(closer)


def unclosed_tag_or_declaration(text):
    """A `<` that opens a tag or declaration with no `>`, so the marker supplies it."""
    return bool(TAG.search(text) or DECL.search(text))


def unclosed_raw_text_element(text):
    """An open raw-text element: its tag is closed, the element is not.

    `x<textarea>hello` passes every other condition here and displays the marker.
    A closed tag is not a closed element, which is the distinction round 3 missed.
    """
    for m in START_TAG.finditer(text):
        name = m.group(1).lower()
        if name in RAW_TEXT and not re.search(
                r"</\s*" + name + r"\s*>", text[m.end():], re.I):
            return True
    return False


def _code_spans(text):
    """Closed code spans as [start, end) content spans, and whether one is left open.

    CommonMark pairs a backtick run with the next run of exactly the same length.
    """
    runs = [(m.start(), m.end()) for m in BACKTICKS.finditer(text)]
    spans, open_run = [], False
    i = 0
    while i < len(runs):
        n = runs[i][1] - runs[i][0]
        j = i + 1
        while j < len(runs) and runs[j][1] - runs[j][0] != n:
            j += 1
        if j == len(runs):
            open_run = True
            break
        spans.append((runs[i][1], runs[j][0]))
        i = j + 1
    return spans, open_run


def unmatched_code_span_opener(text):
    """A backtick run with no equal-length run after it, so a later one closes it."""
    return _code_spans(text)[1]


def inert(text):
    """The carrier text with closed code-span content masked out.

    A code span binds before raw inline HTML, so `<style scoped>` shown in a README
    opens no element and `` `<!--` `` opens no comment. Masking rather than deleting
    keeps every offset, so a trailing backslash is still trailing. Without this the
    predicate refuses documentation *about* HTML, which is most of what a README is:
    all eight refusals in the first corpus run were this shape.
    """
    spans, _ = _code_spans(text)
    out = list(text)
    for a, b in spans:
        for k in range(a, b):
            out[k] = " "
    return "".join(out)


def code_span_capture(text, marker):
    """The marker's own bytes closing a code span the carrier text left open.

    Code spans bind before raw inline HTML in CommonMark, so the backtick wins and
    the marker is rendered as text. Narrow on purpose: the shipped writer emits no
    inline evidence, so a marker with no backtick in it cannot reach this.
    """
    return "`" in marker and unmatched_code_span_opener(text)


def unclosed_expression(text):
    """An MDX expression the carrier text leaves open. Braces counted, not parsed."""
    return text.count("{") > text.count("}")


def lexical_draft(text, marker="", syntax="html"):
    """WITHDRAWN (round 4). The predicate that decided what each character meant.

    Kept so the ten documents it got wrong stay checkable against a rule rather than
    against a memory, and so the rule that replaced it has something to be priced
    against. Do not implement this.
    """
    live = inert(text)
    return (odd_trailing_backslashes(live)
            or unclosed_host_comment(live, syntax)
            or bool(DECL.search(live))
            or unclosed_raw_text_element(live)
            or code_span_capture(text, marker)
            or unclosed_tag_or_declaration(live)
            or (syntax == "mdx" and unclosed_expression(live)))


# Characters that can begin a capture at all. `<` opens every HTML construct a marker
# can complete (comment, tag, declaration, processing instruction, CDATA, raw-text
# element); a backslash escapes the marker's opening bracket; `{` opens an MDX
# expression. A backtick is deliberately absent: refusing every carrier text containing
# one costs 52% of real positions, so the marker clause below carries that case instead.
CAPTURING = {"html": "<\\", "mdx": "<\\{"}


# A marker carrying nothing but its id and its digest. §3.4 permits only this form at a
# carrier position, because a marker's own bytes reach the same constructs its carrier
# text does: `quote` evidence can close a link title, and a `|` in it splits a GFM cell.
# §4 already routes evidence to a side index, so nothing is lost that cannot be kept.
#
# Written to §4's grammar rather than to `\s`, which is the difference between a check
# and a check that ports: `\s` matches LF and U+00A0, and §4 permits neither between
# attributes. An earlier version of this accepted both, which would have handed three
# languages three whitespace definitions to disagree over.
_BODY = (r"[ \t]*stay:[A-Za-z0-9_-]+"
         r"(?:[ \t]+(?:hash|subhash)=sha256:[0-9a-fA-F]+)*"
         r"[ \t]*")
# Delimiters are paired, not alternated: `<!-- ... */}` is not a marker in either host
# syntax, and an earlier version of this accepted it.
PLAIN_MARKER = re.compile(rf"<!--{_BODY}-->\Z|\{{/\*{_BODY}\*/\}}\Z")

# A delimiter run whose meaning depends on what follows it. A flush carrier changes the
# character after such a run from whitespace to `<`, which flips the run from closing to
# neither, so `| *Hello!** |` stops rendering its emphasis. Nothing is captured and no
# refused character appears, so no prefix can see this: it is the insertion itself.
TRAILING_DELIMITER = re.compile(r"[*_~]\Z")


def code_span_refinement(text, marker="", syntax="html", kind="list"):
    """SHIPPED in v1.8. Kept as the name the measurement was published under.

    This was the proposal: the presence rule, minus what a closed code span has
    already neutralised, at §5.5 child carriers only. It is now what §3.4 says,
    so it delegates to `plain_text_state()` rather than keeping a second copy.
    Two copies of one rule are two rules the day they drift, which is what
    `test_oracle.py` exists to forbid, and the copy this function used to hold
    drifted exactly that way: it masked with a scan that paired backticks across
    lines, so it permitted `- a \\`\\n- b <!-- \\` c`, which the shipped rule
    refuses. Those two items are separate blocks; a cross-line scan pairs their
    backticks with each other and masks the `<!--` between them, and a renderer
    does not. (`- a \\`\\n  b \\` <!-- \\` c` is the *other* counterexample, the
    one that killed the intermediate per-line scan that did not stop at an
    unbalanced line. The cross-line copy refuses it, so it does not show this
    drift.)

    **Rows keep the presence rule.** GFM splits cells before inline parsing, so a
    lexical backtick scan pairs across a `|` where a renderer does not: that is
    `carrier_sweep.SHAPES["R4 row, backticks paired across GFM cells"]`, and
    scoping the clause to §5.5 is what keeps it answered.

    Re-derived over the pinned corpus (`corpus.sha256`, 2417 documents) at the
    shipped rule, not at the proposal the decision was priced on:

    | Profile | Positions | v1.7 presence | v1.8 | Recovered |
    |---|---|---|---|---|
    | tree       | 40508 | 3186 (7.87%) | 2168 (5.35%) | 1018 (32.0%) |
    | blank-line | 30799 | 2716 (8.82%) | 1906 (6.19%) |  810 (29.8%) |

    Nothing is newly refused under either profile, every recovered position is a
    list child, and rows are unmoved at 688 of 2762. The 68.1% and 31.4% this
    docstring used to quote were measured before the scan was scoped to a line
    and then stopped at the first line it cannot balance; both narrowings were
    safety fixes, and the consumer figure fell to 36.1% with them.
    """
    return not plain_text_state(text, marker, syntax, flush=(kind == "row"))


def plain_marker(marker):
    """Does this marker carry only its id and digest, in §4's grammar?

    An unwritten marker counts: a caller asking about a carrier text alone passes "".
    """
    return not marker or bool(PLAIN_MARKER.fullmatch(marker.strip()))


# A PLAIN marker already in the carrier text is not text the next marker can be
# captured by: it holds no character a construct is built from, and §4 forbids the
# host closer inside it. Masking it is the same lexical step §5.6's row scan already
# requires (treat markers as opaque tokens), not a judgement about what a character
# means. Without it a container's SECOND child is refused by its first child's stay,
# which makes child identity single-shot per container.
#
# **Plain, not merely complete**, which review round 10 found the hard way: an
# earlier backtick pairs with one inside a `quote=` value, ending the code span
# INSIDE the marker and exposing what follows it, and a `|` in such a value splits
# its GFM cell. Either host form is masked; a record ending at HTML's `--!>` is not,
# since CommonMark does not close a comment there; and §3.3 decides first, so a
# marker-shaped string in a fence is content. `test_oracle.py` pins this against the
# writer's own `_outside_markers`, because two copies of one rule are two rules the
# day they drift.
def outside_markers(text, syntax="html"):
    """``text`` with plain §4 markers masked, offsets and line endings preserved."""
    code = M.code_lines(M.lint._blank_frontmatter(text))
    out = list(text)
    for record in _scan_marker_records(text):
        if not M.lint.marker_outside_code(record.marker, code):
            continue
        if not plain_marker(record.marker.raw):
            continue
        for k in range(record.start, min(record.end, len(out))):
            if out[k] != "\n":
                out[k] = " "
    return "".join(out)


LINE_BREAK = re.compile(r"\r\n|\r|\n")


def lines_with_offsets(text):
    """``(1-based number, line, offset)`` for each line, offsets into ``text``."""
    at = 0
    for number, match in enumerate(LINE_BREAK.finditer(text), start=1):
        yield number, text[at:match.start()], at
        at = match.end()
    yield text.count("\n") + text.count("\r") - text.count("\r\n") + 1, text[at:], at


def inline_code_spans(text, code=None):
    r"""Closed INLINE code spans, §3.4 v1.8's reading. Mirrors `markstay.stamp`.

    Two scopings, and both are the safety property rather than tidiness:

    * **per line**, because a carrier text is the *container's* prefix and for a
      list it spans earlier items, which are separate blocks: two backticks in
      different blocks pair for a lexical scan and not for a renderer;
    * **stopping at the first line whose runs do not pair evenly**, because
      CommonMark pairs runs sequentially across a paragraph, so one leftover run
      takes the next line's first run as its closer and shifts every pairing
      after it. `- a \`\n  b \` <!-- \` c` is the carrier that proved it.

    ``code`` is §3.3's fenced-code line set, which still matters for a tilde
    fence: a backtick fence's delimiter is a lone run and the balance rule ends
    the scan before its body.
    """
    spans = []
    for number, line, offset in lines_with_offsets(text):
        if code and number in code:
            continue
        runs = [(m.start() + offset, m.end() + offset)
                for m in BACKTICKS.finditer(line)]
        found = []
        i = 0
        while i < len(runs):
            width = runs[i][1] - runs[i][0]
            j = i + 1
            while j < len(runs) and runs[j][1] - runs[j][0] != width:
                j += 1
            if j == len(runs):
                return spans
            found.append((runs[i][1], runs[j][0]))
            i = j + 1
        spans.extend(found)
    return spans


def inert_inline(text):
    """``text`` with closed inline code-span CONTENT masked to spaces."""
    out = list(text)
    for a, b in inline_code_spans(text, M.code_lines(text)):
        for k in range(a, b):
            out[k] = " "
    return "".join(out)


def plain_text_state(text, marker="", syntax="html", flush=False):
    """SPEC.md §3.4: may this marker be appended to this carrier text?

    False when the carrier text carries a character that can begin a capture, when the
    marker carries anything but its id and digest, and, at a **flush** carrier only,
    when the text ends in an emphasis delimiter the insertion would reclassify.

    v1.8 adds one scoped exception at a §5.5 child carrier (``flush`` false): the
    content of closed inline code spans is masked before the capture scan, because
    such a span binds before raw inline HTML. Rows keep the v1.7 presence rule,
    because GFM splits cells before inline parsing and a lexical backtick scan
    pairs across a `|` where a renderer does not.

    This is the DERIVATION, an independent copy of the rule the writer implements.
    `test_oracle.py` asserts the two answer alike on every vector, so a change here
    is owed to `markstay.stamp` and a change there is owed here, in the same commit.
    """
    scanned = outside_markers(text, syntax)
    if not flush:
        scanned = inert_inline(scanned)
    if any(ch in scanned for ch in CAPTURING[syntax]):
        return False
    if flush and TRAILING_DELIMITER.search(scanned):
        return False
    return plain_marker(marker)


def conservative(text, marker="", syntax="html", flush=False):
    """The refusal, phrased as the sweep phrases it.

    ``flush`` is forwarded. An earlier version defaulted it away, which dropped the
    TRAILING_DELIMITER guard for every row this function judged and permitted two
    row carriers on the npm corpus that the writer refuses, each of which introduces
    an `<em>` when stamped.
    """
    return not plain_text_state(text, marker, syntax, flush)


ROW = re.compile(r"^\s*\|.*\|\s*$")


def carrier_positions(text, mode="commonmark"):
    """Every position a writer would place a carrier, with its carrier text.

    Read forward from the document's own child segmentation rather than back from a
    stamped copy. Two things this has to get right, and earlier versions got each of
    them wrong in turn:

    * **the scope.** §3.4's carrier text is the *container* block's source, from its
      first line to the marker's line. Not the child's own span: a `<textarea>` opened
      in a table header captures a carrier in a later row, and a preceding sibling item
      does the same in a list, so a child-scoped rule reports safe on a document that
      changes. Not the `subhash` span either, which is normalized content rather than
      raw source and which for a one-line item can end before the text that captures.
    * **the census.** A position only exists where the writer would actually write one,
      so the guards `stamp` already applies are applied here: a child that already
      carries an id, a marker line inside a fenced code block (§3.3), and a list child
      whose line is also a row line of the same container.
    """
    try:
        blocks = M.parse_document(text, mode=mode, child_blocks=True)
    except Exception:
        return
    lines = text.split("\n")
    code = M.code_lines(text)
    for blk in blocks:
        children = list(getattr(blk, "children", ()) or ())
        row_lines = {c.marker_line for c in children if c.kind == "row"}
        for child in children:
            if child.markers or child.marker_line in code:
                continue
            if child.kind != "row" and child.marker_line in row_lines:
                continue
            first, last = blk.line, child.marker_line
            if not (1 <= first <= last <= len(lines)):
                continue
            # The prefix ends where the marker goes, not at the end of the line. For a
            # row that is the flush position inside the last cell, which is what makes
            # the trailing-delimiter check see the cell's last byte rather than `|`.
            tail = lines[last - 1]
            if child.kind == "row":
                pos = _row_marker_position(tail)
                tail = tail[:pos] if pos is not None else tail
            else:
                tail = tail.rstrip()
            yield "\n".join(lines[first - 1:last - 1] + [tail]), child.kind


def main(listing, show=False):
    seen, docs = set(), []
    for line in Path(listing).read_text().splitlines():
        try:
            t = Path(line.strip()).read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if t in seen or len(t) > 200_000:
            continue
        seen.add(t)
        docs.append(t)
    print(f"{len(docs)} documents")
    for mode in ("blank-line", "commonmark"):
        total = draft = wide = rows = 0
        refused = []
        for t in docs:
            for scope, kind in carrier_positions(t, mode):
                marker, flush = "", kind == "row"
                total += 1
                if kind == "row":
                    rows += 1
                if lexical_draft(scope, marker):
                    draft += 1
                if not plain_text_state(scope, marker, flush=flush):
                    wide += 1
                    refused.append(scope)
        if not total:
            print(f"  {mode}: no carrier positions")
            continue
        print(f"  {mode}: {total} carrier positions the writer would use "
              f"({rows} row, {total - rows} child)")
        print(f"    withdrawn round 4 draft    : {draft} ({100*draft/total:.4f}%)")
        print(f"    §3.4 as specified refuses  : {wide} ({100*wide/total:.4f}%)")
        if show:
            for r in refused:
                print(f"      {r[-70:]!r}")


if __name__ == "__main__":
    main(sys.argv[1], show="--show" in sys.argv)
