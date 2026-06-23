"""The cache-key contract, framework-independent and unit-testable on its own.

A markstay cache is a ``{stay_id: body_hash}`` map: the id is the durable key, the
body hash is what flips when a block's content actually changes. Re-ingesting a
document is a three-way diff of the old map against the new one:

* **reuse**   , id present in both, hash unchanged   -> skip embedding (the win)
* **reembed** , id new, or id present but hash changed -> embed
* **evict**   , id gone from the document             -> drop from the store

A block that only *moved* keeps its id and its hash, so it lands in ``reuse``:
movement costs zero re-embeds. This is the property the plan sells, expressed
once here and asserted by ``test_cache.py``. ``langchain_adapter.py`` maps the
same contract onto LangChain's composite ``key_encoder``; the math is identical.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from chunker import Chunk


def index_map(chunks: Iterable[Chunk]) -> dict[str, str]:
    """Project chunks onto the ``{id: body_hash}`` cache map.

    This is the **single-document** contract: a stay id is unique only within a
    document (SPEC.md §12), so a bare-id key is correct for one document's chunks.
    Across documents the identity is ``(source, id)`` , the LangChain adapter folds
    ``source`` into its record key for exactly that reason. Here, a duplicate id in
    the batch raises ``ValueError`` rather than silently collapsing two blocks: the
    chunker already rejects in-document duplicates via lint, so a collision means a
    caller mixed two documents' chunks, which must be scoped by source first.
    """
    out: dict[str, str] = {}
    for c in chunks:
        if c.id in out:
            raise ValueError(f"duplicate chunk id {c.id!r} in batch (sources collide)")
        out[c.id] = c.body_hash
    return out


@dataclass(frozen=True)
class CacheDecision:
    """The three disjoint id sets produced by re-ingesting a document."""

    reuse: frozenset[str]
    reembed: frozenset[str]
    evict: frozenset[str]

    @property
    def saved(self) -> int:
        """Embeddings skipped on this re-ingest (the reused chunks)."""
        return len(self.reuse)


def decide(old: Mapping[str, str], new: Mapping[str, str]) -> CacheDecision:
    """Diff two ``{id: body_hash}`` maps into reuse / reembed / evict id sets."""
    reuse: set[str] = set()
    reembed: set[str] = set()
    for cid, h in new.items():
        if old.get(cid) == h:
            reuse.add(cid)
        else:
            reembed.add(cid)  # id is new, or its body hash changed
    evict = set(old) - set(new)
    return CacheDecision(frozenset(reuse), frozenset(reembed), frozenset(evict))
