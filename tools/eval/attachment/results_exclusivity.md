# Block-tier exclusivity and duplicated ids: the arms

Threshold 0.5, margin 0.05. Intervals are 95% Clopper-Pearson. Outcomes follow `run_attach_eval.py`: *misattached* is `wrong` plus `false_attach`, the outcomes §10's "surface, don't guess" rule exists to prevent. Every table except the partly-marked section and the last strips markers, so tier 1 never fires there and `absent` and `carriers` equal the control by construction.

| Arm | Rule |
|---|---|
| ladder | the v1.10 ladder, frozen in `ladder_v110.py` (control) |
| t2 | tier 2 exclusive, with historical uniqueness |
| t23 | tiers 2 and 3 exclusive (§9.2's discipline on blocks) |
| t23m | t23, but a tier-3 contest commits when every contender's quote is verbatim inside the block (the clean merge) |
| t23d | **post-hoc**: t23m, with the quotes at disjoint places in the block |
| t23dk | **post-hoc**: t23d, with claimed blocks kept as margin rivals at tier 3 (the block tiers chosen for v1.11) |
| absent | a marker on two or more blocks is treated as absent; tiers 2 and 3 run over the whole document |
| carriers | a marker on two or more blocks resolves only among its carriers, by hash then quote; never falls through |
| t23+carriers | t23 with the carriers rule at tier 1 |
| t23dk+carriers | **post-hoc**: t23dk with the carriers rule at tier 1 (the full form chosen for v1.11) |
| detach | copy table only: a marker on two or more blocks detaches the id |

## Closed world, existing operators

Every block stamped. The nine published operators on every corpus, plus the five section operators on the cross-section fixture.

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| t2 | 868 | 691 | 168 | 4 | 5 | 80.1% | [77.2, 82.7] | 0.5% | [0.1, 1.2] |
| t23 | 868 | 690 | 173 | 0 | 5 | 80.0% | [77.1, 82.6] | 0.0% | [0.0, 0.4] |
| t23m | 868 | 699 | 162 | 2 | 5 | 81.0% | [78.2, 83.6] | 0.2% | [0.0, 0.8] |
| t23d | 868 | 698 | 165 | 0 | 5 | 80.9% | [78.1, 83.5] | 0.0% | [0.0, 0.4] |
| t23dk | 868 | 690 | 173 | 0 | 5 | 80.0% | [77.1, 82.6] | 0.0% | [0.0, 0.4] |
| absent | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| carriers | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| t23+carriers | 868 | 690 | 173 | 0 | 5 | 80.0% | [77.1, 82.6] | 0.0% | [0.0, 0.4] |
| t23dk+carriers | 868 | 690 | 173 | 0 | 5 | 80.0% | [77.1, 82.6] | 0.0% | [0.0, 0.4] |

### distinct prose

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| t2 | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| t23 | 180 | 172 | 6 | 0 | 2 | 96.6% | [92.8, 98.8] | 0.0% | [0.0, 2.0] |
| t23m | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| t23d | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| t23dk | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| absent | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| carriers | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |
| t23+carriers | 180 | 172 | 6 | 0 | 2 | 96.6% | [92.8, 98.8] | 0.0% | [0.0, 2.0] |
| t23dk+carriers | 180 | 176 | 2 | 0 | 2 | 98.9% | [96.0, 99.9] | 0.0% | [0.0, 2.0] |

### near_dups

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 72 | 64 | 5 | 2 | 1 | 90.1% | [80.7, 95.9] | 2.8% | [0.3, 9.7] |
| t2 | 72 | 64 | 5 | 2 | 1 | 90.1% | [80.7, 95.9] | 2.8% | [0.3, 9.7] |
| t23 | 72 | 67 | 4 | 0 | 1 | 94.4% | [86.2, 98.4] | 0.0% | [0.0, 5.0] |
| t23m | 72 | 69 | 2 | 0 | 1 | 97.2% | [90.2, 99.7] | 0.0% | [0.0, 5.0] |
| t23d | 72 | 69 | 2 | 0 | 1 | 97.2% | [90.2, 99.7] | 0.0% | [0.0, 5.0] |
| t23dk | 72 | 64 | 7 | 0 | 1 | 90.1% | [80.7, 95.9] | 0.0% | [0.0, 5.0] |
| absent | 72 | 64 | 5 | 2 | 1 | 90.1% | [80.7, 95.9] | 2.8% | [0.3, 9.7] |
| carriers | 72 | 64 | 5 | 2 | 1 | 90.1% | [80.7, 95.9] | 2.8% | [0.3, 9.7] |
| t23+carriers | 72 | 67 | 4 | 0 | 1 | 94.4% | [86.2, 98.4] | 0.0% | [0.0, 5.0] |
| t23dk+carriers | 72 | 64 | 7 | 0 | 1 | 90.1% | [80.7, 95.9] | 0.0% | [0.0, 5.0] |

### cross-section fixture

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 616 | 452 | 158 | 4 | 2 | 73.6% | [69.9, 77.1] | 0.6% | [0.2, 1.7] |
| t2 | 616 | 451 | 161 | 2 | 2 | 73.5% | [69.8, 76.9] | 0.3% | [0.0, 1.2] |
| t23 | 616 | 451 | 163 | 0 | 2 | 73.5% | [69.8, 76.9] | 0.0% | [0.0, 0.6] |
| t23m | 616 | 454 | 158 | 2 | 2 | 73.9% | [70.3, 77.4] | 0.3% | [0.0, 1.2] |
| t23d | 616 | 453 | 161 | 0 | 2 | 73.8% | [70.1, 77.2] | 0.0% | [0.0, 0.6] |
| t23dk | 616 | 450 | 164 | 0 | 2 | 73.3% | [69.6, 76.8] | 0.0% | [0.0, 0.6] |
| absent | 616 | 452 | 158 | 4 | 2 | 73.6% | [69.9, 77.1] | 0.6% | [0.2, 1.7] |
| carriers | 616 | 452 | 158 | 4 | 2 | 73.6% | [69.9, 77.1] | 0.6% | [0.2, 1.7] |
| t23+carriers | 616 | 451 | 163 | 0 | 2 | 73.5% | [69.8, 76.9] | 0.0% | [0.0, 0.6] |
| t23dk+carriers | 616 | 450 | 164 | 0 | 2 | 73.3% | [69.6, 76.8] | 0.0% | [0.0, 0.6] |

### Per operator, where any arm differs

Cells are correct / missed / misattached / detach ok, pooled over every corpus.

| Operator | ladder | t2 | t23 | t23m | t23d | t23dk | absent | carriers | t23+carriers | t23dk+carriers |
|---|---|---|---|---|---|---|---|---|---|---|
| edit_in_place | 57/13/2/0 | 56/16/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 56/16/0/0 | 57/13/2/0 | 57/13/2/0 | 61/11/0/0 | 56/16/0/0 |
| merge | 58/12/2/0 | 58/12/2/0 | 53/19/0/0 | 61/11/0/0 | 61/11/0/0 | 58/14/0/0 | 58/12/2/0 | 58/12/2/0 | 53/19/0/0 | 58/14/0/0 |
| heading_rename | 34/8/2/0 | 34/8/2/0 | 33/11/0/0 | 34/8/2/0 | 33/11/0/0 | 33/11/0/0 | 34/8/2/0 | 34/8/2/0 | 33/11/0/0 | 33/11/0/0 |

### Case by case against the control

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 1 (edit_in_place 1) | 0 | 2 (edit_in_place 2) | 0 |
| t23 | 7 (edit_in_place 1, heading_rename 1, merge 5) | 5 (edit_in_place 5) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23m | 1 (edit_in_place 1) | 8 (edit_in_place 5, merge 3) | 4 (edit_in_place 2, merge 2) | 0 |
| t23d | 2 (edit_in_place 1, heading_rename 1) | 8 (edit_in_place 5, merge 3) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23dk | 2 (edit_in_place 1, heading_rename 1) | 0 | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 7 (edit_in_place 1, heading_rename 1, merge 5) | 5 (edit_in_place 5) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23dk+carriers | 2 (edit_in_place 1, heading_rename 1) | 0 | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |

### Every misattachment, by arm

| Arm | Corpus | Operator | Doc | Id | Outcome | Tier |
|---|---|---|---|---|---|---|
| ladder | near_dups | merge | d0 | `b1-5ba1` | wrong | quote |
| ladder | near_dups | merge | d0 | `b2-73ec` | wrong | quote |
| ladder | cross-section fixture | edit_in_place | d0 | `b29-6183` | wrong | hash |
| ladder | cross-section fixture | edit_in_place | d0 | `b39-6183` | wrong | hash |
| ladder | cross-section fixture | heading_rename | d0 | `b30-2189` | wrong | hash |
| ladder | cross-section fixture | heading_rename | d0 | `b40-2189` | wrong | hash |
| t2 | near_dups | merge | d0 | `b1-5ba1` | wrong | quote |
| t2 | near_dups | merge | d0 | `b2-73ec` | wrong | quote |
| t2 | cross-section fixture | heading_rename | d0 | `b30-2189` | wrong | quote |
| t2 | cross-section fixture | heading_rename | d0 | `b40-2189` | wrong | quote |
| t23m | cross-section fixture | heading_rename | d0 | `b30-2189` | wrong | quote |
| t23m | cross-section fixture | heading_rename | d0 | `b40-2189` | wrong | quote |
| absent | near_dups | merge | d0 | `b1-5ba1` | wrong | quote |
| absent | near_dups | merge | d0 | `b2-73ec` | wrong | quote |
| absent | cross-section fixture | edit_in_place | d0 | `b29-6183` | wrong | hash |
| absent | cross-section fixture | edit_in_place | d0 | `b39-6183` | wrong | hash |
| absent | cross-section fixture | heading_rename | d0 | `b30-2189` | wrong | hash |
| absent | cross-section fixture | heading_rename | d0 | `b40-2189` | wrong | hash |
| carriers | near_dups | merge | d0 | `b1-5ba1` | wrong | quote |
| carriers | near_dups | merge | d0 | `b2-73ec` | wrong | quote |
| carriers | cross-section fixture | edit_in_place | d0 | `b29-6183` | wrong | hash |
| carriers | cross-section fixture | edit_in_place | d0 | `b39-6183` | wrong | hash |
| carriers | cross-section fixture | heading_rename | d0 | `b30-2189` | wrong | hash |
| carriers | cross-section fixture | heading_rename | d0 | `b40-2189` | wrong | hash |

## Closed world, identity-boundary operators

The operators in `perturb.EXCL_OPERATORS`, markers stripped, so a pasted copy is an unmarked twin. `replace_related`'s ground truth (detach) is semantic rather than lexical; read its row apart.

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t2 | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t23 | 1080 | 873 | 183 | 20 | 4 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23m | 1080 | 873 | 183 | 20 | 4 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23d | 1080 | 873 | 183 | 20 | 4 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23dk | 1080 | 872 | 184 | 18 | 6 | 81.3% | [78.9, 83.6] | 1.7% | [1.0, 2.6] |
| absent | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| carriers | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t23+carriers | 1080 | 873 | 183 | 20 | 4 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23dk+carriers | 1080 | 872 | 184 | 18 | 6 | 81.3% | [78.9, 83.6] | 1.7% | [1.0, 2.6] |

Cells are correct / missed / misattached / detach ok, pooled over every corpus.

| Operator | ladder | t2 | t23 | t23m | t23d | t23dk | absent | carriers | t23+carriers | t23dk+carriers |
|---|---|---|---|---|---|---|---|---|---|---|
| replace | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 | 57/11/0/4 |
| replace_related | 57/11/2/2 | 57/11/2/2 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/2/2 | 57/11/2/2 | 57/11/2/2 | 57/11/4/0 | 57/11/2/2 |
| swap_edit | 58/13/1/0 | 58/13/1/0 | 59/13/0/0 | 59/13/0/0 | 59/13/0/0 | 58/14/0/0 | 58/13/1/0 | 58/13/1/0 | 59/13/0/0 | 58/14/0/0 |
| copy_above | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 |
| copy_below | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 |
| copy_start | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 |
| copy_end | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 | 57/15/0/0 |
| copy_above_edit_copy | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 |
| copy_below_edit_copy | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 |
| copy_start_edit_copy | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 |
| copy_end_edit_copy | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 | 61/11/0/0 |
| copy_above_edit_original | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 |
| copy_below_edit_original | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 |
| copy_start_edit_original | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 |
| copy_end_edit_original | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 | 57/11/4/0 |

### Case by case against the control

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 0 | 0 | 0 | 0 |
| t23 | 0 | 1 (swap_edit 1) | 1 (swap_edit 1) | 2 (replace_related 2) |
| t23m | 0 | 1 (swap_edit 1) | 1 (swap_edit 1) | 2 (replace_related 2) |
| t23d | 0 | 1 (swap_edit 1) | 1 (swap_edit 1) | 2 (replace_related 2) |
| t23dk | 0 | 0 | 1 (swap_edit 1) | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 0 | 1 (swap_edit 1) | 1 (swap_edit 1) | 2 (replace_related 2) |
| t23dk+carriers | 0 | 0 | 1 (swap_edit 1) | 0 |

### Misattachments that differ from the control

| Arm | Corpus | Operator | Doc | Id | Outcome | Tier |
|---|---|---|---|---|---|---|
| t23 | near_dups | replace_related | d0 | `b2-73ec` | false_attach | quote |
| t23 | cross-section fixture | replace_related | d0 | `b3-a8c9` | false_attach | quote |
| t23m | near_dups | replace_related | d0 | `b2-73ec` | false_attach | quote |
| t23m | cross-section fixture | replace_related | d0 | `b3-a8c9` | false_attach | quote |
| t23d | near_dups | replace_related | d0 | `b2-73ec` | false_attach | quote |
| t23d | cross-section fixture | replace_related | d0 | `b3-a8c9` | false_attach | quote |
| t23+carriers | near_dups | replace_related | d0 | `b2-73ec` | false_attach | quote |
| t23+carriers | cross-section fixture | replace_related | d0 | `b3-a8c9` | false_attach | quote |

## Open world (half-stamped)

Only every other block carries a marker, run once for each parity. Unstamped blocks still compete for every anchor, which is what a partly stamped document or freshly pasted text looks like.

### Existing operators

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| t2 | 868 | 692 | 167 | 4 | 5 | 80.2% | [77.4, 82.8] | 0.5% | [0.1, 1.2] |
| t23 | 868 | 694 | 168 | 2 | 4 | 80.4% | [77.6, 83.0] | 0.2% | [0.0, 0.8] |
| t23m | 868 | 694 | 166 | 4 | 4 | 80.4% | [77.6, 83.0] | 0.5% | [0.1, 1.2] |
| t23d | 868 | 694 | 168 | 2 | 4 | 80.4% | [77.6, 83.0] | 0.2% | [0.0, 0.8] |
| t23dk | 868 | 692 | 170 | 1 | 5 | 80.2% | [77.4, 82.8] | 0.1% | [0.0, 0.6] |
| absent | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| carriers | 868 | 692 | 165 | 6 | 5 | 80.2% | [77.4, 82.8] | 0.7% | [0.3, 1.5] |
| t23+carriers | 868 | 694 | 168 | 2 | 4 | 80.4% | [77.6, 83.0] | 0.2% | [0.0, 0.8] |
| t23dk+carriers | 868 | 692 | 170 | 1 | 5 | 80.2% | [77.4, 82.8] | 0.1% | [0.0, 0.6] |

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 0 | 0 | 2 (edit_in_place 2) | 0 |
| t23 | 0 | 2 (merge 2) | 5 (edit_in_place 2, heading_rename 2, merge 1) | 1 (heading_delete 1) |
| t23m | 0 | 2 (merge 2) | 3 (edit_in_place 2, merge 1) | 1 (heading_delete 1) |
| t23d | 0 | 2 (merge 2) | 5 (edit_in_place 2, heading_rename 2, merge 1) | 1 (heading_delete 1) |
| t23dk | 0 | 0 | 5 (edit_in_place 2, heading_rename 2, merge 1) | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 0 | 2 (merge 2) | 5 (edit_in_place 2, heading_rename 2, merge 1) | 1 (heading_delete 1) |
| t23dk+carriers | 0 | 0 | 5 (edit_in_place 2, heading_rename 2, merge 1) | 0 |

### Identity-boundary operators

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t2 | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t23 | 1080 | 873 | 182 | 20 | 5 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23m | 1080 | 873 | 182 | 20 | 5 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23d | 1080 | 873 | 182 | 20 | 5 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23dk | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| absent | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| carriers | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |
| t23+carriers | 1080 | 873 | 182 | 20 | 5 | 81.4% | [79.0, 83.7] | 1.9% | [1.1, 2.8] |
| t23dk+carriers | 1080 | 872 | 183 | 19 | 6 | 81.3% | [78.9, 83.6] | 1.8% | [1.1, 2.7] |

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 0 | 0 | 0 | 0 |
| t23 | 0 | 1 (swap_edit 1) | 0 | 1 (replace_related 1) |
| t23m | 0 | 1 (swap_edit 1) | 0 | 1 (replace_related 1) |
| t23d | 0 | 1 (swap_edit 1) | 0 | 1 (replace_related 1) |
| t23dk | 0 | 0 | 0 | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 0 | 1 (swap_edit 1) | 0 | 1 (replace_related 1) |
| t23dk+carriers | 0 | 0 | 0 | 0 |

## Partly marked

Every block stamped, every anchor kept, and every other id's marker left in the edited document, once for each parity. This is where tiers 2 and 3 meet blocks already claimed at tier 1. **This run is not blind**: its stop rule (the chosen form introduces no misattachment against the control) was written after a probe of this same sweep had shown zero.

### Published and section operators, every corpus

All fourteen operators on all three corpora, two parities. Section operators leave a corpus without sections unchanged, which accounts for 280 of the 2016 resolutions, all correct under every arm.

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 2016 | 1835 | 165 | 6 | 10 | 91.5% | [90.2, 92.7] | 0.3% | [0.1, 0.6] |
| t2 | 2016 | 1834 | 168 | 4 | 10 | 91.4% | [90.1, 92.6] | 0.2% | [0.1, 0.5] |
| t23 | 2016 | 1877 | 129 | 0 | 10 | 93.6% | [92.4, 94.6] | 0.0% | [0.0, 0.2] |
| t23m | 2016 | 1877 | 129 | 0 | 10 | 93.6% | [92.4, 94.6] | 0.0% | [0.0, 0.2] |
| t23d | 2016 | 1877 | 129 | 0 | 10 | 93.6% | [92.4, 94.6] | 0.0% | [0.0, 0.2] |
| t23dk | 2016 | 1829 | 177 | 0 | 10 | 91.2% | [89.8, 92.4] | 0.0% | [0.0, 0.2] |
| absent | 2016 | 1835 | 165 | 6 | 10 | 91.5% | [90.2, 92.7] | 0.3% | [0.1, 0.6] |
| carriers | 2016 | 1835 | 165 | 6 | 10 | 91.5% | [90.2, 92.7] | 0.3% | [0.1, 0.6] |
| t23+carriers | 2016 | 1877 | 129 | 0 | 10 | 93.6% | [92.4, 94.6] | 0.0% | [0.0, 0.2] |
| t23dk+carriers | 2016 | 1829 | 177 | 0 | 10 | 91.2% | [89.8, 92.4] | 0.0% | [0.0, 0.2] |

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 1 (edit_in_place 1) | 0 | 2 (edit_in_place 2) | 0 |
| t23 | 5 (merge 5) | 47 (clone 3, cross_section_move 3, cross_section_move_edit 3, decoy 3, delete 3, edit_in_place 7, heading_delete 2, heading_rename 2, heavy_paraphrase 6, insert 3, merge 3, reorder 3, section_move 3, split 3) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23m | 5 (merge 5) | 47 (clone 3, cross_section_move 3, cross_section_move_edit 3, decoy 3, delete 3, edit_in_place 7, heading_delete 2, heading_rename 2, heavy_paraphrase 6, insert 3, merge 3, reorder 3, section_move 3, split 3) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23d | 5 (merge 5) | 47 (clone 3, cross_section_move 3, cross_section_move_edit 3, decoy 3, delete 3, edit_in_place 7, heading_delete 2, heading_rename 2, heavy_paraphrase 6, insert 3, merge 3, reorder 3, section_move 3, split 3) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23dk | 6 (edit_in_place 1, merge 5) | 0 | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 5 (merge 5) | 47 (clone 3, cross_section_move 3, cross_section_move_edit 3, decoy 3, delete 3, edit_in_place 7, heading_delete 2, heading_rename 2, heavy_paraphrase 6, insert 3, merge 3, reorder 3, section_move 3, split 3) | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |
| t23dk+carriers | 6 (edit_in_place 1, merge 5) | 0 | 6 (edit_in_place 2, heading_rename 2, merge 2) | 0 |

Cells are correct / missed / misattached / detach ok, pooled over every corpus.

| Operator | ladder | t2 | t23 | t23m | t23d | t23dk | absent | carriers | t23+carriers | t23dk+carriers |
|---|---|---|---|---|---|---|---|---|---|---|
| reorder | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| edit_in_place | 129/13/2/0 | 128/16/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 128/16/0/0 | 129/13/2/0 | 129/13/2/0 | 136/8/0/0 | 128/16/0/0 |
| heavy_paraphrase | 128/16/0/0 | 128/16/0/0 | 134/10/0/0 | 134/10/0/0 | 134/10/0/0 | 128/16/0/0 | 128/16/0/0 | 128/16/0/0 | 134/10/0/0 | 128/16/0/0 |
| split | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| merge | 130/12/2/0 | 130/12/2/0 | 128/16/0/0 | 128/16/0/0 | 128/16/0/0 | 125/19/0/0 | 130/12/2/0 | 130/12/2/0 | 128/16/0/0 | 125/19/0/0 |
| delete | 125/11/0/8 | 125/11/0/8 | 128/8/0/8 | 128/8/0/8 | 128/8/0/8 | 125/11/0/8 | 125/11/0/8 | 125/11/0/8 | 128/8/0/8 | 125/11/0/8 |
| insert | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| decoy | 131/13/0/0 | 131/13/0/0 | 134/10/0/0 | 134/10/0/0 | 134/10/0/0 | 131/13/0/0 | 131/13/0/0 | 131/13/0/0 | 134/10/0/0 | 131/13/0/0 |
| clone | 129/15/0/0 | 129/15/0/0 | 132/12/0/0 | 132/12/0/0 | 132/12/0/0 | 129/15/0/0 | 129/15/0/0 | 129/15/0/0 | 132/12/0/0 | 129/15/0/0 |
| cross_section_move | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| cross_section_move_edit | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| section_move | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 133/11/0/0 | 133/11/0/0 | 133/11/0/0 | 136/8/0/0 | 133/11/0/0 |
| heading_rename | 134/8/2/0 | 134/8/2/0 | 136/8/0/0 | 136/8/0/0 | 136/8/0/0 | 134/10/0/0 | 134/8/2/0 | 134/8/2/0 | 136/8/0/0 | 134/10/0/0 |
| heading_delete | 131/11/0/2 | 131/11/0/2 | 133/9/0/2 | 133/9/0/2 | 133/9/0/2 | 131/11/0/2 | 131/11/0/2 | 131/11/0/2 | 133/9/0/2 | 131/11/0/2 |

### Every recovery `t23dk+carriers` loses against the control

| Corpus | Operator | Doc | Id | Control's tier | Outcome | Reason |
|---|---|---|---|---|---|---|
| distinct prose | merge | d0m0 | `b1-453e` | quote | missed | unmatched |
| distinct prose | merge | d0m1 | `b2-172a` | quote | missed | unmatched |
| distinct prose | merge | d1m0 | `b1-b3ba` | quote | missed | unmatched |
| distinct prose | merge | d1m1 | `b2-2f40` | quote | missed | unmatched |
| cross-section fixture | edit_in_place | d0m1 | `b34-6183` | hash | missed | ambiguous |
| cross-section fixture | merge | d0m1 | `b4-b59e` | quote | missed | unmatched |

### Every misattachment, by arm

| Arm | Corpus | Operator | Doc | Id | Outcome | Tier |
|---|---|---|---|---|---|---|
| ladder | near_dups | merge | d0m0 | `b1-5ba1` | wrong | quote |
| ladder | near_dups | merge | d0m1 | `b2-73ec` | wrong | quote |
| ladder | cross-section fixture | edit_in_place | d0m0 | `b29-6183` | wrong | hash |
| ladder | cross-section fixture | edit_in_place | d0m0 | `b39-6183` | wrong | hash |
| ladder | cross-section fixture | heading_rename | d0m1 | `b30-2189` | wrong | hash |
| ladder | cross-section fixture | heading_rename | d0m1 | `b40-2189` | wrong | hash |
| t2 | near_dups | merge | d0m0 | `b1-5ba1` | wrong | quote |
| t2 | near_dups | merge | d0m1 | `b2-73ec` | wrong | quote |
| t2 | cross-section fixture | heading_rename | d0m1 | `b30-2189` | wrong | quote |
| t2 | cross-section fixture | heading_rename | d0m1 | `b40-2189` | wrong | quote |
| absent | near_dups | merge | d0m0 | `b1-5ba1` | wrong | quote |
| absent | near_dups | merge | d0m1 | `b2-73ec` | wrong | quote |
| absent | cross-section fixture | edit_in_place | d0m0 | `b29-6183` | wrong | hash |
| absent | cross-section fixture | edit_in_place | d0m0 | `b39-6183` | wrong | hash |
| absent | cross-section fixture | heading_rename | d0m1 | `b30-2189` | wrong | hash |
| absent | cross-section fixture | heading_rename | d0m1 | `b40-2189` | wrong | hash |
| carriers | near_dups | merge | d0m0 | `b1-5ba1` | wrong | quote |
| carriers | near_dups | merge | d0m1 | `b2-73ec` | wrong | quote |
| carriers | cross-section fixture | edit_in_place | d0m0 | `b29-6183` | wrong | hash |
| carriers | cross-section fixture | edit_in_place | d0m0 | `b39-6183` | wrong | hash |
| carriers | cross-section fixture | heading_rename | d0m1 | `b30-2189` | wrong | hash |
| carriers | cross-section fixture | heading_rename | d0m1 | `b40-2189` | wrong | hash |

### Tier 2's claimed filter

The chosen form against itself with the filter removed. Across the sweep above the filter changes 0 of 2016 resolutions. `edit_into_twin` rewrites one marked paragraph into another's exact text, each keeping its own id, and there the filter changes 4 of 144. That operator is built to reach the filter, so it shows the path runs and says nothing about how often the shape occurs.

| Corpus | Doc | Id | with the filter | without it |
|---|---|---|---|---|
| distinct prose | d0m1 | `b2-172a` | correct | missed |
| distinct prose | d1m1 | `b2-2f40` | correct | missed |
| near_dups | d0m1 | `b2-73ec` | correct | missed |
| cross-section fixture | d0m0 | `b3-a8c9` | correct | missed |

### `edit_into_twin`

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 144 | 125 | 19 | 0 | 0 | 86.8% | [80.2, 91.9] | 0.0% | [0.0, 2.5] |
| t2 | 144 | 129 | 15 | 0 | 0 | 89.6% | [83.4, 94.1] | 0.0% | [0.0, 2.5] |
| t23 | 144 | 133 | 11 | 0 | 0 | 92.4% | [86.7, 96.1] | 0.0% | [0.0, 2.5] |
| t23m | 144 | 133 | 11 | 0 | 0 | 92.4% | [86.7, 96.1] | 0.0% | [0.0, 2.5] |
| t23d | 144 | 133 | 11 | 0 | 0 | 92.4% | [86.7, 96.1] | 0.0% | [0.0, 2.5] |
| t23dk | 144 | 129 | 15 | 0 | 0 | 89.6% | [83.4, 94.1] | 0.0% | [0.0, 2.5] |
| absent | 144 | 125 | 19 | 0 | 0 | 86.8% | [80.2, 91.9] | 0.0% | [0.0, 2.5] |
| carriers | 144 | 125 | 19 | 0 | 0 | 86.8% | [80.2, 91.9] | 0.0% | [0.0, 2.5] |
| t23+carriers | 144 | 133 | 11 | 0 | 0 | 92.4% | [86.7, 96.1] | 0.0% | [0.0, 2.5] |
| t23dk+carriers | 144 | 129 | 15 | 0 | 0 | 89.6% | [83.4, 94.1] | 0.0% | [0.0, 2.5] |

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 0 | 4 (edit_into_twin 4) | 0 | 0 |
| t23 | 0 | 8 (edit_into_twin 8) | 0 | 0 |
| t23m | 0 | 8 (edit_into_twin 8) | 0 | 0 |
| t23d | 0 | 8 (edit_into_twin 8) | 0 | 0 |
| t23dk | 0 | 4 (edit_into_twin 4) | 0 | 0 |
| absent | 0 | 0 | 0 | 0 |
| carriers | 0 | 0 | 0 | 0 |
| t23+carriers | 0 | 8 (edit_into_twin 8) | 0 | 0 |
| t23dk+carriers | 0 | 4 (edit_into_twin 4) | 0 | 0 |

### Identity-boundary operators

Outside the registered run. A `copy_*` operator pastes the marker too, so the parity that keeps the copied id has that id on two blocks and tier 1's carriers rule decides it. Those are the copy table's edited-original cases below, under a second name; `t23dk`, which keeps the shipped tier 1, introduces none.

| Arm | n | correct | missed | misattached | detach ok | recovery | 95% CI | misattach rate | 95% CI |
|---|--:|--:|--:|--:|--:|--:|---|--:|---|
| ladder | 2160 | 1920 | 183 | 45 | 12 | 89.6% | [88.2, 90.8] | 2.1% | [1.5, 2.8] |
| t2 | 2160 | 1920 | 183 | 45 | 12 | 89.6% | [88.2, 90.8] | 2.1% | [1.5, 2.8] |
| t23 | 2160 | 1968 | 136 | 48 | 8 | 91.8% | [90.5, 92.9] | 2.2% | [1.6, 2.9] |
| t23m | 2160 | 1968 | 136 | 48 | 8 | 91.8% | [90.5, 92.9] | 2.2% | [1.6, 2.9] |
| t23d | 2160 | 1968 | 136 | 48 | 8 | 91.8% | [90.5, 92.9] | 2.2% | [1.6, 2.9] |
| t23dk | 2160 | 1920 | 184 | 44 | 12 | 89.6% | [88.2, 90.8] | 2.0% | [1.5, 2.7] |
| absent | 2160 | 1912 | 199 | 37 | 12 | 89.2% | [87.8, 90.5] | 1.7% | [1.2, 2.4] |
| carriers | 2160 | 1912 | 199 | 37 | 12 | 89.2% | [87.8, 90.5] | 1.7% | [1.2, 2.4] |
| t23+carriers | 2160 | 1960 | 152 | 40 | 8 | 91.4% | [90.2, 92.6] | 1.9% | [1.3, 2.5] |
| t23dk+carriers | 2160 | 1912 | 200 | 36 | 12 | 89.2% | [87.8, 90.5] | 1.7% | [1.2, 2.3] |

| Arm | recoveries lost | recoveries gained | misattachments fixed | misattachments introduced |
|---|---|---|---|---|
| t2 | 0 | 0 | 0 | 0 |
| t23 | 0 | 48 (copy_above 3, copy_above_edit_copy 3, copy_above_edit_original 3, copy_below 3, copy_below_edit_copy 3, copy_below_edit_original 3, copy_end 3, copy_end_edit_copy 3, copy_end_edit_original 3, copy_start 3, copy_start_edit_copy 3, copy_start_edit_original 3, replace 3, replace_related 3, swap_edit 6) | 1 (swap_edit 1) | 4 (replace_related 4) |
| t23m | 0 | 48 (copy_above 3, copy_above_edit_copy 3, copy_above_edit_original 3, copy_below 3, copy_below_edit_copy 3, copy_below_edit_original 3, copy_end 3, copy_end_edit_copy 3, copy_end_edit_original 3, copy_start 3, copy_start_edit_copy 3, copy_start_edit_original 3, replace 3, replace_related 3, swap_edit 6) | 1 (swap_edit 1) | 4 (replace_related 4) |
| t23d | 0 | 48 (copy_above 3, copy_above_edit_copy 3, copy_above_edit_original 3, copy_below 3, copy_below_edit_copy 3, copy_below_edit_original 3, copy_end 3, copy_end_edit_copy 3, copy_end_edit_original 3, copy_start 3, copy_start_edit_copy 3, copy_start_edit_original 3, replace 3, replace_related 3, swap_edit 6) | 1 (swap_edit 1) | 4 (replace_related 4) |
| t23dk | 0 | 0 | 1 (swap_edit 1) | 0 |
| absent | 16 (copy_below 4, copy_below_edit_original 4, copy_end 4, copy_end_edit_original 4) | 8 (copy_above_edit_copy 4, copy_start_edit_copy 4) | 16 (copy_above 4, copy_above_edit_copy 4, copy_start 4, copy_start_edit_copy 4) | 8 (copy_below_edit_original 4, copy_end_edit_original 4) |
| carriers | 16 (copy_below 4, copy_below_edit_original 4, copy_end 4, copy_end_edit_original 4) | 8 (copy_above_edit_copy 4, copy_start_edit_copy 4) | 16 (copy_above 4, copy_above_edit_copy 4, copy_start 4, copy_start_edit_copy 4) | 8 (copy_below_edit_original 4, copy_end_edit_original 4) |
| t23+carriers | 16 (copy_below 4, copy_below_edit_original 4, copy_end 4, copy_end_edit_original 4) | 56 (copy_above 3, copy_above_edit_copy 7, copy_above_edit_original 3, copy_below 3, copy_below_edit_copy 3, copy_below_edit_original 3, copy_end 3, copy_end_edit_copy 3, copy_end_edit_original 3, copy_start 3, copy_start_edit_copy 7, copy_start_edit_original 3, replace 3, replace_related 3, swap_edit 6) | 17 (copy_above 4, copy_above_edit_copy 4, copy_start 4, copy_start_edit_copy 4, swap_edit 1) | 12 (copy_below_edit_original 4, copy_end_edit_original 4, replace_related 4) |
| t23dk+carriers | 16 (copy_below 4, copy_below_edit_original 4, copy_end 4, copy_end_edit_original 4) | 8 (copy_above_edit_copy 4, copy_start_edit_copy 4) | 17 (copy_above 4, copy_above_edit_copy 4, copy_start 4, copy_start_edit_copy 4, swap_edit 1) | 8 (copy_below_edit_original 4, copy_end_edit_original 4) |

## A copy that keeps the original's marker

Markers kept. The second marked paragraph is pasted with its marker above or below the original, or at the document's start or end, verbatim, with the copy drifted, or with the original drifted. SPEC.md §7 says the copy mints a new stay, so the id belongs to the original in every row. Cells are the copied id's outcome and the rule that decided it; every other id resolves correctly at tier 1 under every arm.

| Operator | ladder | detach | absent | carriers | t23+carriers | t23dk+carriers |
|---|---|---|---|---|---|---|
| copy_above | 0 / 0 / 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| copy_below | 4 / 0 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| copy_start | 0 / 0 / 4 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| copy_end | 4 / 0 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 | 0 / 4 / 0 |
| copy_above_edit_copy | 0 / 0 / 4 | 0 / 4 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 |
| copy_below_edit_copy | 4 / 0 / 0 | 0 / 4 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 |
| copy_start_edit_copy | 0 / 0 / 4 | 0 / 4 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 |
| copy_end_edit_copy | 4 / 0 / 0 | 0 / 4 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 | 4 / 0 / 0 |
| copy_above_edit_original | 0 / 0 / 4 | 0 / 4 / 0 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |
| copy_below_edit_original | 4 / 0 / 0 | 0 / 4 / 0 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |
| copy_start_edit_original | 0 / 0 / 4 | 0 / 4 / 0 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |
| copy_end_edit_original | 4 / 0 / 0 | 0 / 4 / 0 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 | 0 / 0 / 4 |

Cells are correct / missed / wrong over the four documents. Per document:

| Corpus | Doc | Operator | ladder | detach | absent | carriers | t23+carriers | t23dk+carriers |
|---|---|---|---|---|---|---|---|---|
| distinct prose | d0 | copy_above | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d0 | copy_below | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d0 | copy_start | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d0 | copy_end | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d0 | copy_above_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d0 | copy_below_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d0 | copy_start_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d0 | copy_end_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d0 | copy_above_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d0 | copy_below_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d0 | copy_start_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d0 | copy_end_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d1 | copy_above | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d1 | copy_below | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d1 | copy_start | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d1 | copy_end | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| distinct prose | d1 | copy_above_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d1 | copy_below_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d1 | copy_start_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d1 | copy_end_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| distinct prose | d1 | copy_above_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d1 | copy_below_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d1 | copy_start_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| distinct prose | d1 | copy_end_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| near_dups | d0 | copy_above | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| near_dups | d0 | copy_below | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| near_dups | d0 | copy_start | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| near_dups | d0 | copy_end | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| near_dups | d0 | copy_above_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| near_dups | d0 | copy_below_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| near_dups | d0 | copy_start_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| near_dups | d0 | copy_end_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| near_dups | d0 | copy_above_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| near_dups | d0 | copy_below_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| near_dups | d0 | copy_start_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| near_dups | d0 | copy_end_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| cross-section fixture | d0 | copy_above | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| cross-section fixture | d0 | copy_below | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| cross-section fixture | d0 | copy_start | wrong (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| cross-section fixture | d0 | copy_end | correct (marker) | missed (duplicated, duplicated) | missed (quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) | missed (carrier-quote, ambiguous) |
| cross-section fixture | d0 | copy_above_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| cross-section fixture | d0 | copy_below_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| cross-section fixture | d0 | copy_start_edit_copy | wrong (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| cross-section fixture | d0 | copy_end_edit_copy | correct (marker) | missed (duplicated, duplicated) | correct (hash) | correct (carrier-hash) | correct (carrier-hash) | correct (carrier-hash) |
| cross-section fixture | d0 | copy_above_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| cross-section fixture | d0 | copy_below_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| cross-section fixture | d0 | copy_start_edit_original | wrong (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
| cross-section fixture | d0 | copy_end_edit_original | correct (marker) | missed (duplicated, duplicated) | wrong (hash) | wrong (carrier-hash) | wrong (carrier-hash) | wrong (carrier-hash) |
