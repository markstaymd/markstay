#!/usr/bin/env python3
"""Reproduce the linter/replay relocation candidate populations, without judging.

Run from any directory: python3 eval/replay/relocation_recall.py > cases.json
Uses only this repository's pinned history. The linter pass preserves the original
probe's git-log ordering, blank-line parser, and quote.body_score thresholds.
The replay pass preserves cost_history's stamped/real-marker filters and scores.
"""

import json
import subprocess
from functools import lru_cache
from pathlib import Path

import replay as R

from quote import Selector, body_score, normalize

HERE = Path(__file__).resolve().parent
PIN = R.CORPUS_REV
FILES = (
    "CLAUDE.md", "NEIGHBOURS.md", "ROADMAP.md", "SPEC.md",
    "SPEC_DECISIONS.md", "eval/attachment/FINDINGS.md",
)


def git(*args):
    return subprocess.run(
        ["git", "-C", str(HERE.parents[1]), *args], check=True,
        capture_output=True, text=True, errors="replace",
    ).stdout


@lru_cache(None)
def score(old, new):
    return body_score(Selector(old), new)


def blocks(md):
    return [b for b in R.L.parse_document(md, mode="blank-line") if b.index >= 0]


def ids(bs):
    out = {}
    for i, block in enumerate(bs):
        for marker in block.markers:
            if marker.id and not marker.malformed and not marker.has_subhash:
                positions = out.setdefault(marker.id, [])
                if i not in positions:
                    positions.append(i)
    return out


def scan(path, old_commit, new_commit, before, after, get_score):
    bi, ai = ids(before), ids(after)
    kept = set(bi) & set(ai)
    free = [j for j, b in enumerate(after) if not any(
        m.id in kept and not m.has_subhash for m in b.markers
    )]
    out = []
    for mid in sorted(kept):
        if len(bi[mid]) != 1 or len(ai[mid]) != 1:
            continue
        old, now = before[bi[mid][0]].content, after[ai[mid][0]].content
        if not old or not now or R.L.body_hash(old) == R.L.body_hash(now):
            continue
        current_score = get_score(old, now)
        if current_score >= 0.5:
            continue
        ranked = sorted(
            ((get_score(old, b.content), j) for j, b in enumerate(after)
             if j != ai[mid][0]), reverse=True,
        )
        near = [j for s, j in ranked if j in free and s >= 0.8]
        contained = normalize(now) in normalize(old)
        out.append({
            "key": f"{path}#{mid}@{old_commit[:7]}..{new_commit[:7]}",
            "doc": path, "id": mid, "old_commit": old_commit,
            "new_commit": new_commit, "old": old, "id_now": now,
            "id_now_score": current_score, "near": near,
            "contained": contained, "fires": len(near) == 1 and not contained,
            "alternatives": [
                {"index": j, "score": s, "free": j in free,
                 "ids": list(ids([after[j]])), "text": after[j].content}
                for s, j in ranked[:3]
            ],
        })
    return out


def run():
    linter, replay = [], []
    edits = 0
    for path in FILES:
        revs = git("log", "--format=%H", PIN, "--", path).split()[::-1]
        prev = None
        for commit in revs:
            # ls-tree distinguishes an absent path from a failed git command.
            exists = git("ls-tree", "--name-only", commit, "--", path).strip()
            cur = git("show", f"{commit}:{path}") if exists else ""
            if prev is not None and cur:
                edits += 1
                old_commit, old_md = prev
                linter.extend(scan(path, old_commit, commit, blocks(old_md), blocks(cur), score))
            if cur:
                prev = commit, cur
    docs, _ = R.load_corpus(PIN)
    table = R.Table()
    for doc in docs:
        for old, new in zip(doc.revs, doc.revs[1:]):
            if old.stamped:
                replay.extend(scan(doc.name, old.commit, new.commit, old.blocks, new.blocks,
                                   lambda a, b: table.get(normalize(a), normalize(b))))
    lp, rp = {x["key"] for x in linter}, {x["key"] for x in replay}
    summary = {
        "linter_edits": edits, "linter_low": len(linter),
        "linter_fires": sum(x["fires"] for x in linter),
        "replay_low": len(replay), "replay_fires": sum(x["fires"] for x in replay),
        "linter_only": sorted(lp - rp), "replay_only": sorted(rp - lp),
    }
    # A changed population is a failed reproduction, never a silently new result.
    if (summary["linter_low"], summary["linter_fires"]) != (44, 13):
        raise SystemExit(f"Pinned linter population changed: {summary}")
    rows = {x["key"]: {**x, "populations": ["replay"]} for x in replay}
    for row in linter:
        row["populations"] = ["linter"] + (["replay"] if row["key"] in rp else [])
        rows[row["key"]] = row
    print(json.dumps({"rev": PIN, "summary": summary,
                      "cases": sorted(rows.values(), key=lambda x: x["key"])},
                     indent=2, ensure_ascii=False))


if __name__ == "__main__":
    run()
