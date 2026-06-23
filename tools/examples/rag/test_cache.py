"""Phase 1 cache-decision vectors , committed as a permanent regression test.

For a fixed (stamped doc, edit) pair, the reuse / reembed / evict id sets must
equal the expected sets, asserted **by id, not by count** (plan Acceptance
gates). The same scenarios are pushed through LangChain's real ``index()`` to
prove the framework re-embeds exactly the ids ``cache.decide`` names , the
movement case re-embedding **zero** is the signature property.

Edited fixtures are derived deterministically from one stamped base via
``markstay.stamp``/``restamp`` (mint ``id0..id3`` on the base, ``id100`` for any
block a structural edit adds), so the expected id sets below are stable, not
flaky random ids.
"""

from __future__ import annotations

import hashlib
import itertools
import os

import pytest

import markstay
from markstay import lint_document
from cache import decide, index_map
from chunker import ChunkError, chunk
from langchain_adapter import fresh_store, ingest, to_documents

from langchain_core.embeddings import Embeddings

# --- deterministic stamping helpers -----------------------------------------

BASE_PLAIN = (
    "Alpha paragraph introduces the caching idea in plain prose.\n\n"
    "Beta paragraph covers the indexing approach in plain prose.\n\n"
    "Gamma paragraph explains the versioning rules in plain prose.\n\n"
    "Delta paragraph summarizes the logging setup in plain prose.\n"
)
ALL = {"id0", "id1", "id2", "id3"}


def _stamp(plain: str, start: int = 0) -> str:
    c = itertools.count(start)
    return markstay.stamp(plain, new_id=lambda: f"id{next(c)}").text


def _normalize(md: str, mint_start: int = 100) -> str:
    """Fill any block a structural edit left unmarked, then refresh drifted
    hashes. Existing ids are preserved (that is the whole point); new blocks mint
    from ``mint_start`` so they are predictable (``id100``)."""
    c = itertools.count(mint_start)
    stamped = markstay.stamp(md, new_id=lambda: f"id{next(c)}").text
    return markstay.restamp(stamped).text


BASE = _stamp(BASE_PLAIN)


def _units(md: str) -> list[str]:
    return [u.strip() for u in md.split("\n\n") if u.strip()]


def _join(units: list[str]) -> str:
    return "\n\n".join(units) + "\n"


def _content_and_marker(unit: str) -> tuple[str, str]:
    lines = unit.split("\n")
    assert lines[-1].strip().startswith("<!-- stay:"), unit
    return "\n".join(lines[:-1]), lines[-1]


def _set_content(unit: str, new_content: str) -> str:
    _, marker = _content_and_marker(unit)
    return new_content + "\n" + marker


# --- the seven edited variants ----------------------------------------------

def _edit_one() -> str:
    u = _units(BASE)
    u[1] = _set_content(u[1], "Beta paragraph now says something completely different.")
    return _normalize(_join(u))


def _move() -> str:
    return _normalize(_join(list(reversed(_units(BASE)))))


def _insert() -> str:
    u = _units(BASE)
    u.insert(2, "Epsilon paragraph is brand new in the document body.")
    return _normalize(_join(u))


def _delete() -> str:
    u = _units(BASE)
    del u[2]  # drop Gamma (id2) entirely
    return _normalize(_join(u))


def _split() -> str:
    u = _units(BASE)
    _, marker = _content_and_marker(u[1])  # id1 stays on the second half
    u[1] = (
        "Beta first half about indexing internals.\n\n"
        "Beta second half about index maintenance.\n" + marker
    )
    return _normalize(_join(u))


def _merge() -> str:
    u = _units(BASE)
    c2, _ = _content_and_marker(u[2])  # Gamma id2, marker dropped
    c3, m3 = _content_and_marker(u[3])  # Delta id3, marker kept
    u[2] = c2 + "\n" + c3 + "\n" + m3  # one block, id3
    del u[3]
    return _normalize(_join(u))


def _rewrite_all() -> str:
    u = _units(BASE)
    for i, word in enumerate(("Alpha", "Beta", "Gamma", "Delta")):
        u[i] = _set_content(u[i], f"{word} paragraph entirely reworded into new prose.")
    return _normalize(_join(u))


# name -> (new_md, reembed, evict, reuse)
SCENARIOS: dict[str, tuple[str, set[str], set[str], set[str]]] = {
    "edit_one": (_edit_one(), {"id1"}, set(), {"id0", "id2", "id3"}),
    "move": (_move(), set(), set(), set(ALL)),
    "insert": (_insert(), {"id100"}, set(), set(ALL)),
    "delete": (_delete(), set(), {"id2"}, {"id0", "id1", "id3"}),
    "split": (_split(), {"id1", "id100"}, set(), {"id0", "id2", "id3"}),
    "merge": (_merge(), {"id3"}, {"id2"}, {"id0", "id1"}),
    "rewrite_all": (_rewrite_all(), set(ALL), set(), set()),
}


# --- cache-decision id sets (the load-bearing assertion) --------------------

@pytest.mark.parametrize("name", list(SCENARIOS))
def test_cache_decision_id_sets(name):
    new_md, reembed, evict, reuse = SCENARIOS[name]
    old_map = index_map(chunk(BASE, "doc.md"))
    new_map = index_map(chunk(new_md, "doc.md"))
    d = decide(old_map, new_map)
    assert d.reembed == reembed, name
    assert d.evict == evict, name
    assert d.reuse == reuse, name
    # the three sets partition: reuse+reembed = new ids, evict = old-only ids
    assert d.reuse | d.reembed == set(new_map)
    assert d.evict == set(old_map) - set(new_map)


def test_move_is_zero_reembeds():
    """The property the plan sells, isolated and named."""
    d = decide(index_map(chunk(BASE, "doc.md")), index_map(chunk(_move(), "doc.md")))
    assert d.reembed == set()
    assert d.reuse == set(ALL)


def test_one_block_edit_is_one_reembed_regardless_of_position():
    for victim in ("id0", "id1", "id2", "id3"):
        u = _units(BASE)
        idx = int(victim[2:])
        u[idx] = _set_content(u[idx], f"Reworded body for block {victim} only.")
        d = decide(index_map(chunk(BASE, "doc.md")),
                   index_map(chunk(_normalize(_join(u)), "doc.md")))
        assert d.reembed == {victim}, victim
        assert d.evict == set()


# --- the LangChain contract: index() re-embeds exactly decide().reembed ------

class CountingEmbeddings(Embeddings):
    """Records every text index() asks it to embed, so we measure real re-embeds."""

    def __init__(self):
        self.embedded: list[str] = []

    def _vec(self, text: str):
        h = hashlib.sha256((text or " ").encode()).digest()
        return [b / 255.0 for b in h[:8]]

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def _measure_reembeds(old_md: str, new_md: str) -> int:
    emb = CountingEmbeddings()
    rm, vs = fresh_store(emb, namespace="contract")
    ingest(to_documents(chunk(old_md, "doc.md")), rm, vs)  # cold
    emb.embedded.clear()
    ingest(to_documents(chunk(new_md, "doc.md")), rm, vs)  # re-ingest
    return len(emb.embedded)


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_langchain_reembeds_match_decision(name):
    new_md, reembed, _, _ = SCENARIOS[name]
    measured = _measure_reembeds(BASE, new_md)
    assert measured == len(reembed), f"{name}: index() embedded {measured}, expected {len(reembed)}"


def test_two_documents_sharing_a_stay_id_stay_distinct():
    """SPEC.md §12: a stay id is unique only within a document. Two docs that share
    an id AND identical block content must NOT collapse onto one vector record , the
    source-scoped record key keeps them apart (codex review, P1)."""
    # same plain prose, stamped with the SAME deterministic ids in both "documents"
    a = _stamp(BASE_PLAIN)
    b = _stamp(BASE_PLAIN)
    assert set(index_map(chunk(a, "a.md"))) == set(index_map(chunk(b, "b.md")))  # ids collide
    emb = CountingEmbeddings()
    rm, vs = fresh_store(emb, namespace="crossdoc")
    docs = to_documents(chunk(a, "a.md")) + to_documents(chunk(b, "b.md"))
    res = ingest(docs, rm, vs)
    assert res["num_added"] == 8, "two 4-block docs sharing ids must store 8 distinct records"
    assert len(emb.embedded) == 8


def test_langchain_cold_index_embeds_every_block():
    emb = CountingEmbeddings()
    rm, vs = fresh_store(emb, namespace="cold")
    res = ingest(to_documents(chunk(BASE, "doc.md")), rm, vs)
    assert len(emb.embedded) == 4
    assert res["num_added"] == 4


# --- preconditions: a poisoned cache source must fail loudly -----------------

def test_unstamped_block_raises():
    u = _units(BASE)
    content, _ = _content_and_marker(u[1])
    u[1] = content  # strip the marker: an unstamped content block
    with pytest.raises(ChunkError, match="unstamped"):
        chunk(_join(u), "doc.md")


def test_multi_marker_block_raises():
    u = _units(BASE)
    content, marker = _content_and_marker(u[0])
    extra = markstay.format_marker("zzzz9999", hash=markstay.body_hash(content))
    u[0] = content + "\n" + marker + "\n" + extra  # two well-formed markers, one block
    with pytest.raises(ChunkError):
        chunk(_join(u), "doc.md")


def test_hash_drift_raises():
    # corrupt a stored hash so lint reports drift; the chunker must refuse.
    broken = BASE.replace("sha256:", "sha256:deadbeef", 1)
    with pytest.raises(ChunkError):
        chunk(broken, "doc.md")


# --- a stamped corpus parses clean and chunks one-per-marker -----------------

CORPUS = os.path.join(os.path.dirname(__file__), "corpus")


@pytest.mark.parametrize(
    "name", sorted(n for n in os.listdir(CORPUS) if n.endswith(".md"))
)
def test_js_stamped_corpus_roundtrips(name):
    md = open(os.path.join(CORPUS, name), encoding="utf-8").read()
    _, findings = lint_document(md)
    assert findings == [], (name, [f.code for f in findings])  # zero lint, the gate
    chunks = chunk(md, name)  # raises if any fatal finding
    assert len(chunks) == md.count("<!-- stay:")
    assert all(c.id and c.body_hash for c in chunks)
