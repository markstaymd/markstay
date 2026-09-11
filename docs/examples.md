# Examples

These show the marker syntax across common block types and agent workflows.
Writers place block markers on the line after the block. Optional child markers
share a line with list-item or row content, subject to
[§3.4's placement checks](spec.md#34-a-marker-that-shares-a-line-with-content-v17).
See [compatibility](compat.md) for measured visibility and rendering limits.

## Paragraph

```md
Users authenticate with an API key in the Authorization header.
<!-- stay:8f24 -->
```

## Paragraph with recovery evidence

`hash` detects whether the body changed; `quote` helps a tool re-find the block if the
marker is moved or dropped. Neither is identity.

```md
This market doubled in 2025.
<!-- stay:market-growth hash=sha256:7a9c quote="This market doubled in 2025." -->
```

## List

A marker after a list identifies the **whole list**, and that is still the default: a
list carries one stay for the list as a unit. Since
[version 1.3](spec.md#55-child-block-identity-list-items-v13) a **direct list item may
also carry its own stay**, addressed inside its list under the reserved `subhash` key,
which a tool opts into. A document that does not use it is unaffected, and a tool that
does not implement it still has to leave a child-stamped document alone.

```md
- Retry failed requests with jitter.
- Cap retries at five attempts.
<!-- stay:retry-policy -->
```

Under the dependency-free baseline the list must be **tight** (no blank lines between
items) for the marker to bind the whole list; a loose list otherwise binds only its
last item. The [version 1.1](spec.md#52-commonmark-tree-attachment-v11)
CommonMark-tree mode removes that constraint, binding a loose list (and a fence with
internal blank lines) as a single block.

## Code fence

A marker after the closing fence identifies the whole fence, which is stable even when
prose above it shifts the line numbers.

````md
```bash
curl https://api.example.com/v1/items
```
<!-- stay:items-curl-example hash=sha256:7a9c -->
````

## Table

A marker after the table identifies the whole table, and that is still the default.

```md
| Plan | Limit |
|------|------:|
| Pro  | 100   |
<!-- stay:plan-limit-table -->
```

Since [version 1.6](spec.md#56-child-block-identity-table-rows-v16) a **body row may
also carry its own stay**, on the same reserved `subhash` key and the same resolution
ladder as a list item. The carrier is a marker inside the row's **last cell**, written
flush against the cell's content. The measured GFM-preserving formatters keep the
fixture marker on its row; pandoc's native Markdown writer does not (see
[compatibility](compat.md#table-row-carrier)).

```md
| Plan | Limit |
|------|------:|
| Pro  | 100<!-- stay:plan-row-pro subhash=sha256:9f2c --> |
<!-- stay:plan-limit-table hash=sha256:4b81 -->
```

Flush placement is what makes the row body a stable thing to hash: the cells are
trimmed before hashing, so a formatter re-padding the column is not drift, and stamping
a row leaves the containing table's own hash byte-identical.

Writers refuse a new row marker when the container's source prefix contains `<`
or a backslash outside plain markers, or when the flush position ends in `*`,
`_`, or `~`. MDX also refuses `{`. A refused row keeps its content and gets no
new stay; the table can still receive a block stay. New child markers carry only
their id and digest, with recovery evidence stored separately.

## Blockquote

```md
> Identity is not location.
<!-- stay:identity-not-location -->
```

## Heading landmark

Authored, human-readable ids are allowed for important landmarks. The marker follows
the heading, like every other block.

```md
## API
<!-- stay:section-api -->
```

## MDX profile

HTML comments are invalid in MDX v2, so the same marker uses the JSX comment form. One
data model, two serialisations.

```mdx
The paragraph being identified.
{/* stay:8f24 hash=sha256:7a9c */}
```

## Agent edit request

Without stable ids, an agent has to describe its target in fragile prose:

```json
{
  "file": "docs/auth.md",
  "heading": "Authentication",
  "instruction": "Update the curl example for v2."
}
```

With a stable id, the target is unambiguous and the result is auditable:

```json
{
  "file": "docs/auth.md",
  "block": "stay:8f24",
  "operation": "replace",
  "new_markdown": "Use an API key in the Authorization header. v2 also accepts OAuth."
}
```

## Preservation instruction for an agent

The one instruction that keeps markers alive through a rewrite (see
[the findings](evaluation.md) for why it is needed):

```md
Replace only the block with `stay:8f24`.
Preserve every other `<!-- stay:... -->` marker exactly, including its id.
```

## Failure modes markstay is meant to fix

### Heading-slug drift

An agent stores `#setup`. A later edit renames the heading to `## Installation` and the
anchor changes. A block id does not.

```md
## Installation
Install the package.
<!-- stay:install-step -->
```

### Duplicate text

A quote selector alone cannot tell two identical blocks apart; a generated id can.

```md
This statement needs a citation.
<!-- stay:claim-uptime -->

This statement needs a citation.
<!-- stay:claim-latency -->
```

### Review comment that has to survive a move

Primary identity plus W3C-style recovery evidence lets a review tool re-find a moved
paragraph instead of guessing.

```md
This statement needs a citation.
<!-- stay:needs-citation hash=sha256:7a9c quote="This statement needs a citation." -->
```
