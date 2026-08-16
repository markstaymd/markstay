# Heading path as recovery evidence: the arms

Every number here is the **markers-stripped** case (the AI-regeneration failure mode), threshold 0.5, margin 0.05. Intervals are 95% Clopper-Pearson.


| Arm | Clamp | Heading | Size | Gate |
|---|---|---|--:|---|
| A | kept | off | - | - |
| A' | lifted | off | - | - |
| B06 | lifted | bonus | 0.06 | threshold |
| B06c | kept | bonus | 0.06 | threshold |
| B12 | lifted | bonus | 0.12 | threshold |
| B12c | kept | bonus | 0.12 | threshold |
| B12u | lifted | bonus | 0.12 | 0.0 |
| B12cu | kept | bonus | 0.12 | 0.0 |
| D06c | kept | penalty | 0.06 | threshold |
| D12c | kept | penalty | 0.12 | threshold |
| D12 | lifted | penalty | 0.12 | threshold |
| C | lifted | filter | - | - |
| Cc | kept | filter | - | - |

`A` is the shipped resolver. A gated preference applies only to a candidate whose body already clears the commit threshold, so it can reorder qualifying candidates but can never lift a weak body match over the bar; the `u` arms drop that gate, which is the form the cross-section audit measured. The `D` arms are **post-hoc**: see the note in this module's source for why a penalty on mismatched candidates is not the same experiment as a bonus on matched ones.


## cross-section fixture  (the adversarial target)

The **pre-reg** column excludes `cross_section_move_edit`, added after the arms had already run. Lead with it; the post-hoc operator is evidence for the veto it was built for, not for a headline recovery number.

| Arm | n | recovery | 95% CI | pre-reg | false attach | 95% CI | detach |
|-----|--:|---------:|--------|--------:|-------------:|--------|-------:|
| A | 616 | 73.6% | [69.9, 77.1] | 73.5% | 0.6% (4) | [0.2, 1.7] | 25.7% |
| A' | 616 | 73.9% | [70.3, 77.4] | 73.9% | 0.8% (5) | [0.3, 1.9] | 25.2% |
| B06 | 616 | 95.1% | [93.1, 96.7] | 94.7% | 0.8% (5) | [0.3, 1.9] | 4.1% |
| B06c | 616 | 74.3% | [70.6, 77.7] | 74.2% | 0.6% (4) | [0.2, 1.7] | 25.1% |
| B12 | 616 | 95.1% | [93.1, 96.7] | 94.7% | 0.8% (5) | [0.3, 1.9] | 4.1% |
| B12c | 616 | 74.3% | [70.6, 77.7] | 74.2% | 0.6% (4) | [0.2, 1.7] | 25.1% |
| B12u | 616 | 95.1% | [93.1, 96.7] | 94.7% | 0.8% (5) | [0.3, 1.9] | 4.1% |
| B12cu | 616 | 74.3% | [70.6, 77.7] | 74.2% | 0.6% (4) | [0.2, 1.7] | 25.1% |
| D06c | 616 | 74.6% | [71.0, 78.0] | 74.6% | 0.6% (4) | [0.2, 1.7] | 24.8% |
| D12c | 616 | 80.6% | [77.3, 83.7] | 80.5% | 0.6% (4) | [0.2, 1.7] | 18.7% |
| D12 | 616 | 95.1% | [93.1, 96.7] | 94.7% | 0.8% (5) | [0.3, 1.9] | 4.1% |
| C | 616 | 95.0% | [92.9, 96.5] | 94.7% | 0.8% (5) | [0.3, 1.9] | 4.2% |
| Cc | 616 | 94.8% | [92.7, 96.4] | 94.6% | 0.6% (4) | [0.2, 1.7] | 4.6% |

The intervals assume independent trials and these are not: each corpus is a handful of documents put through every operator, so the same block is retried many times and the bounds are narrower than the evidence warrants. Read them as a floor on uncertainty.


### Case-by-case against the control (cross-section fixture)

Ids arm A resolved correctly and this arm did not, and ids arm A handled safely that this arm attaches wrongly. An operator-level aggregate cannot show these: `cross_section_move` moves one block of ~44, so an arm can lose the case SPEC.md §2.2 is *about* and still improve the operator's number.

| Arm | recoveries lost | of those, by operator | new false attachments |
|-----|----------------:|------------------------|----------------------:|
| A | 0 | - | 0 |
| A' | 0 | - | 0 |
| B06 | 0 | - | 0 |
| B06c | 0 | - | 0 |
| B12 | 0 | - | 0 |
| B12c | 0 | - | 0 |
| B12u | 0 | - | 0 |
| B12cu | 0 | - | 0 |
| D06c | 0 | - | 0 |
| D12c | 0 | - | 0 |
| D12 | 0 | - | 0 |
| C | 3 | cross_section_move_edit 1, heavy_paraphrase 2 | 0 |
| Cc | 3 | cross_section_move_edit 1, heavy_paraphrase 2 | 0 |

### Per-operator vetoes (cross-section fixture)

An aggregate can improve while a whole class fails, and the failures in this eval concentrate rather than spread. Cells are recovery / false attachment; **bold** marks a regression against arm A.

| Arm | edit_in_place | clone | cross_section_move | cross_section_move_edit | section_move | heading_rename | heading_delete |
|---|---|---|---|---|---|---|---|
| A | 72.7% / 4.5% | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| A' | **75.0% / 6.8%** | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| B06 | **90.9% / 6.8%** | 97.7% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 77.3% / 4.5% | 100.0% / 0.0% |
| B06c | 77.3% / 4.5% | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| B12 | **90.9% / 6.8%** | 97.7% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 77.3% / 4.5% | 100.0% / 0.0% |
| B12c | 77.3% / 4.5% | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| B12u | **90.9% / 6.8%** | 97.7% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 77.3% / 4.5% | 100.0% / 0.0% |
| B12cu | 77.3% / 4.5% | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| D06c | 77.3% / 4.5% | 72.7% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 75.0% / 0.0% | 77.3% / 4.5% | 74.4% / 0.0% |
| D12c | 84.1% / 4.5% | 79.5% / 0.0% | 81.8% / 0.0% | 81.8% / 0.0% | 81.8% / 0.0% | 77.3% / 4.5% | 81.4% / 0.0% |
| D12 | **90.9% / 6.8%** | 97.7% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 100.0% / 0.0% | 77.3% / 4.5% | 100.0% / 0.0% |
| C | **90.9% / 6.8%** | 97.7% / 0.0% | 100.0% / 0.0% | 97.7% / 0.0% | 100.0% / 0.0% | 79.5% / 4.5% | 100.0% / 0.0% |
| Cc | 90.9% / 4.5% | 97.7% / 0.0% | 100.0% / 0.0% | 97.7% / 0.0% | 100.0% / 0.0% | 79.5% / 4.5% | 100.0% / 0.0% |

What each one guards: `edit_in_place` drift on one twin of a pair; `clone` within-section twins; `cross_section_move` a block that changed section (SPEC.md §2.2); `cross_section_move_edit` the same block, drifted, so it reaches tier 3; `section_move` a whole section relocated; `heading_rename` headings reworded, prose untouched; `heading_delete` a heading deleted, its section absorbed.


## near_dups  (negative control (single-section twins))

| Arm | n | recovery | 95% CI | pre-reg | false attach | 95% CI | detach |
|-----|--:|---------:|--------|--------:|-------------:|--------|-------:|
| A | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| A' | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| B06 | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| B06c | 72 | 85.9% | [75.6, 93.0] | 85.9% | 2.8% (2) | [0.3, 9.7] | 11.3% |
| B12 | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| B12c | 72 | 83.1% | [72.3, 91.0] | 83.1% | 2.8% (2) | [0.3, 9.7] | 14.1% |
| B12u | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| B12cu | 72 | 83.1% | [72.3, 91.0] | 83.1% | 2.8% (2) | [0.3, 9.7] | 14.1% |
| D06c | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| D12c | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| D12 | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| C | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |
| Cc | 72 | 90.1% | [80.7, 95.9] | 90.1% | 2.8% (2) | [0.3, 9.7] | 7.0% |

The intervals assume independent trials and these are not: each corpus is a handful of documents put through every operator, so the same block is retried many times and the bounds are narrower than the evidence warrants. Read them as a floor on uncertainty.


### Case-by-case against the control (near_dups)

Ids arm A resolved correctly and this arm did not, and ids arm A handled safely that this arm attaches wrongly. An operator-level aggregate cannot show these: `cross_section_move` moves one block of ~44, so an arm can lose the case SPEC.md §2.2 is *about* and still improve the operator's number.

| Arm | recoveries lost | of those, by operator | new false attachments |
|-----|----------------:|------------------------|----------------------:|
| A | 0 | - | 0 |
| A' | 0 | - | 0 |
| B06 | 0 | - | 0 |
| B06c | 3 | heavy_paraphrase 3 | 0 |
| B12 | 0 | - | 0 |
| B12c | 5 | heavy_paraphrase 5 | 0 |
| B12u | 0 | - | 0 |
| B12cu | 5 | heavy_paraphrase 5 | 0 |
| D06c | 0 | - | 0 |
| D12c | 0 | - | 0 |
| D12 | 0 | - | 0 |
| C | 0 | - | 0 |
| Cc | 0 | - | 0 |

### Per-operator vetoes (near_dups)

An aggregate can improve while a whole class fails, and the failures in this eval concentrate rather than spread. Cells are recovery / false attachment; **bold** marks a regression against arm A.

| Arm | edit_in_place | clone |
|---|---|---|
| A | 62.5% / 0.0% | 87.5% / 0.0% |
| A' | 62.5% / 0.0% | 87.5% / 0.0% |
| B06 | 62.5% / 0.0% | 87.5% / 0.0% |
| B06c | 62.5% / 0.0% | 87.5% / 0.0% |
| B12 | 62.5% / 0.0% | 87.5% / 0.0% |
| B12c | 62.5% / 0.0% | 87.5% / 0.0% |
| B12u | 62.5% / 0.0% | 87.5% / 0.0% |
| B12cu | 62.5% / 0.0% | 87.5% / 0.0% |
| D06c | 62.5% / 0.0% | 87.5% / 0.0% |
| D12c | 62.5% / 0.0% | 87.5% / 0.0% |
| D12 | 62.5% / 0.0% | 87.5% / 0.0% |
| C | 62.5% / 0.0% | 87.5% / 0.0% |
| Cc | 62.5% / 0.0% | 87.5% / 0.0% |

What each one guards: `edit_in_place` drift on one twin of a pair; `clone` within-section twins.


## distinct prose  (regression guard)

| Arm | n | recovery | 95% CI | pre-reg | false attach | 95% CI | detach |
|-----|--:|---------:|--------|--------:|-------------:|--------|-------:|
| A | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| A' | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| B06 | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| B06c | 180 | 98.3% | [95.2, 99.7] | 98.3% | 0.0% (0) | [0.0, 2.0] | 1.7% |
| B12 | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| B12c | 180 | 97.8% | [94.3, 99.4] | 97.8% | 0.0% (0) | [0.0, 2.0] | 2.2% |
| B12u | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| B12cu | 180 | 97.8% | [94.3, 99.4] | 97.8% | 0.0% (0) | [0.0, 2.0] | 2.2% |
| D06c | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| D12c | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| D12 | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| C | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |
| Cc | 180 | 98.9% | [96.0, 99.9] | 98.9% | 0.0% (0) | [0.0, 2.0] | 1.1% |

The intervals assume independent trials and these are not: each corpus is a handful of documents put through every operator, so the same block is retried many times and the bounds are narrower than the evidence warrants. Read them as a floor on uncertainty.


### Case-by-case against the control (distinct prose)

Ids arm A resolved correctly and this arm did not, and ids arm A handled safely that this arm attaches wrongly. An operator-level aggregate cannot show these: `cross_section_move` moves one block of ~44, so an arm can lose the case SPEC.md §2.2 is *about* and still improve the operator's number.

| Arm | recoveries lost | of those, by operator | new false attachments |
|-----|----------------:|------------------------|----------------------:|
| A | 0 | - | 0 |
| A' | 0 | - | 0 |
| B06 | 0 | - | 0 |
| B06c | 1 | decoy 1 | 0 |
| B12 | 0 | - | 0 |
| B12c | 2 | decoy 2 | 0 |
| B12u | 0 | - | 0 |
| B12cu | 2 | decoy 2 | 0 |
| D06c | 0 | - | 0 |
| D12c | 0 | - | 0 |
| D12 | 0 | - | 0 |
| C | 0 | - | 0 |
| Cc | 0 | - | 0 |

### Per-operator vetoes (distinct prose)

An aggregate can improve while a whole class fails, and the failures in this eval concentrate rather than spread. Cells are recovery / false attachment; **bold** marks a regression against arm A.

| Arm | edit_in_place | clone |
|---|---|---|
| A | 100.0% / 0.0% | 90.0% / 0.0% |
| A' | 100.0% / 0.0% | 90.0% / 0.0% |
| B06 | 100.0% / 0.0% | 90.0% / 0.0% |
| B06c | 100.0% / 0.0% | 90.0% / 0.0% |
| B12 | 100.0% / 0.0% | 90.0% / 0.0% |
| B12c | 100.0% / 0.0% | 90.0% / 0.0% |
| B12u | 100.0% / 0.0% | 90.0% / 0.0% |
| B12cu | 100.0% / 0.0% | 90.0% / 0.0% |
| D06c | 100.0% / 0.0% | 90.0% / 0.0% |
| D12c | 100.0% / 0.0% | 90.0% / 0.0% |
| D12 | 100.0% / 0.0% | 90.0% / 0.0% |
| C | 100.0% / 0.0% | 90.0% / 0.0% |
| Cc | 100.0% / 0.0% | 90.0% / 0.0% |

What each one guards: `edit_in_place` drift on one twin of a pair; `clone` within-section twins.


## no headings  (empty-path guard (doc1, headings removed))

| Arm | n | recovery | 95% CI | pre-reg | false attach | 95% CI | detach |
|-----|--:|---------:|--------|--------:|-------------:|--------|-------:|
| A | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| A' | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B06 | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B06c | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B12 | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B12c | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B12u | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| B12cu | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| D06c | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| D12c | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| D12 | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| C | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |
| Cc | 81 | 98.8% | [93.2, 100.0] | 98.8% | 0.0% (0) | [0.0, 4.5] | 1.2% |

The intervals assume independent trials and these are not: each corpus is a handful of documents put through every operator, so the same block is retried many times and the bounds are narrower than the evidence warrants. Read them as a floor on uncertainty.


### Case-by-case against the control (no headings)

Ids arm A resolved correctly and this arm did not, and ids arm A handled safely that this arm attaches wrongly. An operator-level aggregate cannot show these: `cross_section_move` moves one block of ~44, so an arm can lose the case SPEC.md §2.2 is *about* and still improve the operator's number.

| Arm | recoveries lost | of those, by operator | new false attachments |
|-----|----------------:|------------------------|----------------------:|
| A | 0 | - | 0 |
| A' | 0 | - | 0 |
| B06 | 0 | - | 0 |
| B06c | 0 | - | 0 |
| B12 | 0 | - | 0 |
| B12c | 0 | - | 0 |
| B12u | 0 | - | 0 |
| B12cu | 0 | - | 0 |
| D06c | 0 | - | 0 |
| D12c | 0 | - | 0 |
| D12 | 0 | - | 0 |
| C | 0 | - | 0 |
| Cc | 0 | - | 0 |

### Per-operator vetoes (no headings)

An aggregate can improve while a whole class fails, and the failures in this eval concentrate rather than spread. Cells are recovery / false attachment; **bold** marks a regression against arm A.

| Arm | edit_in_place | clone |
|---|---|---|
| A | 100.0% / 0.0% | 88.9% / 0.0% |
| A' | 100.0% / 0.0% | 88.9% / 0.0% |
| B06 | 100.0% / 0.0% | 88.9% / 0.0% |
| B06c | 100.0% / 0.0% | 88.9% / 0.0% |
| B12 | 100.0% / 0.0% | 88.9% / 0.0% |
| B12c | 100.0% / 0.0% | 88.9% / 0.0% |
| B12u | 100.0% / 0.0% | 88.9% / 0.0% |
| B12cu | 100.0% / 0.0% | 88.9% / 0.0% |
| D06c | 100.0% / 0.0% | 88.9% / 0.0% |
| D12c | 100.0% / 0.0% | 88.9% / 0.0% |
| D12 | 100.0% / 0.0% | 88.9% / 0.0% |
| C | 100.0% / 0.0% | 88.9% / 0.0% |
| Cc | 100.0% / 0.0% | 88.9% / 0.0% |

What each one guards: `edit_in_place` drift on one twin of a pair; `clone` within-section twins.

