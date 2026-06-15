#!/usr/bin/env python3
"""markstay preservation-instruction helper.

Mitigation #1 from the marker-survival eval (`../eval/FINDINGS.md`): the single
biggest lever on whether stays survive a machine edit is not the marker syntax,
it is whether the editing agent was *told* to keep the markers. A naive
full-document rewrite strips nearly every marker; the same rewrite with a
preservation instruction keeps 100% across every inline syntax and every vendor
family the eval tested. This module is the canonical source of that instruction
(SPEC.md §11, the AI editing contract) and a tiny tool to drop it into a prompt.

The instruction text here is the normative phrasing of SPEC.md §11. It folds in
the wording the eval measured as effective ("preserve every marker exactly as
written and in place; do not remove, alter, renumber, or relocate them") so the
adopted instruction is the one shown to work, not a paraphrase of it.

Dependency-free (Python 3.8+ stdlib only); no API credentials, no network.

Usage:
    markstay_preserve.py                  # print the instruction (drop into a
                                          #   system prompt / AGENTS.md / CLAUDE.md)
    markstay_preserve.py --wrap DOC.md    # emit instruction + the doc as a ready
                                          #   editing prompt (pipe to an LLM)
    markstay_preserve.py --wrap DOC.md --task "Rewrite this to be clearer."
                                          # prepend an edit task to the prompt
"""

from __future__ import annotations

import argparse
import sys

# The canonical AI editing contract (SPEC.md §11), phrased as an instruction to an
# editing agent. Keep this in lockstep with SPEC.md §11: this is the same six
# obligations (preserve / keep-attached / mint-new / never-reuse / report-dropped /
# report-duplicate), worded for a model rather than for a tool author.
INSTRUCTION = """\
This Markdown document uses markstay markers: HTML comments of the form
`<!-- stay:ID ... -->` (or, in MDX, `{/* stay:ID ... */}`) placed on or just after
the block they identify. Each marker is a stable address that other tools rely on,
so it must survive your edit.

When you edit this document you MUST:

- preserve every existing `stay:` marker exactly as written, including its id and
  any `hash=` / `quote=` attributes; do not remove, reword, renumber, or relocate it;
- keep each marker attached to the same logical block it was on before, even when
  you move, reword, or reformat that block;
- mint a fresh id (any new short token) only for content that is genuinely new;
- never reuse an existing id for different content;
- if you must drop a marker, report it explicitly in your reply, never drop one
  silently;
- never introduce a duplicate id (the same id on two blocks).

Return the edited Markdown with every original marker still present and in place."""

RETURN_ONLY = "Return only the resulting Markdown, with no commentary and no code fence around it."


def wrap(doc: str, task: str | None = None) -> str:
    """Compose a ready-to-send editing prompt: optional task, then the
    preservation instruction, then the document. Mirrors the eval's prompt
    builder (`../eval/run_eval.py`), the shape that measured 100% survival."""
    parts: list[str] = []
    if task:
        parts.append(task.strip())
    parts.append(INSTRUCTION)
    parts.append(RETURN_ONLY)
    parts.append("---\n\n" + doc.strip() + "\n")
    return "\n\n".join(parts)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Emit the markstay preservation instruction (SPEC.md §11), "
                    "or wrap a document into an editing prompt that carries it.")
    ap.add_argument("--wrap", metavar="DOC.md",
                    help="wrap this Markdown file into an editing prompt instead "
                         "of just printing the instruction ('-' reads stdin)")
    ap.add_argument("--task", metavar="TEXT",
                    help="edit task to prepend to a --wrap prompt "
                         "(e.g. \"Rewrite this to be clearer.\")")
    args = ap.parse_args(argv)

    if args.task and not args.wrap:
        ap.error("--task only applies with --wrap")

    if args.wrap:
        doc = sys.stdin.read() if args.wrap == "-" else open(args.wrap, encoding="utf-8").read()
        sys.stdout.write(wrap(doc, task=args.task) + "\n")
    else:
        sys.stdout.write(INSTRUCTION + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
