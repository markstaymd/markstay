#!/usr/bin/env python3
"""Self-tests for the LLM-driven attachment eval.

No network, no API key. The LLM rewrite is faked with controlled strings and the
deterministic `perturb` operators so the ground-truth / strip / score pipeline is
verified offline. Run:  python test_llm_attach.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import llm_attach as LA

_EVAL = Path(__file__).resolve().parents[2]
if str(_EVAL) not in sys.path:
    sys.path.insert(0, str(_EVAL))
import perturb as PB  # noqa: E402

DOC1 = (_EVAL / "docs" / "doc1.md").read_text()

PASS = 0
FAIL = 0


def check(name, cond):
    global PASS, FAIL
    if cond:
        PASS += 1
    else:
        FAIL += 1
        print(f"  FAIL: {name}")


def make_doc(blocks):
    """blocks: list of (text, id_or_None). Markers trail their block, mirroring
    perturb.serialize, so parse_document attaches them after-block."""
    parts = []
    for text, mid in blocks:
        if mid is None:
            parts.append(text)
        else:
            parts.append(f"{text}\n<!-- stay:{mid} hash=sha256:0badc0de -->")
    return "\n\n".join(parts) + "\n"


def cats(results):
    out = {}
    for r in results:
        out[r.cat] = out.get(r.cat, 0) + 1
    return out


# 1. Identity "rewrite": stripping markers, every block hash-matches -> all correct.
before, _ = PB.annotate(DOC1)
res = LA.score_document(before, before)
c = cats(res)
check("identity: no wrong", c.get("wrong", 0) == 0)
check("identity: no no_truth", c.get("no_truth", 0) == 0)
check("identity: all correct", c.get("correct", 0) == len(res) and len(res) > 0)
check("identity: hash tier did it", all(r.method == "hash" for r in res))
check("identity: similarity ~1.0", all(r.sim > 0.99 for r in res))

# 2. Real-ish drift with preserved markers (heavy paraphrase): distinct prose, so
#    high recovery and zero false attachment.
bpbs = PB.annotate(DOC1)[1]
after_pbs, _ = PB.heavy_paraphrase(bpbs)
after_marked = PB.serialize(after_pbs, strip=False)
res = LA.score_document(before, after_marked)
c = cats(res)
rec, fr, n = LA.recovery_falserate(c)
check("drift: no false attach on distinct prose", c.get("wrong", 0) == 0)
check("drift: recovery high", rec >= 0.9)
check("drift: everything scored (no drop)", c.get("no_truth", 0) == 0)
check("drift: quote tier was exercised", any(r.method == "quote" for r in res))

# 3. Reorder: gold index tracks the preserved marker, hash recovers by content.
after_pbs, _ = PB.reorder(bpbs)
after_marked = PB.serialize(after_pbs, strip=False)
res = LA.score_document(before, after_marked)
c = cats(res)
check("reorder: all correct (gold follows the marker)", c.get("wrong", 0) == 0
      and c.get("correct", 0) == len(res))

# 4. A dropped marker becomes no_truth and is excluded from recovery scoring.
after_pbs, _ = PB.reorder(bpbs)
after_marked = PB.serialize(after_pbs, strip=False)
# drop the first marker line entirely
lines = after_marked.splitlines()
for i, ln in enumerate(lines):
    if ln.startswith("<!-- stay:"):
        del lines[i]
        break
after_dropped = "\n".join(lines) + "\n"
res = LA.score_document(before, after_dropped)
c = cats(res)
check("dropped marker -> exactly one no_truth", c.get("no_truth", 0) == 1)
nt = [r for r in res if r.cat == "no_truth"]
check("dropped marker -> gold is None", nt and nt[0].gold is None)

# 5. `wrong` is reachable: edit the true block far, leave a near-twin pristine, so
#    the resolver's closest match is the twin while the gold is the edited block.
twin_before = make_doc([
    ("The ingest stage retries failed operations three times before giving up.", "a1"),
    ("The ingest stage retries failed operations four times before giving up.", "b1"),
])
twin_after = make_doc([
    ("A completely unrelated sentence about deployment scheduling and audit logs.", "a1"),
    ("The ingest stage retries failed operations four times before giving up.", "b1"),
])
res = LA.score_document(twin_before, twin_after)
by_id = {r.id: r for r in res}
check("twin: id a1 is scored (ground-truthable)", by_id["a1"].cat != "no_truth")
check("twin: id a1 false-attaches to the pristine twin", by_id["a1"].cat == "wrong")
check("twin: a1 gold is its edited block, target is the twin",
      by_id["a1"].gold == 0 and by_id["a1"].target == 1)

# 6. recovery_falserate math.
rec, fr, n = LA.recovery_falserate({"correct": 8, "wrong": 1, "missed": 1, "no_truth": 5})
check("rate math: scored excludes no_truth", n == 10)
check("rate math: recovery", abs(rec - 0.8) < 1e-9)
check("rate math: false-rate", abs(fr - 0.1) < 1e-9)

# 7. band_label boundaries (half-open bands).
check("band 0.29 -> 0.0-0.3", LA.band_label(0.29) == "0.0-0.3")
check("band 0.30 -> 0.3-0.5", LA.band_label(0.30) == "0.3-0.5")
check("band 0.70 -> 0.7-0.9", LA.band_label(0.70) == "0.7-0.9")
check("band 1.00 -> 0.9-1.0", LA.band_label(1.0) == "0.9-1.0")

# 8. similarity is symmetric-ish and bounded.
s = LA.similarity("the quick brown fox", "the quick brown FOX")
check("similarity casefolds to ~1.0", s > 0.99)
check("similarity of unrelated is low", LA.similarity("alpha beta", "zulu yankee") < 0.3)

# 9. strip_outer_fence peels a whole-document markdown fence but keeps inner fences.
wrapped = "```markdown\n# Title\n\nbody\n\n```python\nx=1\n```\n```"
peeled = LA.strip_outer_fence(wrapped)
check("strip_outer_fence: removes outer wrapper", peeled.startswith("# Title"))
check("strip_outer_fence: keeps inner code fence", "```python" in peeled)
plain = "# Title\n\nbody"
check("strip_outer_fence: leaves unfenced text alone", LA.strip_outer_fence(plain) == plain)

# 10. strip_markers removes both syntaxes.
check("strip_markers: html gone",
      "stay:" not in LA.strip_markers("x\n<!-- stay:z hash=sha256:ab -->"))
check("strip_markers: mdx gone",
      "stay:" not in LA.strip_markers("x\n{/* stay:z hash=sha256:ab */}"))


print(f"\n{PASS} passed, {FAIL} failed")
sys.exit(1 if FAIL else 0)
