# Findings: dogfooding markstay on real docs

The marker-survival study asks whether LLMs keep a `stay:` token at all. This study
asks the next question: when an agent updates real documentation, does a stay actually
help preserve the block it names?

The public run uses two open corpora:

- **FastAPI docs**, 12 sampled pages.
- **The Rust Book**, 12 sampled chapters.

Each document was seeded with stays, then sent through realistic update tasks:
`append`, `status`, and `consolidate`. Each cell ran across Claude Haiku and Sonnet,
with and without the section 11 preservation instruction. After the model returned a
full rewritten document, the markstay linter compared `before` and `after`. Every
dropped id was judged as either a real **content drop** or a **marker strip** where the
content survived but the marker did not.

!!! question "The question"
    On real documentation updates, how often does an LLM drop a tracked block, is the
    post-edit catch a useful guard or mostly friction, and how much does the
    preservation instruction change the outcome?

## Public corpus results

Across FastAPI and the Rust Book together: **288 cells, 17,424 seeded stays**.

| corpus | cells | stays | content drops | marker strips | blocked | guard/nag split |
|--------|------:|------:|--------------:|--------------:|--------:|-----------------|
| FastAPI | 144 | 11,784 | 220 | 1110 | 77 | 58% / 42% |
| Rust Book | 144 | 5640 | 89 | 414 | 36 | 53% / 47% |

**The shape is clear: routine appends are safe, full regeneration is risky.**

| task | cells | stays | content drops | marker strips | blocked | guard | nag |
|------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| append | 96 | 5808 | 0 | 0 | 0 | 0 | 0 |
| status | 96 | 5808 | 19 | 89 | 30 | 11 | 19 |
| consolidate | 96 | 5808 | 290 | 1435 | 83 | 53 | 30 |

`append` never dropped a section and never stripped a marker. Rust Book `status` was
also clean; FastAPI `status` was harder, with 19 content drops. The dominant risk is
still the aggressive `consolidate` task, which asks the model to rewrite and merge the
document as a whole.

## The instruction is the main control

The preservation instruction tells the editing agent to preserve every `stay:` marker
with its block. It is the mechanism that keeps ids stable; the linter catch is a
backstop after the fact.

| corpus | naive drops | instructed drops | drop reduction | naive strips | instructed strips | strip reduction |
|--------|------------:|-----------------:|---------------:|-------------:|------------------:|----------------:|
| FastAPI | 173 | 47 | 73% | 870 | 240 | 72% |
| Rust Book | 82 | 7 | 91% | 366 | 48 | 87% |

This does not mean the instruction makes full-document regeneration harmless. It means
that, across public docs and two models, the instruction is the strongest lever by far.
It cuts both real drops and marker-only strips. The remaining catch is still valuable,
but it should be treated as a backstop for risky rewrites, not the thing you rely on
first.

Model choice changes the rate, not the failure mode. Haiku produced 234 content drops
and 1025 marker strips across the public runs; Sonnet produced 75 drops and 499 strips.
Both follow the same pattern: routine edits are quiet, full regeneration is where the
risk lives, and the instruction cuts the damage.

## Seed density decides whether the catch is a guard

The Rust Book was also run as a seed-density control. The documents stayed fixed; only
marker density changed.

| seed density | cells scored | stays scored | content drops | marker strips | blocked | guard | nag | guard/nag split |
|--------------|-------------:|-------------:|--------------:|--------------:|--------:|------:|----:|-----------------|
| dense, all-block | 48 | 4164 | 143 | 1236 | 43 | 22 | 21 | 51% / 49% |
| sparse, headings-only | 47 | 345 | 0 | 36 | 5 | 0 | 5 | 0% / 100% |

This is the most important refinement. Headings-only seeding is quiet and useful when
section anchors are enough, but it mostly protects header identity. If a paragraph
under the heading disappears, there is no paragraph stay to drop. The linter can only
warn about hash drift on the surrounding section.

Dense block-level seeding creates the signal that turns the linter into a real guard:
when a paragraph block disappears, its own id disappears too. The tradeoff is more
source noise and more friction under full regeneration.

## Private-corpus corroboration

A separate run on a private documentation repository of living tracking docs used the
same harness shape, but those source documents are not public. The reported metrics
corroborate the public-corpus shape at headings-only granularity:

- routine appends and status updates were mostly safe;
- aggressive full-document consolidation caused the real section drops;
- the preservation instruction eliminated real section drops in that corpus and cut
  marker stripping by about 96%;
- at headings-only density, the catch was mostly a nag, because many blocked commits
  were marker strips on content that survived.

The private run is useful because it uses actively maintained tracking docs. The public
FastAPI and Rust Book runs are the evidence to cite and inspect: the corpus, harness,
and every per-cell result ship in
[`tools/eval/dogfood/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/dogfood).

## The boundary: rows and bullets

markstay v1 protects blocks. A Markdown table is one block. A tight list is one block.
That means a dropped table row or tight-list bullet can leave the block's stay in place
and only produce non-blocking hash drift.

A companion within-collection run measured this directly on row- and bullet-heavy
tracking docs: **922 of 10,608 rows and bullets, 9%, were dropped**, roughly 30x the
private section-drop rate. The catch never blocked because of a row or bullet drop.

There is an **opt-in** count-diff catch for that loss (`--check-collections`): it blocks
when a kept stay's table or list ends up with fewer rows/bullets than it started with.
Measured precision is the reason it is opt-in, not a default: it is accurate where items
genuinely churn (≈75% on status refreshes, ≈94% on consolidations) but near-pure noise
on append/prose edits (≈7%), and it gets *noisier* on the more capable model (84% on
Haiku, 42% on Sonnet). A raw count cannot tell a benign reflow, two bullets merged into
one, a row reworded, from a real deletion, and fluent models reflow more. It also cannot
see a 1-for-1 row swap. So it is a targeted backstop for churn-heavy trackers, not a
general guard, and true per-row identity still needs the structural fix below.

The practical fix for bullets is structural: make each durable item its own block.

```text
LOOSE list, drop one item:  DROPPED_ID  (blocking, caught)
TIGHT list, drop one item:  HASH_DRIFT  (non-blocking, silent)
```

Tables do not have the same escape hatch under the current spec. A Markdown table row
is not its own block, so per-row identity needs either restructuring into per-row
blocks or a future intra-block addressing extension.

## Conclusions

- **Install the preservation instruction.** It is the active mechanism that keeps
  block ids attached during LLM edits.
- **Keep the linter catch, but understand what it is catching.** Dense block-level
  seeding can make it a real content-loss guard. Sparse headings-only seeding makes it
  a low-noise section identity layer and a nag-prone backstop.
- **Seed for the durable unit you care about.** If the unit is a paragraph or loose
  list item, give that block a stay. If the unit is a table row, markstay does not
  protect it yet.

## Limitations

- The simulation forces full-document regeneration. A real agent using surgical edits
  should strip fewer unrelated markers.
- The content-drop / marker-strip split is judge-based. The structural linter findings
  are exact; the semantic "did this section survive?" call is an LLM judgment.
- The public-corpus run used two Claude models. The earlier marker-survival study
  covers more vendor families and shows the same broad instruction effect.

## Reproduce it

The corpus and the per-cell results ship in
[`tools/eval/dogfood/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/dogfood),
so the numbers above are inspectable with no clone, no network, and no API key, the
same way the marker-survival eval ships its `results.json`. A key is only needed to
re-run the models:

```bash
pip install markstay                  # the published stamper (or: npm install -g markstay)
python prepare_public_corpus.py       # rebuild corpus/ from the pinned upstream commits

export ANTHROPIC_API_KEY=...          # only needed to re-run the models
python run_dogfood.py --docs-dir corpus/fastapi   --sample 12 \
    --models sonnet,haiku --arms naive,instructed --preserve-file PRESERVE.md
python run_dogfood.py --docs-dir corpus/rust-book --sample 12 \
    --models sonnet,haiku --arms naive,instructed --preserve-file PRESERVE.md
```

The corpus is two pinned, stamped samples (FastAPI docs and the Rust Book; commits and
attribution in `corpus/manifest.json` and `corpus/NOTICE`). Stamping mints fresh ids
each run, so a regenerated corpus is structurally identical to the committed copy and
the results reproduce within model noise.
