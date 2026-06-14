# Examples

These show the v1 syntax across the common block types and a few realistic agent
workflows. The marker is always a trailing comment on the line after the block. In
rendered Markdown it is invisible; the source carries it.

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

A marker after a list identifies the **whole list**. List-item identity is deferred
to a later extension, so v1 lists carry one stay for the list as a unit. The list
must be tight (no blank lines between items) for the marker to bind the whole list.

```md
- Retry failed requests with jitter.
- Cap retries at five attempts.
<!-- stay:retry-policy -->
```

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

A marker after the table identifies the whole table. Row-level identity is deferred to
a later extension.

```md
| Plan | Limit |
|------|------:|
| Pro  | 100   |
<!-- stay:plan-limit-table -->
```

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
