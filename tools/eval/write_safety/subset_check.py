#!/usr/bin/env python3
"""Does §5.4's membership test predict what it claims to predict?

SPEC.md §5.4 defines the agreement subset as an equality of line spans, and §13
makes reporting it a SHOULD for any linter carrying the §5.2 parser. The property
underneath is what a reader cares about: **inside the subset the two segmenters
give the same blocks, with each marker bound to the same one**. This checks the
predicate against that property rather than against its own reasoning.

Two corpora, because they exercise different halves:

* **generated**, from fragments including marker-only lines in every position. The
  npm corpus carries no markers at all, so it cannot reach the transparency rule,
  and a claim resting on it alone is vacuous exactly where §5.4 is needed. Review
  round 11 found a false certification here that the corpus run could not see.
* **the corpus, as found and stamped**. Stamping is what puts markers into real
  documents, in the positions a writer actually chooses.

Run:  PYTHONPATH=../../impl/py/src:. python subset_check.py [corpus.txt] [--limit N]
Exit status is 0 when every document's predicate matches the property.
Read, parse and stamp errors abort the run; they must not silently shrink the sample.
An explicitly requested corpus must contain at least one eligible document.
"""
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "linter"))

import markstay as M  # noqa: E402
import markstay_lint as L  # noqa: E402

# One of each shape §5.4 names, plus the marker forms. A marker-only line is the
# interesting one: it is transparent after content and a boundary before it.
FRAGMENTS = [
    "A paragraph.",
    "# Heading",
    "- item",
    "> quote",
    "```\ncode\n```",
    "    indented",
    "[label]: /url",
    "<!-- stay:m1 -->",
    "Text <!-- stay:m2 -->",
    "| h |\n|---|\n| c |",
    "",
]


def generated(depth=3):
    """Every ordered arrangement of ``depth`` fragments, joined with a newline."""
    for combo in itertools.product(FRAGMENTS, repeat=depth):
        yield "\n".join(combo) + "\n"


def blocks(md, mode):
    """The content blocks a conforming reader gets, with marker attachment."""
    return [
        (block.line, block.content, tuple(marker.id for marker in block.markers))
        for block in L.parse_document(md, mode=mode)
        if block.index >= 0
    ]


def holds(md):
    """(predicate, property) for one document."""
    return (
        L.in_agreement_subset(md),
        blocks(md, "blank-line") == blocks(md, "commonmark"),
    )


def check(documents, label):
    certified_but_differs = refused_but_agrees = inside = 0
    examples = []
    total = 0
    for md in documents:
        predicted, actual = holds(md)
        total += 1
        inside += bool(predicted)
        if predicted and not actual:
            certified_but_differs += 1
            if len(examples) < 3:
                examples.append(("certified", md))
        if actual and not predicted:
            refused_but_agrees += 1
            if len(examples) < 3:
                examples.append(("refused", md))
    print(f"  {label}: {total} documents, {inside} in the subset, "
          f"{certified_but_differs} certified that segment differently, "
          f"{refused_but_agrees} refused that segment identically")
    for kind, md in examples:
        print(f"    {kind}: {md!r}")
    return certified_but_differs + refused_but_agrees


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
    listing = next((a for a in argv[1:] if not a.startswith("--")), None)
    limit = None
    if "--limit" in argv:
        limit = int(argv[argv.index("--limit") + 1])
    print("§5.4's predicate against the two segmenters' actual blocks")
    wrong = check(generated(), "generated")
    if listing:
        documents = list(corpus(listing, limit))
        wrong += check(documents, "corpus, as found")
        stamped = []
        for text in documents:
            stamped.append(M.stamp(text, mode="commonmark", child_blocks=True).text)
        wrong += check(stamped, "corpus, stamped")
    print(f"{wrong} documents where the predicate and the property disagree")
    return 1 if wrong else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
