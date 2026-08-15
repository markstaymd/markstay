# Specification (version 1.2)

!!! note "This is the standard, version 1.2"
    The marker grammar, attachment model, hashing, and recovery behaviour below
    are settled. A conforming document and a conforming tool agree on this
    document. The reference [linter](linter.md) and the resolver behind the
    [attachment evaluation](evaluation.md) implement it. Version 1.2 excludes
    leading YAML frontmatter from segmentation, so a `status:` flip is not a
    content edit, and states the condition under which the two segmenters agree
    (version 1.1 stated it too narrowly). The grammar, identity, hashing, and
    recovery are unchanged since version 1.

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

Attachment binds each marker to the block it follows. A conforming tool segments a
document into blocks one of two ways, which draw the same block boundaries on every
document in the [agreement subset](#the-agreement-subset-version-12) below:

- **Blank-line segmentation** is the baseline and the reference default. A **block**
  is a maximal run of non-blank lines bounded by blank lines or the document edges.
  It needs no Markdown parser, so the reference implementation stays dependency-free.
- **CommonMark-tree segmentation** (the version 1.1 refinement, below) makes a
  **block** a node of the CommonMark block tree, so a loose list or a fence with
  internal blank lines is one block. It needs a CommonMark parser and is an optional
  extra.

Both segmenters share the rest:

- **Leading YAML frontmatter** is document metadata, not content: it is excluded
  before segmentation, so it is never a block, never hashed, and never a host a
  marker can bind to ([below](#document-metadata-leading-yaml-frontmatter-version-12)).
- A marker binds to the block **immediately preceding** it. It MAY sit on the
  block's last line or as its own chunk after the block.
- A marker with no preceding content block is an **orphan** (an error).
- More than one marker MAY bind to one block.

### Block granularity

Every stay identifies a **whole block**:

- **List**: a marker after the list identifies the **whole list**. List-item
  identity is deferred to a later extension.
- **Code fence**: the marker after the closing fence identifies the **whole fence**.
- **Table**: the marker after the table identifies the **whole table**; row-level
  identity is deferred.
- **Blockquote**: a marker after the quote identifies the **whole quote**.

### CommonMark-tree attachment (version 1.1)

The blank-line baseline splits two constructs that legitimately contain blank lines:

- a **loose list** (blank lines between items) parses as one block per item, so a
  trailing marker binds the last item, not the whole list;
- a **fenced code block with internal blank lines** parses as multiple blocks, so a
  fence cannot reliably carry one stay.

CommonMark-tree segmentation lifts both: parsing the CommonMark block tree makes a
list, fence, or blockquote a single node regardless of internal blank lines, so the
whole-block granularity above holds for them too. It changes only *what counts as one
block*; the grammar, identity model, hashing, and the quote/margin recovery rule are
unchanged.

It is a **conservative extension**, and it changes nothing at all for a baseline
tool. On the [agreement subset](#the-agreement-subset-version-12) the two segmenters
draw the same block boundaries, so a document in the subset segments identically
under either; outside it they can differ, and always could. CommonMark mode only adds
defined single-stay attachment for the loose lists and blank-line fences version 1
left out of scope. Because it needs a CommonMark parser it is an optional extra: a
tool MAY implement either or both, and the dependency-free baseline stays the default.

### Document metadata: leading YAML frontmatter (version 1.2)

A **leading YAML frontmatter block** is document metadata, not content. A conforming
tool MUST exclude it from the document before segmentation, under both segmenters. It
is never a block: it carries no stay and is never hashed, so flipping `status: draft`
to `status: done` is not a content edit and drifts no hash. Excluding it MUST NOT
change the blocks, the block order, or the line numbers of the rest of the document.

**Recognition**, after line endings are normalised to LF, needs all four of:

1. **Line 1 is exactly `---`** (trailing spaces or tabs allowed; `----` is not a
   fence).
2. **Some later line is exactly `---` or `...`** (trailing spaces or tabs allowed
   here too); the first such line closes the span.
3. **The payload** between them is non-empty and holds **no blank line**.
4. **At least one payload line reads as YAML rather than as prose**, which means,
   after any leading spaces or tabs, either:
     - a **sequence item**: `-`, then one or more spaces or tabs, then a character
       outside `\x00-\x20` and not `\x7f`; or
     - a **mapping key**: a first character outside `\x00-\x20`, not `\x7f`, and
       neither `:` nor `#`; then zero or more characters that are not `:`; then `:`;
       then a space, a tab, or end of line.

   A YAML *comment* (`# …`) does not count, because it is byte-identical to an ATX
   heading.

The closing line is fixed by condition 2 alone. If that span then fails 3 or 4 the
document simply has no frontmatter; a tool MUST NOT rescan for a later fence that
would satisfy them, which is what stops `---` / `Title` / `---` / `title: t` / `---`
from swallowing a document. Conditions 3 and 4 are load-bearing for the same reason:
`---` is also a thematic break and a setext underline, and a looser rule destroys
content. Condition 3 is what stops `---` / blank / `Intro.` / blank / `---` (two
thematic breaks around a paragraph) from reading as frontmatter that swallows the
paragraph; condition 4 is what stops `---` / `Title` / `---` (a thematic break plus a
setext heading) from doing the same.

The whitespace sets are ASCII, spelled out as character ranges rather than delegated
to a language's "whitespace" class, because Python, JavaScript and Rust each classify
a different set and a rule that *removes* a span cannot afford that divergence.

**Recognition is a heuristic over a genuinely ambiguous construct, and this spec says
so rather than pretending otherwise.** A document that opens with a thematic break,
carries one blank-free run of content, and closes with another has two legitimate
readings, and no rule can separate them from the bytes:

```md
---
- Keep this content
---
```

That is a list between two thematic breaks *and* a YAML sequence, and conditions 1 to
4 accept it, so the content is excluded. **Frontmatter wins**, which is the same call
every mainstream Markdown site generator makes on the same bytes. What conditions 3
and 4 buy is not the absence of false positives, it is that the ambiguity is confined
to documents of exactly this shape: an opening thematic break, no blank line before
the closer, and a payload line that reads as YAML. A mapping payload is the same
case, not a safer one: `---` / `title: v` / `---` is equally a setext heading under a
thematic break. Everything outside that shape fails towards ordinary Markdown, where
the worst case is a spurious block and a stray drift warning.

Two consequences worth knowing:

- **A marker stamped onto frontmatter by an older tool usually becomes an orphan**
  (an error), because nothing precedes it any more. Delete that one marker. **The
  exception, and it matters before you delete anything:** a marker with no blank line
  between it and the content below is read as one run by blank-line segmentation and
  binds *forward* to that content, so it is live rather than orphaned and deleting it
  drops a working id. Lint first and delete what the linter actually reports.
- **The exclusion is a source span, not a block.** `...` is a legal YAML end marker
  but not a setext underline, so a CommonMark parser can produce one paragraph node
  that begins inside the metadata and ends outside it. A tree-based tool MUST trim
  such a node to the part after the span rather than dropping it.

Out of scope, deliberately: TOML (`+++`) and JSON frontmatter are not recognised, a
`---` fence anywhere but line 1 is not frontmatter, and whether the metadata itself
should be addressable is left open rather than refused.

### The agreement subset (version 1.2)

A document is in the **agreement subset** when, after the frontmatter span is
excluded, its **maximal runs of non-blank lines and its top-level CommonMark block
nodes cover the same spans of lines**: every run is covered by exactly one node, and
every node covers exactly one whole run. Top-level means outermost: a list item
inside a list, or a paragraph inside a blockquote, is not counted separately. On this
subset the two segmenters draw the same block boundaries, so the document segments
identically under any conforming tool.

Read that as an equality of line spans, **not** as "each run parses to one node on
its own". Parsing a run in isolation asks a different question and gives the wrong
answer: `- a` / blank / `- b` is a one-item list twice when each run is parsed alone,
and a single loose list when the document is parsed whole. The condition is also
necessary, not merely sufficient, so a lint or stamp that happens to agree outside
the subset (a marker-only chunk can fold a boundary difference out of the final block
list) is a coincidence rather than evidence of agreement.

Three ways a document leaves the subset, all of them common:

1. **A block boundary with no blank line at it.** CommonMark starts a new node at a
   heading, fence, quote, list, or thematic break whether or not a blank line
   precedes it; blank-line segmentation cannot see one. `# Heading` / `Body.` is one
   block under the baseline and two under CommonMark.
2. **A blank line inside one node**: a loose list, a fence or HTML block with an
   internal blank line, indented code. Two constructs of the same kind also merge
   across the blank line meant to separate them. This is the case CommonMark-tree
   attachment was written for.
3. **A run no single node covers**: a CommonMark parser consumes link reference
   definitions (`[label]: /url`) and emits no node, so a run of them is a block to
   the baseline and nothing to the tree segmenter.

**For authors**: put a blank line between block-level constructs, keep lists tight,
prefer fenced code and keep fences and HTML blocks free of internal blank lines, do
not place two lists of the same kind back to back, keep link reference definitions
out of a stayed document, and keep marker-shaped text out of code (a source-scanning
tool finds `<!-- stay:x -->` inside a fence; a tree-based one declines to bind it).

Version 1.1 stated this condition as "lists tight and fences free of internal blank
lines", which is case 2 alone: documents that plainly diverge, `# Heading` / `Body.`
first among them, were inside the stated subset while being outside the real one.
Version 1.2 does not change either segmenter to close cases 1 to 3; it states the
condition correctly and leaves the constraint with the author.

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
- **Granularity disagreement**: granularity pinned to whole blocks; loose lists and
  blank-line fences are handled by CommonMark-tree attachment (version 1.1).
- **Metadata read as content** (a `status:` flip drifts a hash; the two segmenters
  disagree about what frontmatter even is): leading YAML frontmatter is excluded from
  segmentation under both segmenters (version 1.2), so it is never stamped and never
  hashed.
- **Scope creep into an annotation product**: core stays at identity + resolution;
  annotation is a separate, layered spec.

## Non-goals

- Annotation, comment storage, threads.
- Transclusion / embedding.
- Row-level table identity, list-item identity, inline-span identity.
- A backend, accounts, or a hosted registry; any global or cross-repo namespace.

(Single-stay attachment for loose lists and blank-line-containing fences was a
version 1 non-goal; version 1.1 resolves it with CommonMark-tree attachment.)

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

## Version history

| Version | What it changed |
|---------|-----------------|
| **1.2** | Excludes leading YAML frontmatter from segmentation under both segmenters, and restates the two segmenters' agreement condition as the agreement subset, which version 1.1 stated too narrowly. Normative change to the attachment model; grammar, identity, hashing, and recovery unchanged. A marker already stamped onto frontmatter usually becomes an orphan error. |
| **1.1** | Adds CommonMark-tree attachment as an optional segmenter, so a loose list, a blank-line fence, or a blockquote with an internal blank line can carry a single stay. Adds no requirement to a baseline tool and changes no marker's meaning; its statement of when the two segmenters agree was corrected in 1.2. |
| **1.0** | The marker grammar, the identity model, blank-line attachment, hash normalisation, quote recovery and the commit rule, the detached state, and the AI editing contract. |

markstay does **not** offer a compatibility guarantee across versions at this stage.
Where a version corrects a defect, it corrects it rather than carrying the defect
forward behind a flag.
