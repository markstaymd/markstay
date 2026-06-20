# Implementations

markstay has four independent implementations across three languages. They are not
ports of one codebase: each is written to the [specification](spec.md) and gated by
a single shared, language-neutral **conformance corpus**, so "the implementations
agree" is a tested fact rather than an assertion. The corpus pins the two promises
that have to be exact, the §8 content hash and the §9 recovery scoring, down to the
bit.

| Language | Package | Install | Source |
|---|---|---|---|
| Python | [`markstay`](https://pypi.org/project/markstay/) (PyPI) | `pip install markstay` | [markstaymd/markstay-py](https://github.com/markstaymd/markstay-py) |
| JavaScript | [`markstay`](https://www.npmjs.com/package/markstay) (npm) | `npm install markstay` | [markstaymd/markstay-core](https://github.com/markstaymd/markstay-core) |
| JavaScript (remark) | [`remark-stay`](https://www.npmjs.com/package/remark-stay) (npm) | `npm install remark-stay` | [markstaymd/remark-stay](https://github.com/markstaymd/remark-stay) |
| Rust | [`markstay`](https://crates.io/crates/markstay) (crates.io) | `cargo add markstay` | [markstaymd/markstay-rs](https://github.com/markstaymd/markstay-rs) |

## What each one is

- **Python (`markstay`)** , the reference implementation. The parser-free core
  (hashing, marker grammar, segmentation, lint, recovery) plus a `markstay` CLI;
  CommonMark-tree attachment (§5.2) is an optional `markstay[commonmark]` extra.
- **JavaScript (`markstay`)** , a second, independent zero-dependency core (Node
  built-ins only) covering the same surface, with a `markstay` CLI that also ships
  the write side: mint ids, stamp a document, refresh drifted hashes, repair
  duplicate ids.
- **`remark-stay`** , a [unified](https://unifiedjs.com/)/remark adapter that does
  §5.2 CommonMark-tree attachment over the mdast, reusing the JS core. Use it inside
  an existing remark pipeline.
- **Rust (`markstay`)** , a third-language core that is the strongest portability
  evidence (statically typed, UTF-8 native, explicit about bytes vs code points). It
  is `no_std` + `alloc` with zero runtime dependencies, ships a single static CLI
  binary, and is the source for a future WASM build.

## One corpus, four runners

Every implementation runs the same conformance vectors, so a change in any one that
breaks cross-implementation agreement fails its own test suite. That shared corpus
is what lets a tool depend on *markstay the spec* rather than on one library's
quirks. The CLI linters (Python, JS, and Rust) exit non-zero on any error-level
finding, so they drop straight into a pre-commit hook or an AI agent's post-edit
check.

To wire markstay into a repo as a commit hook rather than call it from code, see
[Get started](get-started.md). For the design rationale behind the spec these
implementations cover, see the [specification](spec.md) and the
[reference linter](linter.md) findings.
