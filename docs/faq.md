# FAQ

## Why not just use heading anchors?

Heading anchors are generated from heading text, so they drift the moment the heading
changes. Rename `## Setup` to `## Installation` and `#setup` is gone. They also only
exist at heading granularity: there is no anchor for "the third paragraph" or "this
bullet". GitHub, MyST, Docusaurus, and MkDocs all document this drift for generated
anchors. markstay ids are assigned once and never derived from text, so editing the
block does not change its identity.

## Why not UUIDs?

UUIDs are allowed but not required. The objection is cost, not correctness. A document
with a marker after every block, each carrying a 36-character UUID, is heavy to read
in source and expensive in tokens when an agent processes it. A short generated id
(`stay:8f24c9a1`) collides rarely enough within a single document and is far cheaper.
UUIDs remain available for systems that sync ids into an external database and need
global uniqueness.

## Why not an external annotation database?

Two reasons. First, portability: ids that live in a database belong to one application.
Move the Markdown to another tool, export it, or hand it to an agent, and the identity
is gone. Notion, Logseq, and Roam all have excellent block ids that do not survive
leaving the product. markstay's whole premise is that the id should travel *in the
text*. Second, scope: a database implies a backend, accounts, and a service to run.
markstay is meant to be a source-level convention with no infrastructure.

## Why not HTML `id` attributes or `<a name>` anchors?

Raw HTML anchors render into the output DOM, can be stripped by sanitisers more
aggressively than comments, and sit awkwardly next to block-level content. HTML
comments are invisible in rendered Markdown, are preserved as source text by most tools
even when they are dropped from the rendered output, and read to a language model as
metadata rather than content. In the [evaluation](evaluation.md) the comment form tied
or marginally beat every alternative for LLM survival.

## Is markstay an annotation system?

No. It is an identity primitive. Annotation, commenting, transclusion, AI editing, and
cross-references are *consumers* that could build on top of stable block ids. Keeping
the core to identity and recovery (and out of comment storage, threads, and UI) is a
deliberate non-goal, because the moment it becomes an annotation product it stops being
a thing other annotation products can adopt.

## Is Markdown even the right layer?

v1 makes the call: the source layer. Markdown is already the interchange format for
human and agent edits, it travels across tools, and it diffs cleanly in Git, so the id
should travel in the text. The argument against, that an editor or a sidecar file could
carry richer identity without cluttering the prose, is real, but the
[evaluation](evaluation.md) found the sidecar approach worse where it matters most:
out-of-band frontmatter survived LLM editing *worse* than inline markers. Disagreement
is still welcome and would inform later versions.

## Will LLMs actually preserve the markers?

Only if they are told to. This was measured, not assumed (see the
[findings](evaluation.md)). Structure-preserving edits (translation, targeted changes)
keep markers regardless. Full-document rewrites and "clean up" passes strip nearly all
of them when the model is not told, and keep all of them when it is. The practical
consequence is that durability for agent workflows is a *preservation contract* (an
explicit instruction plus a post-edit [linter](linter.md)), not a property of the
syntax.

## Won't a comment after every block clutter my source?

It adds one line per identified block in the raw `.md`. It is invisible in rendered
output, so readers never see it. Coverage is also a choice: you can mark only the
blocks something needs to reference (authored landmarks) rather than every block. Dense
automatic coverage is for tooling that wants to address everything; a human author can
use a handful of human-readable ids.

## What about MDX?

HTML comments are invalid in MDX v2, so MDX uses a profile: the same marker written as
a JSX comment, `{/* stay:8f24 */}`. One data model, two serialisations. `.md` files use
the HTML-comment form.

## Why now?

Because the use case that makes block identity urgent did not exist at scale until
recently: agents that read, edit, and regenerate Markdown documents as a routine part
of their work. Code already has a strong identity substrate (paths, symbols, commit-
anchored lines). Markdown prose does not, and agents fall back to fuzzy text matching
that breaks under ordinary edits. The gap was tolerable when only humans edited
Markdown by hand; it is sharper now.

## Is "markstay" the final name?

Yes. The project name is markstay; the marker token is the shorter `stay:`. Version 1
of the specification is settled too.

## How do I disagree with this?

Open an issue at [markstaymd/markstay](https://github.com/markstaymd/markstay). v1 is
settled but young; a well-argued "this is unnecessary", "this is the wrong layer", or
"this case isn't covered" is exactly the feedback that shapes later versions.
