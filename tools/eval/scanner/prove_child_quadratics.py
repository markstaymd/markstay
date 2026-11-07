#!/usr/bin/env python3
"""Prove Python child parsing and row refusals unchanged, then measure scaling.

Requires markdown-it-py for the CommonMark profile. Baseline and committed HEAD source
snapshots, generated documents, and JSON results remain in --work-dir. No tracked
source is changed. Run after committing the candidate before a long proof.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import importlib.metadata
import platform
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import time
import types
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
PYTHON_COPIES = ("linter/markstay_lint.py", "impl/py/src/markstay/lint.py")

# Siblings a copy imports relatively; snapshotted beside it, never compared.
PYTHON_SUPPORT = ("impl/py/src/markstay/quote.py",)
BASE = "bbad37485b5f5d0ba9a2d9a0cfa7416999d6087c"
FIXED_CASE_COUNT = 18


def serialize(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def documents(count, seed):
    rng = random.Random(seed)
    fixed = [
        "- one <!--stay:a subhash=sha256:aa -->\n- two <!--stay:b subhash=sha256:bb -->\n",
        "- one <!--stay:a subhash=sha256:aa\n- two -->\n- three\n",
        "- one <!--stay:a a=<!--stay:b subhash=sha256:bb -->\n- two\n",
        "- one <!--stay:a a='<!--stay:b subhash=sha256:bb -->' -->\n- two\n",
        "- one {/*stay:a subhash=sha256:aa\n- two */}\n- three\n",
        "- one <!--stay:a subhash=sha256:aa -->\n\n- two <!--stay:b subhash=sha256:bb -->\n",
        "- parent <!--stay:p subhash=sha256:aa -->\n  - nested <!--stay:n subhash=sha256:bb -->\n- sibling\n",
        "- parent <!--stay:p subhash=sha256:aa -->\n  | h | k |\n  | - | - |\n  | a | b<!--stay:r subhash=sha256:aa --> |\n  <!--stay:l subhash=sha256:bb -->\n",
        "| h | k |\n| - | - |\n| a | b<!--stay:r subhash=sha256:aa --> |\n| c | d{/*stay:s subhash=sha256:bb */} |\n",
        "| h | k |\n| - | - |\n| a | <!--stay:x a=<!--stay:y a=tail --> |\n",
        "| h | k |\n| - | - |\n| a | <!--stay:x a='line\nline' --> |\n",
        "```\n- fenced <!--stay:f subhash=sha256:aa -->\n```\n\n- live <!--stay:l subhash=sha256:aa -->\n",
        "---\ntitle: <!--stay:front subhash=sha256:aa -->\n---\n\n- live <!--stay:l subhash=sha256:aa -->\n",
        "- one <!--stay:a subhash=bogus -->\n- two <!--stay:b x-subhash=sha256:aa -->\n",
        "<!--stay:a a='\n\n- crossing <!--stay:b subhash=sha256:aa -->' -->\n- next\n",
        "| <!--stay:a a=<!--stay:b a=tail --> |\n| <!--stay:c a=<!--stay:d a=tail --> |\n",
        "- one <!--stay:a a='\n- two' subhash=sha256:aa -->\n- three\n",
        "- one <!--stay:a subhash=sha256:aa -->{/*stay:b subhash=sha256:bb */}\n- two\n",
    ]
    assert len(fixed) == FIXED_CASE_COUNT
    markers = [
        "<!--stay:a subhash=sha256:aa -->", "{/*stay:b subhash=sha256:bb */}",
        "<!--stay:c hash=sha256:cc -->", "<!--stay:d subhash=bogus -->",
        "<!--stay:e x-subhash=sha256:ee -->", "<!--stay: -->", "{/*stay: */}",
        "<!--stay:x a=<!--stay:y subhash=sha256:aa -->",
        "{/*stay:x a={/*stay:y subhash=sha256:bb */}",
        "<!--stay:x a='one\ntwo' subhash=sha256:aa -->",
        "{/*stay:x a='one\ntwo' subhash=sha256:bb */}",
        "<!--stay:x a=", "{/*stay:x a='", "<!-- ordinary -->", "",
    ]
    atoms = markers + ["\n", "\n\n", "\t", "é🦀", "-->", "*/}", "--!>", "`code`", "\\|"]
    for index in range(count):
        if index < len(fixed):
            text = fixed[index]
        else:
            shape = rng.randrange(7)
            size = rng.randrange(1, 10)
            if shape in (0, 1):
                text = "".join(
                    f"{rng.choice(('- ', '* ', '1. '))}item {i} {rng.choice(markers)}\n"
                    + (f"  - nested {rng.choice(markers)}\n" if shape == 1 else "")
                    + ("\n" if rng.randrange(5) == 0 else "")
                    for i in range(size)
                )
            elif shape in (2, 3):
                prefix = "  " if shape == 3 else ""
                text = f"- parent {rng.choice(markers)}\n" if prefix else ""
                text += prefix + "| h | k |\n" + prefix + "| --- | :---: |\n"
                text += "".join(prefix + f"| a{i} | b{i}{rng.choice(markers)} |\n" for i in range(size))
                if prefix and rng.randrange(2):
                    text += prefix + rng.choice(markers) + "\n"
                if prefix and rng.randrange(2):
                    text += f"- sibling {rng.choice(markers)}\n"
            elif shape == 4:
                text = "".join(rng.choice(atoms) for _ in range(size * 3))
            elif shape == 5:
                opener, closer = rng.choice((("<!--stay:x a=", " -->"), ("{/*stay:x a=", " */}")))
                text = f"- one {opener * size}tail{closer}\n- two {rng.choice(markers)}\n"
            else:
                text = f"# Heading\n{rng.choice(markers)}\n\n" + "".join(
                    f"- item {i} {rng.choice(markers)}\n" for i in range(size)
                )
            if rng.randrange(7) == 0:
                text = "---\ntitle: sample\n---\n\n" + text
            if rng.randrange(7) == 0:
                text = "```md\n" + text + "```\n\n- live <!--stay:live subhash=sha256:aa -->\n"
        # Preserve mixed newlines on every fourth case; all three normalized
        # forms are exercised on the others, including the fixed regressions.
        newline = ("\n", "\r\n", "\r", None)[index % 4]
        if newline is not None:
            text = text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", newline)
        elif index >= len(fixed) and "\n" in text:
            text = text.replace("\n", "\r\n", 1)
        lines = text.replace("\r\n", "\n").replace("\r", "\n").count("\n") + 1
        excluded = sorted(rng.sample(range(1, lines + 1), rng.randrange(min(lines, 4) + 1)))
        yield {"text": text, "excluded_lines": excluded}


def snapshot(destination, base):
    for path in (*PYTHON_COPIES, *PYTHON_SUPPORT):
        target = destination / path
        target.parent.mkdir(parents=True, exist_ok=True)
        source = subprocess.run(
            ["git", "show", f"{base}:{path}"], cwd=ROOT, check=True, capture_output=True
        ).stdout
        target.write_bytes(source)


def load_python(path, name):
    # impl/py's lint.py imports its siblings relatively (`from .quote import ...`), so
    # every copy loads as a submodule of a package rooted at its own directory. The
    # package's __init__ never runs: it would import the whole library.
    package = types.ModuleType(name)
    package.__path__ = [str(path.parent)]
    sys.modules[name] = package
    spec = importlib.util.spec_from_file_location(f'{name}.{path.stem}', path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def projection(module, case):
    text = case["text"]
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    # Full dataclass projection retains child contents, marker private spans,
    # ownership, order, indices, line numbers, ordinals, and all lint findings.
    return {
        "parse": {
            mode: [dataclasses.asdict(block) for block in module.parse_document(text, mode=mode, child_blocks=True)]
            for mode in ("blank-line", "commonmark")
        },
        "parse_without_children": {
            mode: [dataclasses.asdict(block) for block in module.parse_document(text, mode=mode, child_blocks=False)]
            for mode in ("blank-line", "commonmark")
        },
        "lint": {
            mode: [[dataclasses.asdict(value) for value in part] for part in module.lint_document(text, mode=mode, child_blocks=True)]
            for mode in ("blank-line", "commonmark")
        },
        "refused": [
            sorted(module._row_refused_marker_lines(source, code))
            for source in (text, normalized)
            for code in (set(), module.code_lines(source), set(case["excluded_lines"]))
        ],
    }


def compare_projection(modules, case, path, index):
    projections = [projection(module, case) for module in modules]
    values = [serialize(value) for value in projections]
    if values[0] != values[1]:
        raise AssertionError(f"{path} case {index}: {serialize(case)}\nold={values[0]}\nnew={values[1]}")
    return projections, values


def equivalence(modules, cases, path):
    started = time.perf_counter()
    digests = [hashlib.sha256(), hashlib.sha256()]
    coverage = {"child_blocks": 0, "owned_child_markers": 0, "refused_documents": 0, "row_and_list_chunks": 0, "list_owned_in_mixed": 0, "list_owned_after_rows": 0}
    random_coverage = dict.fromkeys(coverage, 0)
    for index, case in enumerate(cases):
        projections, values = compare_projection(modules, case, path, index)
        case_coverage = dict.fromkeys(coverage, 0)
        for blocks in projections[0]["parse"].values():
            for block in blocks:
                case_coverage["child_blocks"] += len(block["children"])
                mixed = len({child["kind"] for child in block["children"]}) == 2
                case_coverage["row_and_list_chunks"] += mixed
                if mixed:
                    last_row = max(child["line"] for child in block["children"] if child["kind"] == "row")
                    list_markers = [marker for child in block["children"] if child["kind"] == "list" for marker in child["markers"]]
                    case_coverage["list_owned_in_mixed"] += len(list_markers)
                    case_coverage["list_owned_after_rows"] += sum(marker["line"] > last_row for marker in list_markers)
                case_coverage["owned_child_markers"] += sum(len(child["markers"]) for child in block["children"])
        case_coverage["refused_documents"] += any(projections[0]["refused"])
        for key, value in case_coverage.items():
            coverage[key] += value
            if index >= FIXED_CASE_COUNT:
                random_coverage[key] += value
        for digest, value in zip(digests, values):
            digest.update(value.encode() + b"\n")
    assert digests[0].digest() == digests[1].digest()
    assert all(coverage.values()), f"vacuous proof coverage: {coverage}"
    assert all(random_coverage.values()), (
        f"vacuous random-tail coverage: {random_coverage}; increase --count or change --seed"
    )
    return {"documents": len(cases), "sha256": digests[0].hexdigest(),
            "seconds": time.perf_counter() - started, "coverage": coverage,
            "random_coverage": random_coverage}


def negative_controls(modules, path):
    """Check that the full-output comparison detects all five target changes."""
    old, new = modules
    child_case = {"text": "- one <!--stay:a subhash=sha256:aa -->\n- two\n", "excluded_lines": []}
    row_case = {"text": "| " + "<!--stay:x a=" * 3 + "tail --> |", "excluded_lines": []}
    passed = []

    def rejects(label, case):
        try:
            compare_projection(modules, case, path, 0)
        except AssertionError as error:
            if not str(error).startswith(f"{path} case 0:"):
                raise
            passed.append(label)
        else:
            raise AssertionError(f"{path}: {label} negative control was not rejected")

    original_parse = new.parse_document
    for label in ("child_content", "child_marker_ownership"):
        def mutate_parse(*args, **kwargs):
            blocks = original_parse(*args, **kwargs)
            if kwargs.get("child_blocks"):
                child = next(child for block in blocks for child in block.children)
                if label == "child_content":
                    child.content += " changed by negative control"
                else:
                    assert child.markers
                    child.markers = []
            return blocks

        with patch.object(new, "parse_document", side_effect=mutate_parse):
            rejects(label, child_case)
    assert old._row_refused_marker_lines(row_case["text"], set()) == {1}
    with patch.object(new, "_row_refused_marker_lines", return_value=set()):
        rejects("row_refusal", row_case)
    # Replace the actual ownership algorithm with list-first ownership; the
    # accepted table at EOF must make the generated comparison reject it.
    priority_case = {"text": "- parent\n  | h | k |\n  | - | - |\n  | a | b<!--stay:r subhash=sha256:aa --> |\n", "excluded_lines": []}

    def list_first(line_starts, records, spans):
        owners = [[] for _ in spans]
        for record in records:
            if record.marker.has_subhash:
                for kind in ("list", "row"):
                    match = next((i for i, span in enumerate(spans)
                                  if span.kind == kind and new._record_belongs_to_child(line_starts, record, span)), None)
                    if match is not None:
                        owners[match].append(record.marker)
                        break
        return owners

    with patch.object(new, "_child_marker_owners", side_effect=list_first):
        rejects("row_priority", priority_case)
    original_owners = new._child_marker_owners
    fallback_case = {"text": "- parent\n  | h | k |\n  | - | - |\n  | a | b<!--stay:r subhash=sha256:bb --> |\n  <!--stay:l subhash=sha256:aa -->\n", "excluded_lines": []}

    def stop_after_row_miss(line_starts, records, spans):
        owners = original_owners(line_starts, records, spans)
        rows = [span for span in spans if span.kind == "row"]
        if rows:
            for span, markers in zip(spans, owners):
                if span.kind == "list":
                    markers[:] = [marker for marker in markers if marker.line < rows[0].start_line]
        return owners

    with patch.object(new, "_child_marker_owners", side_effect=stop_after_row_miss):
        rejects("row_to_list_fallthrough", fallback_case)
    return passed


def timed(function):
    start = time.perf_counter()
    result = function()
    return time.perf_counter() - start, result


def scaling(modules, sizes, repeats):
    rows = []
    for n in sizes:
        child_text = "".join(f"- item {i} <!--stay:c{i} subhash=sha256:aa -->\n" for i in range(n))
        overlap_text = "| " + "<!--stay:x a=" * n + "tail --> |"
        expected_children = None
        for side, module in zip(("old", "new"), modules):
            for repeat in range(repeats):
                no_children_time, _ = timed(lambda: module.parse_document(child_text, child_blocks=False))
                child_time, blocks = timed(lambda: module.parse_document(child_text, child_blocks=True))
                assert len(blocks) == 1 and len(blocks[0].children) == n
                assert [child.markers[0].id for child in blocks[0].children] == [f"c{i}" for i in range(n)]
                child_output = serialize([dataclasses.asdict(block) for block in blocks])
                if expected_children is None:
                    expected_children = child_output
                assert child_output == expected_children, f"{side} child scaling output differs at N={n}"
                rows.append({"case": "child_ownership", "n": n, "side": side, "repeat": repeat,
                             "input_chars": len(child_text), "seconds_without_children": no_children_time,
                             "seconds_with_children": child_time,
                             "output_sha256": hashlib.sha256(child_output.encode()).hexdigest()})
                scan_time, records = timed(lambda: module._scan_marker_records(overlap_text))
                assert len(records) == n
                with patch.object(module, "_scan_marker_records", return_value=records):
                    refusal_time, refused = timed(lambda: module._row_refused_marker_lines(overlap_text, set()))
                assert refused == {1}
                rows.append({"case": "row_overlap", "n": n, "side": side, "repeat": repeat,
                             "input_chars": len(overlap_text), "raw_output_chars": sum(len(r.marker.raw) for r in records),
                             "seconds_scanner": scan_time, "seconds_refused_lines_cached_records": refusal_time})
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=30000)
    parser.add_argument("--seed", type=int, default=201102)
    parser.add_argument("--base", default=BASE)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--work-dir", type=Path)
    parser.add_argument("--sizes", type=int, nargs="+", default=[500, 1000, 2000])
    parser.add_argument("--repeats", type=int, default=1)
    args = parser.parse_args()
    if args.count <= FIXED_CASE_COUNT or args.repeats < 1 or any(n < 2 for n in args.sizes):
        parser.error(f"--count must be at least {FIXED_CASE_COUNT + 1}; --repeats must be positive; --sizes requires N >= 2")
    candidate = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True,
                               capture_output=True, text=True).stdout.strip()
    # Refuse dirty sources before creating a persistent work directory.
    for path in (*PYTHON_COPIES, *PYTHON_SUPPORT):
        committed = subprocess.run(["git", "show", f"{candidate}:{path}"], cwd=ROOT,
                                   check=True, capture_output=True).stdout
        if (ROOT / path).read_bytes() != committed:
            raise SystemExit(f"Uncommitted candidate source: {path}; commit it before running the proof")
    if args.work_dir:
        directory = args.work_dir.resolve()
        directory.mkdir(parents=True, exist_ok=False)
    else:
        parent = ROOT / "eval/scanner/proof-runs"
        parent.mkdir(parents=True, exist_ok=True)
        directory = Path(tempfile.mkdtemp(prefix="child-quadratics-", dir=parent))
    old, new = directory / "old", directory / "new"
    snapshot(old, args.base)
    snapshot(new, candidate)
    cases = list(documents(args.count, args.seed))
    fixture_path = directory / "documents.jsonl"
    fixture_path.write_text("".join(serialize(case) + "\n" for case in cases))
    report = {
        "environment": {"python": platform.python_version(), "markdown_it_py": importlib.metadata.version("markdown-it-py")},
        "base": args.base, "candidate": candidate, "seed": args.seed, "documents": args.count,
        "work_dir": str(directory), "fixture_sha256": hashlib.sha256(fixture_path.read_bytes()).hexdigest(),
        "source_sha256": {side: {path: hashlib.sha256((root / path).read_bytes()).hexdigest() for path in PYTHON_COPIES}
                          for side, root in (("old", old), ("new", new))},
        "python": {},
    }
    for index, path in enumerate(PYTHON_COPIES):
        modules = [load_python(root / path, f"child_proof_{side}_{index}") for side, root in (("old", old), ("new", new))]
        report["python"][path] = equivalence(modules, cases, path)
        report["python"][path]["negative_controls"] = negative_controls(modules, path)
        print(f"Python equivalence passed: {path} ({len(cases)} documents)", flush=True)
        report["python"][path]["timings"] = scaling(modules, args.sizes, args.repeats)
        # A partial report survives an interruption after the first copy.
        (directory / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    result = json.dumps(report, indent=2) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(result)
    print(result)


if __name__ == "__main__":
    main()
