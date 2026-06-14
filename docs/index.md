# markstay

**A research-stage proposal for giving logical blocks of Markdown a stable identity that survives editing.**

markstay is an exploration, not a finished answer. The goal is to find out whether
there is a real gap between how Markdown is used today (the storage format for
documentation, and for documents that AI agents read and rewrite) and what it can
express (no portable way to point at a paragraph, list item, or code block and keep
pointing at it after the text changes).

If that gap is real, a small, source-native identity layer could fill it. This site
states the problem, surveys the [prior art](prior-art.md), and puts a
[draft spec](spec.md) on the table so the idea can be argued with rather than
admired.

!!! note "Status"
    Nothing here is locked. The syntax is a strawman. The intent is to gather
    feedback from the Markdown, AI, documentation, and knowledge-management
    communities, then decide whether the idea is worth standardising at all.

## The problem

Markdown is now the default storage format for READMEs, documentation sites, issues,
pull-request discussion, model prompts, and the output of AI agents that maintain
documents over time.

It has stable handles at every level except one:

- **Files** have paths.
- **Revisions** have commit SHAs.
- **Headings** have generated anchors.
- **Logical blocks** (a specific paragraph, list item, table, or code fence) have
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
them during a rewrite. That risk was measured rather than assumed; see
[the findings](evaluation.md).

## The proposal in one example

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

## Open questions

The hardest questions are not yet settled, and feedback on them is the point of this
site:

1. Is identity-only the right scope, or does it have to ship with annotation?
2. Is Markdown source the right layer, versus the editor or a sidecar?
3. What exactly is hashed (the normalisation rules that decide when two
   implementations agree on drift)?
4. What are the precise block-boundary rules for nested lists, blockquotes, and
   tables?
5. What does adoption actually look like, and would anyone consume the ids?

The [draft spec](spec.md) records the calls the prior art supports, the calls it
leaves open, and the failure modes any real version has to answer. The
[FAQ](faq.md) covers the obvious objections (why not heading anchors, UUIDs, an
external database, or HTML ids).

## What success means

Success here is not adoption. Success is learning whether the problem is real and
whether this proposal fills a genuine gap. If the conclusion is "the gap is real but
this is the wrong design", that is a useful result. If it is "the gap is not real",
that is too.

The work is openly licensed (content under CC BY 4.0, code samples under MIT) and
lives at [markstaymd/markstay](https://github.com/markstaymd/markstay). Issues and
counter-arguments are welcome.
