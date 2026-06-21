"""Dogfood-simulation runner: realistic 'update this document' passes over a
stay-seeded Markdown corpus, scored by the §11 regeneration diff.

Needs an Anthropic key: export ANTHROPIC_API_KEY first.

    python run_dogfood.py --smoke                       # one cheap cell, sanity
    python run_dogfood.py --models sonnet --sample 12   # the real run
    python run_dogfood.py --models sonnet,haiku --sample 12 --arms naive,instructed

Docs are read live from --docs-dir (default the bundled `corpus/`) and sampled
deterministically (smallest-by-words eligible docs first). The report anonymizes
doc names (doc01..); the name->label map and per-cell metrics live only in the JSON
written under --out (default /tmp, outside the repo). Point --docs-dir at one corpus
subdir at a time (e.g. corpus/fastapi) to reproduce a single result table.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path

import dogfood_sim as D
from llm_io import complete_meta

DEFAULT_DOCS_DIR = Path(__file__).resolve().parent / "corpus"
EXCLUDE_NAMES = {"INDEX.md"}  # auto-generated; markers would be wiped on regen


def eligible_docs(docs_dir: Path, word_cap: int):
    # rglob so nested doc trees (FastAPI's advanced/, tutorial/, ...) are found,
    # not just a flat dir. Sort/key on the path relative to docs_dir so same-named
    # files in different subdirs stay distinct.
    out = []
    for p in sorted(docs_dir.rglob("*.md")):
        if p.name in EXCLUDE_NAMES:
            continue
        text = p.read_text()
        if "stay:" not in text:
            continue
        words = len(text.split())
        if words > word_cap:
            continue
        rel = str(p.relative_to(docs_dir))
        out.append((words, p, rel))
    out.sort(key=lambda t: (t[0], t[2]))
    return out


async def judge_drops(judge_model, after_md, dropped_content, max_tokens):
    """Rule survived/deleted on every dropped section in one batched judge call."""
    items = list(dropped_content.items())  # [(id, content), ...] stable order
    if not items:
        return {}
    prompt = D.build_judge_prompt(after_md, items)
    raw, _ = await complete_meta(judge_model, prompt, max_tokens)
    return D.parse_judge(raw, items)


async def run_cell(sem, cell, docs, max_tokens, trunc_ratio, judge_model):
    name = cell["doc"]
    before_md = docs[name]
    preserve = cell["preserve_text"] if cell["arm"] == "instructed" else None
    prompt = D.build_prompt(cell["task"], before_md, preserve)
    async with sem:
        for attempt in range(2):
            try:
                raw, hit_cap = await complete_meta(cell["model"], prompt, max_tokens)
                after_md = D.strip_outer_fence(raw)
                # truncation guard: explicit cap, or output drastically shorter
                # than the source (heuristic for models without stop_reason).
                short = len(after_md) < trunc_ratio * len(before_md)
                cell["truncated"] = bool(hit_cap) or (hit_cap is None and short)
                cell["len_ratio"] = round(len(after_md) / max(1, len(before_md)), 3)
                metrics, dropped_content = D.classify_structural(before_md, after_md)
                # Judge only non-truncated cells with drops (truncated cells are
                # excluded from stats anyway; no drops -> nothing to rule on).
                verdicts = {}
                if not cell["truncated"]:
                    verdicts = await judge_drops(judge_model, after_md,
                                                 dropped_content, max_tokens)
                cell["metrics"] = D.finalize(metrics, verdicts).to_dict()
                cell["ok"] = True
                return cell
            except Exception as e:  # noqa: BLE001
                cell["error"] = f"{type(e).__name__}: {e}"
                if attempt == 0:
                    await asyncio.sleep(3)
    cell["ok"] = False
    return cell


# --- aggregation + report -----------------------------------------------------

def pct(num, den):
    return f"{round(100 * num / den):3d}" if den else "  -"


def summarize(cells):
    ok = [c for c in cells if c.get("ok")]
    usable = [c for c in ok if not c.get("truncated")]
    excluded = len(ok) - len(usable)

    def agg(rows):
        stays = sum(c["metrics"]["n_stays"] for c in rows)
        cdrops = sum(c["metrics"]["n_content_drops"] for c in rows)
        mstrips = sum(c["metrics"]["n_marker_strips"] for c in rows)
        unknown = sum(len(c["metrics"]["judge_unknown"]) for c in rows)
        cells_with_cdrop = sum(1 for c in rows if c["metrics"]["n_content_drops"])
        cells_with_mstrip = sum(1 for c in rows if c["metrics"]["n_marker_strips"])
        blocked = sum(1 for c in rows if c["metrics"]["caught"])
        guard = sum(1 for c in rows if c["metrics"]["is_guard"])
        nag = sum(1 for c in rows if c["metrics"]["is_nag"])
        relocated = sum(c["metrics"]["relocated"] for c in rows)
        duplicated = sum(c["metrics"]["duplicated"] for c in rows)
        hash_drift = sum(c["metrics"]["hash_drift"] for c in rows)
        return dict(n=len(rows), stays=stays, cdrops=cdrops, mstrips=mstrips,
                    unknown=unknown,
                    cells_with_cdrop=cells_with_cdrop, cells_with_mstrip=cells_with_mstrip,
                    blocked=blocked, guard=guard, nag=nag,
                    relocated=relocated, duplicated=duplicated, hash_drift=hash_drift)

    return usable, excluded, agg


def group_by(rows, key):
    d = {}
    for r in rows:
        d.setdefault(r[key], []).append(r)
    return d


def write_report(path, meta, cells, docmap):
    usable, excluded, agg = summarize(cells)
    A = agg(usable)
    L = []
    L.append("# Dogfood simulation results: §11 catch on a stay-seeded corpus\n")
    L.append(f"Models: {meta['models']}  |  arms: {meta['arms']}  |  "
             f"tasks: {', '.join(meta['tasks'])}  |  docs sampled: {len(docmap)}\n")
    L.append(f"Cells: {meta['n_cells']} run, {meta['n_ok']} ok, "
             f"{meta['n_cells'] - meta['n_ok']} failed, {excluded} excluded "
             f"(output truncated at the token cap, drop stats unreliable). "
             f"Scored on {A['n']} usable cells.\n")
    L.append(
        "Each cell asks a model to perform a realistic document update and return "
        "the whole document, then runs the linter's regeneration diff (the exact "
        "pre-commit catch). A `DROPPED_ID` is split into a **content drop** (the "
        "section is genuinely gone, the catch earns its keep) and a **marker strip** "
        "(the section survived, only its `stay:` marker was lost, a false-positive "
        "nag). The split is decided by an LLM judge reading the whole edited "
        "document, not a string heuristic. `naive` = no preservation instruction "
        "(uninstructed session); `instructed` = the real §11 PRESERVE.md guidance "
        "prepended.\n")

    L.append("\n## Headline\n")
    L.append(f"- **Section-drop propensity:** {A['cdrops']} real content drops across "
             f"{A['stays']} seeded stays ({pct(A['cdrops'], A['stays'])}%); "
             f"{A['cells_with_cdrop']} of {A['n']} cells dropped at least one section "
             f"({pct(A['cells_with_cdrop'], A['n'])}% of cells).")
    L.append(f"- **Catch outcome:** {A['blocked']} of {A['n']} cells would be blocked "
             f"by the hook ({pct(A['blocked'], A['n'])}%): {A['guard']} as a genuine "
             f"guard (caught a real content drop), {A['nag']} as a nag (blocked on "
             f"content that survived).")
    L.append(f"- **Marker-strip rate (the friction):** {A['mstrips']} markers stripped "
             f"off surviving content across {A['stays']} stays "
             f"({pct(A['mstrips'], A['stays'])}%); {A['cells_with_mstrip']} of {A['n']} "
             f"cells ({pct(A['cells_with_mstrip'], A['n'])}%) would be blocked at "
             f"least partly on a strip, not a real loss.")
    if A['guard'] + A['nag']:
        L.append(f"- **Guard-vs-nag split of blocked commits:** "
                 f"{pct(A['guard'], A['guard'] + A['nag'])}% guard / "
                 f"{pct(A['nag'], A['guard'] + A['nag'])}% nag.")
    if A['unknown']:
        L.append(f"- Judge was unsure on {A['unknown']} dropped id(s) "
                 f"(counted as neither drop nor strip; guard is a lower bound).")
    L.append(f"- Other findings: relocated {A['relocated']}, duplicated "
             f"{A['duplicated']}, benign hash-drift {A['hash_drift']}.\n")

    def table(title, groups, order=None):
        L.append(f"\n## {title}\n")
        L.append("| group | cells | stays | content-drops | marker-strips | "
                 "blocked | guard | nag |")
        L.append("|-------|------:|------:|--------------:|--------------:|"
                 "--------:|------:|----:|")
        for k in (order or sorted(groups)):
            if k not in groups:
                continue
            a = agg(groups[k])
            L.append(f"| {k} | {a['n']} | {a['stays']} | {a['cdrops']} | "
                     f"{a['mstrips']} | {a['blocked']} | {a['guard']} | {a['nag']} |")

    table("By task (low -> high churn)", group_by(usable, "task"),
          order=list(D.TASKS))
    table("By arm (naive vs §11-instructed)", group_by(usable, "arm"),
          order=["naive", "instructed"])
    table("By model", group_by(usable, "model"))
    table("By document (anonymized)", group_by(usable, "doc_label"))

    # Every real content drop, named (anonymized doc), the cases the catch exists for.
    L.append("\n## Real content drops (every true positive)\n")
    tps = [c for c in usable if c["metrics"]["n_content_drops"]]
    if tps:
        L.append("| doc | task | arm | model | sections dropped | ids |")
        L.append("|-----|------|-----|-------|-----------------:|-----|")
        for c in sorted(tps, key=lambda c: -c["metrics"]["n_content_drops"]):
            ids = ", ".join(c["metrics"]["content_drops"])
            L.append(f"| {c['doc_label']} | {c['task']} | {c['arm']} | {c['model']} | "
                     f"{c['metrics']['n_content_drops']} | {ids} |")
    else:
        L.append("None: no realistic update silently dropped a whole seeded section "
                 "across the scored cells.\n")

    Path(path).write_text("\n".join(L) + "\n")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="sonnet")
    ap.add_argument("--arms", default="naive")
    ap.add_argument("--tasks", default=",".join(D.TASKS))
    ap.add_argument("--docs-dir", default=str(DEFAULT_DOCS_DIR))
    ap.add_argument("--sample", type=int, default=12, help="N smallest eligible docs")
    ap.add_argument("--word-cap", type=int, default=3500,
                    help="skip docs longer than this (keeps rewrites under the token cap)")
    ap.add_argument("--max-tokens", type=int, default=16000)
    ap.add_argument("--trunc-ratio", type=float, default=0.45,
                    help="flag output shorter than this fraction of source as truncated")
    ap.add_argument("--judge-model", default="haiku",
                    help="model that rules survived/deleted on dropped sections")
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--smoke", action="store_true", help="one cheap cell only")
    ap.add_argument("--preserve-file", default="",
                    help="path to PRESERVE.md for the instructed arm; default "
                         "<docs-dir>/../.markstay/PRESERVE.md (the install.sh layout)")
    ap.add_argument("--out", default="/tmp/markstay-dogfood/sim-results")
    args = ap.parse_args()

    docs_dir = Path(args.docs_dir).expanduser()
    if not docs_dir.is_dir():
        sys.exit(f"docs-dir not found: {docs_dir}")
    preserve_path = Path(args.preserve_file).expanduser() if args.preserve_file \
        else docs_dir.parent / ".markstay" / "PRESERVE.md"
    preserve_text = preserve_path.read_text() if preserve_path.exists() else None
    if "instructed" in args.arms.split(",") and not preserve_text:
        sys.exit(f"instructed arm needs PRESERVE.md (not found at {preserve_path})")

    elig = eligible_docs(docs_dir, args.word_cap)
    if not elig:
        sys.exit(f"no eligible seeded docs under {docs_dir}")
    chosen = elig[: args.sample]
    docmap = {rel: p.read_text() for _, p, rel in chosen}
    # stable anonymized labels (doc01..) by sample order; map kept only in JSON
    labels = {name: f"doc{idx + 1:02d}" for idx, name in enumerate(docmap)}

    models = args.models.split(",")
    arms = args.arms.split(",")
    tasks = args.tasks.split(",")

    cells = []
    if args.smoke:
        name = next(iter(docmap))
        cells.append(dict(model=models[0], doc=name, doc_label=labels[name],
                          task=tasks[0], arm=arms[0], preserve_text=preserve_text))
    else:
        for model in models:
            for arm in arms:
                for name in docmap:
                    for task in tasks:
                        cells.append(dict(model=model, doc=name, doc_label=labels[name],
                                          task=task, arm=arm,
                                          preserve_text=preserve_text))

    print(f"running {len(cells)} cells over {len(docmap)} docs "
          f"({len(models)} model(s) x {len(arms)} arm(s) x {len(tasks)} task(s)) ...")
    sem = asyncio.Semaphore(args.concurrency)
    coros = [run_cell(sem, c, docmap, args.max_tokens, args.trunc_ratio,
                      args.judge_model) for c in cells]
    done = 0
    for fut in asyncio.as_completed(coros):
        await fut
        done += 1
        print(f"  {done}/{len(cells)}")

    n_ok = sum(1 for c in cells if c.get("ok"))
    meta = dict(models=args.models, arms=args.arms, tasks=tasks,
                n_cells=len(cells), n_ok=n_ok,
                sample=len(docmap), word_cap=args.word_cap,
                max_tokens=args.max_tokens)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # JSON keeps the real doc names (it stays under --out, default /tmp). Strip the
    # preserve_text blob from each cell so the artifact is metrics-only.
    for c in cells:
        c.pop("preserve_text", None)
    Path(str(out) + ".json").write_text(json.dumps(
        {"meta": meta, "labels": labels, "cells": cells}, indent=2, default=str))
    write_report(str(out) + ".md", meta, cells, docmap)

    usable, excluded, agg = summarize(cells)
    A = agg(usable)
    print(f"\nwrote {out}.json and {out}.md")
    print(f"usable={A['n']} (excluded {excluded} truncated)  "
          f"content-drops={A['cdrops']}/{A['stays']} stays  "
          f"marker-strips={A['mstrips']}/{A['stays']}  "
          f"blocked={A['blocked']} (guard {A['guard']} / nag {A['nag']})")
    for c in cells:
        if not c.get("ok"):
            print(f"  FAILED {c['model']}/{c['doc_label']}/{c['task']}/{c['arm']}: "
                  f"{c.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
