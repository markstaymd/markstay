# External dogfood findings: public corpus replication

This records dogfood runs on two public documentation corpora, so the evidence can be
cited and reproduced from a fresh clone. A separate run on a private corpus of living
tracking docs (not shipped) corroborates the same shape.

The two public corpora are:

- **FastAPI docs**, 12 sampled pages under `corpus/fastapi/`, including
  `advanced/path-operation-advanced-configuration.md`,
  `tutorial/body-nested-models.md`, and `advanced/advanced-dependencies.md`.
- **The Rust Book**, 12 sampled chapters under `corpus/rust-book/`, including
  `ch03-01-variables-and-mutability.md`,
  `ch07-02-defining-modules-to-control-scope-and-privacy.md`, and
  `ch20-04-advanced-functions-and-closures.md`.

The bundled `corpus/` is rebuilt deterministically by `prepare_public_corpus.py`
from pinned upstream commits (recorded in `corpus/manifest.json`); see `corpus/NOTICE`
for attribution.

Both were run through the same dogfood harness shape as the private tracker run:
`append`, `status`, and `consolidate` tasks; `sonnet` and `haiku`; naive and
section 11 instructed arms. The mirrored tables are in `results_external.md`.

## What replicated

**1. Append/status are safe, consolidate is the risk.** Across the two public corpora,
`append` never dropped a section and never stripped a marker. Rust Book `status` was
also clean. FastAPI `status` did show some loss: 19 real drops and 89 marker strips,
which makes FastAPI a harder corpus than the Rust Book for routine status refreshes.
The main shape still matches the private run: almost all loss lives in
`consolidate`, the aggressive full-document rewrite.

| task | cells | stays | content drops | marker strips | blocked | guard | nag |
|------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| append | 96 | 5808 | 0 | 0 | 0 | 0 | 0 |
| status | 96 | 5808 | 19 | 89 | 30 | 11 | 19 |
| consolidate | 96 | 5808 | 290 | 1435 | 83 | 53 | 30 |

**2. The preservation instruction is still the lever.** It did not zero real drops on
the public corpora the way it did on the private tracker corpus, but it cut them hard:

| corpus | naive drops | instructed drops | drop reduction | naive strips | instructed strips | strip reduction |
|--------|------------:|-----------------:|---------------:|-------------:|------------------:|----------------:|
| FastAPI | 173 | 47 | 73% | 870 | 240 | 72% |
| Rust Book | 82 | 7 | 91% | 366 | 48 | 87% |

That is the important external replication: the section 11 instruction is the
mechanism that keeps block ids stable through LLM edits. The post-edit catch is a
backstop, not the main control.

**3. Haiku is much noisier than sonnet, but the shape is the same.** Haiku produced
234 public-corpus content drops and 1025 marker strips; sonnet produced 75 content
drops and 499 strips. Model tier changes rate, not failure mode: the loss is still
concentrated in full regeneration, and the instruction still cuts both drops and
strips.

**4. The public corpora turn the catch into a real guard more often than the private
heading-only tracker run.** FastAPI blocked 77 cells, with a 58% guard / 42% nag split.
Rust Book blocked 36 cells, with a 53% guard / 47% nag split. That differs from the
private heading-only tracker run, where the catch was mostly a nag. The difference led
to the seed-density control below.

## Seed-density refinement

Question: did the private result, "the catch is mostly a nag", come from heading-only
seeding, or from the corpus itself?

Method: hold the same 12 bundled `corpus/rust-book/` chapters fixed and vary only
`stay:` density. The dense copy is the corpus as stamped (blank-line block
granularity); the sparse copy is pruned from it, keeping only markers attached to ATX
headings. Docs where the blank-line stamp landed inside a fenced code block were
skipped, matching the known stamping gap.

Run shape: `consolidate` only; `sonnet,haiku`; `naive,instructed`; 12 docs; 5000-word
cap; 16000 max output tokens. Dense completed 48/48 cells. Sparse completed 47/48
cells; the missing cell was `haiku` / `doc06` / `naive`, blocked by an Anthropic
low-credit error after the other cells completed.

| seed density | cells scored | stays scored | content drops | marker strips | blocked | guard | nag | guard/nag split |
|--------------|-------------:|-------------:|--------------:|--------------:|--------:|------:|----:|-----------------|
| dense, all-block | 48 | 4164 | 143 | 1236 | 43 | 22 | 21 | 51% / 49% |
| sparse, headings-only | 47 | 345 | 0 | 36 | 5 | 0 | 5 | 0% / 100% |

Result: seed density is the driver. On the same documents, sparse heading-only
seeding reproduces the private "nag" shape: every blocked sparse cell was a marker
strip on content the judge found surviving. Dense all-block seeding flips the catch
into a real guard about half the time: 22 blocked cells caught at least one real
content drop, and 143 block-level drops were visible to the hook.

Interpretation: heading-only markers are quieter and reduce raw blocked commits, but
they mostly protect header identity, not the paragraph-level content under those
headers. If a paragraph disappears while the heading remains, sparse seeding has no
paragraph stay to drop. Dense seeding is noisier in source and under full regeneration,
but it creates the signal that lets the section 11 catch distinguish a real content
deletion from a marker-only strip.

Adoption guidance: seed each durable block that must be preserved. Headings-only is a
reasonable low-noise mode when section anchors are enough, but it should be described
as a navigational identity layer and a nag-prone backstop, not as strong content-loss
protection.

## Stamping gap

The seed-density prep exposed a current implementation gap: neither production stamper
does CommonMark tree attachment yet. The dependency-free blank-line stamper can place
markers inside code fences that contain blank lines, so those files had to be skipped
for the dense control. That implementation work is tracked separately.

Spec v1.1 already defines optional CommonMark-tree attachment. The implementation work
is to make the stampers use that path when requested, so fenced code blocks and loose
lists are stamped as CommonMark blocks instead of blank-line chunks.
