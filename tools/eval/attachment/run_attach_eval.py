"""Attachment-survival eval runner.

For every (document, edit operator, marker-stripping) case, this annotates the
document, applies the edit, runs the resolver, and scores each original id
against known ground truth as one of:

    correct        attached to a block the id legitimately belongs to
    wrong          attached to a *different* block (a false reattachment)
    missed         gave up (DETACHED) on a block that did survive (safe miss)
    correct_detach correctly DETACHED an id whose block was deleted
    false_attach   attached an id whose block was deleted (false positive)

`wrong` and `false_attach` are the dangerous outcomes the spec's "surface, don't
silently reattach" rule exists to prevent; the eval reports their combined rate
separately from raw recovery so the precision/recall trade-off is explicit.

No API key or network needed: every edit is deterministic and ground truth is
exact. Run:  python run_attach_eval.py
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import perturb as PB
import resolver as R

HERE = Path(__file__).parent
DOCS_DIR = HERE.parent / "docs"          # reuse the marker-survival fixtures
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]


def score_one(res: R.Resolution, truth: dict) -> tuple[str, str]:
    """Return (category, method) for one id's resolution against its truth."""
    accept = truth["accept"]
    if accept is None:                       # block was deleted
        if res.method == "detached":
            return "correct_detach", res.method
        return "false_attach", res.method
    if res.method == "detached":
        return "missed", res.method
    if res.target in accept:
        return "correct", res.method
    return "wrong", res.method


def run_case(base_md: str, op_name: str, strip: bool, threshold: float,
             margin: float = R.DEFAULT_MARGIN) -> dict:
    before_md, pblocks = PB.annotate(base_md)
    anchors = R.build_anchors(before_md)
    after_pblocks, adj = PB.OPERATORS[op_name](pblocks)
    after_md = PB.serialize(after_pblocks, strip=strip)
    truth = PB.default_truth(after_pblocks)
    truth.update(adj)

    resolutions = R.resolve(anchors, after_md, threshold=threshold, margin=margin)
    cats: dict[str, int] = {}
    methods: dict[str, int] = {}
    detail = []
    for a in anchors:
        res = resolutions[a.id]
        if a.id not in truth:                # shouldn't happen; guard
            continue
        cat, method = score_one(res, truth[a.id])
        cats[cat] = cats.get(cat, 0) + 1
        methods[method] = methods.get(method, 0) + 1
        detail.append({"id": a.id, "cat": cat, "method": method,
                       "target": res.target, "score": round(res.score, 3)})
    return {"op": op_name, "strip": strip, "threshold": threshold,
            "n": len(anchors), "cats": cats, "methods": methods, "detail": detail}


def merge_counts(rows: list[dict], key: str) -> dict[str, int]:
    out: dict[str, int] = {}
    for r in rows:
        for k, v in r[key].items():
            out[k] = out.get(k, 0) + v
    return out


def recovery_and_falserate(cats: dict[str, int]) -> tuple[float, float, int, int]:
    """recovery = correct / (ids whose block survived);
    false-attach rate = (wrong + false_attach) / all ids."""
    survivable = cats.get("correct", 0) + cats.get("wrong", 0) + cats.get("missed", 0)
    total = sum(cats.values())
    recovery = cats.get("correct", 0) / survivable if survivable else 0.0
    false_n = cats.get("wrong", 0) + cats.get("false_attach", 0)
    false_rate = false_n / total if total else 0.0
    return recovery, false_rate, survivable, total


CATS = ["correct", "wrong", "missed", "correct_detach", "false_attach"]


def pct(x):
    return f"{round(100 * x):3d}"


def op_table(L, rows, label):
    L.append(f"\n## {label}\n")
    L.append("| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |")
    L.append("|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|")
    for r in rows:
        c = r["cats"]
        rec, fr, _, _ = recovery_and_falserate(c)
        L.append(f"| {r['op']} | {r['n']} | {c.get('correct',0)} | "
                 f"{c.get('wrong',0)} | {c.get('missed',0)} | "
                 f"{c.get('correct_detach',0)} | {c.get('false_attach',0)} | "
                 f"{pct(rec)}% | {pct(fr)}% |")
    agg = merge_counts(rows, "cats")
    rec, fr, _, _ = recovery_and_falserate(agg)
    L.append(f"| **all** | {sum(r['n'] for r in rows)} | {agg.get('correct',0)} | "
             f"{agg.get('wrong',0)} | {agg.get('missed',0)} | "
             f"{agg.get('correct_detach',0)} | {agg.get('false_attach',0)} | "
             f"**{pct(rec)}%** | **{pct(fr)}%** |")


def write_report(path, sec):
    L = []
    L.append("# Attachment-survival eval results\n")
    L.append(f"Realistic docs: {', '.join(sec['docs'])}  |  adversarial fixture: "
             f"{sec['adv_doc']}  |  operators: {', '.join(PB.OPERATORS)}  |  "
             f"threshold {sec['threshold']}, margin {sec['margin']}\n")
    L.append("Each cell annotates a doc, applies one deterministic edit with known "
             "ground truth, strips (or keeps) markers, and asks the resolver to "
             "re-attach every original id. The headline case is **markers stripped** "
             "(the AI-regeneration failure mode), where the resolver cannot use the "
             "id token and must recover from hash + quote alone. Outcomes: *correct* "
             "(right block), *wrong* (a false reattachment), *missed* (safely gave up "
             "on a recoverable block), *detach✓* (correctly gave up on a deleted "
             "block). `wrong` is the dangerous outcome the spec's "
             "'surface, don't silently reattach' rule exists to prevent.\n")

    L.append("\n# Part 1: realistic documents (lexically distinct blocks)\n")
    op_table(L, sec["rows_strip"], "Markers stripped (hash + quote recovery)")
    op_table(L, sec["rows_keep"], "Markers kept (sanity: id token present -> trivial)")

    L.append("\n## Which tier did the work (markers stripped)\n")
    methods = merge_counts(sec["rows_strip"], "methods")
    total = sum(methods.values())
    L.append("| Tier | ids resolved | share | what it recovers |")
    L.append("|------|-------------:|------:|------------------|")
    blurb = {"marker": "id token survived (n/a here, stripped)",
             "hash": "body unchanged, just moved (exact)",
             "quote": "body drifted: paraphrase / split / merge (fuzzy)",
             "detached": "no confident match: deleted or ambiguous"}
    for m in ["marker", "hash", "quote", "detached"]:
        n = methods.get(m, 0)
        L.append(f"| {m} | {n} | {pct(n/total if total else 0)}% | {blurb[m]} |")

    L.append("\n# Part 2: adversarial fixture (near-duplicate blocks)\n")
    L.append("Blocks that share most of their wording and differ by a single token "
             "(a stage name, a number). This is where content-based recovery is "
             "genuinely dangerous: an edit to one block can make a pristine *twin* the "
             "closest match. Markers stripped throughout.\n")
    op_table(L, sec["adv_rows"], f"Per edit, guard on (margin {sec['margin']})")

    L.append("\n## Margin-guard ablation (the guard's whole job)\n")
    L.append("Same adversarial cases, aggregated over all operators, with the "
             "runner-up margin requirement off vs on. The guard refuses a quote "
             "recovery unless there is a *clear* winner, trading recall (more safe "
             "*missed*) for fewer false reattachments.\n")
    L.append("| margin | recovery | false-rate | correct | wrong | missed | detach✓ |")
    L.append("|-------:|---------:|-----------:|--------:|------:|-------:|--------:|")
    for m, agg in sec["ablation"]:
        rec, fr, _, _ = recovery_and_falserate(agg)
        L.append(f"| {m} | {pct(rec)}% | {pct(fr)}% | {agg.get('correct',0)} | "
                 f"{agg.get('wrong',0)} | {agg.get('missed',0)} | "
                 f"{agg.get('correct_detach',0)} |")

    Path(path).write_text("\n".join(L) + "\n")


def op_rows(bases, strip, threshold, margin):
    rows = []
    for op in PB.OPERATORS:
        cells = [run_case(b, op, strip, threshold, margin) for b in bases]
        rows.append({"op": op, "n": sum(c["n"] for c in cells),
                     "cats": merge_counts(cells, "cats"),
                     "methods": merge_counts(cells, "methods")})
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="doc1,doc2")
    ap.add_argument("--threshold", type=float, default=R.DEFAULT_THRESHOLD)
    ap.add_argument("--margin", type=float, default=R.DEFAULT_MARGIN)
    ap.add_argument("--out", default=str(HERE / "results"))
    args = ap.parse_args()

    docs = args.docs.split(",")
    bases = [(DOCS_DIR / f"{d}.md").read_text() for d in docs]
    adv_base = [(HERE / "fixtures" / "near_dups.md").read_text()]

    rows_strip = op_rows(bases, True, args.threshold, args.margin)
    rows_keep = op_rows(bases, False, args.threshold, args.margin)
    adv_rows = op_rows(adv_base, True, args.threshold, args.margin)

    # Guard ablation on the adversarial fixture: margin off vs on.
    ablation = []
    for m in (0.0, args.margin):
        cells = [run_case(adv_base[0], op, True, args.threshold, m) for op in PB.OPERATORS]
        ablation.append((m, merge_counts(cells, "cats")))

    sec = {"docs": docs, "adv_doc": "fixtures/near_dups.md",
           "threshold": args.threshold, "margin": args.margin,
           "rows_strip": rows_strip, "rows_keep": rows_keep,
           "adv_rows": adv_rows, "ablation": ablation}
    Path(args.out + ".json").write_text(json.dumps(sec, default=str, indent=2))
    write_report(args.out + ".md", sec)

    agg = merge_counts(rows_strip, "cats")
    rec, fr, _, _ = recovery_and_falserate(agg)
    adv_off = ablation[0][1]
    adv_on = ablation[1][1]
    print(f"wrote {args.out}.json and {args.out}.md")
    print(f"[realistic, stripped] recovery={pct(rec)}%  false-attach-rate={pct(fr)}%  {agg}")
    print(f"[adversarial] guard off: wrong={adv_off.get('wrong',0)}  "
          f"guard on: wrong={adv_on.get('wrong',0)}")


if __name__ == "__main__":
    main()
