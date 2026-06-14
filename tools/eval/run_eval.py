"""Marker-survival eval runner.

For every (doc, marker, task, instruction, model) cell: annotate the doc with the
marker, perturb it through the model, and score how many marker ids survived.

Usage:
    python run_eval.py --models haiku,gpt4o-mini
    python run_eval.py --models haiku --markers html_comment,visible_tag --tasks rewrite --smoke
"""

import argparse
import asyncio
import json
import os
import re
from pathlib import Path

import markers as M
import providers as P

HERE = Path(__file__).parent
DOCS_DIR = HERE / "docs"

TASKS = {
    "rewrite": "Rewrite the following Markdown document to be clearer and more concise.",
    "cleanup": "Clean up and tidy the following Markdown document. Fix formatting and remove anything unnecessary.",
    "translate": "Translate the following Markdown document into French. Preserve the Markdown structure.",
    "edit": "Add one extra item to the bulleted list in the following Markdown document. Otherwise keep the document as-is.",
}

PRESERVE = (
    "\n\nIMPORTANT: The document contains marker tokens that identify content "
    "blocks. Preserve every marker token exactly as written and in place. Do not "
    "remove, alter, renumber, or relocate them."
)

RETURN_ONLY = "\n\nReturn only the resulting Markdown, with no commentary or code fences around it."


def strip_outer_fence(text: str) -> str:
    t = text.strip()
    m = re.match(r"^```[a-zA-Z]*\n(.*)\n```$", t, re.DOTALL)
    return m.group(1) if m else t


def build_prompt(task_key, annotated, instructed):
    parts = [TASKS[task_key]]
    if instructed:
        parts.append(PRESERVE)
    parts.append(RETURN_ONLY)
    parts.append("\n\n---\n\n" + annotated)
    return "".join(parts)


def score(marker, ids, output):
    intact = sum(1 for mid in ids if marker.intact(mid, output))
    present = sum(1 for mid in ids if M.id_present(mid, output))
    n = len(ids)
    return {
        "n_ids": n,
        "intact": intact,
        "present": present,
        "intact_rate": intact / n if n else 0.0,
        "present_rate": present / n if n else 0.0,
    }


async def run_cell(sem, cell):
    marker = M.MARKERS[cell["marker"]]
    base = (DOCS_DIR / f"{cell['doc']}.md").read_text()
    annotated, ids = marker.annotate(base)
    prompt = build_prompt(cell["task"], annotated, cell["instructed"])
    async with sem:
        for attempt in range(2):
            try:
                out = strip_outer_fence(await P.complete(cell["model"], prompt))
                cell.update(score(marker, ids, out))
                cell["ok"] = True
                return cell
            except Exception as e:  # noqa: BLE001
                cell["error"] = f"{type(e).__name__}: {e}"
                if attempt == 0:
                    await asyncio.sleep(2)
    cell["ok"] = False
    return cell


def aggregate(rows):
    ok = [r for r in rows if r.get("ok")]

    def grp(key_fn):
        d = {}
        for r in ok:
            d.setdefault(key_fn(r), []).append(r["intact_rate"])
        return {k: sum(v) / len(v) for k, v in sorted(d.items())}

    by_marker = grp(lambda r: r["marker"])
    by_marker_instr = {}
    for r in ok:
        by_marker_instr.setdefault(r["marker"], {"naive": [], "instructed": []})
        by_marker_instr[r["marker"]]["instructed" if r["instructed"] else "naive"].append(r["intact_rate"])
    by_marker_instr = {
        m: {k: (sum(v) / len(v) if v else None) for k, v in d.items()}
        for m, d in by_marker_instr.items()
    }
    by_marker_task = {}
    for r in ok:
        by_marker_task.setdefault(r["marker"], {}).setdefault(r["task"], []).append(r["intact_rate"])
    by_marker_task = {
        m: {t: sum(v) / len(v) for t, v in sorted(d.items())} for m, d in by_marker_task.items()
    }
    return {
        "by_marker": by_marker,
        "by_model": grp(lambda r: r["model"]),
        "by_task": grp(lambda r: r["task"]),
        "by_marker_instr": by_marker_instr,
        "by_marker_task": by_marker_task,
        "n_cells": len(rows),
        "n_ok": len(ok),
        "n_failed": len(rows) - len(ok),
    }


def pct(x):
    return "  -" if x is None else f"{round(100 * x):3d}"


def write_report(rows, agg, path, meta):
    L = []
    L.append("# Marker-survival eval results\n")
    L.append(f"Models: {meta['models']}  |  docs: {meta['docs']}  |  "
             f"tasks: {', '.join(meta['tasks'])}\n")
    L.append(f"Cells: {agg['n_cells']} run, {agg['n_ok']} ok, {agg['n_failed']} failed.\n")
    L.append("Metric: % of block markers that survived **intact** (full marker "
             "syntax with its id still present in the output), averaged over the "
             "cells in each group.\n")

    L.append("\n## Survival by marker syntax: naive vs instructed\n")
    L.append("| Marker | naive | instructed |")
    L.append("|--------|------:|-----------:|")
    order = sorted(agg["by_marker_instr"], key=lambda m: -(agg["by_marker"].get(m, 0)))
    for m in order:
        d = agg["by_marker_instr"][m]
        L.append(f"| {m} | {pct(d.get('naive'))} | {pct(d.get('instructed'))} |")

    L.append("\n## Survival by marker x task (all instruction modes)\n")
    tasks = meta["tasks"]
    L.append("| Marker | " + " | ".join(tasks) + " |")
    L.append("|--------|" + "|".join(["-----:"] * len(tasks)) + "|")
    for m in order:
        d = agg["by_marker_task"].get(m, {})
        L.append(f"| {m} | " + " | ".join(pct(d.get(t)) for t in tasks) + " |")

    L.append("\n## Survival by model\n")
    L.append("| Model | intact % |")
    L.append("|-------|---------:|")
    for k, v in agg["by_model"].items():
        L.append(f"| {k} | {pct(v)} |")

    if agg["n_failed"]:
        L.append("\n## Failures\n")
        seen = set()
        for r in rows:
            if not r.get("ok") and r.get("error") not in seen:
                seen.add(r.get("error"))
                L.append(f"- `{r['model']}` / {r['marker']} / {r['task']}: {r.get('error')}")

    Path(path).write_text("\n".join(L) + "\n")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="haiku,gpt4o-mini")
    ap.add_argument("--docs", default="doc1,doc2")
    ap.add_argument("--markers", default=",".join(M.MARKERS))
    ap.add_argument("--tasks", default=",".join(TASKS))
    ap.add_argument("--concurrency", type=int, default=8)
    ap.add_argument("--smoke", action="store_true", help="one cell per model, ignore matrix")
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args()

    models = args.models.split(",")
    docs = args.docs.split(",")
    mks = args.markers.split(",")
    tasks = args.tasks.split(",")

    cells = []
    if args.smoke:
        for model in models:
            cells.append(dict(model=model, doc=docs[0], marker=mks[0],
                              task=tasks[0], instructed=False))
    else:
        for model in models:
            for doc in docs:
                for mk in mks:
                    for task in tasks:
                        for instructed in (False, True):
                            cells.append(dict(model=model, doc=doc, marker=mk,
                                              task=task, instructed=instructed))

    print(f"running {len(cells)} cells across {len(models)} models ...")
    sem = asyncio.Semaphore(args.concurrency)
    done = 0
    results = []
    coros = [run_cell(sem, c) for c in cells]
    for fut in asyncio.as_completed(coros):
        r = await fut
        results.append(r)
        done += 1
        if done % 20 == 0 or done == len(cells):
            print(f"  {done}/{len(cells)}")

    agg = aggregate(results)
    meta = {"models": args.models, "docs": args.docs, "tasks": tasks}
    Path(args.out + ".json").write_text(json.dumps(
        {"meta": meta, "agg": agg, "rows": results}, indent=2))
    write_report(results, agg, args.out + ".md", meta)
    print(f"\nwrote {args.out}.json and {args.out}.md")
    print(f"ok={agg['n_ok']} failed={agg['n_failed']}")
    if not args.smoke:
        print("\nintact survival by marker (naive / instructed):")
        for m, d in sorted(agg["by_marker_instr"].items(),
                           key=lambda kv: -(agg["by_marker"].get(kv[0], 0))):
            print(f"  {m:18s} {pct(d.get('naive'))}% / {pct(d.get('instructed'))}%")


if __name__ == "__main__":
    asyncio.run(main())
