# LLM-driven attachment-survival eval results

Models: sonnet,gpt4o,opus  |  docs: doc1,doc2,near_dups  |  tasks: copyedit, rewrite, restructure, reword  |  threshold 0.5, margin 0.05

Cells: 36 run, 36 ok, 0 failed. Scored ids: 336; excluded (rewrite dropped/duplicated/relocated the marker, no clean ground truth): 0.

Each cell annotates a doc, has the model rewrite the prose while preserving markers (§11), validates the preserved markers as ground truth via the linter's regeneration diff, strips the markers, and asks the resolver to recover every original id from hash + quote alone. Recovery = correct / scored; false-rate = wrong / scored. `wrong` is the silent mis-attachment SPEC.md §10 forbids.


**Overall (markers stripped, real rewrites): recovery  90%, false-attach   0% over 336 scored ids.**


## Recovery by measured before/after block similarity (the regime test)

| group | scored | correct | wrong | missed | recovery | false-rate |
|-------|-------:|--------:|------:|-------:|---------:|-----------:|
| 0.3-0.5 | 28 | 10 | 0 | 18 |  36% |   0% |
| 0.5-0.7 | 80 | 73 | 0 | 7 |  91% |   0% |
| 0.7-0.9 | 56 | 47 | 1 | 8 |  84% |   2% |
| 0.9-1.0 | 172 | 172 | 0 | 0 | 100% |   0% |

The deterministic eval could not push real prose below ~0.7 similarity; these low bands are the new evidence. If recovery holds in the 0.3-0.5 band, §9 quote params survive real rewrites; if it collapses or false-attach climbs, v1 §9 needs revisiting.


## By rewrite task

| group | scored | correct | wrong | missed | recovery | false-rate |
|-------|-------:|--------:|------:|-------:|---------:|-----------:|
| copyedit | 84 | 84 | 0 | 0 | 100% |   0% |
| rewrite | 84 | 76 | 1 | 7 |  90% |   1% |
| restructure | 84 | 68 | 0 | 16 |  81% |   0% |
| reword | 84 | 74 | 0 | 10 |  88% |   0% |

## By model

| group | scored | correct | wrong | missed | recovery | false-rate |
|-------|-------:|--------:|------:|-------:|---------:|-----------:|
| gpt4o | 112 | 98 | 1 | 13 |  88% |   1% |
| opus | 112 | 101 | 0 | 11 |  90% |   0% |
| sonnet | 112 | 103 | 0 | 9 |  92% |   0% |

## By document

| group | scored | correct | wrong | missed | recovery | false-rate |
|-------|-------:|--------:|------:|-------:|---------:|-----------:|
| doc1 | 120 | 115 | 0 | 5 |  96% |   0% |
| doc2 | 120 | 114 | 0 | 6 |  95% |   0% |
| near_dups | 96 | 73 | 1 | 22 |  76% |   1% |

## Which tier recovered the id (scored ids)

| tier | ids | share |
|------|----:|------:|
| hash | 131 |  39% |
| quote | 172 |  51% |
| detached | 33 |  10% |
| marker | 0 |   0% |

## False attachments (every `wrong`, for inspection)

| model | doc | task | id | sim | resolver score | gold->got |
|-------|-----|------|----|----:|---------------:|-----------|
| gpt4o | near_dups | rewrite | b2-73ec | 0.84 | 0.94 | 2->3 |
