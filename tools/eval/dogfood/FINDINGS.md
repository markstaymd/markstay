# Dogfood findings: public corpus

This is the dogfood study on public documentation corpora, so the evidence can be
cited and re-run without exposing any private content. The corpus, harness, and
per-cell results all ship in this directory; see `README.md` to reproduce.

The two public corpora are:

- **FastAPI docs**, 12 sampled pages under `corpus/fastapi/` (from
  `github.com/fastapi/fastapi`, `docs/en/docs`, at the pinned commit in
  `corpus/manifest.json`), including
  `advanced/path-operation-advanced-configuration.md`,
  `tutorial/body-nested-models.md`, and `advanced/advanced-dependencies.md`.
- **The Rust Book**, 12 sampled chapters under `corpus/rust-book/` (from
  `github.com/rust-lang/book`, `src`, pinned commit in `corpus/manifest.json`),
  including `ch03-01-variables-and-mutability.md`,
  `ch07-02-defining-modules-to-control-scope-and-privacy.md`, and
  `ch20-04-advanced-functions-and-closures.md`.

Both were run through the same harness: `append`, `status`, and `consolidate` tasks;
`sonnet` and `haiku`; naive and section 11 instructed arms. The per-corpus tables are
in `results.md`.

## What replicated

**1. Append/status are safe, consolidate is the risk.** Across the two public corpora,
`append` never dropped a section and never stripped a marker. Rust Book `status` was
also clean. FastAPI `status` did show some loss: 19 real drops and 89 marker strips,
which makes FastAPI a harder corpus than the Rust Book for routine status refreshes.
The main shape: almost all loss lives in `consolidate`, the aggressive full-document
rewrite.

| task | cells | stays | content drops | marker strips | blocked | guard | nag |
|------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| append | 96 | 5808 | 0 | 0 | 0 | 0 | 0 |
| status | 96 | 5808 | 19 | 89 | 30 | 11 | 19 |
| consolidate | 96 | 5808 | 290 | 1435 | 83 | 53 | 30 |

**2. The preservation instruction is the lever.** It did not zero real drops on the
public corpora, but it cut them hard:

| corpus | naive drops | instructed drops | drop reduction | naive strips | instructed strips | strip reduction |
|--------|------------:|-----------------:|---------------:|-------------:|------------------:|----------------:|
| FastAPI | 173 | 47 | 73% | 870 | 240 | 72% |
| Rust Book | 82 | 7 | 91% | 366 | 48 | 87% |

That is the important replication: the section 11 instruction is the mechanism that
keeps block ids stable through LLM edits. The post-edit catch is a backstop, not the
main control.

**3. Haiku is much noisier than sonnet, but the shape is the same.** Haiku produced
234 public-corpus content drops and 1025 marker strips; sonnet produced 75 content
drops and 499 strips. Model tier changes rate, not failure mode: the loss is still
concentrated in full regeneration, and the instruction still cuts both drops and
strips.

**4. Seed density decides whether the catch is a guard.** FastAPI blocked 77 cells,
with a 58% guard / 42% nag split. Rust Book blocked 36 cells, with a 53% guard / 47%
nag split. These corpora are densely seeded (a `stay:` on every block), which is what
turns a block drop into a visible `DROPPED_ID`. The seed-density control below isolates
that effect.

## Seed-density refinement

Question: is the guard-vs-nag split driven by the corpus, or by how densely it is
seeded?

Method: hold the same 12 Rust Book documents fixed and vary only `stay:` density. The
dense copy is stamped at blank-line block granularity (every block gets a stay). The
sparse copy is pruned from that dense copy, keeping only markers attached to ATX
headings. Documents where the blank-line stamp landed inside a fenced code block were
skipped, matching the known stamping gap below. (The dense copy is the bundled
`corpus/rust-book/`; the sparse copy is that same corpus with non-heading markers
removed.)

Run shape: `consolidate` only; `sonnet,haiku`; `naive,instructed`; 12 docs; 5000-word
cap; 16000 max output tokens. Dense completed 48/48 cells. Sparse completed 47/48
cells; the missing cell was `haiku` / `doc06` / `naive`, dropped by a transient
provider error after the other cells completed.

| seed density | cells scored | stays scored | content drops | marker strips | blocked | guard | nag | guard/nag split |
|--------------|-------------:|-------------:|--------------:|--------------:|--------:|------:|----:|-----------------|
| dense, all-block | 48 | 4164 | 143 | 1236 | 43 | 22 | 21 | 51% / 49% |
| sparse, headings-only | 47 | 345 | 0 | 36 | 5 | 0 | 5 | 0% / 100% |

Result: seed density is the driver. On the same documents, sparse heading-only seeding
makes every blocked cell a marker strip on content the judge found surviving (the
catch is pure nag). Dense all-block seeding flips the catch into a real guard about
half the time: 22 blocked cells caught at least one real content drop, and 143
block-level drops were visible to the hook.

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

## Private-corpus corroboration (not shipped)

A separate run used the same harness over a private documentation repository of living
tracking docs, seeded headings-only. Those source documents are not public, so that
corpus is not shipped here; only the shape is reported. It corroborates the public
result: routine appends/status were mostly safe, aggressive consolidation caused the
real section drops, the preservation instruction eliminated real drops and cut marker
stripping by about 96%, and at headings-only density the catch was mostly a nag. That
matches the sparse row of the seed-density table above.

## Stamping gap

The seed-density prep exposed a current implementation gap: neither production stamper
does CommonMark tree attachment yet. The dependency-free blank-line stamper can place
markers inside code fences that contain blank lines, so those files had to be skipped
for the dense control. That implementation work is tracked separately.

Spec v1.1 already defines optional CommonMark-tree attachment. The implementation work
is to make the stampers use that path when requested, so fenced code blocks and loose
lists are stamped as CommonMark blocks instead of blank-line chunks.
