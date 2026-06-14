# markstay reference linter

The post-edit safety net for markstay markers. The marker-survival eval
(`../eval/FINDINGS.md`) settled that a regenerating agent which is not told about
markstay strips nearly every marker (0/10 in a spot check), so silent loss has
to become a *caught* error rather than a quiet break of every downstream
reference. That is this tool's job.

It is dependency-free (Python 3.10+ stdlib only) and fully local: no API
credentials, no network.

## Usage

```bash
# well-formedness + intra-document checks on one or more files
python3 markstay_lint.py FILE [FILE ...]

# regeneration diff: what an edit did to the ids
python3 markstay_lint.py --before OLD.md NEW.md

# machine-readable findings (for a commit hook or an agent's post-edit step)
python3 markstay_lint.py --json --before OLD.md NEW.md
```

Exit status is `1` if any **error**-level finding is reported, `0` otherwise, so
it gates a hook or an agent step directly.

## What it checks

Single-document (`FILE`):

| Code | Level | Meaning |
|------|-------|---------|
| `MALFORMED_MARKER` | error | a `stay:` marker with no parseable id (no bare id token after `stay:`) |
| `ORPHAN_MARKER` | error | a marker with no preceding block to attach to |
| `DUPLICATE_ID` | error | the same id used by two markers in one document |
| `HASH_DRIFT` | warn | a marker's stored `hash=` no longer matches its block's content |

Regeneration diff (`--before OLD.md NEW.md`):

| Code | Level | Meaning |
|------|-------|---------|
| `DROPPED_ID` | error | id in the baseline, gone after the edit (the AI-rewrite failure mode) |
| `DUPLICATED_ID` | error | id appears more than once after the edit (copy without re-mint, or a regeneration collision) |
| `RELOCATED_ID` | error | an id now sits on content that previously carried a *different* id (markers swapped/relocated) |
| `HASH_DRIFT` | warn | id present in both, content edited in place |
| `NEW_ID` | info | id present only after the edit |

## Scope and conventions

- **Marker syntax**: the canonical HTML comment `<!-- stay:ID [hash=sha256:HEX]
  [k=v ...] -->` and the MDX profile `{/* stay:ID ... */}` (one data model, two
 serializations, per `../SPEC.md` §3, §4). Attribute order is free and extra
 attributes are tolerated; only `id` is required.
- **Attachment**: after-block placement over blank-line-delimited blocks
 (`../SPEC.md` §5). A marker binds to the block immediately above it, whether on
 the next line or as its own blank-line-separated chunk. A chunk that is only
 markers attaches to the previous content block.
- **Hash normalization** is `../SPEC.md` §8. `normalize_body` implements it (LF
 endings, per-line trailing whitespace stripped, leading/trailing blank lines
 dropped, marker excluded) and always compares at the precision recorded in the
 marker, so it never reports drift merely because a freshly computed hash is
 longer than a short stored one.

## Known limitation

Relocation detection is exact-content only: it catches markers that swap between
blocks whose text is otherwise unchanged. It does **not** detect partial
relocation when a block is split or merged. That case needs quote/selector
recovery (`../SPEC.md` §9), handled by the attachment-survival eval
(`../eval/attachment/`), not this deterministic linter.

## Programmatic use

`parse_document`, `lint_document`, and `lint_diff` are importable. The
attachment-survival eval is expected to reuse `parse_document` (block + marker
extraction) and `lint_diff` (before/after id accounting) rather than reimplement
marker parsing.

## Tests

```bash
python3 test_lint.py     # plain asserts, no dependency
pytest test_lint.py      # also works
```
