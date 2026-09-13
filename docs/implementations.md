# Implementations

markstay has three cores across Python, JavaScript, and Rust, plus a remark tree
adapter that reuses the JavaScript core. A shared, language-neutral **conformance
corpus** checks the [specification](spec.md), including the §8 content hash and
§9 recovery scoring. The 0.12.0 package family implements specification v1.8;
optional capabilities and each runner's scope are listed below.

| Language | Package | Install | Source |
|---|---|---|---|
| Python | [`markstay`](https://pypi.org/project/markstay/) (PyPI) | `pip install markstay` | [markstaymd/markstay-py](https://github.com/markstaymd/markstay-py) |
| JavaScript | [`markstay`](https://www.npmjs.com/package/markstay) (npm) | `npm install markstay` | [markstaymd/markstay-core](https://github.com/markstaymd/markstay-core) |
| JavaScript (remark) | [`remark-stay`](https://www.npmjs.com/package/remark-stay) (npm) | `npm install remark-stay` | [markstaymd/remark-stay](https://github.com/markstaymd/remark-stay) |
| Rust | [`markstay`](https://crates.io/crates/markstay) (crates.io) | `cargo add markstay` | [markstaymd/markstay-rs](https://github.com/markstaymd/markstay-rs) |

The same package family includes [`rehype-stay`](https://www.npmjs.com/package/rehype-stay),
which emits HTML ids from block stays, and
[`plate-stay`](https://www.npmjs.com/package/plate-stay), the [Plate bridge](plate.md).

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

## Child-block identity is optional, and only one implements it

[Version 1.3](spec.md#55-child-block-identity-list-items-v13) lets a direct list item
carry its own stay under the reserved `subhash` key, and
[version 1.6](spec.md#56-child-block-identity-table-rows-v16) lets a GFM table body row
do the same, on the same key and the same ladder. **The Python reference is the only
implementation that segments and resolves child blocks**, behind `--child-blocks` on the
CLI and `child_blocks=True` in the API, and that is not a gap:
[§16](spec.md#16-conformance-summary) makes segmenting and resolving them a tool's
choice.

What §16 does *not* make optional is three compatibility rules. Two bind a writer:
a marker with a `subhash` never receives a container hash, and never makes its block
count as stamped. The three core writers apply both without requiring child segmentation.
The third arrived with version 1.6 and binds every **reader**: such a marker must never
be reported as the stay of the block containing it. Ignoring it is fine; attributing it
to the container is not, because that hands a consumer a real id bound to the wrong
block with nothing in the output saying so. Rows are why it is now an error rather than
an omission: a row marker sits mid-block, so a whole table's rows could otherwise be
reported as one block's stays. Core conformance vectors pin these rules; adapter
tests check the relevant reader behavior. `plate-stay` refuses child-marked input
because its bridge cannot carry the child's identity through conversion.

## Write safety in version 1.8

[§3.4](spec.md#34-a-marker-that-shares-a-line-with-content-v18) requires block
markers to be inserted on their own line. Its same-line carrier checks apply when
a writer implements list-item or table-row identity:

| Package | Marker-writing scope |
|---------|----------------------|
| Python `markstay` | Applies §3.4 to list-item and row carriers with `child_blocks=True`; the CLI reports each refused carrier. |
| JavaScript and Rust `markstay` | Write block markers on separate lines; do not implement child carriers. |
| `remark-stay` | Reads stays and records annotations in `file.data.stay`; never writes marker comments. |
| `rehype-stay` | Sets `hProperties.id` for HTML emission; never writes marker comments. |
| `plate-stay` | `fromPlate` writes block markers on separate lines; `serializeStay` delegates to it. List-item and table wrappers are refused. |

Only Python reaches these child-carrier checks. Existing
same-line block markers remain readable, and the core writers may refresh their
hashes or replace duplicate ids in place. These rules do not guarantee unchanged
rendering for arbitrary Markdown; see [compatibility](compat.md#marker-insertion-and-rendering-v18).

With `markdown-it-py` installed, the Python linters also emit the optional
`OUTSIDE_SUBSET` advisory when §5.1 and §5.2 disagree on a document's segmentation.
It is informational, does not block a commit, and its absence is not a rendering
guarantee. The JavaScript and Rust cores and the adapters do not emit this advisory.

## One corpus, four full runners

The canonical and packaged Python runners each verify **420 core vectors and 32
optional `rows` vectors**. JavaScript and Rust each verify **420 core vectors**
and explicitly assert that they decline the 32-vector `rows` profile. These four
full runners fail on an unknown profile or missing expected vectors.

`remark-stay` has a separate category-routed parity harness over `parse`, `lint`,
`diff`, `anchors`, and `resolve`, plus the tree-specific tier. It inventories core
categories, but does not load or assert a decline for the optional `rows` profile.
It is not one of the four full runners. The other two adapters have their own
integration suites.

The row profile checks §3.4's placement decisions. Rendering comparisons require
parsers and run in a separate evaluation; they are not language-neutral corpus
assertions. The parser-dependent `OUTSIDE_SUBSET` advisory is likewise excluded
from core finding comparisons and tested in Python's own suites.

The CLI linters (Python, JavaScript, and Rust) exit non-zero on any error-level
finding, so they fit a pre-commit hook or an agent's post-edit check.

To wire markstay into a repo as a commit hook rather than call it from code, see
[Get started](get-started.md). For the design rationale behind the spec these
implementations cover, see the [specification](spec.md) and the
[reference linter](linter.md) findings.
