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
code ships with the site repo (`tools/linter/`, 20/20 self-tests in `test_lint.py`).
The one optional extra is `--commonmark` mode ([version 1.1](spec.md#commonmark-tree-attachment-version-11)),
which needs `markdown-it-py`.

## What it checks

### Single document

| Code | Level | Meaning |
|------|-------|---------|
| `MALFORMED_MARKER` | error | a `stay:` marker with no parseable id |
| `ORPHAN_MARKER` | error | a marker with no preceding block to attach to |
| `DUPLICATE_ID` | error | the same id used by two markers in one document |
| `HASH_DRIFT` | warn | a marker's stored `hash=` no longer matches its block |

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

## Adopting it in a repo

The [`tools/adopt/`](https://github.com/markstaymd/markstay/tree/master/tools/adopt)
directory packages the two mandatory mitigations so a repo can pick them up without
wiring anything by hand.

**The pre-commit hook** (this checker, mitigation #2). An installer vendors the
linter into the target repo and installs a git pre-commit hook that lints each
staged Markdown file and runs the regeneration diff against the committed version,
so a commit that drops, duplicates, or relocates a stay is blocked before it lands.
Hash drift is a warning and does not block; files with no markstay markers pass
silently.

```bash
cd tools/adopt
./install.sh /path/to/your/repo        # vendor the linter + install the hook
# now: edit a .md, drop a stay: marker, `git commit` -> blocked
```

**The preservation instruction** (mitigation #1). The
[AI editing contract](spec.md#ai-editing-contract) is only honoured if the editing
agent is told to honour it, the single biggest lever on whether markers survive a
rewrite. `markstay_preserve.py` is the canonical source of that instruction:

```bash
python3 markstay_preserve.py                       # print it (seed a system prompt / AGENTS.md)
python3 markstay_preserve.py --wrap notes.md       # wrap a doc into a ready editing prompt
```

Together they are the durable deliverable the [evaluation](evaluation.md) pointed
at: instruct the agent up front, then catch any silent loss at commit time.

## Scope and conventions

- **Marker syntax**: the canonical HTML comment
  `<!-- stay:ID [hash=sha256:HEX] [k=v ...] -->` and the MDX profile
  `{/* stay:ID ... */}`. Attribute order is free and unknown attributes are tolerated;
  only `id` is required.
- **Attachment**: after-block placement. A marker binds to the block immediately above
  it. A chunk of markers on their own attaches to the previous content block. Blocks
  are split by blank lines by default; `--commonmark` splits over the CommonMark tree
  instead, so a loose list or a blank-line-containing fence attaches as one block
  ([version 1.1](spec.md#commonmark-tree-attachment-version-11)).
- **Hash normalisation** follows [the spec](spec.md#hash-normalisation): LF line
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
