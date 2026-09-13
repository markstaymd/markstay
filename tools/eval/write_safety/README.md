# Write-path safety

The measurement behind the **§3.4 carrier rule**, in two parts.

**The rule refuses on presence, not on meaning.** §3.4 refuses a carrier whose text
carries `<`, a backslash or `{` (MDX only), and refuses a marker carrying anything beyond
its id and digest. It never asks whether that `<` opens anything.
`carrier_cost.py` holds both predicates: `plain_text_state()` is the rule, and
`lexical_draft()` is the round 4 version that did decide what each character meant,
kept because the ten documents it got wrong are the argument for the one that replaced
it.

`carrier_sweep.py` is the gate: 63 text endings in both required carrier positions under
both segmenters, plus 26 shapes an endings table cannot express, of which the fifteen
prefixed `R4` through `R7` are the review arms' counterexamples. It exits non-zero if the
predicate ever permits something the oracle calls unsafe.

**The limit.** §3.4 also says what a write does *not* promise, and `sweep.py` is the
number behind that sentence. A claim about rendering can only be checked by
rendering: every attempt to reason about it lexically missed something.

The commands below run from `eval/write_safety/`. In the published repository,
that directory is under `tools/`; the same relative paths work there. The
published tools include the linter, writer source, corpus and this harness.
The manifest records the measured corpus by digest and basename; `corpus.txt`
is a local input list that each reader rebuilds.

## Pin the renderer before quoting a number

`requirements.txt` pins markdown-it-py to **4.2.0** (CommonMark 0.31.2). The endings
sweep finds 17 unsafe endings there and 15 under 3.0.0, whose pre-0.31 comment rule
does not accept the doubled `--` a marker leaves after an unclosed `<!--`. The
predicate refuses those two endings under either renderer, but a count without its
renderer is not checkable.

```sh
python -m venv ../../impl/py/.venv
../../impl/py/.venv/bin/pip install -r requirements.txt
```

## What it measures

`sweep.py` renders each document before and after a stamp and compares the element
structure and the words. It reports the blank-line profile (§5.1) split by whether
the document is inside §5.4's **agreement subset**, the tree profile (§5.2), and
child-block stamping under the tree profile, which is what exercises §5.6's in-cell
row carrier. The child arm is reported twice, once under a CommonMark renderer and
once with the GFM table rule on, because a CommonMark renderer shows a table as one
paragraph and pairs delimiters across cells.

`carrier_cost.py` counts positions from the document's own child segmentation, and a
carrier text is a raw-source prefix of the container block, which is what §3.4 specifies.
Three earlier versions got it wrong in three different ways: the first globbed table cells
and list-start lines with two regexes, counting a six-cell row as six positions where a
writer has one (53574, a slice count); the second read the span back out of stamped output
with a paragraph walk that disagreed with the segmenter on seven of 37746 carriers; the
third counted positions the writer's own guards exclude, such as a list nested inside a
fence. The census now applies those guards, which is where 40508 and 30799 come from.

`incremental.py` asks the question the corpus cannot: what §3.4 costs on a document
markstay has **already stamped**. Every other measurement here starts from unmarked text,
so none of them could see that the rule as first written refused a carrier because of a
marker markstay itself had put there. It stamps each document, takes one child's own
marker back out, and asks whether the rule still permits it, with and without the mask,
so a refusal caused by a marker is separated from one the mask cannot touch.

`subset_check.py` checks §5.4's membership predicate against the property it exists to
predict: that inside the subset both segmenters give the same blocks, with each marker
bound to the same one. It runs over generated documents (every arrangement of three
fragments, marker-only lines included) as well as over the corpus, as found and stamped.
The generated arm is the load-bearing one, because no document in this corpus carries a
marker, so a claim resting on the corpus alone says nothing about the marker rules. That
is not hypothetical: review round 11 found a certified document the corpus arm could not
reach.

## The corpus, and how to rebuild it

The published numbers were measured over **npm package documentation**, which is
ordinary third-party Markdown nobody wrote with markstay in mind. Build a listing
and run the sweep:

```sh
find ~ -name '*.md' -path '*node_modules*' | head -4000 > corpus.txt
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python sweep.py corpus.txt --manifest corpus.sha256
```

Documents are deduplicated by content and those over 200 KB are skipped, so a
listing of 4000 paths yields far fewer distinct documents. The published run used
2417. `corpus.sha256` records what a run actually read, so two runs can be compared
rather than merely both quoted.

**It is rebuilt, not reproduced.** The 2026-09-10 run shares 613 documents with the
2026-09-08 run behind the withdrawn drafts' numbers, because `node_modules` on the
measuring machine moved between them. The manifest is what makes two runs comparable;
it does not make an old one repeatable.

Run it from this directory with the packaged reference importable:

```sh
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python sweep.py corpus.txt
```

## The carrier rule (2026-09-10)

63 endings and 26 shapes, both required carrier positions, both segmenters. **39 of
those break the rendering and the rule refuses all 39.**

The `R4` through `R7` shapes are why the rule stopped reasoning. Twelve of the fifteen
are documents the lexical draft permits outright; the other three sat outside the scope
it was reading, and are the reason the carrier text is the container's. The twelve, each
a document the lexical draft permits and a renderer changes: an HTML tag opener preceding a backtick
(CommonMark gives code spans, tags and autolinks equal precedence, resolved by first
opener, so "a code span binds first" is false), a backslash-escaped backtick, a `>`
inside a quoted attribute, `?>` and `]]>` supplied by the marker's own `quote=` evidence,
three separate ways an end tag does not end a raw-text element, backticks paired across
GFM cells by a whole-row scope, a paragraph scope the draft defined as a line, a `quote`
value that closes a link title, and a pipe in one that splits a GFM cell. Deciding those
correctly needs tag and attribute state, per-element raw-text termination, PI and CDATA
closers, inline precedence, backslash escapes and GFM cell splitting, which is an HTML
tokenizer.

**v1.8's code-span mask does not reopen the first of those, and the sweep is what says
so rather than an argument.** That draft asked whether a code span *bound first*; the
mask asks only whether backtick runs pair by length within a line, and refuses on the
presence of a `<` that no closed run brackets. `R4 code span loses to an earlier HTML
tag opener` is still refused under both segmenters, because its `<` sits outside every
span the scan finds, and so is `R4 row, backticks paired across GFM cells`, which is
what scoping the mask to §5.5 keeps answered. All 39 remain refused.

Two of them are the marker's own bytes rather than its carrier text, which is why §3.4
permits only an id-and-digest marker at a carrier and sends evidence to §4's side index.
Two more are context in the **container** rather than in the child, which is why the
carrier text is a prefix of the container block.

The last one is not a capture at all: a flush insertion makes the delimiter run it lands
against both opening and closing where it was closing alone, and the multiple-of-three
rule then refuses the match, so `| *Hello!** |` stops rendering its emphasis with nothing
hidden and none of the capture-opening characters present. No prefix can see that, which
is why the rule carries a one-byte clause for flush positions. That clause came out of
four documents a review arm sent, so `flush_table()` derives it properly: 59 cell bodies
in the flush position, zero misses.

The cost of not deciding, on the corpus: **2168 refusals in 40508** carrier positions
under the tree profile (5.35%) and 1906 in 30799 under the blank-line profile (6.19%),
of which 688 are rows out of 2762. Before v1.8's code-span mask the same corpus refused
3186 (7.87%) and 2716 (8.82%); the recovered 1018 and 810 positions are exclusively §5.5
list children, since the mask reaches neither a row nor an unclosed span, and rows are
unmoved at 688. The alternatives were priced first against that older figure: `<` alone
costs 4.8% and answers 31 of the 39, and adding every backtick costs 61% and answers no
more than this rule does. Exempting a `<` followed by whitespace recovers **128**
positions of 3186 while still answering all 39, which is not worth a clause three
implementations have to agree on, and it does not reach the shape v1.8 does: a tracker's
`<` is followed by a letter. The 139 this paragraph used to quote came from a measurement
that dropped the flush guard at the same time and then blamed the resulting missed
capture on the exemption; with the guard kept, the exemption refuses 3058 and answers
all 39.

```sh
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python carrier_sweep.py
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python carrier_cost.py corpus.txt
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python incremental.py corpus.txt
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python subset_check.py corpus.txt
```

`carrier_sweep.py` exits non-zero if the predicate ever permits something the oracle
calls unsafe, so it is a gate and not only a table. It also exits non-zero if the writer
cannot stamp a child in a document **it produced itself**: every other arm here starts
from unmarked text, which is why none of them could see that §3.4 as first written
refused a carrier because of a marker markstay had put there (70.9% of stamped children,
measured over this corpus, and the amendment that fixed it costs nothing on the unmarked
figures above). `carrier_cost.py` prints the
withdrawn draft's refusal count beside the rule's, so the price stays checkable rather
than remembered.

## The rendering limit (2026-09-10, 2417 documents)

| Profile | Result |
|---|---|
| §5.1, inside §5.4's agreement subset | 1020 documents, **0** changed |
| §5.1, outside the subset | 1397 documents, **159** changed |
| §5.2 | **0** changed |
| §5.2 with child blocks | **0** changed |
| §5.2 with child blocks, GFM tables on | **0** changed |

**Re-run 2026-09-11 with §3.4 implemented**, which is what moved the child-block row from
1 to 0: the one document it changed was `figures/readme.md`, whose cells carry bare `*`
characters, and the flush clause refuses that carrier. The 1021/1396 split became
1020/1397 in the same run, because the subset partition is now the linter's own
derivation of §5.4 rather than this directory's approximation of it. That derivation is
checked against what it predicts rather than against its own reasoning: over the same
2417 documents it agrees with the two segmenters' actual block boundaries in both
directions, with none certified that segment differently and none refused that segment
identically.

**These numbers describe a limit, not a guarantee, and the difference cost two
rejected drafts.** An earlier §3.4 read the first two rows as "a §5.1 writer is safe
exactly on §5.4's agreement subset". It is not: `<textarea>hello` is inside the
subset and unsafe under both profiles, and a heading above a body is outside it and
safe. The subset is a good bet and not a boundary, which is why §13's linter SHOULD is
worded one-directionally and §3.4 promises bytes rather than rendering.

The document that used to change in the child arm is `figures/readme.md`, whose table
cells contain bare `*` characters. Under a CommonMark renderer that table is one
paragraph, so a row marker changed which `*` paired with which; with the table rule on it
is a table and the change disappeared. §3.4's flush clause now refuses the carrier under
both, so the arm reads 0 either way and the pair no longer separates the renderer's
answer from the carrier's. Keep the pair anyway: what it separates is a property of the
renderer, not of this result.

## The MDX profile, measured separately

A CommonMark renderer cannot see an MDX expression, so `mdx_probe` cases are compiled
with `@mdx-js/mdx` 3.1.1 instead of rendered. Three results worth keeping:

- An expression that spans a blank line (`{` / blank / `"hello"}`) breaks when a
  marker is minted into the gap, **under both profiles**. This is the one measured
  construct the tree profile does not rescue, which is why any statement of the limit
  has to name MDX expressions.
- A carrier appended after an unclosed `{/*` or `{` is not a regression the writer
  caused: those documents already fail to compile. §3.4 refuses the position anyway,
  since a writer cannot tell.
- **Counting braces is not lexing.** `{"}"` leaves the expression open, because the
  brace is inside a string, and the round 4 predicate read it as closed. Found by the
  codex arm on 2026-09-10 and reproduced here; §3.4 refuses on the `{` instead.

## The oracle is the fragile part

`render_oracle.py` went through six versions and **every one of them moved a number
that had already been written down**. Each fault was a layout difference read as a
rendering change: whitespace left where a comment was removed from a raw HTML block,
whitespace introduced between two tags, whitespace before a closing tag, and a text
node split in two by a removed marker. A visible-text oracle has the opposite fault
and misses a construct reflowed into another construct with the same words.

`test_oracle.py` pins both directions with three documents a write demonstrably
changes and five it must not flag, plus the predicate against the endings the sweep
found unsafe. One of the three is now written by hand rather than produced by `stamp`,
because §3.4 refuses that carrier: an oracle case that stops firing because the writer
stopped making the mistake is a gate that has turned itself off. Run it before trusting a number this harness prints:

```sh
PYTHONPATH=../../impl/py/src:. ../../impl/py/.venv/bin/python test_oracle.py
```

## What this harness still cannot see

Recorded because a blind spot in an oracle reads as a clean result, and the first two
were found by a review arm rather than by the harness noticing.

- **Whitespace inside a whitespace-preserving element.** `rendered()` collapses every
  run of whitespace, so a marker line inserted inside `<pre>alpha` / blank / `beta</pre>`
  adds a visible blank line that the comparison cannot see. Fixing it means tracking
  which elements preserve whitespace rather than normalising globally.
- ~~**Frontmatter recognition.**~~ Closed 2026-09-11: `agreement.py` imports the
  linter's `in_agreement_subset`, which uses §5.3's own frontmatter rule and excludes
  marker spans per §5.4. Kept here because it is the shape to watch for: the eval had a
  second answer to a normative question, its approximation was recorded honestly in this
  file, and being written down is what let it be read as settled for three days.
- **GFM beyond tables.** The tables arm turns on markdown-it's table rule only.
  Strikethrough, task lists and autolink literals are not modelled, so a construct that
  depends on them renders as CommonMark here.
