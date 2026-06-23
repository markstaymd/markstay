# RAG: a cache key that survives the edit

Every RAG framework re-ingests Markdown constantly, and the leading ones already ship
an incremental indexer so a re-ingest only re-embeds what changed.
[LangChain](https://python.langchain.com/)'s `index()` pairs a `RecordManager` with a
`key_encoder`: it hashes each chunk a splitter produced and skips re-embedding the ones
whose key is unchanged, deleting the ones that vanished. That is the near-miss markstay
completes, the same shape as [Plate one ecosystem over](plate.md).

The flaw is in what gets hashed. The splitter's boundaries are byte- and size-derived,
so an edit early in a document reflows the chunks after it: their text changes, their
keys flip, and they re-embed even though their *content* did not. markstay supplies the
other half, a [stable block id](spec.md) that is the cache key and a
[body hash](spec.md) that flips only on a real content change.

!!! success "Headline (framing it honestly)"
    markstay's body hash *is* a content hash, so against the strongest honest baseline,
    a plain Markdown-block splitter with LangChain's default content-hash key, the pure
    embedding-savings delta is **0**. Both skip unchanged blocks; both re-embed changed
    ones. This page does **not** claim a savings number.

    What markstay adds *at the same embedding cost* is correctness a content hash cannot
    provide, proven live on real Claude Sonnet edits of a four-document corpus:

    - **Byte-identical blocks kept distinct.** A doc with two verbatim-identical blocks:
      the content-hash key stores **2** records (the duplicate collapses, one block is
      lost from the store); markstay stores **3**, both kept, distinct ids.
    - **A stable id across a content change.** When a block is reworded its id is
      unchanged while its body hash moves. A content hash is not an identity; it changes
      the instant the text does. The id is a durable handle (vector-store metadata, deep
      links, an i18n source-to-target map).
    - **Movement is free.** A section reorder re-embeds **0** chunks. This is a parity
      property, true for the content-hash baseline too, so it is reported as a property,
      not a markstay-exclusive win.

## What the native indexer does, and where it is blind

`index()` with a content-hash `key_encoder` is genuinely good at the common case: edit
one block, re-embed one block. markstay ties it there and cannot beat it. The blind
spots are not about *count*, they are about *identity*:

- **A content hash is not a durable id.** The key changes the moment the text does, so
  there is nothing stable to hang vector-store metadata, a deep link, or a translation
  pairing on. The whole value of "this is still the same logical block" is missing.
- **Byte-identical blocks collapse.** Two blocks with the same text hash to the same
  key, so the store keeps one record and silently drops the other. Repeated boilerplate
  (a shared note, an identical step) loses a retrievable unit. markstay keeps each block
  distinct because the id, not the text, is the key.
- **Offset splitters reflow.** A `RecursiveCharacterTextSplitter` re-embeds far more than
  the edited block because the edit shifts every downstream chunk boundary, and the
  amount is set by `chunk_size`, not by how much actually changed (quantified below).

## The adapter

A framework-neutral chunker emits **one chunk per stayed block**, so the cache key is
the stay id directly and a one-block edit invalidates exactly one chunk. The LangChain
binding is thin: it maps each chunk to a `Document` and sets

```python
key_encoder = lambda doc: f"{doc.metadata['source']}:{doc.metadata['stay_id']}:{doc.metadata['body_hash']}"
```

The `source` scope is load-bearing: a stay id is unique only *within* a document
([spec section 12](spec.md)), so two documents sharing an id and hash would otherwise
collapse to one vector record. Movement-immunity is unaffected, the source is constant
when a block moves inside its own document.

The chunker is **lint-first and fail-closed**. It runs the
[reference linter](linter.md) before any cache decision and rejects the whole document
on any error, an unstamped block, a malformed or duplicate marker, or a body hash that
no longer matches its block. A stale or half-stamped document must not be allowed to
seed a cache. It also refuses a block carrying more than one marker: a chunk cannot hold
two cache keys.

## The before/after

The demo runs in one command with no API key. It replays real Sonnet rewrites of a
four-document corpus, captured once into a frozen fixture (the same
[attachment-eval machinery](evaluation.md) that drives the LLM-survival study), so the
numbers are a genuine model's output while staying deterministic:

```text
markstay RAG cache demo , framing (B), real LLM edits replayed from demo_fixture.json (model=sonnet, $0)

1. RE-EMBED DISTRIBUTION (markstay vs the honest block-content-hash baseline)
   real edits; re-embeds measured through LangChain index(); reuse = saved embeddings

   doc                edit         blocks  markstay  block-hash  reused  parity
   caching.md         copyedit         11         2           2       9       =
   caching.md         restructure      11         7           7       4       =
   indexing.md        copyedit         11         0           0      11       =
   indexing.md        restructure      11         6           6       5       =
   observability.md   copyedit         11         1           1      10       =
   observability.md   restructure      11         7           7       4       =
   versioning.md      copyedit         11         1           1      10       =
   versioning.md      restructure      11         7           7       4       =

   -> markstay re-embeds EXACTLY the block-content-hash baseline at every intensity (delta 0).
      The win is not fewer embeddings; it is the correctness below, at the same cost.

2. CORRECTNESS MATRIX (what the re-embed count misses , framing B)

   (i)  movement (section reorder, intact): markstay 0 re-embeds, block-hash 0 , free for both (parity property)
   (ii) byte-identical duplicate blocks (doc has 3, two identical):
          block-content-hash -> 2 records (the duplicate COLLAPSED, one block lost from the store)
          markstay           -> 3 records (both kept, distinct ids)   << markstay-only correctness win
   (iii) stable id across a real content change (caching.md, copyedit):
          id EBbxHXpf unchanged; §8 hash 703d21f69911 -> 85ca18679dab
          the id is a durable handle; a content hash is not an identity (it changed)  << markstay-only

3. STRAWMAN CONTEXT , vs RecursiveCharacterTextSplitter, same edit (restructure);
   note the denominator differs (the splitter shreds 11 blocks into many chunks):
          chunk_size= 300 ->  15 of  18 chunks re-embedded
          chunk_size= 200 ->  21 of  25 chunks re-embedded
          chunk_size= 120 ->  35 of  39 chunks re-embedded
          the 'savings vs recursive' number is config-inflatable; not a headline.

HEADLINE: at parity embedding cost with the strongest honest baseline, markstay adds
  a portable block identity (survives edits + movement) and keeps byte-identical
  blocks distinct , correctness a content hash cannot provide. No dollar figure claimed.
```

## What you are seeing

**The distribution table (section 1).** Each row re-embeds the same real edit under
markstay-as-chunk and under the honest block-content-hash baseline, measured by counting
the embedding calls LangChain's `index()` actually makes. The two columns are equal on
every row: a copyedit touches one or two blocks, a restructure touches most of them, and
markstay tracks the content-hash baseline exactly. That is the point of leading with it.
markstay is not selling fewer embeddings.

**The correctness matrix (section 2).** This is what the count misses. A section reorder
costs **0** re-embeds for both. Two byte-identical blocks are kept as **two** records by
markstay and collapsed to **one** by the content-hash key, so the baseline silently loses
a retrievable block. A reworded block keeps its id while its body hash moves, so a handle
stored against that id (a citation, a translation link, a piece of vector metadata)
survives the edit. None of these is a savings number; all three are correctness.

**The strawman (section 3).** The large "savings vs `RecursiveCharacterTextSplitter`"
number you could quote is config-inflatable: the *same* edit re-embeds 15, 21, or 35
chunks depending only on `chunk_size`. Leading with it would be dishonest, so it is shown
as context and never as the headline.

## Honest scope

- **Block-as-chunk is a clean demo granularity, not the production one.** One chunk per
  block makes the cache key the stay id directly, which is what makes the count legible.
  But on real prose the block sizes are bimodal: a heading is its own tiny block, a
  paragraph is a healthy chunk. The production shape is an **aggregating splitter** (a
  heading plus its following prose as one chunk, keyed by a hash over its members'
  `{id, body_hash}`), named as the follow-up. The cache-hit *count* is unaffected by
  this; the retrieval realism is.
- **No savings claim.** The deliverable is the correctness matrix at parity cost, not a
  dollar figure, for the reasons the headline states.
- **One version in, one version out.** The chunker sees a single document, so it cannot
  detect a marker that was *relocated* onto the wrong block by an edit; that is the
  [section 7 `lint_diff`](spec.md) check the corpus is assumed to have already passed
  before ingestion.
- **LangChain is pinned.** The `index()` contract is captured against a specific
  langchain-core version with a drift-sentinel test, so a framework bump that changes the
  behaviour is caught rather than silently absorbed.

## Reproduce it

The chunker, the adapter, the demo, and the frozen fixture ship in
[`tools/examples/rag/`](https://github.com/markstaymd/markstay/tree/master/tools/examples/rag),
so the before/after above is inspectable with no clone of anything private, no network,
and no API key. The example consumes the published
[`markstay` package](implementations.md), the same Python core the chunker builds on, so
it runs the way a real LangChain user would:

```bash
git clone https://github.com/markstaymd/markstay
cd markstay/tools/examples/rag
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt   # markstay + the pinned langchain-core / text-splitters

python demo.py                    # replay the captured Sonnet edits ($0, no key)
python -m pytest                  # the cache-decision vectors + the demo's claims
```

`demo.py` replays the same captured Sonnet rewrites the
[attachment study](evaluation.md) froze into a fixture, so the contrast is a genuine
model's output while staying deterministic. The test suite pins the cache decisions by
*id set* (not just a count) across edit, move, insert, delete, split, and merge, re-runs
them through a real `index()`, and asserts the demo's headline, so none of it can
silently regress.

## Where this fits

markstay adds no syntax for this: the adapter reads standard `stay:` markers and the body
hash the [v1.1 spec](spec.md) already defines, and consumes the published
[`markstay` package](implementations.md) as a library. A LlamaIndex binding over the same
framework-neutral chunker, and the aggregating splitter above, are the named follow-ups.
To stamp your own corpus and try it, start with [Get started](get-started.md).
