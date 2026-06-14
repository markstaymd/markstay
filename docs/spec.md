# Specification (version 1)

!!! note "This is the standard, version 1"
    The marker grammar, attachment model, hashing, and recovery behaviour below
    are settled. A conforming document and a conforming tool agree on this
    document. The reference [linter](linter.md) and the resolver behind the
    [attachment evaluation](evaluation.md) implement it.

The key words MUST, SHOULD, MAY, and their negatives are used as in RFC 2119.

## What markstay is

A source-level convention that gives a logical Markdown block a **stay**: a stable
address other tools can point at and keep pointing at across edits. The address
*stays* put while the content around it changes.

markstay is **not** an annotation system. Annotation, transclusion, AI-assisted
editing, and cross-references are consumers that build on the stay layer, not part
of it.

## The core model: identity, then evidence

| Field | Role | Changes when content changes? |
|-------|------|-------------------------------|
| `id` | stable logical identity | no |
| `hash` | drift detection | yes |
| `quote` + prefix/suffix | recovery evidence to re-find a detached marker | n/a |

- `id` answers *which block*.
- `hash` answers *did it change since last seen*.
- `quote` (a W3C `TextQuoteSelector`-style snippet) answers *where did it go* when
  the marker is lost.

The `id` is identity; the `hash` and `quote` are never identity, only evidence. A
hash mismatch with the marker present means "same block, changed content", not
"new block".

### Same stay or new stay

The same stay survives wording and formatting changes and movement within or
between documents. A new stay is warranted only on a material semantic change (the
block now asserts something different) or replacement of one statement with
another. Editing a block keeps its stay; replacing its meaning earns a new one.

## Marker syntax

### Primary form: trailing HTML comment

```md
The paragraph being identified.
<!-- stay:8f24 hash=sha256:7a9c -->
```

Invisible in GitHub-rendered Markdown, preserved in the raw `.md` source, needs no
Markdown attribute extension, and degrades to harmless source text on tools that
do not understand it. A conforming `.md` document MUST use this form.

### MDX profile: comment-expression form

HTML comments are invalid in MDX v2, so MDX uses the JSX comment form:

```mdx
The paragraph being identified.
{/* stay:8f24 hash=sha256:7a9c */}
```

One data model, two serialisations. A conforming tool MUST recognise both on
input.

## Marker grammar

A marker body begins with the `stay:` namespace, then a positional id, then
zero or more whitespace-separated attributes.

- **`id` is required and positional**: the first token after `stay:`, character set
  `[A-Za-z0-9_-]+`. A marker with no id token is malformed.
- **Attribute order is free**; a tool MUST NOT depend on it.
- **Reserved keys**: `hash`, `quote`, `prefix`, `suffix`.
- **Extension keys MUST be `x-`-prefixed** (e.g. `x-acme-author="…"`). A tool MUST
  preserve keys it does not understand and MUST NOT act on them.
- **Values** are a bare token, or a `"double-quoted"` string when they contain
  whitespace (`\"` and `\\` are the only escapes).

A marker MUST carry an `id`, SHOULD carry a `hash`, and MAY carry the
`quote`/`prefix`/`suffix` recovery evidence inline or keep it in a side index.

## Attachment model

v1 attachment is defined over **blank-line-delimited blocks**, not a full
CommonMark parse, which keeps the reference implementation dependency-free.

- A **block** is a maximal run of non-blank lines bounded by blank lines or the
  document edges.
- A marker binds to the block **immediately preceding** it. It MAY sit on the
  block's last line or as its own blank-line-separated chunk after the block.
- A marker with no preceding content block is an **orphan** (an error).
- More than one marker MAY bind to one block.

### Block granularity (v1)

Every v1 stay identifies a **whole block**:

- **List**: a marker after the list identifies the **whole list**. List-item
  identity is deferred to a later extension.
- **Code fence**: the marker after the closing fence identifies the **whole fence**.
- **Table**: the marker after the table identifies the **whole table**; row-level
  identity is deferred.
- **Blockquote**: a marker after the quote identifies the **whole quote**.

### Known limits of the blank-line model

Two constructs contain blank lines and so split into multiple blocks. For the
whole-block granularity above to hold in v1:

- **Lists must be tight** (no blank lines between items). A loose list parses as
  multiple blocks, so a trailing marker binds the last item, not the whole list.
- **Fenced code blocks with internal blank lines** should not be relied on to carry
  a single stay.

CommonMark-tree attachment (handling loose lists, blank-line-containing fences, and
nested blockquotes precisely) is the named refinement for a later version. It
relaxes these limits without changing the grammar or the identity model.

## IDs

- Default: a **short opaque generated id**, not derived from the block text, so it
  survives arbitrary edits and gives a rewriting model nothing to "improve".
- Human-readable ids are allowed for authored landmarks (`stay:install-step`).
- UUIDs are permitted but never required (too token-heavy for dense coverage).
- Duplicate ids within a document are invalid.

## Identity rules

- **No duplicate stays**: two blocks in one document MUST NOT share an id.
- **Move preserves** the id.
- **Copy mints a new** id (two logical blocks must not share identity). How a tool
  repairs a duplicate (mint on paste, on next lint, or on prompt) is tool
  behaviour, not protocol.

## Hash normalisation

`hash` detects whether a block's body changed. It is not identity, and it is lossy
by design: it detects semantic drift, not byte-exact change. The body (markers
removed) is normalised, in order:

1. line endings → LF,
2. strip trailing whitespace from every line,
3. drop leading and trailing blank lines,

then hashed with **SHA-256**, written `hash=sha256:<hex>` in lowercase hex. The hex
MAY be truncated; a tool compares at the precision stored in the marker. As a
result, whitespace-only and line-ending-only edits do not register as drift,
including inside code fences , intended, because they do not change meaning.

## Quote / selector recovery

When a marker is lost (an agent rewrites the document and drops the comment), the
id is re-found from a `TextQuoteSelector`-style triple: `quote` (the block body),
`prefix` and `suffix` (neighbour context, up to 48 characters each). Matching
casefolds and collapses whitespace, scores body similarity in `[0, 1]` with a
containment floor for split/merge survival, and uses prefix/suffix only as a small
tiebreaker.

A recovery is committed only when the best candidate scores **≥ 0.5** and beats the
runner-up by a **margin ≥ 0.05**; otherwise the marker is reported **detached**,
never reattached. Quote recovery is best-effort evidence, never authority: the
trustworthy signals are the surviving id and the exact `hash`. The
[attachment evaluation](evaluation.md) measures the hash tier alone recovering 81%
of moved-but-unchanged blocks with zero false attachment.

### The resolution ladder

1. **MARKER** , the id's marker is still present → trust it.
2. **HASH** , no marker, but exactly one block's body hash equals the stored hash →
   content survived verbatim, just lost its marker.
3. **QUOTE** , no marker and no unique hash hit → fuzzy-recover, committing only on
   a clear winner; otherwise **DETACHED**.

## Detached and stale markers

When a marker cannot be confidently mapped to a block, a tool MUST mark it
**outdated** rather than guess a nearby block. Silent reattachment to the wrong
block is worse than an explicit stale state (the precedent is GitHub review
comments). A marker whose block was genuinely deleted MUST resolve to detached ,
that is a correct outcome, not a failure.

## AI editing contract

Markdown is routinely edited by machines, and that is exactly when stays are lost
(see the [evaluation](evaluation.md)). An agent editing a markstay document MUST:

- **preserve** every existing stay,
- **keep** each stay attached to the same logical content it had before,
- **mint** a new stay for newly-addressed content,
- **never reuse** a stay id for semantically different content,
- **report** any stay it drops,
- **report** any duplicate stay it introduces.

The contract is measurable: the reference [linter](linter.md)'s regeneration diff
detects dropped, duplicated, and relocated stays and exits non-zero, so a post-edit
lint step turns silent loss into a caught error. This contract (a preservation
instruction plus the post-edit linter) is the durable deliverable for the AI use
case , not the marker syntax, which measurement found barely affects survival.

## Address scope

A stay is unique within a single document; there is no global or cross-repo stay.
The canonical address of a block is its document address plus its stay id, reusing
the URL-fragment convention:

```
auth.md#oauth-summary
docs/architecture.md#a1f0
```

Cross-document reference resolution is a consumer's concern; this spec defines the
in-document stay and its address form.

## Failure modes and how the spec answers them

- **Marker detachment**: hash-drift check + quote recovery + explicit stale state.
  On distinct prose the marker→hash→quote ladder re-attaches 98% of ids with zero
  false attachment; near-duplicate blocks are the residual risk, so a quote match
  without a clear margin surfaces as detached.
- **Sanitiser stripping**: the MDX/attribute profiles, and consumers that detect a
  missing expected marker.
- **AI regeneration churn**: the AI editing contract above , a preservation
  instruction restores survival to 100% in the [evaluation](evaluation.md); a
  post-edit [linter](linter.md) catches silent loss; generated non-semantic ids
  give a model nothing to "improve".
- **Copy-paste duplication**: copy mints a new id; tools detect and repair
  duplicates.
- **Granularity disagreement**: granularity pinned over blank-line blocks.
- **Scope creep into an annotation product**: core stays at identity + resolution;
  annotation is a separate, layered spec.

## Non-goals (v1)

- Annotation, comment storage, threads.
- Transclusion / embedding.
- Row-level table identity, list-item identity, inline-span identity.
- Single-stay attachment for loose lists and blank-line-containing fences (deferred
  to the CommonMark-tree refinement).
- A backend, accounts, or a hosted registry; any global or cross-repo namespace.

## Closest existing standards

- Recovery anchoring: W3C Web Annotation Data Model selectors (`TextQuoteSelector`,
  `TextPositionSelector`).
- Markdown syntax lineage: Pandoc / PHP Markdown Extra / kramdown `{#id}` attribute
  lists.
- Markdown product precedent: Obsidian block references (`^block-id`).
- Block-database precedent: Notion comments parented by block id; Logseq / Roam
  block references.
- Revision / stale-state precedent: GitHub review comments (commit + path + line,
  with an outdated state).

See [prior art](prior-art.md) for the full survey and source links.
