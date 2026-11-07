# markstay reference linter

The post-edit safety net for markstay markers. The marker-survival eval
(`../eval/FINDINGS.md`) settled that a regenerating agent which is not told about
markstay strips nearly every marker (0/10 in a spot check), so silent loss has
to become a *caught* error rather than a quiet break of every downstream
reference. That is this tool's job.

The default path is dependency-free (Python 3.10+ stdlib only) and fully local: no
API credentials, no network. CommonMark mode (`--commonmark`, below) is the one
optional extra and needs `markdown-it-py`.

With the optional parser installed, lint also emits the informational
`OUTSIDE_SUBSET` advisory (§5.4) when blank-line and CommonMark segmentation
select different blocks. It does not affect the exit status and is absent
without that dependency. `--commonmark` selects tree segmentation for the lint;
the advisory describes the document's agreement between profiles either way.

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

# Optional list-item and table-row identity plus before/after recovery.
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
| `ORPHAN_CHILD` | warn | an opt-in child marker has no stayed parent container |

Regeneration diff (`--before OLD.md NEW.md`):

| Code | Level | Meaning |
|------|-------|---------|
| `DROPPED_ID` | error | id in the baseline, gone after the edit (the AI-rewrite failure mode) |
| `ADOPTED_ID` | warn | a block stay rewritten in place as its list item's child stay (`subhash`), where `DROPPED_ID` would otherwise fire (SPEC.md §16, v1.10). Kept, and printed rather than passed in silence: the test is lexical, so check the marker sits on the item it names |
| `DROPPED_CHILD_ID` | error | a child (`subhash`) id in the baseline that no marker carries after the edit, reported apart from `DROPPED_ID` so it is never named as its container's stay (SPEC.md §16, v1.9). Needs no `--child-blocks`: an item's marker stripped from a surviving item is the case it exists for, and an item deleted with its marker blocks the way a deleted section does |
| `DUPLICATED_ID` | error | id appears more than once after the edit (copy without re-mint, or a regeneration collision) |
| `RELOCATED_ID` | error | an id now sits on content that previously carried a *different* id (markers swapped), or it has moved off its block: its current block scores under 0.5 against its old text while that text survives on exactly one free block in the run above it (SPEC.md §11, v1.11; see [Relocation](#relocation)) |
| `HASH_DRIFT` | warn | id present in both, content edited in place (hidden from text output by default, see [Hash drift](#hash-drift)) |
| `NEW_ID` | info | id present only after the edit |
| `CHILD_DROPPED` | error | an opt-in child id cannot be recovered from its parent, exact child hash, or sibling-scoped quote evidence. When it fires, `DROPPED_CHILD_ID` is not repeated for the same id |

## Child blocks

`--child-blocks` enables the optional child segmenter from `../SPEC.md` §5.5 and
§5.6. A direct list item or accepted GFM table body row carries an ordinary stay
id and stores its child hash under `subhash=sha256:...`:

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

Table rows use the parser-free §5.6 scan under both block segmenters. The scan
requires outer pipes, treats complete marker spans as opaque while fixing cell
boundaries, accepts ragged body rows without parser padding, and refuses the whole
candidate on an unsafe body line. A row body trims named ASCII whitespace from
each cell, escapes backslashes and pipes, then joins the cells with `|`. A table
contributes row children only when it is the sole accepted candidate in its
selected §5 container.

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

The profile stays opt-in because §16 makes child segmentation and recovery
optional. Exact `subhash` key presence is not optional: even without
`--child-blocks`, `subhash=bogus` and quoted `subhash` values are never attributed
to their containing block, while `x-subhash` remains an ordinary extension key.

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
 attributes are tolerated; only `id` is required. Recognition validates the
 complete attribute body after normalizing line endings, with LF allowed only
 inside a quoted value. HTML discovery stops at the first `-->` or `--!>` and
 accepts only `-->`; MDX discovery stops at the first `*/` and accepts it only
 when `}` follows immediately. A rejected opener cannot consume a later opener,
 and every accepted marker retains its original source bytes.
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
- **A fenced code block is content, not markup** (`../SPEC.md` §3.3, v1.5). A
 marker-shaped string on a line inside a fence identifies no block, is hashed with
 the body rather than removed from it, and does not make its block stamped; the
 write path will not put one there either. Recognition is a line scan, identical
 under both segmenters: at most three leading **spaces** (a tab is not one) then
 three or more backticks or tildes, a backtick fence's info string carrying no
 backtick, closed by a run of the same character at least as long followed by
 nothing but spaces and tabs, and an unclosed fence running to the end of the
 document. The fence lines are part of the block, so a marker in an opening
 fence's info string is content too.

 The rule is why `find_markers` and `strip_markers` stay code-blind: they are
 grammar-level primitives answering "is this a well-formed marker" for a string
 with no document around it, which is what the conformance corpus needs. Whole-
 document callers compute `code_lines(text)` once and filter against it, on the
 frontmatter-blanking precedent.

 Three things it deliberately does not cover, in each case because seeing them
 needs the block parser the baseline exists to avoid: indented code blocks, inline
 code spans, and a fence the line scan cannot see (one carrying a blockquote
 marker, or indented more than three spaces, as a fence inside a nested list item
 is). A marker there is still a marker. The sharpest case is a fence whose opener
 shares its line with a list marker (`- ` then the backticks): the line scan
 cannot see it open and reads the *closing* line as an opener instead. With no
 later fence-shaped line that phantom runs to the end of the document and every
 marker after it goes silent; with one, the phantom closes and later lines come
 back, except for the block that straddles the close, which stays unstampable
 because a fence was open when it started. Either way it fails closed , nothing is
 stamped and nothing is rewritten , but nothing is identified either.

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
 falls through to "not frontmatter", where for this linter, a reader, the worst
 case is a stray hash-drift warning rather than silently discarded content. A
 writer has one worse case and refuses it (§5.3, v1.11): a payload that still reads
 as YAML but holds a blank line is YAML to a frontmatter reader, so the packaged
 `stamp` writes no marker into that span. Recognition here does not change. Spans
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

## Relocation

`RELOCATED_ID` has two branches. An exact swap: an id now sits on content that
carried a different id in the baseline. And a move (SPEC.md §11, v1.11): a kept
id carried by one block before and after, whose hash changed, is reported when

1. §9's body score, without context, of its old text against its current block
   is under 0.5;
2. exactly one **candidate** scores 0.8 or more against the old text. The
   candidates are the run of free blocks directly above the current block, back to
   the nearest block carrying an id present in both documents (a free block
   carries none), less any block whose body is unchanged from a baseline block
   other than the id's own: that block was there before the edit, so the edit did
   not strand it. An unmarked heading that restates the paragraph under it is the
   case this exists for; and
3. the current block's normalized text is not inside the old text.

That is the shape the rule exists for. In this repo's own history it fires on
13 of 168 edits, 7.7 per 100, and a hand census puts true relocations at 17, 10.1
per 100 (`../eval/replay/FINDINGS.md`): a paragraph typed between a block and
its trailing marker takes the marker, and the original paragraph is
left unmarked directly above. Clause 3 keeps a split from firing: a blank line
typed into a paragraph leaves the marker on a short tail that the old text
contains, and either half is an acceptable home for the id. All 13 firings are
real relocations, so conditional recall is 13 of 17.

What it does not catch: old text that survives anywhere other than in the run
of free blocks above the id's block, a successor edited under 0.8, a surviving
copy whose body is unchanged from a baseline block other than the id's own, and a
split or merge where content only partly
moved (except the reworded-tail split below, which fires). Those stay
`HASH_DRIFT`, and partial relocation is the domain of quote/selector recovery
(`../SPEC.md` §9, `../eval/attachment/`).

What it reports although the id did not move, all known and accepted:

- **A split whose tail is then reworded.** Clause 3 needs the tail inside the old
  text; once the tail is edited it is not, and the head directly above still
  scores 0.8 or more.
- **A block in the run above, carrying no kept id, that echoes the old text,
  while the paragraph is rewritten.** The echo is a heading, blockquote or
  lead-in that repeats the paragraph's old wording, anywhere between the
  paragraph and the nearest block above carrying a kept id. It may be unmarked
  or carry only new ids or child (`subhash`) markers, and it may be newly typed
  or edited in the same commit. It scores 0.8 or more against the old text while
  the rewritten paragraph scores under 0.5.
  An echoing block unchanged from a baseline block other than the paragraph
  itself is excluded (above), but one edit to it, even an added period, makes it
  a candidate again. This is the same block structure as
  a relocation whose stranded block was edited, which the rule exists to catch,
  and no content test on the two documents alone separates them.
- **Two blocks made identical (the exact-swap branch).** An edit that makes one
  block's text identical to another block's baseline text reports
  `RELOCATED_ID` for the edited block's id, although neither marker moved. This
  branch predates v1.11.

Each blocks a commit. Rewording the echoing block so it no longer repeats the old
text clears the second; when the id still names the block it should, the hook's
one-time bypass is `git commit --no-verify`. Moving the marker onto the echoing
block also clears the error, but it changes what the id names, so do it only
when the id really belongs there.

**Cost.** Each free block sits in the window of at most one block, so the scan
makes at most one comparison per free block for each kept id on that block.
Measured 2026-11-07 on a shared machine, N kept ids each rewritten with two free
blocks typed above it (`test_relocation_cost.py`, the same documents in all four
implementations), N = 2000 and 4000 free blocks: 3.0 s for this linter and the
Python package, 1.7 s in JavaScript, 0.7 s in Rust, doubling with N. The
document-wide search the rule replaced took 109 s in Rust and 251 s in JavaScript
at N = 1000 with 1000 free blocks. The quadratic case left is an edit that piles
every marker onto one block: then every id scans the whole document above it,
and N = 250 takes 28 s here, 13 s in JavaScript and 6.6 s in Rust. Every id
there is correctly reported as relocated.

## Programmatic use

`parse_document`, `lint_document`, and `lint_diff` are importable and all take a
`mode=` argument (`"blank-line"` default, `"commonmark"` for the §5.2 segmenter).
They also accept `child_blocks=True` for the experimental profile above.
The attachment-survival eval reuses `parse_document` (block + marker extraction)
and `lint_diff` (before/after id accounting) rather than reimplement marker
parsing, so it inherits the same mode switch.

`heading_paths(blocks)` and `canonical_heading(title)` are **experimental and
canonical-Python-only**: no `SPEC.md` text defines a heading path, no check here
consumes one, and the other implementations do not have them. They exist so the
attachment eval can measure whether a block's enclosing section is useful
recovery evidence for the §9 quote tier (`../eval/attachment/`). Their
derivation rules are pinned by tests rather than by the spec, so treat them as a
measurement tool and not as linter surface.

## Tests

```bash
python3 test_lint.py     # plain asserts, no dependency
pytest test_lint.py      # also works
```
