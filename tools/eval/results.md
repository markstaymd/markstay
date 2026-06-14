# Marker-survival eval results

Models: haiku,sonnet,gpt4o-mini  |  docs: doc1,doc2  |  tasks: rewrite, cleanup, translate, edit

Cells: 384 run, 384 ok, 0 failed.

Metric: % of block markers that survived **intact** (full marker syntax with its id still present in the output), averaged over the cells in each group.


## Survival by marker syntax: naive vs instructed

| Marker | naive | instructed |
|--------|------:|-----------:|
| html_comment |  54 | 100 |
| html_comment_hash |  54 | 100 |
| visible_tag |  50 | 100 |
| pandoc_attr |  50 | 100 |
| mdx_comment |  50 | 100 |
| kramdown_ial |  50 | 100 |
| obsidian_caret |  50 | 100 |
| frontmatter_map |  25 |  75 |

## Survival by marker x task (all instruction modes)

| Marker | rewrite | cleanup | translate | edit |
|--------|-----:|-----:|-----:|-----:|
| html_comment |  58 |  50 | 100 | 100 |
| html_comment_hash |  58 |  50 | 100 | 100 |
| visible_tag |  50 |  50 | 100 | 100 |
| pandoc_attr |  50 |  50 | 100 | 100 |
| mdx_comment |  50 |  50 | 100 | 100 |
| kramdown_ial |  50 |  50 | 100 | 100 |
| obsidian_caret |  50 |  50 | 100 | 100 |
| frontmatter_map |  32 |  25 |  58 |  83 |

## Survival by model

| Model | intact % |
|-------|---------:|
| gpt4o-mini |  68 |
| haiku |  73 |
| sonnet |  77 |
