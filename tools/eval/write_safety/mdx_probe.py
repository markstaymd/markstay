#!/usr/bin/env python3
"""Does an MDX carrier break the document? (SPEC.md §3.4, and its limit)

A CommonMark renderer cannot see an MDX expression at all, so `render_oracle.py` is
blind here and the oracle is the MDX compiler itself: compile before, write, compile
after, and a document that compiled and now does not is the failure.

Needs Node and `@mdx-js/mdx`, which this repo does not vendor:

    npm install --prefix /tmp/markstay-mdx-probe @mdx-js/mdx@3.1.1
    MDX_DIR=/tmp/markstay-mdx-probe PYTHONPATH=../../impl/py/src:. \
      ../../impl/py/.venv/bin/python mdx_probe.py

Run both commands from eval/write_safety/ after installing requirements.txt.

Without MDX_DIR it looks for ./mdx/node_modules and otherwise skips, because an
unavailable compiler must not read as a pass.
"""
import json
import os
import pathlib
import subprocess
import sys

import markstay as M

COMPILE_JS = """\
import {compile} from '@mdx-js/mdx'
import {readFileSync} from 'node:fs'
try {
  await compile(readFileSync(process.argv[2], 'utf8'))
  process.stdout.write('OK\\n')
} catch (e) {
  process.stdout.write('FAIL ' + e.message.split('\\n')[0] + '\\n')
}
"""

# (document, stamp kwargs). Each is compiled, stamped, and compiled again.
CASES = {
    "tight list, nothing open": ("- one\n- two\n", {"child_blocks": True}),
    "expression spanning a blank line, top level": ('{\n\n"hello"}\n', {}),
    "expression spanning a blank line, in an item": ('- {\n\n  "hello"}\n',
                                                    {"child_blocks": True}),
    "expression on one line": ('- x{\n', {"child_blocks": True}),
    "comment closed with */ but not */}": ("- x{/* c */\n", {"child_blocks": True}),
    "comment properly closed": ("- x{/* c */}\n", {"child_blocks": True}),
    # ROUND 4 REVIEW (codex, 2026-09-10): brace counting is not a lexer. The `}` here
    # is inside a string, so the expression is still open and the predicate accepts.
    "a brace inside a string is not a closer": ('{"}"\n\n}\n', {}),
}


def mdx_dir():
    for candidate in (os.environ.get("MDX_DIR"), "mdx"):
        if candidate and pathlib.Path(candidate, "node_modules", "@mdx-js",
                                      "mdx").is_dir():
            return pathlib.Path(candidate)
    return None


def main():
    root = mdx_dir()
    if root is None:
        print("skipped: no @mdx-js/mdx found (see this file's docstring)")
        return 0
    js = root / "_markstay_compile.mjs"
    js.write_text(COMPILE_JS)
    doc = root / "_markstay_probe.mdx"

    def compiles(src):
        doc.write_text(src)
        r = subprocess.run(["node", js.name, doc.name], cwd=root,
                           capture_output=True, text=True)
        return r.stdout.strip()

    version = json.loads(
        (root / "node_modules/@mdx-js/mdx/package.json").read_text())["version"]
    print(f"@mdx-js/mdx {version}")
    regressions = []
    for name, (src, kw) in CASES.items():
        before = compiles(src)
        for mode in ("blank-line", "commonmark"):
            out = M.stamp(src, syntax="mdx", mode=mode, **kw).text
            if out == src:
                print(f"{name[:44]:44s} {mode:11s} nothing minted")
                continue
            after = compiles(out)
            verdict = ("REGRESSION" if before.startswith("OK") and
                       after.startswith("FAIL") else
                       "both fail" if after.startswith("FAIL") else "both ok")
            print(f"{name[:44]:44s} {mode:11s} {verdict}")
            if verdict == "REGRESSION":
                regressions.append((name, mode, after))
    js.unlink()
    doc.unlink()
    print(f"\n{len(regressions)} regressions: "
          f"{sorted({n for n, _, _ in regressions})}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
