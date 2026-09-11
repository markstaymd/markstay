#!/usr/bin/env python3
"""The measurement behind SPEC.md §3.4's numbers.

Usage:
    python sweep.py CORPUS_LISTING [--manifest OUT]

CORPUS_LISTING is a file of paths, one per line. Documents are deduplicated by
content and those over 200 KB are skipped, so the same listing gives the same
corpus on any machine that holds the same files. --manifest writes the sha256 of
each document actually used, which is what makes a rerun checkable rather than
merely repeatable.

It answers three questions on that corpus:

  * does stamping under the blank-line profile (§5.1) change the rendering, split
    by whether the document is in §5.4's agreement subset;
  * does stamping under the tree profile (§5.2);
  * does child-block stamping under the tree profile, which exercises §5.6's row
    carrier, under a CommonMark renderer and again with the GFM table rule on.

The last pair is reported as a pair on purpose. A CommonMark renderer shows a GFM
table as one paragraph, so `*` and backtick runs in different cells pair with each
other and a row marker changes which pairs with which. That is the renderer's
answer, not the row carrier's, and turning the table rule on separates the two.
"""
import hashlib
import sys
from pathlib import Path

import markstay as M

from agreement import in_subset
from render_oracle import rendered


def corpus(listing):
    seen, out = set(), []
    for line in Path(listing).read_text().splitlines():
        p = Path(line.strip())
        if not line.strip():
            continue
        try:
            text = p.read_text()
        except (OSError, UnicodeDecodeError):
            continue
        if text in seen or len(text) > 200_000:
            continue
        seen.add(text)
        out.append((p, text))
    return out


def main(argv):
    docs = corpus(argv[1])
    manifest = None
    if "--manifest" in argv:
        manifest = open(argv[argv.index("--manifest") + 1], "w")
    counts = {k: 0 for k in ("sub_ok", "sub_changed", "out_ok", "out_changed",
                             "tree", "child", "child_tables")}
    for path, text in docs:
        if manifest:
            manifest.write(f"{hashlib.sha256(text.encode()).hexdigest()}  {path.name}\n")
        before = rendered(text)
        baseline_changed = before != rendered(M.stamp(text).text)
        if in_subset(text):
            counts["sub_changed" if baseline_changed else "sub_ok"] += 1
        else:
            counts["out_changed" if baseline_changed else "out_ok"] += 1
        if before != rendered(M.stamp(text, mode="commonmark").text):
            counts["tree"] += 1
        try:
            child = M.stamp(text, mode="commonmark", child_blocks=True).text
        except Exception:
            continue
        if before != rendered(child):
            counts["child"] += 1
        if rendered(text, tables=True) != rendered(child, tables=True):
            counts["child_tables"] += 1
    if manifest:
        manifest.close()
    n = len(docs)
    print(f"{n} documents")
    print(f"  §5.1, in §5.4's agreement subset : "
          f"{counts['sub_ok']} preserved, {counts['sub_changed']} changed")
    print(f"  §5.1, outside the subset         : "
          f"{counts['out_ok']} preserved, {counts['out_changed']} changed")
    print(f"  §5.2                             : {counts['tree']} changed")
    print(f"  §5.2 with child blocks (§5.5/5.6): {counts['child']} changed")
    print(f"  §5.2 with child blocks, tables on: {counts['child_tables']} changed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
