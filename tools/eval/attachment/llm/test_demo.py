#!/usr/bin/env python3
"""Self-tests for the one-command attachment demo (`demo.py`).

No network, no API key: exercises the frozen-fixture replay path only, the same
path `python demo.py` takes with no flags. Run:  python test_demo.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import demo as D

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"FAIL: {name}")


# The committed fixture must exist and carry its provenance, the demo's honesty
# rests on it being a real captured rewrite, not a hand-written one.
check("fixture exists", D.FIXTURE.exists())
fx = json.loads(D.FIXTURE.read_text())
for k in ("doc", "model", "task", "before_annotated", "after_with_markers"):
    check(f"fixture has {k}", k in fx and fx[k])
check("fixture before-doc carries markers", "stay:" in fx["before_annotated"])
check("fixture after-doc carries markers (gold)", "stay:" in fx["after_with_markers"])

rows, s = D.evaluate(fx["before_annotated"], fx["after_with_markers"])

# The whole point of the demo: a heavy rewrite, identity still recovered, and
# crucially never a *wrong* attachment (the §10-forbidden outcome).
check("scored every block", s["n"] == 10)
check("zero false attachments", s["wrong"] == 0)
check("recovers a clear majority", s["correct"] >= 7)
check("recovery > exact-match baseline", s["correct"] > s["exact"])
check("quote tier carries reworded blocks", s["quote_saves"] >= 1)
check("heavy rewrite (mean sim < 0.9)", s["mean_sim"] < 0.9)
check("every row marked", all(r["mark"] in (D.OK, D.DETACH, D.WRONG) for r in rows))
check("no row marked wrong", all(r["mark"] != D.WRONG for r in rows))

meta = {k: fx[k] for k in ("doc", "model", "task", "captured")}
out = D.render(meta, rows, s, live=False)
check("render shows the headline", "HEADLINE" in out)
check("render states recovery + false-attach", "recovery" in out and "false-attach" in out)
check("render names the baseline contrast", "exact content match only" in out)
check("render has no false-attachment banner", "FALSE ATTACHMENT" not in out)
check("render points at the live reproduce path", "--live" in out)

print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
