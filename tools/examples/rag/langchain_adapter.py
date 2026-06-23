"""Thin LangChain binding: markstay chunks -> ``index()`` with a composite key.

The pinned LangChain contract: ``index()`` derives each record's identity from a
``key_encoder`` callable, with no separate caller-supplied content-hash field. So
the cache key is a *composite* ``f"{source}:{stay_id}:{body_hash}"``:

* block unchanged   -> same key -> ``index()`` skips it (no embedding);
* block content changed -> new body_hash -> new key -> embedded, old key deleted
  under ``cleanup="incremental"``;
* block moved but unchanged -> same key (no position/header metadata folded in)
  -> skipped.

This reproduces ``cache.decide`` exactly, against the framework's own machinery.
The pinned versions live in ``requirements.txt``; a LangChain bump that moves this
API is caught by ``test_cache.py``'s contract assertion, not silently drifted.
"""

from __future__ import annotations

from collections.abc import Iterable

from langchain_core.documents import Document
from langchain_core.indexing import InMemoryRecordManager, index
from langchain_core.vectorstores import InMemoryVectorStore

from chunker import Chunk


def key_encoder(doc: Document) -> str:
    """The composite record key: source + stay id (identity) + body hash (trigger).

    A stay id is unique only *within a document* (SPEC.md §12: the canonical
    address is ``document-address#stay-id``), so the document ``source`` must be in
    the key. Without it, two documents that happen to share a stay id and body hash
    would collapse onto one vector-store record, and a block moved between documents
    would skip re-embedding while keeping stale ``source`` metadata. Folding
    ``source`` in scopes identity per document; movement *within* a document keeps
    the same key (0 re-embeds) because ``source`` and the id are unchanged."""
    return f"{doc.metadata['source']}:{doc.metadata['stay_id']}:{doc.metadata['body_hash']}"


def to_document(c: Chunk) -> Document:
    """Map one markstay :class:`Chunk` onto a LangChain ``Document``. The cache key
    fields ride in metadata; ``source`` is the ``source_id_key`` group."""
    return Document(
        page_content=c.text,
        metadata={"source": c.source, "stay_id": c.id, "body_hash": c.body_hash},
    )


def to_documents(chunks: Iterable[Chunk]) -> list[Document]:
    return [to_document(c) for c in chunks]


def ingest(docs, record_manager, vector_store):
    """Run one indexing pass with the markstay composite key and incremental
    cleanup. Returns LangChain's ``IndexingResult`` (added/updated/skipped/
    deleted counts)."""
    return index(
        docs,
        record_manager,
        vector_store,
        cleanup="incremental",
        source_id_key="source",
        key_encoder=key_encoder,
    )


def fresh_store(embeddings, namespace: str = "markstay-rag"):
    """A ready-to-use (record_manager, vector_store) pair backed by the in-memory
    stores. ``embeddings`` is any LangChain ``Embeddings`` (a counting wrapper in
    the tests/demo; a real model under ``demo.py --real-embed``)."""
    rm = InMemoryRecordManager(namespace=namespace)
    rm.create_schema()
    vs = InMemoryVectorStore(embeddings)
    return rm, vs
