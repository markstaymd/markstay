"""markstay-aware chunker: one chunk per stayed Markdown block.

Turns a *stamped* Markdown document into a list of :class:`Chunk` objects whose
``id`` is the stay id (the stable, edit- and movement-resilient cache key,
SPEC.md §6) and whose ``body_hash`` is the §8 content hash (the re-embed
trigger). Framework-neutral: it composes the published ``markstay`` package's read
side (``lint_document``, ``body_hash``) and adds no new core primitive. The LangChain binding lives in
``langchain_adapter.py``; the cache decision in ``cache.py``.

Preconditions enforced before any chunk is emitted (a poisoned cache is worse
than a loud failure, plan Phase 1):

* **lint clean** , every lint *error* (duplicate id, malformed/orphan marker) plus
  the ``HASH_DRIFT`` *warning* (which core lint rates non-fatal) raises
  ``ChunkError`` before a single cache decision is made;
* **fully stamped** , a content block with no stay marker is an error, not a
  silent skip (a partial cache re-embeds the unstamped blocks on every run);
* **one marker per block** , a chunk carries exactly one cache key, so a block
  with multiple stay markers is rejected. The spec permits multiple markers on a
  block; this adapter deliberately does not.

Limitation: ``lint_document`` sees a single version, so it cannot detect a marker
that was *relocated* onto a different block (two markers swapped reads as clean).
That is a regeneration-diff concern (``lint_diff`` against a baseline, SPEC.md
§7); this layer assumes the stamped input was already validated that way before
ingestion. The demo sidesteps it by restamping a marker-preserving rewrite.
"""

from __future__ import annotations

from dataclasses import dataclass

from markstay import body_hash, lint_document

# Findings that are fatal for a *cache source*. Lint's own errors (duplicate id,
# malformed/orphan marker) are always fatal. HASH_DRIFT is only a lint *warning*
# (§8: "you edited in place, run restamp"), but for an ingestion cache it is
# fatal: a stored hash that disagrees with its block means an un-restamped edit,
# so the document's markers are not authoritative and must not seed a cache until
# a deliberate restamp acknowledges the change.
_FATAL_WARN_CODES = {"HASH_DRIFT"}


@dataclass(frozen=True)
class Chunk:
    """One stayed block, ready to embed. ``id`` is the cache key, ``body_hash``
    is the re-embed trigger, ``source`` groups chunks by document."""

    id: str
    text: str
    body_hash: str
    source: str


class ChunkError(ValueError):
    """The document violates a chunker precondition (see the module docstring)."""


def chunk(md: str, source: str) -> list[Chunk]:
    """Chunk a stamped document into one :class:`Chunk` per stayed block.

    Raises :class:`ChunkError` if the document does not lint clean, carries an
    unstamped content block, or carries a block with more than one stay marker.
    """
    blocks, findings = lint_document(md)
    fatal = [
        f for f in findings
        if f.level == "error" or f.code in _FATAL_WARN_CODES
    ]
    if fatal:
        detail = "\n  ".join(
            f"{f.code}: {f.message}" + (f" (id={f.id})" if f.id else "")
            for f in fatal
        )
        raise ChunkError(
            f"{source}: document does not lint clean; refusing to chunk a "
            f"poisoned cache source:\n  {detail}"
        )

    chunks: list[Chunk] = []
    for b in blocks:
        if b.index < 0:
            continue  # orphan marker chunk; lint would have errored if it mattered
        ids = [m.id for m in b.markers if m.id and not m.malformed]
        if not ids:
            raise ChunkError(
                f"{source}: content block at line {b.line} is unstamped; every "
                f"block must be stayed before chunking (run `markstay stamp` first)."
            )
        if len(ids) > 1:
            raise ChunkError(
                f"{source}: block at line {b.line} carries {len(ids)} stay markers "
                f"({', '.join(ids)}); one cache key per chunk is required."
            )
        chunks.append(
            Chunk(id=ids[0], text=b.content, body_hash=body_hash(b.content), source=source)
        )
    return chunks
