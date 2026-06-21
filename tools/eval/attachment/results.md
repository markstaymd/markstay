# Attachment-survival eval results

Realistic docs: doc1, doc2  |  adversarial fixture: fixtures/near_dups.md  |  operators: reorder, edit_in_place, heavy_paraphrase, split, merge, delete, insert, decoy, clone  |  threshold 0.5, margin 0.05

Each cell annotates a doc, applies one deterministic edit with known ground truth, strips (or keeps) markers, and asks the resolver to re-attach every original id. The headline case is **markers stripped** (the AI-regeneration failure mode), where the resolver cannot use the id token and must recover from hash + quote alone. Outcomes: *correct* (right block), *wrong* (a false reattachment), *missed* (safely gave up on a recoverable block), *detach✓* (correctly gave up on a deleted block). `wrong` is the dangerous outcome the spec's 'surface, don't silently reattach' rule exists to prevent.


# Part 1: realistic documents (lexically distinct blocks)


## Markers stripped (hash + quote recovery)

| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |
|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|
| reorder | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| edit_in_place | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| heavy_paraphrase | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| split | 20 | 19 | 0 | 1 | 0 | 0 |  95% |   0% |
| merge | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| delete | 20 | 18 | 0 | 0 | 2 | 0 | 100% |   0% |
| insert | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| decoy | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| clone | 20 | 18 | 0 | 2 | 0 | 0 |  90% |   0% |
| **all** | 180 | 175 | 0 | 3 | 2 | 0 | ** 98%** | **  0%** |

## Markers kept (sanity: id token present -> trivial)

| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |
|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|
| reorder | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| edit_in_place | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| heavy_paraphrase | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| split | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| merge | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| delete | 20 | 18 | 0 | 0 | 2 | 0 | 100% |   0% |
| insert | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| decoy | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| clone | 20 | 20 | 0 | 0 | 0 | 0 | 100% |   0% |
| **all** | 180 | 178 | 0 | 0 | 2 | 0 | **100%** | **  0%** |

## Which tier did the work (markers stripped)

| Tier | ids resolved | share | what it recovers |
|------|-------------:|------:|------------------|
| marker | 0 |   0% | id token survived (n/a here, stripped) |
| hash | 146 |  81% | body unchanged, just moved (exact) |
| quote | 29 |  16% | body drifted: paraphrase / split / merge (fuzzy) |
| detached | 5 |   3% | no confident match: deleted or ambiguous |

# Part 2: adversarial fixture (near-duplicate blocks)

Blocks that share most of their wording and differ by a single token (a stage name, a number). This is where content-based recovery is genuinely dangerous: an edit to one block can make a pristine *twin* the closest match. Markers stripped throughout.


## Per edit, guard on (margin 0.05)

| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |
|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|
| reorder | 8 | 8 | 0 | 0 | 0 | 0 | 100% |   0% |
| edit_in_place | 8 | 5 | 1 | 2 | 0 | 0 |  62% |  12% |
| heavy_paraphrase | 8 | 7 | 0 | 1 | 0 | 0 |  88% |   0% |
| split | 8 | 8 | 0 | 0 | 0 | 0 | 100% |   0% |
| merge | 8 | 6 | 2 | 0 | 0 | 0 |  75% |  25% |
| delete | 8 | 7 | 0 | 0 | 1 | 0 | 100% |   0% |
| insert | 8 | 8 | 0 | 0 | 0 | 0 | 100% |   0% |
| decoy | 8 | 7 | 0 | 1 | 0 | 0 |  88% |   0% |
| clone | 8 | 7 | 0 | 1 | 0 | 0 |  88% |   0% |
| **all** | 72 | 63 | 3 | 5 | 1 | 0 | ** 89%** | **  4%** |

## Margin-guard ablation (the guard's whole job)

Same adversarial cases, aggregated over all operators, with the runner-up margin requirement off vs on. The guard refuses a quote recovery unless there is a *clear* winner, trading recall (more safe *missed*) for fewer false reattachments.

| margin | recovery | false-rate | correct | wrong | missed | detach✓ |
|-------:|---------:|-----------:|--------:|------:|-------:|--------:|
| 0.0 |  93% |   8% | 66 | 5 | 0 | 0 |
| 0.05 |  89% |   4% | 63 | 3 | 5 | 1 |
