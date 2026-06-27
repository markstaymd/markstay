#!/usr/bin/env python3
"""markstay render/formatter survival matrix.

Does a markstay marker survive the Markdown toolchain an adopter actually pushes
their `.md` through? This harness runs a pinned, representative set of formatters,
renderers, and HTML sanitizers over a small fixture corpus and records a
parser-verified verdict per (tool, axis) cell.

Two axes, two oracles (see classify.py):

- SOURCE ROUND-TRIP (md -> md): the load-bearing axis. markstay's value is
  edit-survival, so the question that matters is "does my formatter preserve the
  marker, on the right block, when it reflows the doc?". Oracle = the reference
  linter's `lint_diff` (DROPPED / RELOCATED / DUPLICATED) plus a marker-cleanliness
  check; a §8 hash drift on reflow is expected and never fails a cell.
- RENDER-EMIT (md -> HTML): the visibility axis. The marker should be invisible in
  the render (the good default for an HTML comment) and must not leak as visible
  text. For rehype-stay's `id=` emit, the third column measures whether the anchor
  survives an HTML sanitizer.

Offline and deterministic: every tool runs locally over vendored fixtures, no
network. Run the classifier self-tests first (test_render.py) so the matrix is only
trusted once the oracle is proven on hand-labelled cases.

    ./.venv/bin/python run.py            # write results.json + MATRIX.md + versions.json
    ./.venv/bin/python run.py --print    # also print the matrix to stdout

The harness needs mdformat + cmarkgfm + markdown (the eval venv); it re-execs into
./.venv if it was started with a bare python that cannot import them.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]                       # umbrella root
VENV_PY = HERE / ".venv" / "bin" / "python"

# Re-exec into the eval venv if the renderers we import in-process are missing.
# (A venv's bin/python symlinks to the base interpreter, so comparing resolved
# executable paths is unreliable; an env sentinel both detects "already re-exec'd"
# and prevents an infinite loop when the venv itself lacks the modules.)
try:
    import mdformat  # noqa: F401
    import cmarkgfm  # noqa: F401
    import markdown  # noqa: F401
except ModuleNotFoundError:
    if VENV_PY.exists() and not os.environ.get("MARKSTAY_RENDER_REEXEC"):
        os.environ["MARKSTAY_RENDER_REEXEC"] = "1"
        os.execv(str(VENV_PY), [str(VENV_PY), str(Path(__file__).resolve()), *sys.argv[1:]])
    raise

sys.path.insert(0, str(ROOT / "linter"))     # reuse the reference linter (lint_diff)
import markstay_lint as L  # noqa: E402

import classify  # noqa: E402

JS = HERE / "js" / "render.mjs"
FIX = HERE / "fixtures"


# --- tool runners ----------------------------------------------------------

def _run(cmd, text):
    p = subprocess.run(cmd, input=text, capture_output=True, text=True, cwd=str(HERE))
    return {"out": p.stdout, "err": p.stderr.strip() or None, "rc": p.returncode}


def run_node(tool, text):
    return _run(["node", str(JS), tool], text)


def run_prettier(text):
    return _run(["prettier", "--parser", "markdown"], text)


def run_pandoc(frm, to, text):
    return _run(["pandoc", "-f", frm, "-t", to], text)


def run_mdformat(text):
    return {"out": mdformat.text(text), "err": None, "rc": 0}


def run_cmarkgfm(text):
    # Default (safe) mode = GitHub's posture: raw HTML, including our comment, is
    # omitted from the render rather than passed through. This is exactly the §3.1
    # claim under test: invisible in the GitHub render.
    return {"out": cmarkgfm.github_flavored_markdown_to_html(text), "err": None, "rc": 0}


def run_pymarkdown(text):
    # python-markdown is MkDocs' engine (markstay's own site). tables + fenced_code
    # are the representative extensions every MkDocs theme enables.
    return {"out": markdown.markdown(text, extensions=["tables", "fenced_code"]),
            "err": None, "rc": 0}


# --- the pinned tool set (decision 1) --------------------------------------
# axis: roundtrip | render | sanitize. `run` maps fixture markdown -> a result
# dict. `remediation` is the §13 answer printed for a non-green cell.

HTML_FIXTURES = ["blocks", "blocks_trailing", "hash"]

TOOLS = [
    # --- source round-trip (md -> md) -------------------------------------
    {"key": "prettier", "label": "prettier", "axis": "roundtrip",
     "run": run_prettier, "fixtures": HTML_FIXTURES},
    {"key": "mdformat", "label": "mdformat", "axis": "roundtrip",
     "run": run_mdformat, "fixtures": HTML_FIXTURES},
    {"key": "remark", "label": "remark + remark-stringify", "axis": "roundtrip",
     "run": lambda t: run_node("remark", t), "fixtures": HTML_FIXTURES},
    {"key": "pandoc-gfm", "label": "pandoc (gfm → gfm)", "axis": "roundtrip",
     "run": lambda t: run_pandoc("gfm", "gfm", t), "fixtures": HTML_FIXTURES},
    {"key": "pandoc-markdown", "label": "pandoc (markdown → markdown)", "axis": "roundtrip",
     "run": lambda t: run_pandoc("markdown", "markdown", t), "fixtures": HTML_FIXTURES,
     "remediation": "trailing inline markers are rewritten to a `<!-- ... -->`{=html} "
                    "code span; keep markers on their own line (marker-only chunk) or "
                    "use the `gfm` writer, which preserves them"},
    {"key": "remark-mdx", "label": "remark-mdx (§3.2 round-trip)", "axis": "roundtrip",
     "run": lambda t: run_node("remark-mdx", t), "fixtures": ["mdx"]},

    # --- render-emit (md -> HTML) -----------------------------------------
    {"key": "github", "label": "GitHub (cmark-gfm)", "axis": "render",
     "run": run_cmarkgfm, "fixtures": HTML_FIXTURES},
    {"key": "markdown-it", "label": "markdown-it (html: true)", "axis": "render",
     "run": lambda t: run_node("markdown-it", t), "fixtures": HTML_FIXTURES},
    {"key": "markdown-it-default", "label": "markdown-it (default, html: false)", "axis": "render",
     "run": lambda t: run_node("markdown-it-default", t), "fixtures": HTML_FIXTURES,
     "remediation": "the default config HTML-escapes the comment to visible text; set "
                    "`html: true`, or rely on the consumer detecting a missing expected marker"},
    {"key": "marked", "label": "marked", "axis": "render",
     "run": lambda t: run_node("marked", t), "fixtures": HTML_FIXTURES},
    {"key": "python-markdown", "label": "python-markdown (MkDocs)", "axis": "render",
     "run": run_pymarkdown, "fixtures": HTML_FIXTURES},
    {"key": "mdx", "label": "MDX (@mdx-js/mdx)", "axis": "render", "classifier": "mdx",
     "run": lambda t: run_node("mdx", t), "fixtures": ["mdx", "blocks"], "primary": "mdx",
     "remediation": "the HTML-comment form is invalid MDX and is rejected at compile; "
                    "use the §3.2 `{/* stay:id */}` form (which compiles away invisibly)"},

    # --- sanitizers over rehype-stay's id= emit (gap 4) -------------------
    {"key": "rehype-sanitize", "label": "rehype-sanitize", "axis": "sanitize",
     "fixtures": ["blocks", "blocks_trailing"],
     "remediation": "GitHub's schema clobbers `id` to `user-content-<id>`, so the "
                    "anchor survives but the `doc.md#stay-id` deep link must target "
                    "the prefixed id (or the consumer re-derives it)"},
    {"key": "dompurify", "label": "DOMPurify", "axis": "sanitize",
     "fixtures": ["blocks", "blocks_trailing"]},
]

CLASSIFIERS = {
    "roundtrip": classify.roundtrip_verdict,
    "render": classify.render_verdict,
    "sanitize": classify.sanitizer_verdict,
    "mdx": classify.mdx_verdict,
}


def load_fixture(key):
    return (FIX / f"{key}.md").read_text()


def process_tool(tool):
    """Run one tool over its fixtures; return (cell, per_fixture_records)."""
    axis = tool["axis"]
    classifier = CLASSIFIERS[tool.get("classifier", axis)]
    records = []

    for fx in tool["fixtures"]:
        md = load_fixture(fx)
        if axis == "sanitize":
            # Sanitizers run over rehype-stay's emitted HTML, not the raw markdown.
            emit = run_node("rehype-stay", md)
            if emit["rc"] != 0:
                records.append({"fixture": fx, "verdict": "ERROR",
                                "note": "rehype-stay emit failed: %s" % classify._first_line(emit["err"])})
                continue
            res = run_node(tool["key"], emit["out"])
            v = classifier(emit["out"], res)
        else:
            res = tool["run"](md)
            v = classifier(md, res)
        records.append({"fixture": fx, **v})

    # Cell verdict = worst across fixtures, except MDX whose headline is its §3.2
    # (primary) fixture; the HTML-comment ERROR is the documented limitation, noted
    # but not the headline.
    sev_axis = "render" if axis == "render" else axis
    if tool.get("primary"):
        primary = next(r for r in records if r["fixture"] == tool["primary"])
        cell_verdict = primary["verdict"]
    else:
        cell_verdict = classify.worst(sev_axis, [r["verdict"] for r in records])

    # Cell note: the note from the fixture that produced the headline verdict, plus a
    # short tail when a non-primary fixture diverges (e.g. trailing vs marker-only).
    lead = next(r for r in records if r["verdict"] == cell_verdict)
    note = lead["note"]
    divergent = sorted({r["fixture"] for r in records if r["verdict"] != cell_verdict})
    if tool.get("primary"):
        others = [r for r in records if r["fixture"] != tool["primary"]]
        if others:
            note += "; %s fixture: %s" % (others[0]["fixture"], others[0]["verdict"])
    elif divergent:
        note += " (differs on: %s)" % ", ".join(divergent)

    cell = {
        "key": tool["key"], "label": tool["label"], "axis": axis,
        "verdict": cell_verdict, "note": note,
        "remediation": tool.get("remediation"),
        "fixtures": {r["fixture"]: {"verdict": r["verdict"], "note": r["note"]} for r in records},
    }
    return cell, records


# --- version pinning (Phase 0 guardrail) -----------------------------------

def _ver_cli(cmd, prefix=""):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True).stdout.strip()
        return out.splitlines()[0].replace(prefix, "").strip() if out else "?"
    except Exception as e:  # noqa: BLE001
        return "unavailable: %s" % e


def capture_versions():
    import importlib.metadata as md
    versions = {
        "pandoc": _ver_cli(["pandoc", "--version"], "pandoc "),
        "prettier": _ver_cli(["prettier", "--version"]),
        "node": _ver_cli(["node", "--version"]),
        "python": sys.version.split()[0],
    }
    for pkg in ("mdformat", "cmarkgfm", "markdown", "markdown-it-py"):
        try:
            versions[pkg] = md.version(pkg)
        except Exception:  # noqa: BLE001
            versions[pkg] = "unavailable"
    # JS renderers from the pinned lockfile.
    lock = HERE / "js" / "package-lock.json"
    if lock.exists():
        data = json.loads(lock.read_text())
        for name in ("markdown-it", "marked", "remark-parse", "remark-stringify",
                     "remark-mdx", "@mdx-js/mdx", "rehype-sanitize", "dompurify",
                     "remark-rehype", "rehype-stringify"):
            p = data.get("packages", {}).get("node_modules/" + name)
            if p:
                versions["npm:" + name] = p["version"]
    return versions


# --- matrix rendering ------------------------------------------------------

VERDICT_MARK = {
    "SURVIVES": "✅ SURVIVES", "INVISIBLE": "✅ INVISIBLE", "ID_SURVIVES": "✅ ID kept",
    "MANGLED": "⚠️ MANGLED", "ID_PREFIXED": "⚠️ ID renamed",
    "LEAKED_VISIBLE": "❌ LEAKED", "DROPPED": "❌ DROPPED", "RELOCATED": "❌ RELOCATED",
    "DUPLICATED": "❌ DUPLICATED", "ID_STRIPPED": "❌ ID stripped",
    "ERROR": "❌ ERROR",
}


def render_matrix_md(cells, versions):
    by_axis = {"roundtrip": [], "render": [], "sanitize": []}
    for c in cells:
        by_axis[c["axis"]].append(c)

    out = []
    out.append("# markstay render-survival matrix\n")
    out.append("Does a `stay:` marker survive the Markdown toolchain people push `.md` "
               "through? Each verdict is parser-verified by the reference linter "
               "(round-trip) or by HTML inspection (render/sanitize), not grepped. "
               "Generated by `run.py`; the classifier is proven on hand-labelled cases "
               "in `test_render.py`. Parser mode pinned: `%s`.\n" % classify.PARSE_MODE)
    out.append("Legend: ✅ survives · ⚠️ survives but degraded "
               "(named below) · ❌ lost.\n")

    out.append("## Source round-trip (md → md) — the load-bearing axis\n")
    out.append("Does the formatter preserve the marker, on the right block, when it "
               "reflows the doc? A §8 hash drift on reflow is expected and is **not** a "
               "failure.\n")
    out.append("| Tool | Verdict | Notes |")
    out.append("|------|---------|-------|")
    for c in by_axis["roundtrip"]:
        out.append("| `%s` | %s | %s |" % (c["label"], VERDICT_MARK[c["verdict"]], _cellnote(c)))
    out.append("")

    out.append("## Render-emit (md → HTML) — the visibility axis\n")
    out.append("The marker should be invisible in the render (the good default for a "
               "comment) and must not leak as visible text.\n")
    out.append("| Tool | Verdict | Notes |")
    out.append("|------|---------|-------|")
    for c in by_axis["render"]:
        out.append("| `%s` | %s | %s |" % (c["label"], VERDICT_MARK[c["verdict"]], _cellnote(c)))
    out.append("")

    out.append("## Anchor after sanitizer (rehype-stay `id=` emit) — gap 4\n")
    out.append("Does the HTML `id=` that makes `doc.md#stay-id` resolve survive an HTML "
               "sanitizer?\n")
    out.append("| Sanitizer | Verdict | Notes |")
    out.append("|-----------|---------|-------|")
    for c in by_axis["sanitize"]:
        out.append("| `%s` | %s | %s |" % (c["label"], VERDICT_MARK[c["verdict"]], _cellnote(c)))
    out.append("")

    out.append("## Pinned versions\n")
    out.append("A re-run on a version bump re-measures rather than trusting these "
               "verdicts (see `versions.json`).\n")
    out.append("| Tool | Version |")
    out.append("|------|---------|")
    for k, v in versions.items():
        out.append("| `%s` | %s |" % (k, v))
    out.append("")
    return "\n".join(out)


_GREEN = ("SURVIVES", "INVISIBLE", "ID_SURVIVES")


def _cellnote(c):
    note = c["note"]
    # Show the §13 remediation when the headline verdict is non-green, OR when a
    # green headline still hides a per-fixture failure (MDX: §3.2 renders fine, but
    # the HTML-comment form is rejected — the adopter needs that caveat).
    fixture_failed = any(v["verdict"] not in _GREEN for v in c["fixtures"].values())
    if c["remediation"] and (c["verdict"] not in _GREEN or fixture_failed):
        note += " — **→** %s" % c["remediation"]
    return note


# --- main ------------------------------------------------------------------

def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--print", action="store_true", help="print the matrix to stdout")
    ap.add_argument("--no-self-test", action="store_true",
                    help="skip the classifier self-tests (not recommended)")
    args = ap.parse_args()

    if not args.no_self_test:
        import test_render
        test_render.run_self_tests()  # raises on failure: the matrix is untrusted otherwise

    versions = capture_versions()
    (HERE / "versions.json").write_text(json.dumps(versions, indent=2) + "\n")

    cells = []
    all_records = []
    for tool in TOOLS:
        cell, records = process_tool(tool)
        cells.append(cell)
        for r in records:
            all_records.append({"tool": tool["key"], "axis": tool["axis"], **r})
        print("  %-34s %s" % (cell["label"], cell["verdict"]), file=sys.stderr)

    results = {"parse_mode": classify.PARSE_MODE, "versions": versions,
               "cells": cells, "records": all_records}
    (HERE / "results.json").write_text(json.dumps(results, indent=2) + "\n")

    matrix = render_matrix_md(cells, versions)
    (HERE / "MATRIX.md").write_text(matrix)
    print("wrote results.json, MATRIX.md, versions.json", file=sys.stderr)
    if args.print:
        print(matrix)


if __name__ == "__main__":
    main()
