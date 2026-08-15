# markstay reference linter

The post-edit safety net for markstay markers. The marker-survival eval
(`../eval/FINDINGS.md`) settled that a regenerating agent which is not told about
markstay strips nearly every marker (0/10 in a spot check), so silent loss has
to become a *caught* error rather than a quiet break of every downstream
reference. That is this tool's job.

The default path is dependency-free (Python 3.10+ stdlib only) and fully local: no
API credentials, no network. CommonMark mode (`--commonmark`, below) is the one
optional extra and needs `markdown-it-py`.

## Usage

```bash
# well-formedness + intra-document checks on one or more files
python3 markstay_lint.py FILE [FILE ...]

# regeneration diff: what an edit did to the ids
python3 markstay_lint.py --before OLD.md NEW.md

# machine-readable findings (for a commit hook or an agent's post-edit step)
python3 markstay_lint.py --json --before OLD.md NEW.md

# list HASH_DRIFT in the text output (hidden by default, see "Hash drift" below)
python3 markstay_lint.py --show-drift FILE

# CommonMark-tree attachment (SPEC.md §5.2, v1.1): a loose list or a fence with
# internal blank lines attaches as one block. Needs markdown-it-py.
python3 markstay_lint.py --commonmark FILE

# Experimental direct list-item identity and before/after recovery.
python3 markstay_lint.py --child-blocks --commonmark FILE
python3 markstay_lint.py --child-blocks --commonmark --before OLD.md NEW.md
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
| `HASH_DRIFT` | warn | a marker's stored `hash=` no longer matches its block's content (hidden from text output by default, see [Hash drift](#hash-drift)) |
| `ORPHAN_CHILD` | warn | an opt-in child marker has no stayed parent list |

Regeneration diff (`--before OLD.md NEW.md`):

| Code | Level | Meaning |
|------|-------|---------|
| `DROPPED_ID` | error | id in the baseline, gone after the edit (the AI-rewrite failure mode) |
| `DUPLICATED_ID` | error | id appears more than once after the edit (copy without re-mint, or a regeneration collision) |
| `RELOCATED_ID` | error | an id now sits on content that previously carried a *different* id (markers swapped/relocated) |
| `HASH_DRIFT` | warn | id present in both, content edited in place (hidden from text output by default, see [Hash drift](#hash-drift)) |
| `NEW_ID` | info | id present only after the edit |
| `CHILD_DROPPED` | error | an opt-in child id cannot be recovered from its parent, exact child hash, or sibling-scoped quote evidence |

## Experimental child blocks

`--child-blocks` enables the list-item identity prototype. It is off by default
and is **not** part of the v1.1 standard, which defers item identity at `../SPEC.md`
§5.1. A direct list item carries an ordinary stay id and stores its item hash
under `subhash=sha256:...`:

```md
- Ship the linter <!-- stay:a7c1 subhash=sha256:9d2f -->
- Ship the hook <!-- stay:b3e0 subhash=sha256:41ac -->
<!-- stay:parent hash=sha256:8a77 -->
```

The child hash body cuts stay markers, removes the first line's indentation, list
marker, and following syntactic gap, then removes the equivalent content
indentation from continuation lines. Bullet-glyph changes and ordered-list
renumbering therefore do not drift a child. Nested source remains part of the
direct item's body.

CommonMark mode reads direct `listItem` source spans, including loose and
multi-paragraph lists. The dependency-free blank-line mode deliberately accepts
only a restricted profile: flat, tight, single-paragraph items, with continuation
lines using the exact content indentation. It emits no child blocks for loose
lists, lazy continuations, nested blocks, tabs, fences, mixed list delimiters, or
other unclear boundaries. Those documents fall back to existing whole-block
attachment.

Recovery resolves the parent first, then applies child marker, unchanged-parent
ordinal, unique sibling hash, unique document hash, and sibling-scoped quote tiers.
Ordinal never changes the quote score or commit margin. Identical baseline siblings
without a surviving marker detach rather than guess.

Attachment safety is measured from two independent directions, both at 0% false
attachment: a deterministic matrix of 6 list shapes x 9 edit operations (0/324, 95%
Clopper-Pearson upper bound 0.92%) and real LLM rewrites of list-heavy documents
(0/256 on gpt4o, bound 1.16%). Recovery is 95.0% and 92.2% respectively, and the
similarity band where an item is attached at all lands on the `../SPEC.md` §9
constants. See `../eval/attachment/README.md`.

The prototype stays opt-in regardless, because safety is not the same as worth:
catch precision on real item drops is unmeasured, so no v1.2 spec text,
cross-language parity, or conformance category follows from it yet.

## Hash drift

`HASH_DRIFT` is the one finding that only ever says "this block was edited in
place". It never blocks (only `error` findings gate, SPEC.md §16), and in a normal
edit it is the dominant line, so the **text render hides it by default** and
collapses it to one discoverable receipt (`-> N hash-drift findings hidden
(--show-drift to list)`). Pass `--show-drift` to enumerate it. The `error`/`warn`/
`info` summary always counts the real totals, so a hidden drift is still counted as
the warn it is.

This is a presentation choice only. The finding stays in the data model at `warn`,
in the `lint_document` / `lint_diff` return tuples, and in `--json` (which is
byte-identical with and without `--show-drift`). Structured consumers that key off
`HASH_DRIFT`, including caches and re-embed triggers that treat a stale hash as
fatal, read those, not the printed text, so they are unaffected. If you need drift
in a pipeline, read `--json` or the return tuple.

## Scope and conventions

- **Marker syntax**: the canonical HTML comment `<!-- stay:ID [hash=sha256:HEX]
  [k=v ...] -->` and the MDX profile `{/* stay:ID ... */}` (one data model, two
 serializations, per `../SPEC.md` §3, §4). Attribute order is free and extra
 attributes are tolerated; only `id` is required.
- **Attachment**: after-block placement (`../SPEC.md` §5). A marker binds to the
 block immediately above it, whether on the next line or as its own chunk; a chunk
 that is only markers attaches to the previous content block. Blocks are split by
 blank lines by default (dependency-free); `--commonmark` / `parse_document(...,
 mode="commonmark")` splits over the CommonMark tree instead, so a loose list or a
 blank-line-containing fence attaches as one block (`../SPEC.md` §5.2, v1.1). The
 two modes agree on the documents `../SPEC.md` §5.4 calls the agreement subset:
 every maximal run of non-blank lines is exactly one CommonMark node. In practice
 that means blank lines between constructs, tight lists, fenced rather than
 indented code, and no link reference definitions.
- **Leading YAML frontmatter is metadata, not a block.** It is skipped by both
 segmenters: never a block, never stamped, never hashed. Without this, a
 metadata-only edit (`status: draft` -> `status: done`) drifts a content hash, and
 the two segmenters disagree about the span , the baseline reads it as one block
 while CommonMark reads the closing fence as a setext underline and turns the
 metadata into an H2.

 Recognition is conservative, because `---` is also a thematic break and a setext
 underline. A span counts as frontmatter only when **all** of: line 1 is exactly
 `---`; a later line is exactly `---` or `...`; the payload between them is
 non-empty and has no blank line; and at least one payload line is unambiguously
 YAML (a `key:` or a `- item`). A YAML **comment does not count**, since `# x` is
 also an ATX heading. "Unambiguously YAML" is judged with ASCII whitespace, as everywhere else in the spec (§8/§9): the runtimes' own Unicode whitespace sets disagree with each other, and a rule that DELETES a span must not vary by implementation. Conditions 3 and 4 confine the ambiguity rather
 than removing it: a blank-free payload that reads as YAML is also ordinary Markdown,
 as a sequence (`---`/`- Keep this`/`---`, a list between two thematic breaks) or as
 a mapping (`---`/`title: v`/`---`, a setext heading under one). Both satisfy all
 four conditions and their content **is** excluded (frontmatter wins, as it does in
 every mainstream site generator). A document that fails any of the four conditions
 falls through to "not frontmatter", where the worst case is a stray hash-drift
 warning rather than silently discarded content. Spans
 left alone as ordinary Markdown therefore include `---` with no closing fence,
 any `---` fence that is not at line 1, `---`/blank/prose/blank/`---` (two thematic
 breaks), `---`/`Title`/`---` (a setext heading), and comment-only payloads.

 A marker stamped onto frontmatter **before** this behaviour existed sits after the
 closing fence, and usually raises `ORPHAN_MARKER`: it has no block to attach to.
 Delete it. The exception is a marker with **no blank line** between it and the
 content below, which blank-line segmentation reads as one run and binds to that
 content, so it stays live and must not be deleted , lint first
 (`frontmatter-marker-binds-forward-with-no-blank-line` pins the shape). A marker written *inside* the payload is blanked with the rest of
 the frontmatter and raises nothing; no tool writes one there, since the stamper
 always writes after the block.
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

`parse_document`, `lint_document`, and `lint_diff` are importable and all take a
`mode=` argument (`"blank-line"` default, `"commonmark"` for the §5.2 segmenter).
They also accept `child_blocks=True` for the experimental profile above.
The attachment-survival eval reuses `parse_document` (block + marker extraction)
and `lint_diff` (before/after id accounting) rather than reimplement marker
parsing, so it inherits the same mode switch.

## Tests

```bash
python3 test_lint.py     # plain asserts, no dependency
pytest test_lint.py      # also works
```
