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
      `deserializeMd` restores neither the ids nor the block types (see below).

## What Plate writes, and what it leaves out

`serialize({ withBlockId: true })` is **serialize-only**, verified against
`@platejs/markdown` 53.2.2 and 53.5.3:

- **No content fingerprint.** The wrapper is an id and nothing else. If an agent
  rewrites the block's text, the id still points at it, but nothing records that the
  content changed. You cannot tell a stale annotation from a current one.
- **No reader.** Feeding `withBlockId` output back through Plate's own `deserializeMd`
  recovers `id: null` for every block **and** turns each wrapper into a paragraph of
  literal `<block …>` text, so a heading, code block or quote inside it is no longer one in
  the editor. Through 53.3.17 that paragraph also flattened the content and dropped inline
  marks, so re-importing corrupted the document. From 53.3.18 it keeps the source as raw
  text and writes it back on save, which stops the corruption and still restores no id
  and no block type.
- **No recovery.** If the visible `<block>` wrapper is stripped (a reformat, a paste, an
  agent that drops it), the id is simply gone.

markstay carries the same id plus a body hash (the
[drift signal](spec.md), section 8) and a quote selector (the
[recovery model](spec.md), section 9), so it answers "did this block change?" and
"which new block is this old one?" that `withBlockId` cannot.

### Plain Plate saves of markstay documents

Since 53.3.18, markstay's own markers survive a plain Plate save. With Plate's
recommended `remarkGfm` + `remarkMdx` setup and its list and table plugins, a markstay
document loaded into and saved from a headless Plate editor with no markstay code keeps
every block, list-item and table-row marker on its block. That was measured at 53.3.18
and 53.5.3 on one document carrying 10 markers. The save has two costs:

- **A blank line before each block marker.** Readers still bound each block marker to
  the block above in that document, but the blank line breaks the
  [§5](spec.md#5-attachment-model) writer rule, which puts a marker directly after its
  block's last line of content. That rule matters for a block with blank lines inside
  it, such as a loose list or a fence with internal blank lines, and neither was tested.
  Nor was the MDX comment-expression marker form.
- **List and table reformatting.** Plate rewrites list glyphs and pads table cells,
  which drifts those blocks' hashes once until you restamp.

Without `remarkMdx`, every version from 53.2.2 to 53.5.3 rewrites each marker as escaped
`{/\* … \*/}` text that no reader recognises.

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
through markstay and back with ids and block types intact, which Plate's native
deserialize does not restore.

The bridge is **fail-closed**. It converts the block kinds whose identity markstay can
carry under the dependency-free baseline, a heading, a paragraph, a single-paragraph
blockquote, or a closed code fence, and **rejects** anything else with a clear error
rather than guessing:

- **List items.** Plate wraps each list *item* as its own `<block>`. The bridge
  does not implement the optional [child identity](spec.md#55-child-block-identity-list-items-v13)
  in §§5.5-5.6, so per-item ids have no mapping here.
- **Tables, multi-paragraph or loose blocks, fences with internal blank lines.**
  Outside the bridge's validated subset; refused without conversion.

`fromPlate` writes each marker on a separate line after the block, and the editor
API's `serializeStay` delegates to it. Neither reaches the list-item or table-row
carrier covered by [§3.4](spec.md#34-a-marker-that-shares-a-line-with-content-v18).
On import, `toPlate` and `deserializeStay` refuse input carrying a `subhash`
marker, because the bridge cannot preserve child identity through conversion.

Refusing what it cannot map cleanly is the point: a converter that quietly produces a
wrong id is worse than one that tells you it cannot.

## The before/after

The demo runs in one command with no API key. It replays the same captured Sonnet
rewrite the [attachment study](evaluation.md) uses, so the numbers are a genuine
model's output while staying deterministic. This is its full output against the
published `markstay` 0.14.0:

```text
Plate withBlockId vs markstay , what survives an AI edit of the same .md?

  source  : a real sonnet 'restructure' rewrite (captured 2026-06-22), mean block similarity 0.713
  doc     : 10 blocks; markstay bridges 8 (the list + table are below block granularity, SPEC §5.1/§14)
            skipped b4-91e5: "- The partner identifier resolves to an…"
            skipped b8-1f07: "| Stage | Retries | Backoff |"

WORKFLOW 1 , did a block's content drift? (edit, then check)
  markstay  : 6/8 bridged blocks flagged HASH_DRIFT (stored §8 hash != new body)
              · b1-453e drifted
              · b2-172a drifted
              · b3-6484 drifted
              · b5-6088 drifted
              · b7-1f32 drifted
              · b9-4451 drifted
  Plate     : 0/8 , the <block id> wrapper carries no hash, so drift is undetectable
              (0 markstay markers survive in the Plate form, by construction)

WORKFLOW 2 , the markers got stripped (the skeptic's "an AI deletes them").
            Which old block is which new one?
  old id     tier      conf   recovered
  ----------------------------------------------------------
  b0-0ef9    hash      1.00  ✓ #0
  b1-453e    quote     0.77  ✓ #1
  b2-172a    quote     0.67  ✓ #2
  b3-6484    detached  0.46  ○ outdated 
  b5-6088    quote     0.73  ✓ #4
  b6-7c6e    hash      1.00  ✓ #5
  b7-1f32    detached  0.51  ○ outdated 
  b9-4451    quote     0.57  ✓ #7

HEADLINE
  Drift     : markstay flags 6 edited blocks; Plate flags 0 (no hash channel).
  Recovery  : 6/8 blocks re-identified after a full marker strip, 0 misattached.
              Plate recovers 0 (no reader; its deserialize returns id:null). Exact-content
              match alone gets 2; the §9 quote tier recovers the reworded rest.

So Plate writes the id; markstay makes it mean something across an edit: it
detects the drift and re-finds the block when the marker is gone.
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
property to look for, on this one document. Plate has no reader at all, so its
recovery here is zero.

## Honest scope

- The headline covers the **8 bridged blocks**. The document's list and table are
  reported as skipped because this adapter does not support their conversion.
- Recovery is best-effort and degrades as a rewrite drifts further from the original
  (the [attachment study](evaluation.md) measures the full curve). In normal use you
  would also give the model the [section 11 preservation instruction](spec.md) so the
  markers rarely get stripped at all; this demo is the worst case, markers fully gone,
  and the stored evidence still finds most blocks.
- The bridge is pinned to a captured `@platejs/markdown` format and re-verified when
  Plate bumps it, so the worked example tracks real Plate output rather than a guess.

## Reproduce it

The bridge, the demo, and their fixtures ship in
[`tools/examples/plate/`](https://github.com/markstaymd/markstay/tree/master/tools/examples/plate),
so the before/after above is inspectable with no clone of anything private, no network,
and no API key. The example consumes the published
[`markstay` package](implementations.md), the same core the bridge builds on, so it runs
the way a real Plate user would:

```bash
git clone https://github.com/markstaymd/markstay
cd markstay/tools/examples/plate
npm i                  # pulls the published `markstay` package
node demo.js           # replay the captured rewrite ($0, no key)
node --test            # the bridge round-trip, fail-closed, and demo self-tests
```

`demo.js` replays the same captured Sonnet rewrite the [attachment study](evaluation.md)
froze into a fixture, so the contrast is a genuine model's output while staying
deterministic. The `node --test` suite pins the bridge's supported subset (heading,
paragraph, single-paragraph blockquote, closed fence), its fail-closed rejections of
everything else, and the demo's headline, so none of it can silently regress.

## Where this fits

markstay does not change to read `<block id>` as a native marker, that visible wrapper
contradicts the invisible-comment design and would reopen the settled
[spec](spec.md). The bridge consumes Plate's id as foreign input and produces
standard markstay markers, no new syntax. The core it builds on is the published
[`markstay` package](implementations.md); start with [Get started](get-started.md) to
stamp your own documents.
