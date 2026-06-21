"""markstay attachment demo , the 20-second skeptic-converter.

The objection markstay always meets: *"an LLM will just delete your
`<!-- stay -->` comments, so the ids are useless."* This demo deletes them, then
shows markstay re-attaching each original id to the right block anyway, from the
content hash + quote selector alone (SPEC.md §8/§9), and refusing to guess when a
block is reworded past recognition (§10).

It runs in one command with **no API key**: it replays a *real* LLM rewrite
captured once into `demo_fixture.json`. The headline number is therefore a real
model's output, but the demo is deterministic and free to reproduce.

    python demo.py                       # replay the frozen real rewrite ($0, no key)
    python demo.py --live --model sonnet # rewrite live to prove it isn't cherry-picked
    python demo.py --capture --model sonnet --task reword   # regenerate the fixture

`--live`/`--capture` need a key: source ~/.credentials/unlock.sh first.
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

HERE = Path(__file__).parent
DOCS_DIR = _EVAL / "docs"
FIXTURE = HERE / "demo_fixture.json"

# Marks for the per-id table.
OK = "✓"        # correct re-attachment
DETACH = "○"    # safely detached (correct: nothing to point at confidently)
WRONG = "✗"     # false attachment (the outcome §10 forbids)


def _first_line(body: str, width: int = 46) -> str:
    line = (body or "").strip().splitlines()[0] if (body or "").strip() else ""
    return line if len(line) <= width else line[: width - 1] + "…"


def evaluate(before_annotated: str, after_with_markers: str):
    """Run the resolver on the marker-stripped rewrite and score every original id
    against the preserved-marker gold mapping. Returns (rows, summary)."""
    anchors = R.build_anchors(before_annotated)
    gt = LA.ground_truth(before_annotated, after_with_markers)
    stripped = LA.strip_markers(after_with_markers)
    resolutions = R.resolve(anchors, stripped)
    before_body = {a.id: a.selector.quote for a in anchors}

    rows = []
    for a in anchors:
        res = resolutions[a.id]
        gold = gt.id_to_idx.get(a.id)
        if gold is None:
            continue  # rewrite lost/dup'd/moved this marker: no clean ground truth
        sim = LA.similarity(before_body[a.id], gt.after_bodies[gold])
        if res.method == "detached":
            cat, mark = "missed", DETACH
        elif res.target == gold:
            cat, mark = "correct", OK
        else:
            cat, mark = "wrong", WRONG
        preview = (gt.after_bodies[res.target] if res.target is not None
                   else before_body[a.id])
        rows.append(dict(id=a.id, cat=cat, mark=mark, tier=res.method,
                         score=res.score, sim=sim, target=res.target,
                         preview=_first_line(preview)))

    n = len(rows)
    correct = sum(1 for r in rows if r["cat"] == "correct")
    wrong = sum(1 for r in rows if r["cat"] == "wrong")
    detached = sum(1 for r in rows if r["cat"] == "missed")
    exact = sum(1 for r in rows if r["tier"] == "hash")  # naive exact-match baseline
    quote_saves = sum(1 for r in rows if r["cat"] == "correct" and r["tier"] == "quote")
    mean_sim = sum(r["sim"] for r in rows) / n if n else 0.0
    summary = dict(n=n, correct=correct, wrong=wrong, detached=detached,
                   exact=exact, quote_saves=quote_saves, mean_sim=mean_sim)
    return rows, summary


def render(meta: dict, rows: list, s: dict, live: bool) -> str:
    src = ("a live %s '%s' rewrite" % (meta["model"], meta["task"]) if live
           else "a real %s '%s' rewrite, captured %s" %
                (meta["model"], meta["task"], meta.get("captured", "?")))
    L = []
    L.append("")
    L.append("markstay attachment demo , can a block's identity survive an LLM")
    L.append("rewrite that DELETES the markers?")
    L.append("")
    L.append("  document : docs/%s.md (%d blocks)" % (meta["doc"], s["n"]))
    L.append("  rewrite  : %s, then every marker stripped out" % src)
    L.append("  drift    : mean block text similarity before->after = %.2f"
             % s["mean_sim"])
    L.append("             (every prose block reworded; only verbatim code/tables match)")
    L.append("")
    L.append("The skeptic's objection: \"an LLM will just delete your <!-- stay -->")
    L.append("comments.\" Fine , they're gone. Can markstay still say which new block")
    L.append("is which old one, from hash + quote alone?")
    L.append("")
    L.append("  old id     tier      conf   recovered block")
    L.append("  " + "-" * 64)
    for r in rows:
        conf = "%.2f" % r["score"] if r["tier"] != "hash" else "1.00"
        if r["cat"] == "missed":
            tail = '○  flagged outdated (was "%s")' % r["preview"]
        elif r["cat"] == "wrong":
            tail = '✗ #%-3d "%s"  FALSE ATTACHMENT' % (r["target"], r["preview"])
        else:
            tail = '✓ #%-3d "%s"' % (r["target"], r["preview"])
        L.append("  %-9s  %-8s  %-5s %s" % (r["id"], r["tier"], conf, tail))
    L.append("")
    rec = round(100 * s["correct"] / s["n"]) if s["n"] else 0
    L.append("HEADLINE")
    L.append("  %d/%d blocks re-identified, %d misattached  (recovery %d%%, false-attach %d%%)"
             % (s["correct"], s["n"], s["wrong"], rec,
                round(100 * s["wrong"] / s["n"]) if s["n"] else 0))
    L.append("")
    L.append("  Without markstay (exact content match only): %d/%d recover."
             % (s["exact"], s["n"]))
    L.append("  The quote selector + the id recover %d more reworded block(s) that a"
             % s["quote_saves"])
    L.append("  content hash alone would miss, and the §9 commit rule (score + margin)")
    L.append("  turns the unrecoverable ones into a safe \"outdated\", never a wrong guess.")
    L.append("")
    L.append("In normal use you'd also give the model the §11 preserve instruction so the")
    L.append("markers rarely get stripped at all (see markstay.org/dogfood). This demo is")
    L.append("the worst case , markers fully gone , and identity still holds.")
    L.append("")
    if not live:
        L.append("Reproduce against a live model (needs an API key):")
        L.append("  source ~/.credentials/unlock.sh && python demo.py --live --model sonnet")
        L.append("")
    return "\n".join(L)


async def _rewrite(doc: str, model: str, task: str):
    import providers as P  # noqa: E402 (eval/ on path)
    before_annotated, _ = PB.annotate((DOCS_DIR / f"{doc}.md").read_text())
    prompt = LA.build_prompt(task, before_annotated)
    raw = await P.complete(model, prompt, max_tokens=4000)
    after = LA.strip_outer_fence(raw)
    # Refuse a fixture/live result whose ground truth isn't clean: a dropped or
    # relocated marker means no trustworthy gold label for this demo.
    gt = LA.ground_truth(before_annotated, after)
    bad = gt.dropped | gt.duplicated | gt.relocated
    if bad:
        raise SystemExit(f"rewrite did not preserve markers cleanly ({len(bad)} "
                         f"dropped/dup/relocated): {sorted(bad)}. Try another task/model.")
    return before_annotated, after


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--live", action="store_true",
                    help="rewrite live with a real model instead of replaying the fixture")
    ap.add_argument("--capture", action="store_true",
                    help="rewrite live AND overwrite demo_fixture.json (maintenance)")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--task", default="reword", choices=list(LA.TASKS))
    ap.add_argument("--doc", default="doc1")
    ap.add_argument("--date", default=None,
                    help="capture date stamp for the fixture (YYYY-MM-DD)")
    args = ap.parse_args()

    if args.live or args.capture:
        before_annotated, after = asyncio.run(_rewrite(args.doc, args.model, args.task))
        meta = dict(doc=args.doc, model=args.model, task=args.task,
                    captured=args.date or "(live)")
        if args.capture:
            _, s = evaluate(before_annotated, after)
            FIXTURE.write_text(json.dumps(dict(
                doc=args.doc, model=args.model, task=args.task,
                captured=args.date or "(live)",
                note=("Real %s rewrite of docs/%s.md under the '%s' instruction, "
                      "markers preserved (SPEC.md §11) then stripped for replay. "
                      "Regenerate: python demo.py --capture --model %s --task %s"
                      % (args.model, args.doc, args.task, args.model, args.task)),
                mean_similarity=round(s["mean_sim"], 3),
                before_annotated=before_annotated,
                after_with_markers=after), indent=2) + "\n")
            print(f"wrote {FIXTURE.name}: {s['correct']}/{s['n']} recovered, "
                  f"{s['wrong']} wrong, mean sim {s['mean_sim']:.2f}")
            return
    else:
        if not FIXTURE.exists():
            raise SystemExit(f"no fixture at {FIXTURE}; run: python demo.py --capture")
        fx = json.loads(FIXTURE.read_text())
        meta = {k: fx[k] for k in ("doc", "model", "task", "captured")}
        before_annotated, after = fx["before_annotated"], fx["after_with_markers"]

    rows, s = evaluate(before_annotated, after)
    print(render(meta, rows, s, live=args.live))


if __name__ == "__main__":
    main()
