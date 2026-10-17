#!/usr/bin/env python3
"""Djot carrier evidence: where does each parser attach a `{stay=…}` specifier?

Runs every fixture in fixtures/ through djot.js, jotdown and pandoc's Djot reader,
finds every node carrying a stay (a `stay` key, an `#id` equal to a fixture's id, or a
comment naming one), and reports, per stay and parser, the canonical kind and text of
the node it landed on. Two more axes for the parsers that can write Djot: does the
stay land in the same place after the parser's own Djot round-trip, and is the id
visible in the rendered HTML text.

    python3 run.py            # writes results.json + MATRIX.md, prints the summary
    python3 run.py --check    # also exit 1 if MATRIX.md is stale

PANDOC names a pandoc with a `djot` reader (3.3 or later); README.md says how to
fetch the pinned one. Nothing here is normative: the matrix is what the parsers did,
and FINDINGS.md says what the spec should take from it.
"""

import html
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
JOTDOWN = HERE / "rs" / "target" / "release" / "jotdown-dump"
PANDOC = os.environ.get("PANDOC", "pandoc")
PARSERS = ("djotjs", "djotjs-main", "jotdown", "pandoc")  # the Djot readers
WRITERS = ("djotjs", "djotjs-main", "pandoc", "carve")
JS_ARG = {"djotjs": [], "djotjs-main": ["main"], "carve": ["carve"]}


def sh(cmd, text, cwd=None):
    r = subprocess.run(cmd, input=text, capture_output=True, text=True, cwd=cwd)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd[0]} failed: {r.stderr.strip()}")
    return r.stdout


def preflight():
    formats = sh([PANDOC, "--list-input-formats"], "")
    if "djot" not in formats.split():
        sys.exit(f"{PANDOC} has no djot reader; set PANDOC (README.md, Setup)")
    if not (HERE / "js" / "node_modules" / "@djot" / "djot").is_dir():
        sys.exit("djot.js missing: (cd js && npm ci)")
    if not JOTDOWN.exists():
        sh(["cargo", "build", "--release", "--locked", "-q"], "", cwd=HERE / "rs")


def versions():
    lock = json.loads((HERE / "js" / "package-lock.json").read_text())
    main_ref = lock["packages"]["node_modules/djot-main"]["resolved"].rsplit("#", 1)[-1]
    cargo_lock = (HERE / "rs" / "Cargo.lock").read_text()
    jot = re.search(r'name = "jotdown"\nversion = "([^"]+)"', cargo_lock)
    if jot is None:
        sys.exit("rs/Cargo.lock has no jotdown entry")
    return {
        "djotjs": lock["packages"]["node_modules/@djot/djot"]["version"],
        "djotjs-main": main_ref[:12],
        "carve": lock["packages"]["node_modules/@markup-carve/carve"]["version"],
        "jotdown": jot.group(1),
        "pandoc": sh([PANDOC, "--version"], "").splitlines()[0].split()[-1],
    }


# ---------------------------------------------------------------- normalisers
# Each yields (kind, attrs, text) for every node, attrs as a list of (key, value)
# pairs in source order, with `#id` as ("#", id) and a comment as ("%", body).

BLOCK_KINDS = {
    "djotjs": {
        "heading": "heading", "para": "para", "bullet_list": "list",
        "ordered_list": "list", "task_list": "list", "definition_list": "list",
        "list_item": "item", "task_list_item": "item", "table": "table", "row": "row",
        "cell": "cell", "code_block": "code", "block_quote": "quote", "div": "div",
        "section": "section", "thematic_break": "break", "footnote": "footnote",
        "caption": "caption", "doc": "doc",
    },
    "jotdown": {
        "Heading": "heading", "Paragraph": "para", "List": "list", "ListItem": "item",
        "TaskListItem": "item", "DescriptionList": "list", "Table": "table",
        "TableRow": "row", "TableCell": "cell", "CodeBlock": "code",
        "Blockquote": "quote", "Div": "div", "Section": "section",
        "ThematicBreak": "break", "Footnote": "footnote", "Caption": "caption",
        "Document": "doc", "root": "doc", "DanglingAttributes": "dangling",
    },
}


def squash(s):
    return " ".join(s.split())


def djotjs_text(n):
    if n.get("tag") in ("soft_break", "hard_break"):
        return " "
    own = n.get("text", "") if n.get("tag") in ("str", "verbatim", "code_block") else ""
    return own + "".join(djotjs_text(c) for c in n.get("children", []))


def walk_djotjs(ast):
    def visit(n):
        attrs = []
        for k, v in (n.get("attributes") or {}).items():
            attrs.append(("#", v) if k == "id" else (k, v))
        kind = BLOCK_KINDS["djotjs"].get(n.get("tag"), "inline")
        yield kind, attrs, squash(djotjs_text(n))
        for c in n.get("children", []):
            yield from visit(c)

    yield from visit(ast)
    for fn in (ast.get("footnotes") or {}).values():
        yield from visit(fn)


CARVE_KINDS = {
    "heading": "heading", "paragraph": "para", "list": "list", "list_item": "item",
    "definition_list": "list", "table": "table", "table_row": "row",
    "table_cell": "cell", "code_block": "code", "block_quote": "quote", "div": "div",
    "section": "section", "thematic_break": "break", "admonition": "div",
    "figure": "figure", "document": "doc",
}


def carve_text(n):
    if isinstance(n, list):
        return "".join(carve_text(c) for c in n)
    if not isinstance(n, dict):
        return ""
    if n.get("type") in ("soft_break", "hard_break"):
        return " "
    own = n.get("value", "") if n.get("type") in ("text", "code") else ""
    if n.get("type") == "code_block":
        own = n.get("content", "")
    return own + "".join(carve_text(n[k]) for k in ("children", "items", "rows", "cells")
                         if k in n)


def walk_carve(ast):
    """Carve nodes are dicts with a `type`; children sit under several keys, so
    visit every dict reachable from the node rather than naming them."""
    def visit(x):
        if isinstance(x, list):
            for i in x:
                yield from visit(i)
            return
        if not isinstance(x, dict):
            return
        if "type" in x:
            a = x.get("attrs") or {}
            attrs = ([("#", a["id"])] if a.get("id") else []) \
                + [(".", c) for c in a.get("classes", [])] \
                + list((a.get("keyValues") or {}).items())
            if x["type"] == "comment":
                attrs.append(("%", x.get("content", "")))  # a block node of its own
            kind = CARVE_KINDS.get(x["type"], "inline")
            yield kind, attrs, squash(carve_text(x))
        for k, v in x.items():
            if k not in ("attrs", "pos") and isinstance(v, (list, dict)):
                yield from visit(v)

    yield from visit(ast)


def walk_jotdown(tree):
    def visit(n):
        attrs = []
        for kind, key, value in n["attrs"]:
            attrs.append({"id": ("#", value), "comment": ("%", value),
                          "class": (".", value)}.get(kind, (key, value)))
        yield BLOCK_KINDS["jotdown"].get(n["tag"], "inline"), attrs, squash(n["text"])
        for c in n["children"]:
            yield from visit(c)

    yield from visit(tree)


# pandoc JSON: where each element type keeps its Attr, and which part holds children.
PANDOC_ATTR = {"Header": 1, "Div": 0, "CodeBlock": 0, "Table": 0, "Row": 0, "Cell": 0,
               "Span": 0, "Code": 0, "Link": 0, "Image": 0, "Figure": 0}
PANDOC_KIND = {"Header": "heading", "Para": "para", "Plain": "para", "BulletList": "list",
               "OrderedList": "list", "DefinitionList": "list", "Table": "table",
               "Row": "row", "Cell": "cell", "CodeBlock": "code", "BlockQuote": "quote",
               "Div": "div", "HorizontalRule": "break", "Note": "footnote",
               "Figure": "figure"}


def pandoc_text(x):
    if isinstance(x, dict):
        t = x.get("t")
        if t == "Str":
            return x["c"]
        if t in ("Space", "SoftBreak", "LineBreak"):
            return " "
        if t == "CodeBlock":
            return x["c"][1]
        return pandoc_text(x.get("c"))
    if isinstance(x, list):
        return "".join(pandoc_text(i) for i in x)
    return ""


def pandoc_blocks(x):
    """Direct block children of a Div, for unwrapping pandoc's attribute wrapper."""
    return [b for b in x["c"][1] if isinstance(b, dict)]


def walk_pandoc(doc):
    def visit(x):
        if isinstance(x, list):
            for i in x:
                yield from visit(i)
            return
        if not isinstance(x, dict) or "t" not in x:
            return
        t = x["t"]
        attrs, kind = [], PANDOC_KIND.get(t, "inline")
        if t in PANDOC_ATTR:
            ident, classes, kvs = x["c"][PANDOC_ATTR[t]]
            kv = [tuple(p) for p in kvs]
            if ("wrapper", "1") in kv:
                # pandoc has no Attr on Para or a list, so its Djot reader wraps the
                # block in a Div marked wrapper=1. Report the wrapped block's kind.
                kv.remove(("wrapper", "1"))
                if t == "Div":
                    inner = pandoc_blocks(x)
                    kind = PANDOC_KIND.get(inner[0]["t"], "inline") if len(inner) == 1 else "div"
            elif t == "Div" and "section" in classes:
                kind = "section"
            attrs = ([("#", ident)] if ident else []) + [(".", c) for c in classes] + kv
        yield kind, attrs, squash(pandoc_text(x))
        if isinstance(x.get("c"), (list, dict)):
            yield from visit(x["c"])

    yield from visit(doc["blocks"])


# ---------------------------------------------------------------- observation

def observe(nodes, ids):
    """Where each stay id landed: a list of {kind, text, keys} (empty = nowhere)."""
    found = {i: [] for i in ids}
    for kind, attrs, text in nodes:
        for key, value in attrs:
            hit = None
            if key in ("stay", "#") and value in found:
                hit = value
            elif key == "%":
                m = re.search(r"stay:(\S+)", value)
                hit = m.group(1) if m and m.group(1) in found else None
            if hit:
                keys = {k: v for k, v in attrs if k.startswith("stay-")}
                found[hit].append({"kind": kind, "text": text[:24], "via": key,
                                   "keys": keys})
    return found


def verdict(want, got):
    if want["kind"] in ("content", "none"):
        return "as-intended" if not got else "read-as-marker"
    if not got:
        return "lost"
    hits = [g for g in got if g["kind"] == want["kind"] and g["text"].startswith(want["text"])]
    if hits and len(got) == 1:
        return "as-intended"
    if hits:
        return "as-intended+duplicate"
    g = got[0]
    if g["kind"] == "dangling":
        return "dangling"
    return f"elsewhere:{g['kind']}"


def visible_in_html(page, ids):
    text = html.unescape(re.sub(r"<[^>]*>", " ", page))
    return sorted(i for i in ids if i in text)


def run_fixture(fx):
    src = (FIXTURES / f"{fx['name']}.dj").read_text()
    ids = list(fx["want"])
    js = {p: json.loads(sh(["node", "js/dump.mjs", *JS_ARG[p]], src, cwd=HERE))
          for p in JS_ARG}
    jot = json.loads(sh([str(JOTDOWN)], src))
    pan = json.loads(sh([PANDOC, "-f", "djot", "-t", "json"], src))
    got = {
        "djotjs": observe(walk_djotjs(js["djotjs"]["ast"]), ids),
        "djotjs-main": observe(walk_djotjs(js["djotjs-main"]["ast"]), ids),
        "jotdown": observe(walk_jotdown(jot), ids),
        "pandoc": observe(walk_pandoc(pan), ids),
        "carve": observe(walk_carve(js["carve"]["ast"]), ids),
    }
    # Round-trip through each writer, re-read by the same parser.
    rt_src = {p: js[p]["djot"] for p in JS_ARG}
    rt_src["pandoc"] = sh([PANDOC, "-f", "djot", "-t", "djot"], src)
    walker = {"djotjs": walk_djotjs, "djotjs-main": walk_djotjs, "carve": walk_carve}
    roundtrip = {p: observe(walker[p](json.loads(sh(
        ["node", "js/dump.mjs", *JS_ARG[p]], rt_src[p], cwd=HERE))["ast"]), ids)
        for p in JS_ARG}
    roundtrip["pandoc"] = observe(walk_pandoc(json.loads(sh(
        [PANDOC, "-f", "djot", "-t", "json"], rt_src["pandoc"]))), ids)
    pan_html = sh([PANDOC, "-f", "djot", "-t", "html"], src)
    row = {"name": fx["name"], "about": fx["about"], "source": src, "stays": {}}
    for i in ids:
        want = fx["want"][i]
        row["stays"][i] = {
            "want": want,
            "parsers": {p: {"got": got[p][i], "verdict": verdict(want, got[p][i])}
                        for p in PARSERS + ("carve",)},
            "roundtrip": {p: {"got": roundtrip[p][i],
                              "same": roundtrip[p][i] == got[p][i]}
                          for p in roundtrip},
        }
    pages = {p: js[p]["html"] for p in JS_ARG}
    pages["pandoc"] = pan_html
    row["visible"] = {p: visible_in_html(h, ids) for p, h in pages.items()}
    row["html_ids"] = {p: re.findall(r'\bid="([^"]+)"', h) for p, h in pages.items()}
    row["roundtrip_source"] = rt_src
    return row


# ---------------------------------------------------------------- report

CURRENT = ("djotjs-main", "jotdown", "pandoc")  # 0.3.2 is superseded by main


def placement(got):
    """The blocks a stay landed on. Inline, dangling and absent all mean the same
    thing to markstay, no block stay, so they compare equal."""
    return sorted((g["kind"], g["text"]) for g in got
                  if g["kind"] not in ("inline", "dangling"))


def agreement(stay, parsers=PARSERS):
    places = {json.dumps(placement(stay["parsers"][p]["got"])) for p in parsers}
    return "agree" if len(places) == 1 else "DISAGREE"


def matrix(rows, vers):
    out = ["# Djot carrier matrix", "",
           "Generated by `run.py`; do not edit. Versions: "
           + ", ".join(f"{k} {v}" for k, v in vers.items()) + ".", "",
           "Verdict is against the fixture's intent (what markstay would want the stay "
           "to mean), not against the Djot spec. `elsewhere:K` = attached to a K that "
           "is not the intended block; `dangling` = parsed, attached to nothing; "
           "`lost` = no trace in the tree. The two agreement columns compare block "
           "placement only: inline, dangling and lost all mean no block stay. Round-trip `changed`/`lost` is the stay's "
           "place after the parser's own Djot writer, re-read by the same parser.", "",
           "| fixture | stay | want | djot.js 0.3.2 | djot.js main | jotdown | pandoc | all four | current three | carve | carve = main | 0.3.2 rt | main rt | pandoc rt | visible |",
           "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for i, s in r["stays"].items():
            w = s["want"]
            cells = [s["parsers"][p]["verdict"] for p in PARSERS]
            rt = []
            for p in WRITERS:
                x = s["roundtrip"][p]
                rt.append("same" if x["same"] else ("lost" if not x["got"] else "changed"))
            vis = ", ".join(p for p, v in r["visible"].items() if i in v) or "no"
            out.append(f"| {r['name']} | `{i}` | {w['kind']} {w['text']!r} | "
                       + " | ".join(cells) + f" | {agreement(s)} | {agreement(s, CURRENT)} | "
                       + f"{s['parsers']['carve']['verdict']} | {agreement(s, ('djotjs-main', 'carve'))} | "
                       + " | ".join(rt) + f" | {vis} |")
    return "\n".join(out) + "\n"


def main():
    preflight()
    vers = versions()
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    rows = [run_fixture(fx) for fx in manifest]
    (HERE / "results.json").write_text(
        json.dumps({"versions": vers, "fixtures": rows}, indent=1, ensure_ascii=False) + "\n")
    text = matrix(rows, vers)
    stale = (HERE / "MATRIX.md").exists() and (HERE / "MATRIX.md").read_text() != text
    (HERE / "MATRIX.md").write_text(text)
    stays = [s for r in rows for s in r["stays"].values()]
    dis = sum(agreement(s) == "DISAGREE" for s in stays)
    cur = sum(agreement(s, CURRENT) == "DISAGREE" for s in stays)
    print(f"{len(rows)} fixtures, {len(stays)} stays; block placement differs on "
          f"{dis} across all four parsers, {cur} across the current three")
    car = [r["name"] for r in rows for s in r["stays"].values()
           if agreement(s, ("djotjs-main", "carve")) == "DISAGREE"]
    print(f"Carve places {len(car)} stays differently from djot.js main: {', '.join(car)}")
    if "--check" in sys.argv and stale:
        sys.exit("MATRIX.md was stale and has been rewritten")


if __name__ == "__main__":
    main()
