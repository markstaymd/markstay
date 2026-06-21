# External dogfood simulation results

Mirrored summary tables from the public-corpus runs over the bundled `corpus/`
(`corpus/fastapi` and `corpus/rust-book`, rebuilt deterministically with
`prepare_public_corpus.py`).

Each cell asks a model to perform a realistic documentation update and return the
whole document, then runs the linter's regeneration diff. A `DROPPED_ID` is split by
an LLM judge into a real **content drop** or a **marker strip** on surviving content.
`naive` means no preservation instruction; `instructed` means the section 11
preservation instruction was prepended.

## FastAPI

Models: `sonnet,haiku`; arms: `naive,instructed`; tasks: `append`, `status`,
`consolidate`; docs sampled: 12.

Cells: 144 run, 144 ok, 0 failed, 0 excluded.

Headline:

- Section-drop propensity: 220 real content drops across 11,784 seeded stays, 2%.
- Catch outcome: 77 of 144 cells would be blocked by the hook, 53%.
- Guard/nag split of blocked commits: 58% guard / 42% nag.
- Marker-strip rate: 1110 markers stripped off surviving content across 11,784 stays,
  9%.
- Other findings: relocated 251, duplicated 0, benign hash-drift 2612.

By task:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| append | 48 | 3928 | 0 | 0 | 0 | 0 | 0 |
| status | 48 | 3928 | 19 | 89 | 30 | 11 | 19 |
| consolidate | 48 | 3928 | 201 | 1021 | 47 | 34 | 13 |

By arm:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| naive | 72 | 5892 | 173 | 870 | 38 | 25 | 13 |
| instructed | 72 | 5892 | 47 | 240 | 39 | 20 | 19 |

By model:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| haiku | 72 | 5892 | 150 | 712 | 44 | 25 | 19 |
| sonnet | 72 | 5892 | 70 | 398 | 33 | 20 | 13 |

By document:

| path | label | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|------|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| `advanced/path-operation-advanced-configuration.md` | doc01 | 12 | 840 | 20 | 103 | 8 | 4 | 4 |
| `advanced/additional-responses.md` | doc02 | 12 | 720 | 6 | 131 | 6 | 5 | 1 |
| `tutorial/extra-models.md` | doc03 | 12 | 984 | 25 | 52 | 5 | 2 | 3 |
| `tutorial/body.md` | doc04 | 12 | 840 | 3 | 46 | 7 | 2 | 5 |
| `tutorial/request-files.md` | doc05 | 12 | 948 | 17 | 101 | 7 | 4 | 3 |
| `tutorial/body-nested-models.md` | doc06 | 12 | 1056 | 19 | 93 | 8 | 5 | 3 |
| `how-to/custom-docs-ui-assets.md` | doc07 | 12 | 912 | 5 | 35 | 5 | 2 | 3 |
| `advanced/openapi-callbacks.md` | doc08 | 12 | 948 | 16 | 118 | 6 | 5 | 1 |
| `advanced/events.md` | doc09 | 12 | 960 | 29 | 108 | 6 | 3 | 3 |
| `fastapi-people.md` | doc10 | 12 | 1524 | 13 | 142 | 4 | 2 | 2 |
| `tutorial/schema-extra-example.md` | doc11 | 12 | 1080 | 51 | 115 | 8 | 7 | 1 |
| `advanced/advanced-dependencies.md` | doc12 | 12 | 972 | 16 | 66 | 7 | 4 | 3 |

## Rust Book

Models: `sonnet,haiku`; arms: `naive,instructed`; tasks: `append`, `status`,
`consolidate`; docs sampled: 12.

Cells: 144 run, 144 ok, 0 failed, 0 excluded.

Headline:

- Section-drop propensity: 89 real content drops across 5640 seeded stays, 2%.
- Catch outcome: 36 of 144 cells would be blocked by the hook, 25%.
- Guard/nag split of blocked commits: 53% guard / 47% nag.
- Marker-strip rate: 414 markers stripped off surviving content across 5640 stays,
  7%.
- Other findings: relocated 12, duplicated 0, benign hash-drift 2057.

By task:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| append | 48 | 1880 | 0 | 0 | 0 | 0 | 0 |
| status | 48 | 1880 | 0 | 0 | 0 | 0 | 0 |
| consolidate | 48 | 1880 | 89 | 414 | 36 | 19 | 17 |

By arm:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| naive | 72 | 2820 | 82 | 366 | 21 | 15 | 6 |
| instructed | 72 | 2820 | 7 | 48 | 15 | 4 | 11 |

By model:

| group | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| haiku | 72 | 2820 | 84 | 313 | 22 | 16 | 6 |
| sonnet | 72 | 2820 | 5 | 101 | 14 | 3 | 11 |

By document:

| path | label | cells | stays | content-drops | marker-strips | blocked | guard | nag |
|------|-------|------:|------:|--------------:|--------------:|--------:|------:|----:|
| `ch10-00-generics.md` | doc01 | 12 | 336 | 3 | 7 | 3 | 1 | 2 |
| `ch12-01-accepting-command-line-arguments.md` | doc02 | 12 | 348 | 3 | 57 | 3 | 2 | 1 |
| `ch01-01-installation.md` | doc03 | 12 | 564 | 6 | 92 | 4 | 3 | 1 |
| `ch06-03-if-let.md` | doc04 | 12 | 456 | 1 | 11 | 2 | 1 | 1 |
| `ch15-03-drop.md` | doc05 | 12 | 432 | 13 | 45 | 4 | 2 | 2 |
| `ch07-02-defining-modules-to-control-scope-and-privacy.md` | doc06 | 12 | 444 | 7 | 23 | 1 | 1 | 0 |
| `ch20-04-advanced-functions-and-closures.md` | doc07 | 12 | 552 | 5 | 56 | 4 | 2 | 2 |
| `ch09-01-unrecoverable-errors-with-panic.md` | doc08 | 12 | 372 | 1 | 12 | 3 | 1 | 2 |
| `ch18-01-what-is-oo.md` | doc09 | 12 | 348 | 2 | 33 | 4 | 2 | 2 |
| `ch11-02-running-tests.md` | doc10 | 12 | 612 | 27 | 20 | 2 | 1 | 1 |
| `ch13-03-improving-our-io-project.md` | doc11 | 12 | 648 | 10 | 22 | 3 | 2 | 1 |
| `ch03-01-variables-and-mutability.md` | doc12 | 12 | 528 | 11 | 36 | 3 | 1 | 2 |

## Seed-density control

The same 12 Rust Book documents were then held fixed while only marker density
changed. Dense means blank-line block granularity. Sparse means headings-only.

| seed density | cells scored | stays scored | content drops | marker strips | blocked | guard | nag | guard/nag split |
|--------------|-------------:|-------------:|--------------:|--------------:|--------:|------:|----:|-----------------|
| dense, all-block | 48 | 4164 | 143 | 1236 | 43 | 22 | 21 | 51% / 49% |
| sparse, headings-only | 47 | 345 | 0 | 36 | 5 | 0 | 5 | 0% / 100% |
