"""Is a document in SPEC.md §5.4's agreement subset, and does that predict safety?

§5.4: after frontmatter (§5.3) and marker spans are excluded, the maximal runs of
non-blank lines and the top-level CommonMark block nodes cover the same spans of
lines. §5.4's case 2, "a blank line inside one node", is exactly the shape every
measured write-path damage takes, so the hypothesis is that the blank-line writer
preserves rendering precisely on this subset.

The derivation lives in the linter, not here. §13 makes reporting this a SHOULD
for any linter carrying the §5.2 parser, so a second copy in the eval would be a
second answer to a normative question: the earlier one here matched any `---`
region rather than §5.3's payload rules and counted marker spans as content, which
put every stamped document outside the subset.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "linter"))

from markstay_lint import in_agreement_subset  # noqa: E402,F401

__all__ = ["in_agreement_subset", "in_subset"]


def in_subset(text):
    """The name this eval's harnesses call it by."""
    return in_agreement_subset(text)
