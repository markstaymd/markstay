"""Is a block's enclosing section useful recovery evidence for the QUOTE tier?

The QUOTE tier's residual failure is a near-duplicate block: an edit to the true
block can make a pristine twin the closest match. `prefix`/`suffix` already give
the resolver two contextual signals (SPEC.md §9); a stored **heading path** would
be a third, borrowed from revdown. This runs the arms that price it.

It is a 2x2 of two independent choices, not a list of variants, because their
interaction is the result: the bonus is what makes lifting the clamp safe, and
the clamp is what gives the bonus a floor.

    A       shipped resolver (clamp kept, no heading evidence)
    A'      clamp lifted only. Any B gain measured without this arm could be
            the clamp's rather than the heading path's.
    B..     a bonus when the candidate's heading path equals the stored one,
            swept over size (0.06 / 0.12) and over both clamp settings
    B..u    the same, *ungated*: the bonus applies at any body score. Gated
            arms require the body to clear the commit threshold first, so the
            bonus can only reorder candidates that already qualify on their own
            text and can never lift a weak body match over the bar.
    C       revdown's hard filter to equal-path candidates. Included to be
            priced, not to be shipped: SPEC.md §2.2 requires a stay to survive
            movement within a document, which a filter cannot do by construction.

Corpora, each answering a different question:

    cross-section   the multi-section fixture: adversarial twins under different
                    parents, plus the four structural operators (a block that
                    changes section, a moved section, renamed and deleted
                    headings). The only corpus where the mechanism can fire and
                    the only one that prices arm C's cost.
    near_dups       single-section twins. The negative control: every path is
                    identical, so an arm that moves this number is broken.
    distinct prose  doc1 + doc2, the regression guard.
    no-headings     doc1 with its heading lines removed, so no anchor stores a
                    path at all. Every arm must be bit-identical to control:
                    this is the guard against rewarding candidates for matching
                    an empty path.

Run:  python run_attach_eval.py --arms      (writes results_headingpath.{json,md})
"""

from __future__ import annotations

import json
import re
from math import comb
from pathlib import Path

import perturb as PB
import resolver as R

HERE = Path(__file__).parent
DOCS_DIR = HERE.parent / "docs"

# (label, clamp, heading mode, size, gate). `gate=None` means "the commit
# threshold", i.e. the preference is a tiebreaker among candidates that already
# clear the bar on body text alone; 0.0 is the ungated form the cross-section
# audit measured.
#
# The D arms are **post-hoc**, added after the pre-registered ones ran, and the
# reason is written down rather than smoothed over: every clamped bonus arm
# moved the single-section negative control, which the plan's own rule calls
# broken rather than effective. A bonus raises matched scores into the 1.0
# ceiling the clamp imposes, so on a document where everything matches it
# collapses margins and detaches. Expressing the same preference as a penalty on
# *mismatched* candidates is the same ranking without that side effect.
ARMS = [
    ("A",     True,  "off",     0.0,  None),
    ("A'",    False, "off",     0.0,  None),
    ("B06",   False, "bonus",   0.06, None),
    ("B06c",  True,  "bonus",   0.06, None),
    ("B12",   False, "bonus",   0.12, None),
    ("B12c",  True,  "bonus",   0.12, None),
    ("B12u",  False, "bonus",   0.12, 0.0),
    ("B12cu", True,  "bonus",   0.12, 0.0),
    ("D06c",  True,  "penalty", 0.06, None),
    ("D12c",  True,  "penalty", 0.12, None),
    ("D12",   False, "penalty", 0.12, None),
    ("C",     False, "filter",  0.0,  None),
    ("Cc",    True,  "filter",  0.0,  None),
]

# Operators added after the pre-registered arms had run. They are reported, and
# the aggregate is reported both with and without them, because an operator
# chosen once results are visible cannot also be neutral evidence for a headline
# number: this one was built to expose a specific failure and it adds cases the
# preference arms happen to win.
POSTHOC_OPS = {"cross_section_move_edit"}

# Operators whose failure is a veto rather than an aggregate cost. Each names a
# guarantee an arm could break while still posting a better headline number.
VETO_OPS = {
    "cross_section_move": "a block that changed section (SPEC.md §2.2)",
    "cross_section_move_edit": "the same block, drifted, so it reaches tier 3",
    "section_move": "a whole section relocated",
    "heading_rename": "headings reworded, prose untouched",
    "heading_delete": "a heading deleted, its section absorbed",
    "clone": "within-section twins",
    "edit_in_place": "drift on one twin of a pair",
}


def _binom_cdf(k: int, n: int, p: float) -> float:
    """P(X <= k) for X ~ Binomial(n, p). Direct summation: n here is in the
    hundreds and k is small, so accuracy beats cleverness."""
    if p <= 0:
        return 1.0
    if p >= 1:
        return 0.0 if k < n else 1.0
    return sum(comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def clopper_pearson(k: int, n: int, alpha: float = 0.05) -> tuple[float, float]:
    """Exact 95% binomial confidence interval, by bisection on the binomial CDF.

    Dependency-free on purpose: this eval has no install step, and an interval
    is the difference between "0 of 72" and "0 of 351" being read as the same
    result. With zero events the upper bound collapses to 1 - alpha**(1/n),
    which is why the project's ~1% false-attach bar needs n >= ~300."""
    if n == 0:
        return 0.0, 1.0
    lo, hi = 0.0, 1.0
    if k > 0:
        a, b = 0.0, 1.0
        for _ in range(80):  # P(X >= k) = alpha/2  ->  1 - CDF(k-1) = alpha/2
            mid = (a + b) / 2
            if 1 - _binom_cdf(k - 1, n, mid) < alpha / 2:
                a = mid
            else:
                b = mid
        lo = (a + b) / 2
    if k < n:
        a, b = 0.0, 1.0
        for _ in range(80):  # P(X <= k) = alpha/2
            mid = (a + b) / 2
            if _binom_cdf(k, n, mid) > alpha / 2:
                a = mid
            else:
                b = mid
        hi = (a + b) / 2
    return lo, hi


def strip_headings(md: str) -> str:
    """Drop every ATX heading line, leaving the prose. Produces a corpus where
    no anchor can store a path, which is the empty-path guard's test case."""
    keep = [ln for ln in md.split("\n") if not re.match(r"^ {0,3}#{1,6}(?:[ \t]|$)", ln)]
    return re.sub(r"\n{3,}", "\n\n", "\n".join(keep))


def corpora() -> list[dict]:
    fixture = HERE / "fixtures" / "cross_section_dups.md"
    if not fixture.exists():
        raise SystemExit(
            f"missing {fixture.name}: the multi-section fixture is not part of "
            "this copy. Run this from the markstay umbrella.")
    doc1 = (DOCS_DIR / "doc1.md").read_text()
    all_ops = {**PB.OPERATORS, **PB.SECTION_OPERATORS}
    return [
        {"name": "cross-section fixture", "role": "the adversarial target",
         "bases": [fixture.read_text()], "ops": list(all_ops)},
        {"name": "near_dups", "role": "negative control (single-section twins)",
         "bases": [(HERE / "fixtures" / "near_dups.md").read_text()],
         "ops": list(PB.OPERATORS)},
        {"name": "distinct prose", "role": "regression guard",
         "bases": [(DOCS_DIR / f"{d}.md").read_text() for d in ("doc1", "doc2")],
         "ops": list(PB.OPERATORS)},
        {"name": "no headings", "role": "empty-path guard (doc1, headings removed)",
         "bases": [strip_headings(doc1)], "ops": list(PB.OPERATORS)},
    ]


def _rates(cats: dict) -> dict:
    correct = cats.get("correct", 0)
    wrong = cats.get("wrong", 0)
    missed = cats.get("missed", 0)
    false_n = wrong + cats.get("false_attach", 0)
    survivable = correct + wrong + missed
    total = sum(cats.values())
    rec_lo, rec_hi = clopper_pearson(correct, survivable)
    f_lo, f_hi = clopper_pearson(false_n, total)
    return {
        "n": total,
        "survivable": survivable,
        "cats": cats,
        "recovery": correct / survivable if survivable else 0.0,
        "recovery_ci": [rec_lo, rec_hi],
        "false_attach": false_n / total if total else 0.0,
        "false_attach_n": false_n,
        "false_attach_ci": [f_lo, f_hi],
        "detach": missed / survivable if survivable else 0.0,
    }


def _per_case(cells: list[dict]) -> dict[str, str]:
    """(document, id) -> outcome category, so an arm can be compared to the
    control case by case. An operator-level aggregate hides the cost that
    matters here: `cross_section_move` moves one block out of ~44, so an arm can
    lose that block, the one SPEC.md §2.2 is about, and still post a better
    number for the operator by helping the 43 that did not move."""
    return {f"{doc}:{d['id']}": d["cat"]
            for doc, cell in cells for d in cell["detail"]}


def run(threshold=R.DEFAULT_THRESHOLD, margin=R.DEFAULT_MARGIN) -> dict:
    import run_attach_eval as RUN  # circular only at import time

    out = {"threshold": threshold, "margin": margin,
           "arms": [a[0] for a in ARMS], "corpora": []}
    for corpus in corpora():
        entry = {"name": corpus["name"], "role": corpus["role"],
                 "ops": corpus["ops"], "arms": {}}
        cases: dict[str, dict[str, dict[str, str]]] = {}
        for label, clamp, mode, size, gate in ARMS:
            kw = {"heading_path": mode, "clamp": clamp,
                  "heading_bonus": size, "heading_gate": gate}
            rows, cases[label] = [], {}
            for op in corpus["ops"]:
                cells = [(f"d{i}", RUN.run_case(b, op, True, threshold, margin, kw))
                         for i, b in enumerate(corpus["bases"])]
                rows.append({
                    "op": op,
                    "n": sum(c["n"] for _, c in cells),
                    "cats": RUN.merge_counts([c for _, c in cells], "cats"),
                })
                cases[label][op] = _per_case(cells)
            pre = [r for r in rows if r["op"] not in POSTHOC_OPS]
            entry["arms"][label] = {
                "config": {"clamp": clamp, "mode": mode,
                           "size": size, "gate": gate},
                "overall": _rates(RUN.merge_counts(rows, "cats")),
                "pre_registered": _rates(RUN.merge_counts(pre, "cats")),
                "by_op": {r["op"]: _rates(r["cats"]) for r in rows},
            }

        # Case-by-case against the shipped control, which is the only way to see
        # a single guaranteed case being traded for an aggregate gain.
        safe = {"correct", "correct_detach"}
        for label in entry["arms"]:
            lost, introduced = [], []
            for op, base in cases["A"].items():
                arm = cases[label][op]
                for key, cat in base.items():
                    now = arm.get(key)
                    if cat == "correct" and now != "correct":
                        lost.append({"op": op, "case": key, "became": now})
                    if cat in safe and now not in safe:
                        introduced.append({"op": op, "case": key, "became": now})
            entry["arms"][label]["regressions"] = {
                "lost_recovery": lost,
                "unsafe": [r for r in introduced
                           if r["became"] in ("wrong", "false_attach")],
            }
        out["corpora"].append(entry)
    return out


def _pct(x):
    return f"{100 * x:.1f}%"


def _ci(pair):
    return f"[{100 * pair[0]:.1f}, {100 * pair[1]:.1f}]"


def report(data: dict) -> str:
    L = ["# Heading path as recovery evidence: the arms\n"]
    L.append(
        "Every number here is the **markers-stripped** case (the AI-regeneration "
        "failure mode), threshold "
        f"{data['threshold']}, margin {data['margin']}. Intervals are 95% "
        "Clopper-Pearson.\n")
    L.append(
        "\n| Arm | Clamp | Heading | Size | Gate |\n|---|---|---|--:|---|")
    sized = ("bonus", "penalty")
    for label, clamp, mode, size, gate in ARMS:
        L.append(f"| {label} | {'kept' if clamp else 'lifted'} | {mode} | "
                 f"{size if mode in sized else '-'} | "
                 f"{('threshold' if gate is None else gate) if mode in sized else '-'} |")
    L.append(
        "\n`A` is the shipped resolver. A gated preference applies only to a "
        "candidate whose body already clears the commit threshold, so it can "
        "reorder qualifying candidates but can never lift a weak body match over "
        "the bar; the `u` arms drop that gate, which is the form the "
        "cross-section audit measured. The `D` arms are **post-hoc**: see the "
        "note in this module's source for why a penalty on mismatched candidates "
        "is not the same experiment as a bonus on matched ones.\n")

    for corpus in data["corpora"]:
        posthoc = [op for op in corpus["ops"] if op in POSTHOC_OPS]
        L.append(f"\n## {corpus['name']}  ({corpus['role']})\n")
        if posthoc:
            L.append(
                "The **pre-reg** column excludes "
                + ", ".join(f"`{op}`" for op in posthoc)
                + ", added after the arms had already run. Lead with it; the "
                  "post-hoc operator is evidence for the veto it was built for, "
                  "not for a headline recovery number.\n")
        L.append("| Arm | n | recovery | 95% CI | pre-reg | false attach | 95% CI | detach |")
        L.append("|-----|--:|---------:|--------|--------:|-------------:|--------|-------:|")
        for label in data["arms"]:
            a = corpus["arms"][label]["overall"]
            pre = corpus["arms"][label]["pre_registered"]
            L.append(
                f"| {label} | {a['n']} | {_pct(a['recovery'])} | "
                f"{_ci(a['recovery_ci'])} | {_pct(pre['recovery'])} | "
                f"{_pct(a['false_attach'])} "
                f"({a['false_attach_n']}) | {_ci(a['false_attach_ci'])} | "
                f"{_pct(a['detach'])} |")
        L.append(
            "\nThe intervals assume independent trials and these are not: each "
            "corpus is a handful of documents put through every operator, so the "
            "same block is retried many times and the bounds are narrower than "
            "the evidence warrants. Read them as a floor on uncertainty.\n")

        L.append(f"\n### Case-by-case against the control ({corpus['name']})\n")
        L.append(
            "Ids arm A resolved correctly and this arm did not, and ids arm A "
            "handled safely that this arm attaches wrongly. An operator-level "
            "aggregate cannot show these: `cross_section_move` moves one block "
            "of ~44, so an arm can lose the case SPEC.md §2.2 is *about* and "
            "still improve the operator's number.\n")
        L.append("| Arm | recoveries lost | of those, by operator | new false attachments |")
        L.append("|-----|----------------:|------------------------|----------------------:|")
        for label in data["arms"]:
            reg = corpus["arms"][label]["regressions"]
            per_op: dict[str, int] = {}
            for r in reg["lost_recovery"]:
                per_op[r["op"]] = per_op.get(r["op"], 0) + 1
            detail = ", ".join(f"{k} {v}" for k, v in sorted(per_op.items())) or "-"
            L.append(f"| {label} | {len(reg['lost_recovery'])} | {detail} | "
                     f"{len(reg['unsafe'])} |")

        vetoes = [op for op in corpus["ops"] if op in VETO_OPS]
        if vetoes:
            L.append(f"\n### Per-operator vetoes ({corpus['name']})\n")
            L.append(
                "An aggregate can improve while a whole class fails, and the "
                "failures in this eval concentrate rather than spread. Cells are "
                "recovery / false attachment; **bold** marks a regression against "
                "arm A.\n")
            L.append("| Arm | " + " | ".join(vetoes) + " |")
            L.append("|---" * (len(vetoes) + 1) + "|")
            base = corpus["arms"]["A"]["by_op"]
            for label in data["arms"]:
                cells = []
                for op in vetoes:
                    cur, ref = corpus["arms"][label]["by_op"][op], base[op]
                    worse = (cur["recovery"] < ref["recovery"] - 1e-9
                             or cur["false_attach"] > ref["false_attach"] + 1e-9)
                    cell = f"{_pct(cur['recovery'])} / {_pct(cur['false_attach'])}"
                    cells.append(f"**{cell}**" if worse else cell)
                L.append(f"| {label} | " + " | ".join(cells) + " |")
            L.append("\nWhat each one guards: "
                     + "; ".join(f"`{op}` {VETO_OPS[op]}" for op in vetoes) + ".\n")
    return "\n".join(L) + "\n"


def write(out: str) -> dict:
    data = run()
    Path(out + ".json").write_text(json.dumps(data, indent=1) + "\n")
    Path(out + ".md").write_text(report(data))
    return data
