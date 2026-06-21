"""LLM-driven attachment-survival eval runner.

For every (document, rewrite task, model) cell: annotate the doc, have the model
rewrite the prose while preserving markers (§11), validate the preserved markers
as ground truth via the linter's regeneration diff, strip the markers, run the
resolver on the stripped text, and score recovery against the gold mapping,
bucketed by the measured before/after similarity of each block.

Needs an API key: source ~/.credentials/unlock.sh first.

    python run_llm_attach_eval.py --models sonnet
    python run_llm_attach_eval.py --models sonnet,gpt4o --docs doc1,doc2 --adversarial
    python run_llm_attach_eval.py --models sonnet --smoke      # one cheap cell
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

import llm_attach as LA

_EVAL = Path(__file__).resolve().parents[2]
if str(_EVAL) not in sys.path:
    sys.path.insert(0, str(_EVAL))
import perturb as PB  # noqa: E402
import resolver as R  # noqa: E402
import providers as P  # noqa: E402

HERE = Path(__file__).parent
DOCS_DIR = _EVAL / "docs"
ADV_DOC = _EVAL / "attachment" / "fixtures" / "near_dups.md"


async def run_cell(sem, cell, threshold, margin):
    base = (DOCS_DIR / f"{cell['doc']}.md").read_text() if cell["doc"] != "near_dups" \
        else ADV_DOC.read_text()
    before_md, _ = PB.annotate(base)
    prompt = LA.build_prompt(cell["task"], before_md)
    async with sem:
        for attempt in range(2):
            try:
                raw = await P.complete(cell["model"], prompt, max_tokens=4000)
                after = LA.strip_outer_fence(raw)
                results = LA.score_document(before_md, after, threshold, margin)
                cell["results"] = [r.__dict__ for r in results]
                cell["ok"] = True
                return cell
            except Exception as e:  # noqa: BLE001
                cell["error"] = f"{type(e).__name__}: {e}"
                if attempt == 0:
                    await asyncio.sleep(2)
    cell["ok"] = False
    return cell


def all_results(cells):
    out = []
    for c in cells:
        if c.get("ok"):
            for r in c["results"]:
                out.append({**r, "doc": c["doc"], "task": c["task"], "model": c["model"]})
    return out


def cats_of(rows):
    cats = {}
    for r in rows:
        cats[r["cat"]] = cats.get(r["cat"], 0) + 1
    return cats


def pct(x):
    return f"{round(100 * x):3d}"


def grp(rows, keyfn):
    d = {}
    for r in rows:
        d.setdefault(keyfn(r), []).append(r)
    return d


def cat_table(L, title, groups, order=None):
    L.append(f"\n## {title}\n")
    L.append("| group | scored | correct | wrong | missed | recovery | false-rate |")
    L.append("|-------|-------:|--------:|------:|-------:|---------:|-----------:|")
    keys = order or sorted(groups)
    for k in keys:
        if k not in groups:
            continue
        cats = cats_of(groups[k])
        rec, fr, n = LA.recovery_falserate(cats)
        L.append(f"| {k} | {n} | {cats.get('correct',0)} | {cats.get('wrong',0)} | "
                 f"{cats.get('missed',0)} | {pct(rec)}% | {pct(fr)}% |")


def write_report(path, meta, rows, no_truth_n):
    L = []
    L.append("# LLM-driven attachment-survival eval results\n")
    L.append(f"Models: {meta['models']}  |  docs: {meta['docs']}  |  "
             f"tasks: {', '.join(meta['tasks'])}  |  threshold {meta['threshold']}, "
             f"margin {meta['margin']}\n")
    L.append(f"Cells: {meta['n_cells']} run, {meta['n_ok']} ok, {meta['n_failed']} failed. "
             f"Scored ids: {len(rows)}; excluded (rewrite dropped/duplicated/relocated "
             f"the marker, no clean ground truth): {no_truth_n}.\n")
    L.append("Each cell annotates a doc, has the model rewrite the prose while "
             "preserving markers (§11), validates the preserved markers as ground "
             "truth via the linter's regeneration diff, strips the markers, and asks "
             "the resolver to recover every original id from hash + quote alone. "
             "Recovery = correct / scored; false-rate = wrong / scored. `wrong` is the "
             "silent mis-attachment SPEC.md §10 forbids.\n")

    overall = cats_of(rows)
    rec, fr, n = LA.recovery_falserate(overall)
    L.append(f"\n**Overall (markers stripped, real rewrites): recovery {pct(rec)}%, "
             f"false-attach {pct(fr)}% over {n} scored ids.**\n")

    # The headline: recovery as a function of measured rewrite similarity.
    bands = grp(rows, lambda r: LA.band_label(r["sim"]))
    band_order = [LA.band_label((lo + hi) / 2 - 1e-9) for lo, hi in LA.BANDS]
    cat_table(L, "Recovery by measured before/after block similarity (the regime test)",
              bands, order=band_order)
    L.append("\nThe deterministic eval could not push real prose below ~0.7 "
             "similarity; these low bands are the new evidence. If recovery holds in "
             "the 0.3-0.5 band, §9 quote params survive real rewrites; if it collapses "
             "or false-attach climbs, v1 §9 needs revisiting.\n")

    cat_table(L, "By rewrite task", grp(rows, lambda r: r["task"]),
              order=list(LA.TASKS))
    cat_table(L, "By model", grp(rows, lambda r: r["model"]))
    cat_table(L, "By document", grp(rows, lambda r: r["doc"]))

    # Which tier did the work (scored ids only).
    L.append("\n## Which tier recovered the id (scored ids)\n")
    methods = {}
    for r in rows:
        methods[r["method"]] = methods.get(r["method"], 0) + 1
    tot = sum(methods.values()) or 1
    L.append("| tier | ids | share |")
    L.append("|------|----:|------:|")
    for m in ["hash", "quote", "detached", "marker"]:
        L.append(f"| {m} | {methods.get(m,0)} | {pct(methods.get(m,0)/tot)}% |")

    # Every wrong attachment, named: the cases that would move the spec.
    wrongs = [r for r in rows if r["cat"] == "wrong"]
    if wrongs:
        L.append("\n## False attachments (every `wrong`, for inspection)\n")
        L.append("| model | doc | task | id | sim | resolver score | gold->got |")
        L.append("|-------|-----|------|----|----:|---------------:|-----------|")
        for r in sorted(wrongs, key=lambda r: r["sim"]):
            L.append(f"| {r['model']} | {r['doc']} | {r['task']} | {r['id']} | "
                     f"{r['sim']:.2f} | {r['score']:.2f} | {r['gold']}->{r['target']} |")
    else:
        L.append("\n## False attachments\n\nNone across the scored ids.\n")

    Path(path).write_text("\n".join(L) + "\n")


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", default="sonnet")
    ap.add_argument("--docs", default="doc1,doc2")
    ap.add_argument("--tasks", default=",".join(LA.TASKS))
    ap.add_argument("--adversarial", action="store_true",
                    help="also run the near-duplicate fixture (false-attach stress)")
    ap.add_argument("--threshold", type=float, default=R.DEFAULT_THRESHOLD)
    ap.add_argument("--margin", type=float, default=R.DEFAULT_MARGIN)
    ap.add_argument("--concurrency", type=int, default=6)
    ap.add_argument("--smoke", action="store_true", help="one cell only")
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args()

    models = args.models.split(",")
    docs = args.docs.split(",")
    if args.adversarial:
        docs = docs + ["near_dups"]
    tasks = args.tasks.split(",")

    cells = []
    if args.smoke:
        cells.append(dict(model=models[0], doc=docs[0], task=tasks[0]))
    else:
        for model in models:
            for doc in docs:
                for task in tasks:
                    cells.append(dict(model=model, doc=doc, task=task))

    print(f"running {len(cells)} cells across {len(models)} model(s) ...")
    sem = asyncio.Semaphore(args.concurrency)
    coros = [run_cell(sem, c, args.threshold, args.margin) for c in cells]
    done = 0
    for fut in asyncio.as_completed(coros):
        await fut
        done += 1
        print(f"  {done}/{len(cells)}")

    n_ok = sum(1 for c in cells if c.get("ok"))
    rows = all_results(cells)
    no_truth_n = sum(1 for r in rows if r["cat"] == "no_truth")
    rows = [r for r in rows if r["cat"] != "no_truth"]

    meta = {"models": args.models, "docs": ",".join(docs), "tasks": tasks,
            "threshold": args.threshold, "margin": args.margin,
            "n_cells": len(cells), "n_ok": n_ok, "n_failed": len(cells) - n_ok}
    Path(args.out + ".json").write_text(json.dumps(
        {"meta": meta, "cells": cells}, indent=2, default=str))
    write_report(args.out + ".md", meta, rows, no_truth_n)

    overall = cats_of(rows)
    rec, fr, n = LA.recovery_falserate(overall)
    print(f"\nwrote {args.out}.json and {args.out}.md")
    print(f"scored={n}  recovery={pct(rec)}%  false-attach={pct(fr)}%  "
          f"excluded(no_truth)={no_truth_n}")
    if any(not c.get("ok") for c in cells):
        for c in cells:
            if not c.get("ok"):
                print(f"  FAILED {c['model']}/{c['doc']}/{c['task']}: {c.get('error')}")


if __name__ == "__main__":
    asyncio.run(main())
