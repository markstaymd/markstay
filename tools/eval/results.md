# Marker-survival eval results

Models: haiku,sonnet,gpt4o-mini,kimi,opus  |  docs: doc1,doc2  |  tasks: rewrite, cleanup, translate, edit

Cells: 640 run, 640 ok, 0 failed.

Metric: % of block markers that survived **intact** (full marker syntax with its id still present in the output), averaged over the cells in each group.


## Survival by marker syntax: naive vs instructed

| Marker | naive | instructed |
|--------|------:|-----------:|
| html_comment |  67 | 100 |
| html_comment_hash |  65 | 100 |
| mdx_comment |  64 |  98 |
| obsidian_caret |  60 | 100 |
| kramdown_ial |  55 | 100 |
| pandoc_attr |  55 | 100 |
| visible_tag |  55 | 100 |
| frontmatter_map |  45 |  84 |

## Survival by marker x task (all instruction modes)

| Marker | rewrite | cleanup | translate | edit |
|--------|-----:|-----:|-----:|-----:|
| html_comment |  80 |  55 | 100 | 100 |
| html_comment_hash |  70 |  60 | 100 | 100 |
| mdx_comment |  79 |  45 | 100 | 100 |
| obsidian_caret |  70 |  50 | 100 | 100 |
| kramdown_ial |  60 |  50 | 100 | 100 |
| pandoc_attr |  60 |  50 | 100 | 100 |
| visible_tag |  60 |  50 | 100 | 100 |
| frontmatter_map |  59 |  45 |  70 |  85 |

## Survival by model

| Model | intact % |
|-------|---------:|
| gpt4o-mini |  70 |
| haiku |  73 |
| kimi |  76 |
| opus |  90 |
| sonnet |  82 |
