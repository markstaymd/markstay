# Plate: completing `withBlockId`

[Plate](https://platejs.org/) is the first mainstream Markdown editor to write a block
id into the `.md` itself. Its `@platejs/markdown` serializer has a `withBlockId` option
that wraps every block:

```md
<block id="aTitleId01">
  ## Setup
</block>
```

The documented purpose is "to enable AI comment tracking", binding an annotation to a
block so it survives an edit. That is exactly the problem markstay exists for, and Plate
has taken the key step of putting the id in the source text rather than a separate
editor database. But `withBlockId` writes the id and stops there. markstay is the other
half.

!!! success "Headline"
    On a real Claude Sonnet rewrite of a 10-block document (mean block similarity 0.71),
    converting Plate's wrappers to markstay markers first:

    - **Drift:** markstay flags **6 of 8** edited blocks as content-changed; Plate's
      `<block id>` wrapper flags **0**, it carries no content fingerprint.
    - **Recovery after a full marker strip:** markstay re-identifies **6 of 8** blocks,
      **0 misattached**; Plate recovers **0**.
    - The conversion **round-trips losslessly** for supported blocks; Plate's own
      `deserializeMd` does not (see below).

## What Plate writes, and what it leaves out

`serialize({ withBlockId: true })` is **serialize-only**, verified against
`@platejs/markdown` 53.2.2:

- **No content fingerprint.** The wrapper is an id and nothing else. If an agent
  rewrites the block's text, the id still points at it, but nothing records that the
  content changed. You cannot tell a stale annotation from a current one.
- **No reader, and a lossy round-trip.** Feeding `withBlockId` output back through
  Plate's own `deserializeMd` recovers `id: null` for every block **and** turns each
  wrapper into a paragraph of literal `<block …>` text, flattening headings, code, and
  quotes and dropping inline marks. Re-importing a `withBlockId` document does not just
  lose the ids, it corrupts the content.
- **No recovery.** If the visible `<block>` wrapper is stripped (a reformat, a paste, an
  agent that drops it), the id is simply gone.

markstay carries the same id plus a body hash (the
[drift signal](spec.md), section 8) and a quote selector (the
[recovery model](spec.md), section 9), so it answers "did this block change?" and
"which new block is this old one?" that `withBlockId` cannot.

## The bridge

A small, dependency-free converter relocates each id from Plate's visible wrapper to
markstay's invisible trailing comment, at the same block boundary:

```md
## Setup
<!-- stay:aTitleId01 hash=sha256:0ecddf15e1af -->
```

The id is carried over **verbatim** (Plate's default `nanoid(10)` already satisfies the
markstay id grammar), now with a content hash and recoverability attached. A reverse
direction re-wraps a markstay document as `withBlockId`, so a Plate user can round-trip
through markstay and back, losslessly, which Plate's native deserialize cannot do.

The bridge is **fail-closed**. It converts the block kinds whose identity markstay can
carry under the dependency-free baseline, a heading, a paragraph, a single-paragraph
blockquote, or a closed code fence, and **rejects** anything else with a clear error
rather than guessing:

- **List items.** Plate wraps each list *item* as its own `<block>`, but a markstay
  marker identifies the [whole list](spec.md), not an item (list-item identity is a
  deferred extension). Per-item ids have nowhere to attach, so the bridge refuses them.
- **Tables, multi-paragraph or loose blocks, fences with internal blank lines.** Below
  the baseline's block granularity; deferred, not silently mismapped.

Refusing what it cannot map cleanly is the point: a converter that quietly produces a
wrong id is worse than one that tells you it cannot.

## The before/after

The demo runs in one command with no API key. It replays the same captured Sonnet
rewrite the [attachment study](evaluation.md) uses, so the numbers are a genuine
model's output while staying deterministic:

```text
Plate withBlockId vs markstay , what survives an AI edit of the same .md?

  source  : a real sonnet 'restructure' rewrite, mean block similarity 0.713
  doc     : 10 blocks; markstay bridges 8 (the list + table are below
            block granularity)
            skipped b4: "- The partner identifier resolves to an…"
            skipped b8: "| Stage | Retries | Backoff |"

WORKFLOW 1 , did a block's content drift? (edit, then check)
  markstay  : 6/8 bridged blocks flagged HASH_DRIFT (stored hash != new body)
  Plate     : 0/8 , the <block id> wrapper carries no hash, drift is undetectable

WORKFLOW 2 , the markers got stripped ("an AI deletes them"). Which old
            block is which new one?
  old id     tier      conf   recovered
  ----------------------------------------------------------
  b0-0ef9    hash      1.00  ✓ #0
  b1-453e    quote     0.75  ✓ #1
  b2-172a    quote     0.65  ✓ #2
  b3-6484    detached  0.44  ○ outdated
  b5-6088    quote     0.70  ✓ #4
  b6-7c6e    hash      1.00  ✓ #5
  b7-1f32    detached  0.50  ○ outdated
  b9-4451    quote     0.56  ✓ #7

HEADLINE
  Drift     : markstay flags 6 edited blocks; Plate flags 0 (no hash channel).
  Recovery  : 6/8 blocks re-identified after a full marker strip, 0 misattached.
              Plate recovers 0; exact-content match alone gets 2, the quote
              tier recovers the reworded rest.
```

## What you are seeing

**Workflow 1, drift.** The document is converted to markstay *before* the edit, so each
marker stores the block's pre-edit hash. After the rewrite, the six reworded blocks no
longer match their stored hash and are flagged; the unchanged title and code block are
not. Plate's wrapper has no hash to compare, so the same check on the `<block id>` form
is structurally impossible, it reports nothing.

**Workflow 2, recovery.** Every marker is deleted, the worst case the skeptic always
raises. markstay still re-identifies a block from its content hash (exact survivors like
the title and code) and, where the text was reworded, from the quote selector as the
clear best match. Two blocks were reworded past confident recognition; the
[section 9 commit rule](spec.md) refuses to guess and flags them outdated rather than
binding them to the wrong block. The run produces **zero wrong attachments**, the
property that makes recovery safe to rely on. Plate has no reader at all, so its
recovery here is zero.

## Honest scope

- The headline covers the **8 bridged blocks**. The document's list and table are
  reported as skipped, not hidden, they are below the baseline's block granularity, the
  same boundary the [public dogfood study](dogfood.md) documents.
- Recovery is best-effort and degrades as a rewrite drifts further from the original
  (the [attachment study](evaluation.md) measures the full curve). In normal use you
  would also give the model the [section 11 preservation instruction](spec.md) so the
  markers rarely get stripped at all; this demo is the worst case, markers fully gone,
  and identity still holds.
- The bridge is pinned to a captured `@platejs/markdown` format and re-verified when
  Plate bumps it, so the worked example tracks real Plate output rather than a guess.

## Where this fits

markstay does not change to read `<block id>` as a native marker, that visible wrapper
contradicts the invisible-comment design and would reopen the locked
[v1.1 spec](spec.md). The bridge consumes Plate's id as foreign input and produces
standard markstay markers, no new syntax. The core it builds on is the published
[`markstay` package](implementations.md); start with [Get started](get-started.md) to
stamp your own documents.
