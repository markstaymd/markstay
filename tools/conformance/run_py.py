#!/usr/bin/env python3
"""Python conformance runner: verify every corpus vector against the reference.

Loads both tiers (`spec/` and `gen/`) and, for each vector, recomputes the
reference output and asserts it matches the vector's stored expectation. The JS
runner (`impl/js/test/conformance.test.js`) loads the same JSON and asserts the
same shapes against the JS implementation, so the two runners are the cross-impl
regression sentinel: any change that breaks agreement fails one of them.

A `spec/` vector the reference fails is a REFERENCE BUG (the prose is authority),
not a corpus error. A `gen/` vector that fails means the reference changed since
generation; re-run generate.py only if the change was intended.

Exit status is 0 when every vector passes, 1 otherwise.

Run:  python3 conformance/run_py.py [--verbose]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "linter"))
sys.path.insert(0, str(ROOT / "eval" / "attachment"))
sys.path.insert(0, str(ROOT / "impl" / "py" / "src"))

import markstay_lint as L  # noqa: E402
import quote as Q  # noqa: E402
import resolver as R  # noqa: E402
import markstay as MW  # noqa: E402  (write path: impl/py is its canonical Python home)
from difflib import SequenceMatcher  # noqa: E402

# Reuse the exact serialization the generator used, so spec/ and gen/ are
# verified through identical shapes.
from generate import (  # noqa: E402
    marker_dict, block_dict, finding_dict, expect_hash, expect_resolve,
    expect_anchors,
)

TOL = 1e-9


def approx(a, b) -> bool:
    """Deep equality with a 1e-9 float tolerance (ints compare exactly under it)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a == b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < TOL
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(approx(a[k], b[k]) for k in a)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(approx(x, y) for x, y in zip(a, b))
    return a == b


def corpus_findings(findings, *, with_line):
    """Exclude only §5.4's optional parser advisory from core equality."""
    return [
        finding_dict(f, with_line=with_line)
        for f in findings
        if not (f.code == "OUTSIDE_SUBSET" and f.level == "info")
    ]


# --- per-category verifiers: (vector) -> (ok, detail) ---------------------

def v_hash(v) -> tuple[bool, str]:
    got = expect_hash(v["body"])
    want = {"normalized": v["normalized"], "sha256": v["sha256"],
            "truncations": v["truncations"]}
    return approx(got, want), f"got={got}"


def v_markers(v) -> tuple[bool, str]:
    got = [marker_dict(mk) for mk in L.find_markers(v["text"])]
    return approx(got, v["markers"]), f"got={got}"


def v_parse(v) -> tuple[bool, str]:
    got = [block_dict(b) for b in L.parse_document(v["doc"])]
    return approx(got, v["blocks"]), f"got={got}"


def v_lint(v) -> tuple[bool, str]:
    _, findings = L.lint_document(v["doc"])
    got = corpus_findings(L.sort_findings(findings), with_line=True)
    return approx(got, v["findings"]), f"got={got}"


def v_diff(v) -> tuple[bool, str]:
    findings = L.lint_diff(v["before"], v["after"])
    got = corpus_findings(L.sort_findings(findings), with_line=False)
    return approx(got, v["findings"]), f"got={got}"


def v_seqmatch(v) -> tuple[bool, str]:
    sm = SequenceMatcher(None, v["a"], v["b"], autojunk=False)
    got = {"ratio": sm.ratio(),
           "matching_blocks": [list(x) for x in sm.get_matching_blocks()]}
    want = {"ratio": v["ratio"], "matching_blocks": v["matching_blocks"]}
    return approx(got, want), f"got={got}"


def v_score(v) -> tuple[bool, str]:
    fn = v["fn"]
    if fn == "ratio":
        got = Q._ratio(v["a"], v["b"])
        return approx(got, v["score"]), f"got={got}"
    if fn == "body_score":
        got = Q.body_score(Q.Selector(quote=v["quote"]), v["candidate"])
        return approx(got, v["score"]), f"got={got}"
    if fn == "context_bonus":
        sel = Q.Selector(quote="q", prefix=v["prefix"], suffix=v["suffix"])
        got = Q.context_bonus(sel, v["prev"], v["next"])
        return approx(got, v["bonus"]), f"got={got}"
    if fn == "best_match":
        sel = Q.Selector(quote=v["quote"], prefix=v["prefix"], suffix=v["suffix"])
        idx, score, runner = Q.best_match(sel, v["candidates"])
        got = {"index": idx, "score": score, "runner_up": runner}
        want = {"index": v["index"], "score": v["score"], "runner_up": v["runner_up"]}
        return approx(got, want), f"got={got}"
    return False, f"unknown score fn: {fn!r}"


def v_resolve(v) -> tuple[bool, str]:
    """A vector that omits `threshold`/`margin` asserts the implementation's own
    §9 defaults, so an ABSENT field is passed through as None rather than
    defaulted here. Each field defaults independently. A field that is present
    is used as given, including a null, which fails loudly rather than being
    silently read as an omission."""
    got = expect_resolve(
        v["before"], v["after"],
        v["threshold"] if "threshold" in v else None,
        v["margin"] if "margin" in v else None,
    )
    return approx(got, v["resolutions"]), f"got={got}"


def v_anchors(v) -> tuple[bool, str]:
    """What `build_anchors` stores (§9), as opposed to what `resolve` decides.

    A separate category because resolution cannot see it: an implementation that
    stores whole neighbour blocks and one that stores §9's 48-character window
    produce identical resolutions, since both window the candidate side (and the
    stored side) at match time. The storage defect corrected in this release was
    invisible to all 34 resolve vectors and is caught here."""
    got = expect_anchors(v["document"])
    return approx(got, v["anchors"]), f"got={got}"


def _id_factory(ids):
    it = iter(ids)
    return lambda: next(it)


def _cursor_random(byte_list):
    """A byte source over a fixed list, consumed in order across random(n) draws."""
    state = {"i": 0}

    def r(n):
        i = state["i"]
        out = bytes(byte_list[i:i + n])
        state["i"] = i + n
        return out

    return r


def v_mint(v) -> tuple[bool, str]:
    """Id-minting vectors (§6): a fixed byte array is the injected source, so the
    rejection loop runs deterministically and identically across all three impls."""
    kwargs = {}
    if "alphabet" in v:
        kwargs["alphabet"] = v["alphabet"]
    got = MW.mint_id(v["length"], random=_cursor_random(v["bytes"]), **kwargs)
    return approx(got, v["expected"]), f"got={got}"


def v_stamp(v) -> tuple[bool, str]:
    """Write-path vectors (§3/§4/§6/§7/§8). The id sequence is injected so the
    minting helpers are deterministic; expected output is the frozen oracle."""
    op = v["op"]
    o = v.get("options", {})
    if op == "stamp":
        r = MW.stamp(v["input"], syntax=o.get("syntax", "html"), hash=o.get("hash", True),
                     hash_length=o.get("hashLength", MW.DEFAULT_HASH_LENGTH),
                     new_id=_id_factory(v["ids"]))
        got = {"text": r.text, "minted": r.minted}
    elif op == "restamp":
        r = MW.restamp(v["input"], hash_length=o.get("hashLength"),
                       add_missing=o.get("addMissing", False))
        got = {"text": r.text, "refreshed": r.refreshed}
    elif op == "repair":
        r = MW.repair_duplicates(v["input"], new_id=_id_factory(v["ids"]))
        got = {"text": r.text, "renamed": r.renamed}
    else:
        return False, f"unknown stamp op: {op!r}"
    return approx(got, v["expected"]), f"got={got}"


def v_preserve(v) -> tuple[bool, str]:
    """§11 preservation instruction + prompt composition. The corpus is the single
    source of the instruction text: each implementation carries its own copy so an
    installed package needs no corpus on disk, and this vector is what holds the
    copies byte-identical to each other."""
    fn = v["fn"]
    if fn == "instruction":
        got = MW.PRESERVE_INSTRUCTION
    elif fn == "return_only":
        got = MW.PRESERVE_RETURN_ONLY
    elif fn == "wrap":
        got = MW.preserve_wrap(v["doc"], v.get("task"))
    else:
        return False, f"unknown preserve fn: {fn!r}"
    return approx(got, v["expected"]), f"got={got!r}"


def v_check(v) -> tuple[bool, str]:
    """Commit-shaped baseline pairing and findings, with Git already materialized."""
    entries = [MW.CommitEntry(
        e["status"], e["src"], e["dst"], e.get("before"), e.get("after")
    ) for e in v["entries"]]
    result = MW.check_entries(entries, v.get("scope"))
    got = {
        "pairings": [{"path": path, "baseline": baseline}
                     for path, baseline in result.pairings],
        "reports": [
            {"label": label,
             "findings": corpus_findings(MW.sort_findings(findings),
                                         with_line=True)}
            for label, findings in result.reports
        ],
        "notes": result.notes,
        "hasErrors": result.has_errors,
    }
    return approx(got, v["expected"]), f"got={got}"


def v_rows(v) -> tuple[bool, str]:
    """SPEC.md §5.6 table-row identity: the optional `rows` profile.

    One category with three operation shapes, because row identity is not one
    function: recognition and attachment (`children`), the transactional write
    path with its migration probe (`stamp`), and §9.2 child recovery
    (`resolve`). Splitting them into three categories would let a runner
    advertise the profile while implementing only the half it found easy.
    """
    op = v["op"]
    if op == "children":
        mode = v.get("mode", "blank-line")
        blocks = [
            b for b in L.parse_document(v["doc"], mode=mode, child_blocks=True)
            if b.index >= 0
        ]
        got = {
            "blockIds": sorted(L._id_index(blocks)),
            "childIds": sorted(L._child_id_index(blocks)),
            "rows": [
                {"container": b.index, "ordinal": c.ordinal, "body": c.content,
                 "ids": [mk.id for mk in c.markers]}
                for b in blocks for c in b.children if c.kind == "row"
            ],
        }
    elif op == "stamp":
        ids = iter(v["ids"])
        r = MW.stamp(v["doc"], child_blocks=True, new_id=lambda: next(ids))
        got = {"text": r.text, "minted": r.minted, "drifted": list(r.drifted)}
    elif op == "resolve":
        mode = v.get("mode", "blank-line")
        resolved = L._resolve_children(
            L._build_child_anchors(v["before"], mode), v["after"], mode
        )
        got = {k: {"method": m, "target": t}
               for k, (m, t) in sorted(resolved.items())}
    else:
        return False, f"unknown rows op: {op!r}"
    return approx(got, v["expected"]), f"got={got}"


VERIFIERS = {
    "hash": v_hash, "markers": v_markers, "parse": v_parse, "lint": v_lint,
    "diff": v_diff, "seqmatch": v_seqmatch, "score": v_score, "resolve": v_resolve,
    "stamp": v_stamp, "mint": v_mint, "preserve": v_preserve, "check": v_check,
    "anchors": v_anchors,
    "rows": v_rows,
}

# Optional profiles a corpus file may declare with a top-level `profile` key.
# Every full runner knows the whole set; each advertises only what it
# implements. A profile a runner has never HEARD of is a failure rather than a
# skip, so adding a category to the corpus without touching the runners cannot
# pass as silence. §16 keeps §5.5 and §5.6 segmentation optional, so declining
# `rows` is conforming; running 419 of 420 core vectors is not.
KNOWN_PROFILES = {"rows"}
ADVERTISED_PROFILES = {"rows"}  # the Python reference implements §5.6

# A category that belongs to an optional profile is verified only by a runner
# advertising it, so the core coverage check below must not demand its vectors.
PROFILE_CATEGORIES = {"rows": "rows"}

# The corpus inventory, asserted rather than reported. Counting and printing what
# was found cannot catch a vector that goes missing: the denominator shrinks with
# the numerator, so `419/419 (419 core)` passes and reads like success. The JS and
# Rust runners have pinned these since the profile landed; this is the canonical
# runner holding the same guarantee its own README claims.
CORE_VECTORS = 420
PROFILE_VECTORS = {"rows": 31}


def main(argv=None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    verbose = "--verbose" in argv or "-v" in argv

    files = sorted((HERE / "spec").glob("*.json")) + sorted((HERE / "gen").glob("*.json"))
    if not files:
        print("no corpus files found under spec/ or gen/", file=sys.stderr)
        return 1
    files += sorted((HERE / "rows").glob("*.json"))

    total = 0
    failed = 0
    core_total = 0
    profile_total: dict[str, int] = {}
    declined: dict[str, int] = {}
    seen: set[str] = set()
    for path in files:
        data = json.loads(path.read_text())
        category = data["category"]
        tier = path.parent.name
        profile = data.get("profile")
        if profile is not None and profile not in KNOWN_PROFILES:
            print(f"  ?? {tier}/{path.name}: unknown profile {profile!r}")
            failed += 1
            continue
        if profile is not None and profile not in ADVERTISED_PROFILES:
            declined[profile] = declined.get(profile, 0) + len(data["vectors"])
            continue
        seen.add(category)
        verify = VERIFIERS.get(category)
        if verify is None:
            print(f"  ?? {tier}/{path.name}: unknown category {category!r}")
            failed += 1
            continue
        if profile is None:
            core_total += len(data["vectors"])
        else:
            profile_total[profile] = profile_total.get(profile, 0) + len(data["vectors"])
        for v in data["vectors"]:
            total += 1
            name = v.get("name", "?")
            try:
                ok, detail = verify(v)
            except Exception as e:  # noqa: BLE001
                ok, detail = False, f"{type(e).__name__}: {e}"
            if ok:
                if verbose:
                    print(f"  ok   {tier}/{category}:{name}")
            else:
                failed += 1
                print(f"  FAIL {tier}/{category}:{name}  {detail}")

    # A verifier with no vectors is a check that silently is not running. That is
    # the failure class this whole project exists to catch, so a corpus missing a
    # category fails here rather than passing on the strength of the others.
    expected = {
        c for c in VERIFIERS
        if PROFILE_CATEGORIES.get(c, None) in (None, *ADVERTISED_PROFILES)
    }
    for category in sorted(expected - seen):
        print(f"  FAIL coverage: verifier {category!r} has no vectors in the corpus")
        failed += 1

    if core_total != CORE_VECTORS:
        print(
            f"  FAIL inventory: {core_total} core vectors, expected {CORE_VECTORS}"
        )
        failed += 1
    # Every advertised profile must DECLARE a count. Reading the declaration with
    # .get() and skipping a missing one reinstates exactly the hole this check
    # exists to close: an empty PROFILE_VECTORS would pass while running anything.
    if set(PROFILE_VECTORS) != ADVERTISED_PROFILES:
        print(
            f"  FAIL inventory: PROFILE_VECTORS declares {sorted(PROFILE_VECTORS)}, "
            f"advertised profiles are {sorted(ADVERTISED_PROFILES)}"
        )
        failed += 1
    for profile in sorted(ADVERTISED_PROFILES & set(PROFILE_VECTORS)):
        want = PROFILE_VECTORS[profile]
        got = profile_total.get(profile, 0)
        if got != want:
            print(
                f"  FAIL inventory: {got} {profile} vectors, expected {want}"
            )
            failed += 1

    split = ", ".join(
        [f"{core_total} core"]
        + [f"{n} {p}" for p, n in sorted(profile_total.items())]
    )
    print(f"\n{total - failed}/{total} corpus vectors pass ({split})")
    for profile, n in sorted(declined.items()):
        print(f"  declined optional profile {profile!r} ({n} vectors not advertised)")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
