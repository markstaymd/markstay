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
import item_eval

HERE = Path(__file__).parent
DOCS_DIR = HERE.parent / "docs"  # reuse the marker-survival fixtures
THRESHOLDS = [0.3, 0.4, 0.5, 0.6, 0.7]


def score_one(res: R.Resolution, truth: dict) -> tuple[str, str]:
    """Return (category, method) for one id's resolution against its truth."""
    accept = truth["accept"]
    if accept is None:  # block was deleted
        if res.method == "detached":
            return "correct_detach", res.method
        return "false_attach", res.method
    if res.method == "detached":
        return "missed", res.method
    if res.target in accept:
        return "correct", res.method
    return "wrong", res.method


def run_case(
    base_md: str,
    op_name: str,
    strip: bool,
    threshold: float,
    margin: float = R.DEFAULT_MARGIN,
    resolve_kw: dict | None = None,
) -> dict:
    """One (document, operator, strip) cell. `resolve_kw` passes the
    experimental resolver arguments through; empty is the shipped resolver."""
    before_md, pblocks = PB.annotate(base_md)
    anchors = R.build_anchors(before_md)
    # Lookup spans both registries; which operators a *report* iterates is the
    # caller's choice, so the default report's operator list stays as it was.
    after_pblocks, adj = {**PB.OPERATORS, **PB.SECTION_OPERATORS}[op_name](pblocks)
    after_md = PB.serialize(after_pblocks, strip=strip)
    truth = PB.default_truth(after_pblocks)
    truth.update(adj)

    resolutions = R.resolve(anchors, after_md, threshold=threshold, margin=margin,
                            **(resolve_kw or {}))
    cats: dict[str, int] = {}
    methods: dict[str, int] = {}
    detail = []
    for a in anchors:
        res = resolutions[a.id]
        if a.id not in truth:  # shouldn't happen; guard
            continue
        cat, method = score_one(res, truth[a.id])
        cats[cat] = cats.get(cat, 0) + 1
        methods[method] = methods.get(method, 0) + 1
        detail.append(
            {
                "id": a.id,
                "cat": cat,
                "method": method,
                "target": res.target,
                "score": round(res.score, 3),
            }
        )
    return {
        "op": op_name,
        "strip": strip,
        "threshold": threshold,
        "n": len(anchors),
        "cats": cats,
        "methods": methods,
        "detail": detail,
    }


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
    L.append(
        "| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |"
    )
    L.append(
        "|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|"
    )
    for r in rows:
        c = r["cats"]
        rec, fr, _, _ = recovery_and_falserate(c)
        L.append(
            f"| {r['op']} | {r['n']} | {c.get('correct',0)} | "
            f"{c.get('wrong',0)} | {c.get('missed',0)} | "
            f"{c.get('correct_detach',0)} | {c.get('false_attach',0)} | "
            f"{pct(rec)}% | {pct(fr)}% |"
        )
    agg = merge_counts(rows, "cats")
    rec, fr, _, _ = recovery_and_falserate(agg)
    L.append(
        f"| **all** | {sum(r['n'] for r in rows)} | {agg.get('correct',0)} | "
        f"{agg.get('wrong',0)} | {agg.get('missed',0)} | "
        f"{agg.get('correct_detach',0)} | {agg.get('false_attach',0)} | "
        f"**{pct(rec)}%** | **{pct(fr)}%** |"
    )


def write_report(path, sec):
    L = []
    L.append("# Attachment-survival eval results\n")
    L.append(
        f"Realistic docs: {', '.join(sec['docs'])}  |  adversarial fixture: "
        f"{sec['adv_doc']}  |  operators: {', '.join(PB.OPERATORS)}  |  "
        f"threshold {sec['threshold']}, margin {sec['margin']}\n"
    )
    L.append(
        "Each cell annotates a doc, applies one deterministic edit with known "
        "ground truth, strips (or keeps) markers, and asks the resolver to "
        "re-attach every original id. The headline case is **markers stripped** "
        "(the AI-regeneration failure mode), where the resolver cannot use the "
        "id token and must recover from hash + quote alone. Outcomes: *correct* "
        "(right block), *wrong* (a false reattachment), *missed* (safely gave up "
        "on a recoverable block), *detach✓* (correctly gave up on a deleted "
        "block). `wrong` is the dangerous outcome the spec's "
        "'surface, don't silently reattach' rule exists to prevent.\n"
    )

    L.append("\n# Part 1: realistic documents (lexically distinct blocks)\n")
    op_table(L, sec["rows_strip"], "Markers stripped (hash + quote recovery)")
    op_table(L, sec["rows_keep"], "Markers kept (sanity: id token present -> trivial)")

    L.append("\n## Which tier did the work (markers stripped)\n")
    methods = merge_counts(sec["rows_strip"], "methods")
    total = sum(methods.values())
    L.append("| Tier | ids resolved | share | what it recovers |")
    L.append("|------|-------------:|------:|------------------|")
    blurb = {
        "marker": "id token survived (n/a here, stripped)",
        "hash": "body unchanged, just moved (exact)",
        "quote": "body drifted: paraphrase / split / merge (fuzzy)",
        "detached": "no confident match: deleted or ambiguous",
    }
    for m in ["marker", "hash", "quote", "detached"]:
        n = methods.get(m, 0)
        L.append(f"| {m} | {n} | {pct(n/total if total else 0)}% | {blurb[m]} |")

    L.append("\n# Part 2: adversarial fixture (near-duplicate blocks)\n")
    L.append(
        "Blocks that share most of their wording and differ by a single token "
        "(a stage name, a number). This is where content-based recovery is "
        "genuinely dangerous: an edit to one block can make a pristine *twin* the "
        "closest match. Markers stripped throughout.\n"
    )
    op_table(L, sec["adv_rows"], f"Per edit, guard on (margin {sec['margin']})")

    L.append("\n## Margin-guard ablation (the guard's whole job)\n")
    L.append(
        "Same adversarial cases, aggregated over all operators, with the "
        "runner-up margin requirement off vs on. The guard refuses a quote "
        "recovery unless there is a *clear* winner, trading recall (more safe "
        "*missed*) for fewer false reattachments.\n"
    )
    L.append("| margin | recovery | false-rate | correct | wrong | missed | detach✓ |")
    L.append("|-------:|---------:|-----------:|--------:|------:|-------:|--------:|")
    for m, agg in sec["ablation"]:
        rec, fr, _, _ = recovery_and_falserate(agg)
        L.append(
            f"| {m} | {pct(rec)}% | {pct(fr)}% | {agg.get('correct',0)} | "
            f"{agg.get('wrong',0)} | {agg.get('missed',0)} | "
            f"{agg.get('correct_detach',0)} |"
        )

    Path(path).write_text("\n".join(L) + "\n")


def op_rows(bases, strip, threshold, margin, ops=None, resolve_kw=None):
    rows = []
    for op in ops or PB.OPERATORS:
        cells = [run_case(b, op, strip, threshold, margin, resolve_kw) for b in bases]
        rows.append(
            {
                "op": op,
                "n": sum(c["n"] for c in cells),
                "cats": merge_counts(cells, "cats"),
                "methods": merge_counts(cells, "methods"),
            }
        )
    return rows


def fixture_shape(base_md, n_ops):
    """Count what the fixture actually contains, rather than asserting it.

    A block is a *relevant* case only when something else in the document scores
    at or over the commit threshold against it AND sits under a different
    heading path: that is the only arrangement a heading-path signal can act on.
    Blocks whose only rivals share their section are the negative control, and
    the ~1% false-attach bar this project holds itself to needs the relevant
    count (not the total) to reach ~300 before a clean run can certify it."""
    import markstay_lint as lint      # `L` is the report-lines name in this module
    from quote import Selector, body_score

    blocks = [b for b in lint.parse_document(base_md) if b.index >= 0]
    paths = [tuple(lint.canonical_heading(t) for t in p)
             for p in lint.heading_paths(base_md, blocks)]
    bodies = [b.content for b in blocks]
    cross = same = 0
    for i, body in enumerate(bodies):
        sel = Selector(quote=body)
        rivals = [j for j in range(len(bodies))
                  if j != i and body_score(sel, bodies[j]) >= R.DEFAULT_THRESHOLD]
        if any(paths[j] != paths[i] for j in rivals):
            cross += 1
        elif rivals:
            same += 1
    return {
        "blocks": len(blocks),
        "distinct_heading_paths": len(set(paths)),
        "cross_section_blocks": cross,
        "cross_section_resolutions": cross * n_ops,
        "same_section_only_blocks": same,
        "same_section_only_resolutions": same * n_ops,
        "uncontested_blocks": len(bodies) - cross - same,
    }


def run_cross_section(out, threshold, margin, resolve_kw=None):
    """Control baseline for the multi-section fixture, recorded before any
    heading-path arm exists so the arms have something to be measured against.

    Runs the within-section operators *and* `PB.SECTION_OPERATORS`, which move
    the heading structure itself. Deliberately writes its own artifact: folding
    it into `results.md` would move the project's published headline numbers as a
    side effect of adding a fixture."""
    fixture = HERE / "fixtures" / "cross_section_dups.md"
    if not fixture.exists():
        # This runner is published to the site's tools tree; the fixture is not
        # on that allowlist yet. Say so instead of raising, so a reader of the
        # public copy learns what is missing rather than reading a traceback.
        raise SystemExit(
            f"missing {fixture.name}: the multi-section fixture is not part of "
            "this copy. Run this from the markstay umbrella, or add "
            "fixtures/cross_section_dups.md to sync-site-tools.sh.")
    base = fixture.read_text()
    ops = {**PB.OPERATORS, **PB.SECTION_OPERATORS}
    rows = op_rows([base], True, threshold, margin, ops=ops, resolve_kw=resolve_kw)
    shape = fixture_shape(base, len(ops))

    agg = merge_counts(rows, "cats")
    rec, fr, _, total = recovery_and_falserate(agg)
    L = ["# Cross-section fixture: control baseline\n"]
    L.append(
        f"Fixture: `fixtures/cross_section_dups.md`  |  operators: "
        f"{len(ops)} ({len(PB.SECTION_OPERATORS)} of them structural)  |  "
        f"threshold {threshold}, margin {margin}  |  markers stripped\n")
    L.append(
        "Recorded **before** any heading-path arm is written, so a later arm is "
        "compared against a number that was fixed in advance. The structural "
        "operators are the half the older fixtures cannot express: "
        "`cross_section_move` and `heading_delete` change a block's section "
        "while keeping its text, which is the cost side of treating section "
        "position as evidence, and `SPEC.md` §2.2 requires a stay to survive "
        "both.\n")
    L.append("\n## What the fixture contains\n")
    L.append("| | count |")
    L.append("|---|---:|")
    L.append(f"| content blocks | {shape['blocks']} |")
    L.append(f"| distinct heading paths | {shape['distinct_heading_paths']} |")
    L.append(f"| blocks with a **cross-section** rival at or over threshold | "
             f"{shape['cross_section_blocks']} "
             f"(**{shape['cross_section_resolutions']}** resolutions) |")
    L.append(f"| blocks whose only rivals are **same-section** (negative control) | "
             f"{shape['same_section_only_blocks']} "
             f"({shape['same_section_only_resolutions']} resolutions) |")
    L.append(f"| blocks with no rival at all | {shape['uncontested_blocks']} |")
    L.append(
        "\nThe relevant count is the cross-section one: a clean run can only "
        "certify the project's ~1% false-attach bar at roughly 300 or more "
        "(`results_item.md`), and the total is not a substitute for it.\n")
    op_table(L, rows, "Per operator (markers stripped)")
    L.append(
        f"\nControl: **{pct(rec)}% recovery, {pct(fr)}% false attachment** over "
        f"{total} resolutions.\n")
    Path(out + ".md").write_text("\n".join(L) + "\n")
    Path(out + ".json").write_text(json.dumps(
        {"fixture": "fixtures/cross_section_dups.md",
         "threshold": threshold, "margin": margin,
         "operators": list(ops), "shape": shape, "rows": rows, "agg": agg,
         "recovery": rec, "false_rate": fr, "n": total}, indent=1) + "\n")
    print(f"wrote {out}.json and {out}.md")
    print(f"[cross-section control] recovery={pct(rec)}%  "
          f"false-attach={pct(fr)}%  n={total}  {agg}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--docs", default="doc1,doc2")
    ap.add_argument("--threshold", type=float, default=R.DEFAULT_THRESHOLD)
    ap.add_argument("--margin", type=float, default=R.DEFAULT_MARGIN)
    ap.add_argument("--out", default=None)
    ap.add_argument("--granularity", choices=("block", "item"), default="block")
    ap.add_argument("--fixture", choices=("default", "cross-section"),
                    default="default",
                    help="'cross-section' runs the multi-section fixture with "
                         "the structural operators into its own artifact")
    ap.add_argument("--arms", action="store_true",
                    help="run the experimental heading-path arms over every "
                         "corpus into results_headingpath.{json,md}")
    ap.add_argument("--heading-path", choices=R.HEADING_MODES, default="off",
                    help="experimental: use the enclosing heading path as extra "
                         "quote-tier evidence (default off, and off is the "
                         "shipped resolver bit for bit)")
    ap.add_argument("--heading-bonus", type=float, default=R.DEFAULT_HEADING_BONUS)
    ap.add_argument("--heading-gate", type=float, default=None,
                    help="minimum body score before the heading bonus applies "
                         "(default: the commit threshold, making it a pure "
                         "tiebreaker; 0.0 for the ungated form)")
    ap.add_argument("--unclamp", action="store_true",
                    help="experimental: run the runner-up margin on unclamped "
                         "scores instead of clamping both to 1.0 first")
    args = ap.parse_args()
    resolve_kw = {"heading_path": args.heading_path, "clamp": not args.unclamp,
                  "heading_bonus": args.heading_bonus,
                  "heading_gate": args.heading_gate}
    out = args.out or str(
        HERE / ("results_item" if args.granularity == "item" else "results")
    )

    if args.arms:
        try:
            import heading_arms
        except ImportError:  # same posture as the missing-fixture message below
            raise SystemExit(
                "missing heading_arms.py: the experimental heading-path arms are "
                "not part of this copy. Run this from the markstay umbrella.")
        arms_out = args.out or str(HERE / "results_headingpath")
        data = heading_arms.write(arms_out)
        print(f"wrote {arms_out}.json and {arms_out}.md")
        for corpus in data["corpora"]:
            head = ", ".join(
                f"{label} {corpus['arms'][label]['overall']['recovery']:.1%}/"
                f"{corpus['arms'][label]['overall']['false_attach']:.1%}"
                for label in ("A", "B12c", "C"))
            print(f"[{corpus['name']}] {head}   (recovery/false, full table in the report)")
        return

    if args.fixture == "cross-section":
        run_cross_section(args.out or str(HERE / "results_crosssection_fixture"),
                          args.threshold, args.margin, resolve_kw)
        return

    if args.granularity == "item":
        payload = item_eval.write(out)
        summary = payload["summary"]
        print(f"wrote {out}.json and {out}.md")
        print(
            f"[items] recovery={summary['recovery_rate']:.1%}  "
            f"false-attach={summary['false_attach_rate']:.1%}  "
            f"detach={summary['detach_rate']:.1%}  {summary['cats']}"
        )
        return

    docs = args.docs.split(",")
    bases = [(DOCS_DIR / f"{d}.md").read_text() for d in docs]
    adv_base = [(HERE / "fixtures" / "near_dups.md").read_text()]

    rows_strip = op_rows(bases, True, args.threshold, args.margin,
                         resolve_kw=resolve_kw)
    rows_keep = op_rows(bases, False, args.threshold, args.margin,
                        resolve_kw=resolve_kw)
    adv_rows = op_rows(adv_base, True, args.threshold, args.margin,
                       resolve_kw=resolve_kw)

    # Guard ablation on the adversarial fixture: margin off vs on.
    ablation = []
    for m in (0.0, args.margin):
        cells = [
            run_case(adv_base[0], op, True, args.threshold, m, resolve_kw)
            for op in PB.OPERATORS
        ]
        ablation.append((m, merge_counts(cells, "cats")))

    sec = {
        "docs": docs,
        "adv_doc": "fixtures/near_dups.md",
        "threshold": args.threshold,
        "margin": args.margin,
        "rows_strip": rows_strip,
        "rows_keep": rows_keep,
        "adv_rows": adv_rows,
        "ablation": ablation,
    }
    Path(out + ".json").write_text(json.dumps(sec, default=str, indent=2))
    write_report(out + ".md", sec)

    agg = merge_counts(rows_strip, "cats")
    rec, fr, _, _ = recovery_and_falserate(agg)
    adv_off = ablation[0][1]
    adv_on = ablation[1][1]
    print(f"wrote {out}.json and {out}.md")
    print(
        f"[realistic, stripped] recovery={pct(rec)}%  false-attach-rate={pct(fr)}%  {agg}"
    )
    print(
        f"[adversarial] guard off: wrong={adv_off.get('wrong',0)}  "
        f"guard on: wrong={adv_on.get('wrong',0)}"
    )


if __name__ == "__main__":
    main()
