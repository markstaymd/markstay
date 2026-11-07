#!/usr/bin/env python3
"""Deterministic old/new scanner proof, with snapshots and Rust probes in /tmp.

Run from any directory: python3 eval/scanner/prove_unterminated.py --count 30000.
The JSON report includes fixture/output digests and old/new timings. No tracked
source is changed. Rust's private scanner is exposed only in temporary copies.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import shutil
import subprocess
import sys
import tempfile
import time
import types

ROOT = Path(__file__).resolve().parents[2]
PYTHON_COPIES = ("linter/markstay_lint.py", "impl/py/src/markstay/lint.py")

# Siblings a copy imports relatively; snapshotted beside it, never compared.
PYTHON_SUPPORT = ("impl/py/src/markstay/quote.py",)


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def serialize(value):
    return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))


def documents(count, seed):
    rng = random.Random(seed)
    atoms = [
        '<!--stay:x a=', '{/*stay:x a=', '<!--stay:x a="', "{/*stay:x a='",
        '<!-- stay:Alpha hash=sha256:ABCD -->', '{/* stay:Beta subhash=bogus */}',
        '<!--stay: -->', '{/*stay: */}', '<!-- ordinary -->', '{/* ordinary */}',
        '<!--stay:x a="one\ntwo" -->', "{/*stay:y a='one\ntwo' */}",
        '<!--stay:x a="<!--stay:inner -->" -->', '{/*stay:x a="{/*stay:inner */}" */}',
        '<!--stay:x a=one b=two\n-->', '{/*stay:x a=one b=two\n*/}',
        '<!--stay:x a=<!--stay:y b=tail\n-->', '{/*stay:x a={/*stay:y b=tail\n*/}',
        '<!--stay:x a="--!>" -->', '<!--stay:x a=--!> tail -->',
        '<!--stay:x hash=sha256:AB a="line\r\nline" -->',
        '<!--stay:x subhash=sha256:AB -->', '<!--stay:x x-subhash=bogus -->',
        '<!--stay:x a="unterminated', "{/*stay:y a='unterminated", '-->', '--!>', '*/}',
        '\n', '\r', '\r\n', ' ', '\t', '\n\n', 'alpha', 'é🦀',
        '```\n<!--stay:fenced -->\n```\n', '- child <!--stay:k subhash=bogus -->\n',
        '|a|b|\n|-|-|\n|c|d <!--stay:r subhash=sha256:ab -->|\n',
    ]
    # Fixed cases guarantee every advertised grammar feature even at low --count.
    fixed = [
        '<!--stay:x a=' * 12 + '\n-->', '{/*stay:x a=' * 12 + '\n*/}',
        '<!--stay:x a="one\r\ntwo\rthree" -->',
        '<!--stay:x a="--!>" -->\r{/*stay:y */}',
        '<!--stay:outer a=<!--stay:inner -->',
        '---\na: <!--stay:front -->\n---\n\nbody <!--stay:body -->',
    ]
    for i in range(count):
        text = fixed[i] if i < len(fixed) else ''.join(rng.choice(atoms) for _ in range(rng.randrange(5, 36)))
        # Normalize random documents into all three newline forms, but also retain
        # mixed original forms on one quarter of cases.
        if i % 4 != 3:
            text = text.replace('\r\n', '\n').replace('\r', '\n').replace('\n', ('\n', '\r\n', '\r')[i % 4])
        yield {"text": text, "offset": rng.randrange(0, 24), "children": i % 2 == 1}


def snapshot(dest, base=None):
    paths = [*PYTHON_COPIES, *PYTHON_SUPPORT]
    if base:
        tracked = run('git', 'ls-tree', '-r', '--name-only', base, 'impl/js', 'impl/rs', cwd=ROOT, capture_output=True, text=True).stdout.splitlines()
        paths += [p for p in tracked if '/src/' in p or p.endswith(('package.json', 'Cargo.toml', 'Cargo.lock'))]
    else:
        paths += [str(p.relative_to(ROOT)) for folder in ('impl/js/src', 'impl/rs/src') for p in (ROOT / folder).rglob('*') if p.is_file()]
        paths += ['impl/js/package.json', 'impl/rs/Cargo.toml', 'impl/rs/Cargo.lock']
    for path in paths:
        target = dest / path
        target.parent.mkdir(parents=True, exist_ok=True)
        if base:
            target.write_bytes(run('git', 'show', f'{base}:{path}', cwd=ROOT, capture_output=True).stdout)
        else:
            shutil.copyfile(ROOT / path, target)


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


def digest_lines(lines):
    h = hashlib.sha256()
    for line in lines:
        h.update(line.encode())
        h.update(b'\n')
    return h.hexdigest()


def python_proof(old, new, cases):
    result = {}
    for i, path in enumerate(PYTHON_COPIES):
        modules = [load_python(root / path, f'proof_{side}_{i}') for root, side in ((old, 'old'), (new, 'new'))]
        digests = [hashlib.sha256(), hashlib.sha256()]
        started = time.perf_counter()
        for index, case in enumerate(cases):
            values = []
            for side, module in enumerate(modules):
                value = serialize({
                    'find_markers': [dataclasses.asdict(m) for m in module.find_markers(case['text'], case['offset'])],
                    'lint_document': [[dataclasses.asdict(v) for v in part] for part in module.lint_document(case['text'], child_blocks=case['children'])],
                })
                digests[side].update(value.encode() + b'\n')
                values.append(value)
            if values[0] != values[1]:
                raise AssertionError(f'{path} case {index}: {serialize(case)}\nold={values[0]}\nnew={values[1]}')
        result[path] = {'documents': len(cases), 'sha256': digests[0].hexdigest(), 'seconds': time.perf_counter() - started}
        assert digests[0].digest() == digests[1].digest()
        result[path]['timings'] = []
        for n in (1000, 2000, 4000):
            text = '<!--stay:x a=' * n + '\n-->'
            row = {'n': n}
            for side, module in zip(('old', 'new'), modules):
                started = time.perf_counter()
                assert module.find_markers(text) == []
                row[side] = time.perf_counter() - started
            result[path]['timings'].append(row)
        print(f'Python proof passed: {path}', flush=True)
    return result


JS_PROBE = r'''
import fs from 'node:fs';
import { performance } from 'node:perf_hooks';
import { pathToFileURL } from 'node:url';
const [root, input, mode] = process.argv.slice(2);
const {scanMarkerRecords, findMarkers} = await import(pathToFileURL(root + '/impl/js/src/markers.js'));
const {lintDocument} = await import(pathToFileURL(root + '/impl/js/src/lint.js'));
if (mode === 'timing') {
  for (const n of [1000, 2000, 4000]) {
    const text = '<!--stay:x a='.repeat(n) + '\n-->';
    const start = performance.now();
    if (findMarkers(text).length) throw Error('unexpected marker');
    console.log(JSON.stringify({n, seconds:(performance.now()-start)/1000}));
  }
} else {
  for (const line of fs.readFileSync(input, 'utf8').trimEnd().split('\n')) {
    const c = JSON.parse(line);
    console.log(JSON.stringify({scanMarkerRecords:scanMarkerRecords(c.text,c.offset), findMarkers:findMarkers(c.text,c.offset), lintDocument:lintDocument(c.text)}));
  }
}
'''

RUST_WRAPPER = r'''
#[doc(hidden)]
pub fn scanner_proof(text: &str, offset: usize) -> alloc::string::String {
    let records: alloc::vec::Vec<_> = markers::scan_marker_records(text, offset)
        .into_iter().map(|r| (r.start, r.end, r.marker)).collect();
    alloc::format!("{:?}", (records, find_markers(text, offset), lint_document(text)))
}
'''
RUST_PROBE = r'''
use std::io::{self, BufRead};
use std::time::Instant;
fn main() {
    if std::env::args().any(|a| a == "timing") {
        for n in [1000, 2000, 4000] {
            let text = "<!--stay:x a=".repeat(n) + "\n-->";
            let start = Instant::now();
            assert!(markstay::find_markers(&text, 0).is_empty());
            println!("{}", serde_json::json!({"n":n,"seconds":start.elapsed().as_secs_f64()}));
        }
    } else {
        for line in io::stdin().lock().lines() {
            let value: serde_json::Value = serde_json::from_str(&line.unwrap()).unwrap();
            let output = markstay::scanner_proof(value["text"].as_str().unwrap(), value["offset"].as_u64().unwrap() as usize);
            println!("{}", serde_json::to_string(&output).unwrap());
        }
    }
}
'''


def rust_probe(root):
    crate = root / 'impl/rs'
    lib = crate / 'src/lib.rs'
    lib.write_text(lib.read_text() + RUST_WRAPPER)
    cargo = crate / 'Cargo.toml'
    cargo.write_text(cargo.read_text().replace('[dependencies]', '[dependencies]\nserde_json = "1"', 1))
    (crate / 'src/bin/scanner-proof.rs').write_text(RUST_PROBE)
    run('cargo', 'build', '--offline', '--release', '--bin', 'scanner-proof', cwd=crate)
    return crate / 'target/release/scanner-proof'


def process_proof(label, commands, input_path, temp):
    paths = []
    timings = []
    started = time.perf_counter()
    for side, command in zip(('old', 'new'), commands):
        path = temp / f'{label}-{side}.jsonl'
        with input_path.open('rb') as source, path.open('wb') as output:
            run(*command, stdin=source, stdout=output)
        paths.append(path)
        timing_cmd = command[:-1] + ['timing'] if label == 'javascript' else command + ['timing']
        timings.append([json.loads(line) for line in run(*timing_cmd, capture_output=True, text=True).stdout.splitlines()])
    # Compare bytes first, retain the first failing line as a useful fixture.
    old_bytes, new_bytes = (p.read_bytes() for p in paths)
    if old_bytes != new_bytes:
        for index, (left, right) in enumerate(zip(old_bytes.splitlines(), new_bytes.splitlines())):
            if left != right:
                case = input_path.read_text().splitlines()[index]
                raise AssertionError(f'{label} case {index}: {case}\nold={left!r}\nnew={right!r}')
        raise AssertionError(f'{label}: different output lengths')
    print(f'{label} proof passed', flush=True)
    return {'documents': len(old_bytes.splitlines()), 'sha256': hashlib.sha256(old_bytes).hexdigest(), 'seconds': time.perf_counter()-started, 'timings': [{'n': a['n'], 'old': a['seconds'], 'new': b['seconds']} for a,b in zip(*timings)]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=30000)
    parser.add_argument('--seed', type=int, default=181023)
    parser.add_argument('--base', default='9a2fc93')
    parser.add_argument('--report', type=Path)
    args = parser.parse_args()
    cases = list(documents(args.count, args.seed))
    with tempfile.TemporaryDirectory(prefix='markstay-scanner-') as directory:
        temp = Path(directory)
        old, new = temp / 'old', temp / 'new'
        snapshot(old, args.base)
        snapshot(new)
        input_path = temp / 'documents.jsonl'
        input_path.write_text(''.join(serialize(c) + '\n' for c in cases))
        report = {'base': args.base, 'seed': args.seed, 'documents': args.count, 'fixture_sha256': hashlib.sha256(input_path.read_bytes()).hexdigest(), 'source_sha256': {path: hashlib.sha256((new / path).read_bytes()).hexdigest() for path in (*PYTHON_COPIES, 'impl/js/src/markers.js', 'impl/rs/src/markers.rs')}}
        report['python'] = python_proof(old, new, cases)
        js = temp / 'probe.mjs'
        js.write_text(JS_PROBE)
        report['javascript'] = process_proof('javascript', [['node', str(js), str(root), str(input_path), 'proof'] for root in (old,new)], input_path, temp)
        binaries = [rust_probe(root) for root in (old,new)]
        report['rust'] = process_proof('rust', [[str(binary)] for binary in binaries], input_path, temp)
        result = json.dumps(report, indent=2) + '\n'
        if args.report:
            args.report.write_text(result)
        print(result)


if __name__ == '__main__':
    main()
