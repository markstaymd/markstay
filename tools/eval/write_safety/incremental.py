#!/usr/bin/env python3
"""What §3.4 costs on a document markstay has already stamped.

The carrier cost in `carrier_cost.py` is measured on documents that carry no
markers, which is every document in this corpus. A stamped one carries several,
and §3.4's carrier text is raw source, so without the mask every marker this
specification wrote sits in the prefix of every later carrier in its container:
the second item of a stamped list and every row added to a stamped table would be
permanently unstampable. This counts that, and it is the measurement behind the
70.9% figure in SPEC.md §3.4 and SPEC_DECISIONS.md.

One question per stamped child: with its own marker taken back out, as it would be
the moment an author adds a sibling, does the rule still permit it? The rule is
evaluated twice, once masking markers as §3.4 says and once with them visible, so
the answer separates "refused because of a marker" from "refused for a reason the
mask cannot touch".

Run:  PYTHONPATH=../../impl/py/src:. python incremental.py corpus.txt [--limit N]
Read, parse and stamp errors abort the run; they must not count as zero measurements.
The corpus must contain at least one eligible document.
"""
import sys
from pathlib import Path

import markstay as M

from carrier_cost import CAPTURING, TRAILING_DELIMITER, outside_markers, plain_marker
from markstay.stamp import _row_marker_position


def unmasked_state(text, marker="", syntax="html", flush=False):
    """§3.4 BEFORE the mask: the prefix scanned with its own markers visible."""
    if any(character in text for character in CAPTURING[syntax]):
        return False
    if flush and TRAILING_DELIMITER.search(text):
        return False
    return plain_marker(marker)


def masked_state(text, marker="", syntax="html", flush=False):
    """§3.4 as specified, which is the same scan over ``outside_markers``."""
    return unmasked_state(outside_markers(text, syntax), marker, syntax, flush)


def probe(text, mode):
    """(stamped children, refused unmasked, refused only because of a marker)."""
    total = refused = only = 0
    blocks = M.parse_document(text, mode=mode, child_blocks=True)
    lines = text.split("\n")
    code = M.code_lines(text)
    for block in blocks:
        for child in getattr(block, "children", ()) or ():
            if child.marker_line <= 0 or child.marker_line in code:
                continue
            if not child.markers:
                continue  # never stamped: the carrier_cost.py case
            tail = lines[child.marker_line - 1]
            for marker in child.markers:
                tail = tail.replace(marker.raw, "")
            if child.kind == "row":
                position = _row_marker_position(tail)
                if position is None:
                    continue
                tail = tail[:position]
            else:
                tail = tail.rstrip()
            scope = "\n".join(lines[block.line - 1:child.marker_line - 1] + [tail])
            flush = child.kind == "row"
            total += 1
            if not unmasked_state(scope, "", flush=flush):
                refused += 1
                if masked_state(scope, "", flush=flush):
                    only += 1
    return total, refused, only


def corpus(listing, limit=None):
    seen = set()
    for line in Path(listing).read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        path = Path(line.strip())
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as error:
            raise RuntimeError(f"Cannot read corpus document {path}: {error}") from error
        if text in seen or len(text) > 200_000:
            continue
        seen.add(text)
        yield text
        if limit and len(seen) >= limit:
            return
    if not seen:
        raise ValueError(f"Corpus listing {listing} contains no eligible documents")


def main(argv):
    limit = int(argv[argv.index("--limit") + 1]) if "--limit" in argv else None
    documents = list(corpus(argv[1], limit))
    print(f"{len(documents)} documents")
    for mode in ("blank-line", "commonmark"):
        total = refused = only = 0
        for text in documents:
            stamped = M.stamp(text, child_blocks=True, mode=mode).text
            counts = probe(stamped, mode)
            total += counts[0]
            refused += counts[1]
            only += counts[2]
        share = 100 * refused / max(total, 1)
        print(f"  {mode}: of {total} stamped children, re-stamping one beside its "
              f"siblings is refused for {refused} ({share:.2f}%) without the mask, "
              f"{only} of them solely because of a marker in the prefix")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
