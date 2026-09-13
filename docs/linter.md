# Reference linter

The [evaluation](evaluation.md) settled that an agent which is not told about markstay
strips nearly every marker during a rewrite. The defence is to make silent loss a
*caught* error rather than a quiet break of every downstream reference. That is what a
linter is for, and it is the second of the two mandatory mitigations in the
[specification](spec.md).

A [reference checker](https://github.com/markstaymd/markstay/tree/master/tools/linter)
implements the rules below. Its default path is dependency-free (Python standard
library only) and fully local: no network, no credentials. It is meant to run as a git
pre-commit hook or as the post-edit step of an agent that edits markstay documents. The
code and its tests ship with the site repo (`tools/linter/`). The optional
`markdown-it-py` dependency enables `--commonmark` mode
([version 1.1](spec.md#52-commonmark-tree-attachment-v11)) and the agreement-subset
advisory below, including when the selected segmentation mode is the default.

## What it checks

### Single document

| Code | Level | Meaning |
|------|-------|---------|
| `MALFORMED_MARKER` | error | a `stay:` marker with no parseable id |
| `ORPHAN_MARKER` | error | a marker with no preceding block to attach to |
| `DUPLICATE_ID` | error | the same id used by two markers in one document |
| `HASH_DRIFT` | warn | a marker's stored `hash=` no longer matches its block |
| `OUTSIDE_SUBSET` | info | §5.1 and §5.2 segment this document differently; emitted when the optional CommonMark parser is installed |

`OUTSIDE_SUBSET` implements the advisory in [§16](spec.md#16-conformance-summary).
It identifies documents outside [§5.4's agreement subset](spec.md#54-the-agreement-subset-v12),
where a blank-line write was more likely to change rendering in the measured
corpus. It does not block a hook, and a document without this finding has no
guarantee of unchanged rendering. It is separate from [§3.4's writer
refusals](spec.md#34-a-marker-that-shares-a-line-with-content-v18): a child carrier
can be refused even inside the agreement subset. The parser-free JavaScript and
Rust cores and the adapters do not emit this diagnostic.

### Regeneration diff (before vs after an edit)

| Code | Level | Meaning |
|------|-------|---------|
| `DROPPED_ID` | error | id in the baseline, gone after the edit (the AI-rewrite failure mode) |
| `DUPLICATED_ID` | error | id appears more than once after the edit (copy without re-mint, or a regeneration collision) |
| `RELOCATED_ID` | error | an id now sits on content that previously carried a *different* id |
| `HASH_DRIFT` | warn | id present in both, content edited in place |
| `NEW_ID` | info | id present only after the edit |

Any error-level finding exits non-zero, so the check gates a hook or an agent step
directly.

One `ORPHAN_MARKER` is worth naming, because it is the only thing
[version 1.2](spec.md#53-document-metadata-leading-yaml-frontmatter-v12) can
turn from silent into loud: a document stamped by a pre-1.2 tool may carry a marker
on its YAML frontmatter. Frontmatter is no longer a block, so that marker usually has
nothing to attach to. Delete the ones reported here; the blocks below them keep their
ids. Delete only those: a frontmatter marker with no blank line between it and the
content below binds forward to that content and is not reported, because it is still
doing its job.

## Usage

The runnable script is `tools/linter/markstay_lint.py` in the repo; `markstay-lint`
below stands in for `python3 markstay_lint.py`.

```bash
# well-formedness + intra-document checks
markstay-lint FILE [FILE ...]

# regeneration diff: what an edit did to the ids
markstay-lint --before OLD.md NEW.md

# machine-readable findings for a hook or agent step
markstay-lint --json --before OLD.md NEW.md

# CommonMark-tree attachment (version 1.1): a loose list or a fence with internal
# blank lines attaches as one block. Needs markdown-it-py.
markstay-lint --commonmark FILE
```

## Install it as a commit hook

To wire this checker into a repo as a git pre-commit hook (alongside the §11
preservation instruction), see [Get started](get-started.md). The
[`tools/adopt/`](https://github.com/markstaymd/markstay/tree/master/tools/adopt)
installer vendors the linter and blocks any commit that drops, duplicates, or
relocates a stay.

## Scope and conventions

- **Marker syntax**: the canonical HTML comment
  `<!-- stay:ID [hash=sha256:HEX] [k=v ...] -->` and the MDX profile
  `{/* stay:ID ... */}`. Attribute order is free and unknown attributes are tolerated;
  only `id` is required.
- **Attachment**: after-block placement. A marker binds to the block immediately above
  it. A chunk of markers on their own attaches to the previous content block. Blocks
  are split by blank lines by default; `--commonmark` splits over the CommonMark tree
  instead, so a loose list or a blank-line-containing fence attaches as one block
  ([version 1.1](spec.md#52-commonmark-tree-attachment-v11)).
- **Hash normalisation** follows [the spec](spec.md#8-hash-normalization): LF line
  endings, per-line trailing whitespace stripped, leading and trailing blank lines
  dropped, the marker excluded. The checker always compares at the precision recorded
  in the marker, so it never reports drift merely because a freshly computed hash is
  longer than a short stored one.

## Known limitation

Relocation detection is exact-content only: it catches markers that swap between blocks
whose text is otherwise unchanged. It does **not** detect partial relocation when a
block is split or merged. That case needs the `quote`/selector recovery model and is
the subject of the next planned experiment, not a deterministic linter.

## Why a deterministic check, not a smarter one

The point of the linter is to be boring and certain. It answers one question with no
model in the loop: did this edit drop, duplicate, or relocate any id? That is exactly
the class of failure the [evaluation](evaluation.md) showed an agent will introduce by
accident, and it is cheap to catch deterministically. Anything that needs judgement
(was this the *right* block to keep?) belongs to the recovery model, not the gate.
