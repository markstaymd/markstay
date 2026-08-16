# Cross-section fixture: control baseline

Fixture: `fixtures/cross_section_dups.md`  |  operators: 14 (5 of them structural)  |  threshold 0.5, margin 0.05  |  markers stripped

Recorded **before** any heading-path arm is written, so a later arm is compared against a number that was fixed in advance. The structural operators are the half the older fixtures cannot express: `cross_section_move` and `heading_delete` change a block's section while keeping its text, which is the cost side of treating section position as evidence, and `SPEC.md` §2.2 requires a stay to survive both.


## What the fixture contains

| | count |
|---|---:|
| content blocks | 44 |
| distinct heading paths | 18 |
| blocks with a **cross-section** rival at or over threshold | 27 (**378** resolutions) |
| blocks whose only rivals are **same-section** (negative control) | 7 (98 resolutions) |
| blocks with no rival at all | 10 |

The relevant count is the cross-section one: a clean run can only certify the project's ~1% false-attach bar at roughly 300 or more (`results_item.md`), and the total is not a substitute for it.


## Per operator (markers stripped)

| Edit | n | correct | wrong | missed | detach✓ | false-attach | recovery | false-rate |
|------|--:|--------:|------:|-------:|--------:|-------------:|---------:|-----------:|
| reorder | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| edit_in_place | 44 | 32 | 2 | 10 | 0 | 0 |  73% |   5% |
| heavy_paraphrase | 44 | 28 | 0 | 16 | 0 | 0 |  64% |   0% |
| split | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| merge | 44 | 32 | 0 | 12 | 0 | 0 |  73% |   0% |
| delete | 44 | 32 | 0 | 11 | 1 | 0 |  74% |   0% |
| insert | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| decoy | 44 | 32 | 0 | 12 | 0 | 0 |  73% |   0% |
| clone | 44 | 32 | 0 | 12 | 0 | 0 |  73% |   0% |
| cross_section_move | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| cross_section_move_edit | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| section_move | 44 | 33 | 0 | 11 | 0 | 0 |  75% |   0% |
| heading_rename | 44 | 34 | 2 | 8 | 0 | 0 |  77% |   5% |
| heading_delete | 44 | 32 | 0 | 11 | 1 | 0 |  74% |   0% |
| **all** | 616 | 452 | 4 | 158 | 2 | 0 | ** 74%** | **  1%** |

Control: ** 74% recovery,   1% false attachment** over 616 resolutions.

