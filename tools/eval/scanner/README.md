# Overlapping unterminated candidate proof

Run from the checkout root with Python 3.10+, Node, Cargo, and the cached
`impl/rs` test dependencies:

```sh
python3 eval/scanner/prove_unterminated.py --count 30000 --report scanner-proof.json
```

`--base` defaults to `9a2fc93`, the commit before the overlapping-candidate fix. `--seed` defaults to `181023`.
The baseline sources come from Git and the candidate sources from the current
checkout. Snapshots and probe executables live in a temporary directory, removed
when the command finishes. Rust builds in release mode with `--offline`.

The generated documents combine HTML and MDX hosts, LF, CRLF, lone CR, `--!>`,
unclosed and nested openers, multiline quoted values, Unicode, fences, lists,
rows, and frontmatter. Discovery receives offsets from 0 through 23. Python
linting alternates child processing on and off. The first six documents are fixed
regressions; the remainder use the seeded generator.

Each implementation compares its baseline output against its candidate output:

- Both Python copies serialize every returned marker, block, child, and finding
  from `find_markers` and `lint_document`, using sorted compact JSON.
- JavaScript serializes `scanMarkerRecords`, `findMarkers`, and `lintDocument`
  with `JSON.stringify`, preserving every returned property and its order.
- Rust serializes scanner record offsets and full markers, `find_markers`, and
  `lint_document` with its existing `Debug` implementations, then JSON-escapes
  the result. The probe includes private marker surgery spans. A temporary crate
  wrapper exposes `scan_marker_records` only in the snapshots; tracked Rust
  sources and package dependencies are unchanged.

Every document must match byte for byte. This tests old versus new within each
implementation, not equality between implementations. On a mismatch, the command
fails with the document index, source fixture, and both serialized outputs.

The JSON report records the seed, fixture digest, candidate source digests,
output digests, document counts, and elapsed times. It also measures discovery
once at N = 1000, 2000, and 4000 on `'<!--stay:x a=' * N + '\n-->'`, verifying
that each call returns no markers. These wall-clock measurements show the
pathological scaling; the unit tests separately bound visited parser states.

## Python child ownership and row refusal proof

```sh
python3 eval/scanner/prove_child_quadratics.py --count 30000 --repeats 3
python3 eval/scanner/followup_measure.py
```

The child proof requires `markdown-it-py`. It compares both Python copies against
`bbad37485b5f5d0ba9a2d9a0cfa7416999d6087c`, before the ownership and row refusal
optimizations. `--base`, `--seed`, `--count`, `--sizes`, and `--repeats` customize
the run. Sizes require N >= 2 for the overlap case; `--count` requires at least 19
documents (18 fixed regressions plus a random tail). Candidate sources are pinned
to committed `HEAD`, recorded in the report. Dirty candidate sources are refused
before creating a work directory.
Snapshots, generated fixtures, and the JSON report persist under the
ignored `eval/scanner/proof-runs/`; `--work-dir` selects a fresh directory and
`--report` writes another report copy.

Every generated document must preserve the full parse (children on and off) and lint results in both
blank-line and CommonMark modes, including child bodies, ownership, marker bytes,
source lines, and ordinals. Row refusal sets are compared on raw and normalized
text with empty, fenced-code, and generated exclusion masks. The generator mixes
lists, tables, tables inside list items, nested items, malformed and overlapping
markers, multiline markers, frontmatter, fences, Unicode, and newline forms.
Coverage counters reject an empty exercise of children, child stays, refusals,
containers with both row and list children, list-owned markers in those containers,
or list-owned markers after rows. The random tail must independently meet every
counter; fixed regressions cannot satisfy that gate. The report includes both
total `coverage` and `random_coverage`. A small run or another seed may fail the
random gate; increase `--count` or change `--seed` to obtain the required coverage.
Negative controls confirm that changing child content, dropping child ownership,
reversing row ownership priority, suppressing a row refusal, or losing the fallback
to list ownership after a row miss each fails the comparison in both copies.

Scaling measures child parsing at N = 500, 1000, 2000, comparing complete child
outputs. Row refusal timing uses precomputed scanner records so the measurement
isolates pair processing: overlapping valid marker raw strings themselves have
quadratic total size, which this optimization does not change. The copied
follow-up measurement script resolves the checkout from its own location.
These measurements cover blank-line child parsing and row refusal processing.
CommonMark's existing per-item token scans and the table-to-container scan are
outside these optimizations.
