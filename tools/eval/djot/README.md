# Djot carrier evidence

Where does a Djot parser attach a `{stay=…}` block attribute? This eval runs a fixture
battery through four Djot readers and records, per stay, the node it landed on, so the
Djot profile states only what the readers agree on. Where they disagree, the writer
refuses that shape. That is §5.4's agreement subset, measured before it is written.

`MATRIX.md` is the table, generated. `FINDINGS.md` is the narrative; read that first.

## Readers

| key | what | pinned by |
|---|---|---|
| `djotjs` | djot.js 0.3.2, the last npm release (2024-12-19) | `js/package.json` |
| `djotjs-main` | djot.js `main` at `3b3a9f5` (2026-10-03), 56 commits past 0.3.2 | `js/package.json` (git dependency) |
| `jotdown` | jotdown 0.10.0, the Rust parser | `rs/Cargo.toml`, `rs/Cargo.lock` |
| `pandoc` | pandoc 3.12's Djot reader | `PANDOC`, see Setup |
| `carve` | Carve 0.1.9 (2026-09-30), a Djot-derived language read over the same fixtures, reported in its own columns | `js/package.json` |

Three axes per stay: **placement** (kind and text of the node carrying it, compared with
the fixture's intent in `fixtures/manifest.json`), **round-trip** (re-read after the
reader's own Djot writer; jotdown has none), and **visibility** (is the id in the
rendered HTML text).

## Setup

```bash
( cd js && npm ci )                     # djot.js 0.3.2 + main (main builds on install), Carve
( cd rs && cargo build --release --locked )
```

pandoc must be 3.3 or later for a `djot` reader; the system one may be older. The
measured one is 3.12, fetched and checked against GitHub's release digest:

```bash
mkdir -p ~/.cache/markstay-djot && cd ~/.cache/markstay-djot
curl -sLO https://github.com/jgm/pandoc/releases/download/3.12/pandoc-3.12-linux-amd64.tar.gz
echo "67d7d011fed8c8543306022b985b9b2499ab9b74818df91d8727c7e9ebc5ba06  pandoc-3.12-linux-amd64.tar.gz" | sha256sum -c
tar xzf pandoc-3.12-linux-amd64.tar.gz
```

## Run

```bash
PANDOC=~/.cache/markstay-djot/pandoc-3.12/bin/pandoc python3 run.py
```

Writes `results.json` (every observation, the round-trip sources, the HTML ids) and
`MATRIX.md`, and prints the disagreement count. `--check` exits 1 if `MATRIX.md` was
stale.

## Files

| File | Role |
|---|---|
| `run.py` | harness: runs the readers, normalises each tree, writes the matrix |
| `fixtures/*.dj` | one shape per file |
| `fixtures/manifest.json` | each fixture's purpose and the intended placement of each stay |
| `js/dump.mjs` | djot.js AST, HTML and Djot rendering as JSON |
| `rs/src/main.rs` | jotdown events as a JSON tree with byte ranges; reports unattached specifiers |
| `results.json`, `MATRIX.md` | output |
| `FINDINGS.md` | what the profile should take from it |
