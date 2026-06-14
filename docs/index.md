# markstay

**A specification for giving logical blocks of Markdown a stable identity that survives editing.**

markstay is a small, source-native identity layer for Markdown. It gives a logical
block of content a **stay**: a stable address other tools can point at and keep
pointing at across edits, moves, and AI rewrites. The address *stays* put while the
content around it changes.

This site states the problem, surveys the [prior art](prior-art.md), and gives the
[specification](spec.md). Version 1 is settled: the marker grammar, attachment
model, hashing, and recovery behaviour are fixed, and a reference
[linter](linter.md) and an [evaluation](evaluation.md) back them with runnable code
and measurements.

!!! note "Status: version 1, settled"
    The v1 surface is small and stable. It is also young: real-world use and
    critique will shape later versions (finer-grained identity and CommonMark-tree
    attachment are the named next steps). Issues and counter-arguments are welcome.

## The problem

Markdown is now the default storage format for READMEs, documentation sites, issues,
pull-request discussion, model prompts, and the output of AI agents that maintain
documents over time.

It has stable handles at every level except one:

- **Files** have paths.
- **Revisions** have commit SHAs.
- **Headings** have generated anchors.
- **Logical blocks** (a specific paragraph, list, table, or code fence) have
  nothing.

There is no portable way to say "this paragraph" and have the reference still hold
after the block is edited, moved, or regenerated. Heading anchors drift when the
heading text changes. Line numbers break on the first insertion above them. Quote
matching fails on repeated or rewritten text. The handles that exist all encode
*location*, and location is exactly what editing destroys.

## Why it matters now

Agents increasingly work like repository collaborators: they read a file, change one
section, and open a pull request. In code they have a rich identity substrate (paths,
symbols, AST nodes, line ranges anchored to commits). In Markdown prose they fall
back to fuzzy text descriptions:

```text
the second paragraph under "Limitations"
the bullet about retries
the code block after the warning
```

Insert a paragraph, split a list, or add another warning, and each of those can
silently point at the wrong block. A stable per-block id turns "the bullet about
retries" into a handle an agent can store, cite, and edit against, and lets the edit
be audited afterwards (which ids changed, which were dropped).

This is the case markstay is built around. It is also where the idea is most fragile,
because the same agents that would *use* the ids are the ones most likely to *destroy*
them during a rewrite. That risk was measured, not assumed; see
[the findings](evaluation.md).

## markstay in one example

A block carries a marker on the line after it. The canonical form is a trailing HTML
comment, invisible in rendered Markdown and preserved in the source:

```md
Users authenticate with an API key in the Authorization header.
<!-- stay:8f24 -->
```

Identity can travel with optional evidence for detecting and recovering from drift:

```md
Users authenticate with an API key in the Authorization header.
<!-- stay:8f24 hash=sha256:7a9c quote="Users authenticate with an API key" -->
```

That is the whole surface area. Everything else is rules about what the marker binds
to, how it is preserved, and how a tool recovers when it is lost. See the
[examples](examples.md) for lists, code fences, tables, the MDX profile, and agent
edit requests.

## The one idea everything hangs on: identity is not location

Every mature system that anchors comments to editable content (Google Docs, Notion,
Figma, GitHub review comments) separates the stable identity of a thing from evidence
about where it currently sits. markstay takes the same split:

| Field | Role | Changes when content changes? |
|-------|------|-------------------------------|
| `id` | stable logical identity | no |
| `hash` | drift detection (did this block's body change?) | yes |
| `quote` + prefix/suffix | recovery evidence to re-find a detached marker | n/a |

The id is the identity. The hash and quote are never identity, only evidence. A hash
mismatch with the marker still present means "same block, changed content", not "new
block". This split is the single most consistent lesson from the
[prior art](prior-art.md).

## What version 1 settles

The [specification](spec.md) fixes:

- **Marker grammar**: a positional `stay:` id plus free-order `key=value`
  attributes, HTML-comment form for `.md` and a JSX-comment profile for MDX.
- **Attachment**: markers bind to the blank-line-delimited block above them, at
  whole-block granularity (whole list, fence, table, quote).
- **Hashing**: an exact normalization rule, so two implementations agree on drift.
- **Recovery**: a `TextQuoteSelector`-style ladder (marker → hash → quote) that
  surfaces a detached marker as outdated rather than guessing.
- **The AI editing contract**: what an agent must do to preserve stays, made
  measurable by the post-edit [linter](linter.md).

Deferred to later versions, by design: list-item and table-row identity, and
CommonMark-tree attachment (so loose lists and blank-line-containing code fences can
carry a single stay). The [FAQ](faq.md) covers the obvious objections (why not
heading anchors, UUIDs, an external database, or HTML ids).

## Scope

markstay is deliberately one thing: identity and recovery. Annotation, transclusion,
AI editing, and cross-references are consumers that build on the stay layer, not part
of it. Keeping the core small is what lets other tools adopt it.

The work is openly licensed (content under CC BY 4.0, code samples under MIT) and
lives at [markstaymd/markstay](https://github.com/markstaymd/markstay). Issues and
counter-arguments are welcome.
