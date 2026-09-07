#!/usr/bin/env python3
"""Generate the `gen/` conformance tier from the Python reference.

The conformance corpus has two tiers:

* `spec/` , hand-authored from SPEC.md prose, asserting what the *words* require.
  These are authority; a `spec/` vector the reference fails is a reference bug.
* `gen/`  , emitted here from the reference functions, for breadth/regression.

Both tiers share one vector shape per category (the `*_dict` / `*_list` helpers
below); `run_py.py` imports those helpers so it verifies both tiers identically,
and `impl/js/test/conformance.test.js` reproduces the same shapes in JS. Where
the two tiers disagree, the `spec/` tier wins (the prose is authority).

Run:  python3 conformance/generate.py    # rewrites conformance/gen/*.json
"""

from __future__ import annotations

import json
import random
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

GEN = HERE / "gen"


# --- canonical vector shapes (shared with run_py.py) ----------------------

def marker_dict(mk) -> dict:
    return {
        "id": mk.id,
        "hash": mk.hash,
        "raw": mk.raw,
        "syntax": mk.syntax,
        "line": mk.line,
        "malformed": mk.malformed,
    }


def block_dict(b) -> dict:
    return {
        "content": b.content,
        "index": b.index,
        "ids": [mk.id for mk in b.markers],
        "line": b.line,
        "orphan": b.index == -1,
    }


def finding_dict(f, with_line: bool) -> dict:
    d = {"level": f.level, "code": f.code, "id": f.id}
    if with_line:
        d["line"] = f.line
    return d


# --- reference computations behind each category -------------------------

def expect_hash(body: str) -> dict:
    full = L.body_hash(body)
    return {
        "normalized": L.normalize_body(body),
        "sha256": full,
        "truncations": {str(n): L.body_hash(body, n) for n in (4, 8, 12, 16)},
    }


def expect_markers(text: str) -> list:
    return [marker_dict(mk) for mk in L.find_markers(text)]


def expect_parse(doc: str) -> list:
    return [block_dict(b) for b in L.parse_document(doc)]


def expect_lint(doc: str) -> list:
    _, findings = L.lint_document(doc)
    return [finding_dict(f, with_line=True) for f in L.sort_findings(findings)]


def expect_diff(before: str, after: str) -> list:
    findings = L.lint_diff(before, after)
    return [finding_dict(f, with_line=False) for f in L.sort_findings(findings)]


def expect_seqmatch(a: str, b: str) -> dict:
    sm = SequenceMatcher(None, a, b, autojunk=False)
    return {
        "ratio": sm.ratio(),
        "matching_blocks": [list(x) for x in sm.get_matching_blocks()],
    }


def expect_anchors(document: str) -> list[dict]:
    """What `build_anchors` EMITS for a document, in document order.

    Resolution outcomes cannot test this. Two implementations, one storing §9's
    48-character window and one storing whole neighbour blocks, resolve
    identically as long as both window at match time, so a storage-conformance
    defect is invisible to every `resolve` vector. §9 constrains the stored
    field, so the corpus asserts the stored field."""
    return [
        {"id": a.id, "hash": a.hash, "quote": a.selector.quote,
         "prefix": a.selector.prefix, "suffix": a.selector.suffix}
        for a in R.build_anchors(document)
    ]


def expect_resolve(before: str, after: str,
                   threshold: float | None = None,
                   margin: float | None = None) -> dict:
    """`threshold`/`margin` of None means the vector omitted them, so the
    implementation's own §9 defaults (0.5 / 0.05) must be what applies. Every
    other vector injects both, which is exactly why an implementation could
    compile in different constants and still pass the whole category."""
    kw = {}
    if threshold is not None:
        kw["threshold"] = threshold
    if margin is not None:
        kw["margin"] = margin
    anchors = R.build_anchors(before)
    res = R.resolve(anchors, after, **kw)
    return {
        r.id: {"method": r.method, "target": r.target, "score": r.score}
        for r in res.values()
    }


# --- gen-tier inputs -------------------------------------------------------

def _doc(name: str) -> str:
    return (ROOT / "eval" / "docs" / name).read_text()


def _fixture(name: str) -> str:
    return (ROOT / "eval" / "attachment" / "fixtures" / name).read_text()


def seqmatch_pairs() -> list[tuple[str, str]]:
    curated = [
        ("", ""), ("a", ""), ("", "a"), ("abc", "abc"),
        ("tide", "diet"), ("diet", "tide"),
        ("aaaa", "aa"), ("aa", "aaaa"), ("abcabcabc", "abcabc"),
        ("the quick brown fox", "the quick red fox"),
        ("banana", "ananas"), ("abcdef", "fedcba"), ("xxxxyyyy", "yyyyxxxx"),
        ("hello world", "hello cruel world"), ("aXbXcXd", "abcd"),
        ("mississippi", "missouri"), ("aaaaaa", "aaa"),
        ("the ingest stage retries failed operations three times",
         "the persist stage retries failed operations five times"),
        # non-BMP: code-point vs UTF-16 unit divergence
        ("\U0001F600\U0001F601", "\U0001F601\U0001F600"),
        ("a\U0001F600b", "ab"), ("\U0001F4A9x\U0001F4A9", "x\U0001F4A9x"),
        ("café", "cafe"), ("naïve", "naive"),
    ]
    rng = random.Random(20260616)
    alphabet = "abcde \U0001F600é"
    rand = []
    for _ in range(120):
        la = rng.randint(0, 14)
        lb = rng.randint(0, 14)
        a = "".join(rng.choice(alphabet) for _ in range(la))
        b = "".join(rng.choice(alphabet) for _ in range(lb))
        rand.append((a, b))
    return curated + rand


def hash_bodies() -> list[str]:
    return [
        "A single normalized paragraph.",
        "trailing spaces here   \nand a tab\there\t",
        "windows\r\nline\r\nendings",
        "lone\rcarriage\rreturns",
        "\n\n\nleading and trailing blank lines\n\n\n",
        "   \n  leading blank-ish lines with whitespace\nbody line\n   \n",
        "```\ncode with trailing ws   \n\tindented\t\n```",
        "café au lait , non-ASCII UTF-8 body",
        "emoji body \U0001F600 stays stable",
        "line one\nline two\nline three",
        "",
        "   ",
        "\n\n",
        "one",
    ]


def marker_texts() -> list[str]:
    return [
        "Para.\n<!-- stay:8f24 hash=sha256:7a9c -->",
        "Para.\n<!-- stay:a1b2 -->",
        "MDX.\n{/* stay:mdx1 hash=sha256:ABCD */}",
        "<!-- stay:note=hello -->",                       # malformed: no id
        "<!-- stay:id1 x-acme-author=\"jo\" hash=sha256:dead -->",
        "<!-- stay:id2 hash=sha256:DEADbeef extra=1 -->",  # uppercase hex -> lowered
        "reordered\n<!-- stay:r1 hash=sha256:abcd k=v -->\nmore",
        "line0\nline1\n<!-- stay:onln2 -->\nline3",        # line number check
        # SPEC.md §3.3 makes this string content, not a marker, and this vector
        # still expects `find_markers` to RETURN it. That is the point: the
        # function is a raw grammar primitive with no document around it, so it
        # answers the grammar question and nothing else. Every document-level
        # consumer (parse, lint, stamp, restamp) filters this same marker out
        # against `code_lines`, so a `markers` vector and a `parse` vector over
        # the same text are meant to disagree here. Do not "fix" one to match
        # the other.
        "```\n<!-- stay:infence hash=sha256:1234 -->\n```",
        "two\n<!-- stay:m1 -->\n<!-- stay:m2 hash=sha256:beef -->",
        '<!-- stay:multi x-note="line one\nline two" hash=sha256:cafe -->',
        "no markers here at all",
    ]


def parse_docs() -> list[str]:
    return [
        "Just one paragraph.\n<!-- stay:p1 -->\n",
        "Some content.\n\n<!-- stay:x -->\n",
        "<!-- stay:loose -->\n\nReal content below.\n",
        "A.\n<!-- stay:a -->\n\nB.\n<!-- stay:b -->\n",
        "Block one.\n<!-- stay:dup -->\n\nBlock two.\n<!-- stay:dup -->\n",
        "first\n\nsecond\n\nthird\n",
        "windows\r\nendings\r\n\r\nsecond block\r\n",
        "trailing marker chunk\n\n<!-- stay:t1 -->\n<!-- stay:t2 -->\n",
        _doc("doc1.md"),
    ]


def lint_docs() -> list[str]:
    body = "The order pipeline ingests messages and normalizes them."
    h = L.body_hash(body, 4)
    # §4: a stored hash in uppercase hex is not drift. The body is chosen so its
    # 4-char truncation actually CONTAINS hex letters, otherwise `.upper()` is a
    # no-op and the vector silently degenerates into a second clean-hash case.
    up_body = "Users authenticate with an API token."
    up = L.body_hash(up_body, 4).upper()
    assert up != up.lower(), f"{up_body!r} truncates to {up!r}: no letters to upper-case"
    return [
        f"{body}\n<!-- stay:8f24 hash=sha256:{h} -->\n",
        f"{up_body}\n<!-- stay:8f24 hash=sha256:{up} -->\n",
        "Block one.\n<!-- stay:dup -->\n\nBlock two.\n<!-- stay:dup -->\n",
        "A paragraph.\n<!-- stay:note=hello -->\n",
        "<!-- stay:loose -->\n\nReal content below.\n",
        "Edited content.\n<!-- stay:z9 hash=sha256:dead -->\n",
        "An MDX block.\n{/* stay:mdx1 hash=sha256:abcd */}\n",
        "clean para.\n<!-- stay:ok -->\n\nanother.\n<!-- stay:ok2 -->\n",
    ]


def diff_pairs() -> list[tuple[str, str]]:
    return [
        ("A.\n<!-- stay:a -->\n\nB.\n<!-- stay:b -->\n",
         "A.\n<!-- stay:a -->\n\nB rewritten without its marker.\n"),
        ("A.\n<!-- stay:a -->\n",
         "A.\n<!-- stay:a -->\n\nCopy of A.\n<!-- stay:a -->\n"),
        ("A.\n<!-- stay:a -->\n",
         "A.\n<!-- stay:a -->\n\nBrand new block.\n<!-- stay:c -->\n"),
        ("Alpha content.\n<!-- stay:aaa -->\n\nBeta content.\n<!-- stay:bbb -->\n",
         "Beta content.\n<!-- stay:aaa -->\n\nAlpha content.\n<!-- stay:bbb -->\n"),
        ("Alpha content.\n<!-- stay:aaa -->\n",
         "Alpha content, now revised.\n<!-- stay:aaa -->\n"),
        ("Keep me.\n<!-- stay:k -->\n",
         "Keep me.\n<!-- stay:k -->\n"),
    ]


def score_vectors() -> list[dict]:
    out: list[dict] = []
    ratio_pairs = [
        ("the quick brown fox", "the quick red fox"),
        ("", "x"), ("x", ""), ("", ""), ("same", "same"),
        ("tide", "diet"),
    ]
    for a, b in ratio_pairs:
        out.append({"fn": "ratio", "a": a, "b": b, "score": Q._ratio(a, b)})

    body_pairs = [
        ("The validation stage checks three things.",
         "The validation stage checks three things."),
        ("A short paragraph about retries.",
         "A short paragraph about retries with more detail appended here."),
        ("the ingest stage retries three times",
         "the persist stage retries five times"),
        ("completely unrelated text xyz", "the quick brown fox jumps"),
        ("contained", "this sentence has contained inside it somewhere"),
    ]
    for q, c in body_pairs:
        out.append({"fn": "body_score", "quote": q, "candidate": c,
                    "score": Q.body_score(Q.Selector(quote=q), c)})

    # The last two cases carry a stored prefix/suffix well past §9's 48 characters,
    # which `build_anchors` no longer emits but a consumer-assembled selector or one
    # stored by a pre-fix version still can. Matching windows the stored side too, so
    # the bonus is identical to the same selector already windowed: the pair below is
    # byte-identical after windowing and must score the same. Nothing in `anchors` or
    # `resolve` can see this, because both build their selectors from a document.
    _long_prev = ("Operators can override these retry defaults on a per-partner basis, "
                  "but every override expires after thirty days.")
    ctx_cases = [
        ("preceding context here", "following context there",
         "...the preceding context here", "following context there and more..."),
        ("", "suffix only", "irrelevant", "suffix only matches"),
        ("prefix only", "", "a prefix only here", "irrelevant"),
        (_long_prev, "", _long_prev, "irrelevant"),
        (_long_prev[-48:], "", _long_prev, "irrelevant"),
    ]
    for prefix, suffix, prev, nxt in ctx_cases:
        sel = Q.Selector(quote="q", prefix=prefix, suffix=suffix)
        out.append({"fn": "context_bonus", "prefix": prefix, "suffix": suffix,
                    "prev": prev, "next": nxt,
                    "bonus": Q.context_bonus(sel, prev, nxt)})

    bm_cases = [
        ("the quick brown fox jumps", "", "",
         ["the quick brown fox jumps", "a totally different sentence here",
          "the quick brown fox leaps high"]),
        ("completely unrelated text xyz", "", "",
         ["the quick brown fox jumps", "a totally different sentence here"]),
        # exact tie: two identical candidates -> later index wins, runner_up 1.0
        ("identical block body", "", "",
         ["identical block body", "identical block body"]),
    ]
    for quote, prefix, suffix, cands in bm_cases:
        sel = Q.Selector(quote=quote, prefix=prefix, suffix=suffix)
        idx, score, runner = Q.best_match(sel, cands)
        out.append({"fn": "best_match", "quote": quote, "prefix": prefix,
                    "suffix": suffix, "candidates": cands,
                    "index": idx, "score": score, "runner_up": runner})
    return out


def _id_factory(ids):
    it = iter(ids)
    return lambda: next(it)


def stamp_vectors() -> list[dict]:
    """Write-path vectors (SPEC.md §3/§4/§6/§7/§8). Inputs, options, and id
    sequences are authored here; the id sequence is injected so minting is
    deterministic, and the expected output is frozen from the reference write
    path (impl/py), exactly as every other gen/ category freezes reference
    output. The JS reference must reproduce these bytes from the same inputs."""
    doc = "# Title\n\nFirst paragraph.\n\nSecond paragraph.\n\n- a\n- b\n"
    cases = [
        ("stamp-single-block-trailing-3.1", "stamp", "Hello world.", {}, ["abc12345"]),
        ("stamp-multi-block-sequential-ids", "stamp", doc, {}, ["id00", "id01", "id02", "id03"]),
        ("stamp-mdx-no-hash", "stamp", "Body.", {"syntax": "mdx", "hash": False}, ["m1"]),
        ("stamp-hash-length-4", "stamp", "Body.", {"hashLength": 4}, ["h1"]),
        ("stamp-idempotent-already-marked", "stamp",
         f"Marked.\n<!-- stay:keep hash=sha256:{L.body_hash('Marked.', 12)} -->", {}, ["unused"]),
        ("stamp-marker-only-chunk-identifies-block", "stamp",
         "Para body.\n\n<!-- stay:keep hash=sha256:0000 -->\n\nOther.", {}, ["new0"]),
        ("stamp-minted-id-avoids-collision", "stamp",
         "A.\n<!-- stay:id00 -->\n\nB.", {}, ["id00", "id00", "id01"]),
        ("restamp-refreshes-drifted-hash", "restamp",
         f"Edited body now.\n<!-- stay:r1 hash=sha256:{L.body_hash('Original body.', 12)} -->", {}, None),
        ("restamp-no-op-when-undrifted", "restamp",
         f"Body.\n<!-- stay:r1 hash=sha256:{L.body_hash('Body.', 12)} -->", {}, None),
        ("restamp-preserves-stored-precision", "restamp",
         "New text here.\n<!-- stay:p1 hash=sha256:0000 -->", {}, None),
        ("restamp-add-missing", "restamp", "Body text.\n<!-- stay:n1 -->", {"addMissing": True}, None),
        ("repair-duplicate-first-kept-second-reminted", "repair",
         "Para one.\n<!-- stay:dup hash=sha256:0000 -->\n\nPara two.\n<!-- stay:dup hash=sha256:1111 -->",
         {}, ["fresh1"]),
        ("repair-same-block-duplicate-markers", "repair",
         "A.\n<!-- stay:dup -->\n<!-- stay:dup -->", {}, ["fresh1"]),
        ("repair-no-op-without-duplicates", "repair",
         "One.\n<!-- stay:a -->\n\nTwo.\n<!-- stay:b -->", {}, ["unused"]),
        ("repair-reminted-id-avoids-collision", "repair",
         "One.\n<!-- stay:dup -->\n\nTwo.\n<!-- stay:dup -->\n\nThree.\n<!-- stay:taken -->",
         {}, ["taken", "ok1"]),
        # §4 regression: the write-path hash scanner must honour a word boundary,
        # so an unknown key merely *ending* in `hash` is preserved verbatim and the
        # real `hash` attribute is the one refreshed. Kept last so the frozen file
        # order matches the order this vector was first landed in.
        ("restamp-preserves-unknown-key-ending-in-hash", "restamp",
         "Body.\n<!-- stay:x rehash=sha256:abc hash=sha256:beef -->", {}, None),
        # §16's write-path shim, the two rules that bind EVERY implementation whether
        # or not it segments child blocks (§5.5 resolution is optional; these are not).
        # Both run in the default profile, with no child support asked for, because
        # that is the tool the rules are aimed at. Until these landed the corpus had
        # no vector mentioning `subhash` at all, so the rules were pinned only by each
        # implementation's own unit tests and nothing checked that the four agree.
        ("stamp-subhash-marker-does-not-count-as-stamped", "stamp",
         "- Ship the linter <!-- stay:c1 subhash=sha256:9d2f -->\n"
         "- Ship the hook <!-- stay:c2 subhash=sha256:41ac -->\n", {}, ["cont1"]),
        ("restamp-add-missing-leaves-a-subhash-marker-alone", "restamp",
         "- Alpha <!-- stay:k1 subhash=sha256:8655 -->\n- Beta\n",
         {"addMissing": True}, None),
        # The boundary half of the same rule, mirroring
        # `restamp-preserves-unknown-key-ending-in-hash` above: a custom key merely
        # ENDING in `subhash` is not the reserved key (§4), so the marker still stamps
        # its block and nothing is minted. Both separators are in one vector because
        # they fail differently: `resubhash` is caught by any boundary at all, while
        # `x-subhash` is caught only by the whitespace boundary the attribute grammar
        # actually has. Under a word boundary the second block mints a spurious second
        # stay onto a block that already has one.
        # The same boundary on the `hash` key, and the case that showed why `\b` is the
        # wrong test: `x-hash` is a §4 custom key, so the scanner must skip it and
        # refresh the real `hash` beside it. Under a word boundary the write path
        # spliced over `x-hash`'s value instead, silently destroying a key §4 requires
        # to be preserved verbatim.
        ("restamp-preserves-custom-key-with-hyphen-ending-in-hash", "restamp",
         f"Edited body now.\n<!-- stay:x x-hash=sha256:abc hash=sha256:{L.body_hash('Original body.', 12)} -->",
         {}, None),
        ("stamp-custom-key-ending-in-subhash-still-stamps", "stamp",
         "A paragraph.\n<!-- stay:x1 resubhash=sha256:abcd -->\n\n"
         "Another paragraph.\n<!-- stay:x2 x-subhash=sha256:abcd -->\n",
         {}, ["unused"]),
    ]
    out = []
    for name, op, text, o, ids in cases:
        if op == "stamp":
            r = MW.stamp(text, syntax=o.get("syntax", "html"), hash=o.get("hash", True),
                         hash_length=o.get("hashLength", MW.DEFAULT_HASH_LENGTH),
                         new_id=_id_factory(ids))
            expected = {"text": r.text, "minted": r.minted}
        elif op == "restamp":
            r = MW.restamp(text, hash_length=o.get("hashLength"), add_missing=o.get("addMissing", False))
            expected = {"text": r.text, "refreshed": r.refreshed}
        else:  # repair
            r = MW.repair_duplicates(text, new_id=_id_factory(ids))
            expected = {"text": r.text, "renamed": r.renamed}
        v = {"name": name, "op": op, "input": text, "options": o}
        if ids is not None:
            v["ids"] = ids
        v["expected"] = expected
        out.append(v)
    return out


def resolve_pairs() -> list[dict]:
    """Resolve scenarios for the gen tier (SPEC.md §9's evidence ladder).

    Every scenario carries a descriptive `name` and an `expect` claim naming the
    tier each anchor id must actually resolve through. A detach is claimed as
    `detached:<reason>` (`threshold`, `margin` or `no-candidates`), because
    "detached" alone does not say which gate refused and the names here assert the
    gate. `resolve_vectors()` checks the claim against
    the freshly computed resolutions and strips it before writing, so a scenario
    that stops exercising the branch it is named for fails generation instead of
    shipping as decorative coverage. Two scenarios here used to do exactly that (a
    "block deleted -> detached" case that attached the deleted id by QUOTE, and a
    "margin guard" case that never got past the hash tier), which is why the claim
    is machine-checked rather than written in a comment.
    """
    marker_kept = ("First paragraph here.\n<!-- stay:p1 -->\n\n"
                   "Second paragraph here.\n<!-- stay:p2 -->\n")
    # Blocks for the two scenarios that pin behaviour §9's words do NOT settle,
    # which is why they live here and not in the hand-authored spec/ tier.
    prev_s = "Retry policy overview."
    next_s = "Escalation contacts are listed below."
    filler = "Unrelated appendix note about billing exports."
    target = "The ingest stage retries failed operations three times."
    twin = "The ingest stage retries failed operations four times."
    # ~185 chars each, well past §9's 48-char context window.
    prev_l = ("Operators can override these retry defaults on a per-partner basis, but "
              "every override expires automatically after thirty days so that stale "
              "tuning never silently persists in production.")
    next_l = ("Each completed run is recorded in the audit log together with the operator "
              "name, the affected partner, and the exact timestamp of the change, so the "
              "history is always reconstructable.")
    # Exact Ratcliff/Obershelp bodies for the binary64 margin pair. Both gaps are
    # 1/20 as rationals; only the floating-point representation separates them.
    q13 = "alpha bravo x"                    # 13 chars
    c070 = "alpha b"                         # 7  -> 14/20 = 7/10
    c065 = "alpha bravo x wmnqjkzgyfudp"     # 27 -> 26/40 = 13/20
    near_dups = _fixture("near_dups.md")
    # Same document with the ingest paragraph (and its trailing blank line) removed,
    # so the anchor on it misses the hash tier and has to compete against its two
    # surviving near-twins.
    ingest_para = next(p for p in near_dups.split("\n\n")
                       if p.startswith("The ingest stage retries"))
    near_dups_ingest_cut = near_dups.replace(ingest_para + "\n\n", "", 1)
    assert near_dups_ingest_cut != near_dups, "near_dups.md fixture shape changed"
    return [
        {"name": "marker-tier-survives-reorder",
         "before": marker_kept,
         "after": ("Second paragraph here.\n<!-- stay:p2 -->\n\n"
                   "First paragraph here.\n<!-- stay:p1 -->\n"),
         "threshold": 0.5, "margin": 0.05,
         "expect": {"p1": "marker", "p2": "marker"}},
        {"name": "hash-tier-recovers-stripped-verbatim",
         "before": marker_kept,
         "after": "Second paragraph here.\n\nFirst paragraph here.\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"p1": "hash", "p2": "hash"}},
        # Deleted block, bodies distinct enough that the survivor scores below
        # threshold: the detach is a real refusal, not an accident of the corpus.
        {"name": "deleted-block-detaches-below-threshold",
         "before": ("The order pipeline ingests partner messages.\n<!-- stay:keep -->\n\n"
                    "Invalid payloads route to a dead-letter queue.\n<!-- stay:gone -->\n"),
         "after": "The order pipeline ingests partner messages.\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"keep": "hash", "gone": "detached:threshold"}},
        # The same deletion where the survivor is a formulaic near-twin of the
        # deleted block: QUOTE commits the deleted id onto it. A false attachment,
        # frozen deliberately because it is what the model does and every
        # implementation must agree on it (SPEC.md §9's residual, not a bug).
        {"name": "deleted-block-quote-attaches-to-similar-survivor",
         "before": marker_kept,
         "after": "First paragraph here.\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"p1": "hash", "p2": "quote"}},
        {"name": "paraphrase-quote-recovers-one-detaches-other",
         "before": ("The order pipeline ingests and normalizes partner messages.\n"
                    "<!-- stay:ing -->\n\n"
                    "Invalid payloads route to a dead-letter queue for replay.\n"
                    "<!-- stay:dlq -->\n"),
         "after": ("Partner messages are ingested and normalized by the pipeline.\n\n"
                   "Bad payloads are sent to a dead-letter queue so they can be replayed.\n"),
         "threshold": 0.5, "margin": 0.05,
         "expect": {"ing": "detached:threshold", "dlq": "quote"}},
        # Reaches the QUOTE tier over two surviving near-duplicates and fails the
        # margin check, which is the branch the scenario is named for. The guard
        # sees `best_match`'s clamped pair (1.0 vs 0.975233, delta 0.024767); the
        # unclamped aggregate would be 1.025051 vs 0.975233, so the refusal does
        # not depend on the clamp either way.
        {"name": "near-dup-margin-guard-detaches",
         "before": near_dups.replace(
             "The ingest stage retries",
             "<!-- stay:pre -->\nThe ingest stage retries", 1),
         "after": near_dups_ingest_cut,
         "threshold": 0.5, "margin": 0.05,
         "expect": {"pre": "detached:margin"}},
        # SPEC.md §9 says the context bonus exists to "break near-ties between
        # structurally identical blocks". For exactly those blocks it cannot:
        # `best_match` clamps each score to 1.0 before returning, so a twin with
        # both neighbours matched (raw 1.1) and a twin with neither (raw 1.0118)
        # both arrive at the guard as 1.0 and the margin is 0. The words and the
        # code disagree here and §9 does not settle which is right, so the
        # behaviour is frozen in gen/ rather than asserted in spec/.
        {"name": "clamp-flattens-matched-context-on-identical-twins",
         "before": f"{prev_s}\n\n{target}\n<!-- stay:ing -->\n\n{next_s}\n",
         "after": f"{prev_s}\n\n{target}\n\n{next_s}\n\n{filler}\n\n{target}\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"ing": "detached:margin"}},
        # The regression sentinel for §9's stored-context window. Both neighbours
        # here are ~185 characters, far past the 48 §9 allows a selector to carry.
        # While the stored side was NOT windowed (every implementation through
        # v1.2) the ratio was capped near 2*48/(len+48), so a perfectly preserved
        # neighbour yielded 0.041 of its 0.05 and this document detached at margin
        # 0.0323 even though the edited original is sitting between its own two
        # untouched neighbours. With both sides windowed it commits at 0.0504,
        # recovering the edited block against a verbatim copy of itself further
        # down. Revert the stored-side window and this vector goes back to
        # detached, which is what makes it worth keeping.
        {"name": "long-neighbours-do-not-starve-the-context-bonus",
         "before": f"{prev_l}\n\n{target}\n<!-- stay:ing -->\n\n{next_l}\n",
         "after": f"{prev_l}\n\n{twin}\n\n{next_l}\n\n{filler}\n\n{twin}\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"ing": "quote"}},
        # §9 states a mathematical condition ("margin >= 0.05") and does not
        # mandate binary64, so an implementation comparing exact rationals would
        # see 7/10 - 13/20 = 1/20 and commit where this detaches. That makes the
        # outcome reference behaviour rather than a spec requirement, so it is
        # frozen here instead of asserted in spec/. It is worth freezing: all
        # three implementations do use binary64, where the subtraction yields
        # 0.04999999999999993, and an implementation that started rounding or
        # comparing with an epsilon would diverge silently. spec/ brackets the
        # margin with rationals (24/30 - 24/32 commits, 23/28 - 44/57 detaches);
        # this is the representation-sensitive step between them.
        {"name": "margin-binary64-one-step-under-detaches",
         "before": f"{q13}\n<!-- stay:q1 -->\n",
         "after": f"{c070}\n\n{c065}\n",
         "threshold": 0.5, "margin": 0.05,
         "expect": {"q1": "detached:margin"}},
    ]


def _detach_reasons(before: str, after: str, threshold: float, margin: float) -> dict:
    """Which §9 gate refused, per detached id. `detached` on its own is not a
    branch: the threshold and the margin are separate refusals and a scenario
    named for one of them can silently start exercising the other."""
    anchors = R.build_anchors(before)
    bodies = [b.content for b in L.parse_document(after) if b.index >= 0]
    out = {}
    for a in anchors:
        idx, score, runner = Q.best_match(a.selector, bodies)
        if idx < 0:
            out[a.id] = "no-candidates"
            continue
        # Report the gate that actually refused, in the order the resolver checks
        # them. Once the threshold has failed the margin is moot, so naming both
        # would credit a co-cause that decided nothing.
        out[a.id] = "threshold" if score < threshold else "margin"
    return out


def resolve_vectors() -> list[dict]:
    """Freeze the resolve scenarios, enforcing each one's `expect` claim."""
    out = []
    for p in resolve_pairs():
        claim = p.pop("expect")
        res = expect_resolve(p["before"], p["after"], p["threshold"], p["margin"])
        reasons = _detach_reasons(p["before"], p["after"], p["threshold"], p["margin"])
        got = {
            k: (f"detached:{reasons.get(k, '?')}" if v["method"] == "detached"
                else v["method"])
            for k, v in res.items()
        }
        if got != claim:
            raise SystemExit(
                f"resolve scenario {p['name']!r} does not exercise what it claims:\n"
                f"  claimed: {claim}\n  actual:  {got}\n"
                "Fix the scenario or correct the claim; do not ship a vector whose "
                "name asserts a branch it never reaches."
            )
        out.append({**p, "resolutions": res})
    return out


# --- emit ------------------------------------------------------------------

def write(category: str, vectors: list, named: bool = True) -> None:
    if named:
        for i, v in enumerate(vectors):
            v.setdefault("name", f"{category}-{i:03d}")
    payload = {"category": category, "tier": "gen", "vectors": vectors}
    (GEN / f"{category}.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n")
    print(f"  gen/{category}.json: {len(vectors)} vectors")


def main() -> int:
    GEN.mkdir(exist_ok=True)
    print("Generating gen/ tier from the Python reference:")

    write("hash", [{"body": b, **expect_hash(b)} for b in hash_bodies()])
    write("markers", [{"text": t, "markers": expect_markers(t)} for t in marker_texts()])
    write("parse", [{"doc": d, "blocks": expect_parse(d)} for d in parse_docs()])
    write("lint", [{"doc": d, "findings": expect_lint(d)} for d in lint_docs()])
    write("diff", [{"before": a, "after": b, "findings": expect_diff(a, b)}
                   for a, b in diff_pairs()])
    write("seqmatch", [{"a": a, "b": b, **expect_seqmatch(a, b)}
                       for a, b in seqmatch_pairs()])
    write("score", score_vectors())
    write("resolve", resolve_vectors())
    write("stamp", stamp_vectors(), named=False)  # names are authored in stamp_vectors()

    print("Done.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
