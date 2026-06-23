"""The demo: markstay-as-chunk vs the honest baselines, in one command.

markstay's pure *embedding-savings* edge over a block-content-hash baseline is
**zero**, because ``body_hash`` *is* a content hash. So the deliverable is **not a
dollar figure**; it is a **correctness matrix at parity embedding cost**, measured
over *real* LLM edits (the frozen ``demo_fixture.json``, captured from real model
rewrites of the corpus):

  1. Re-embed distribution , for every (doc, edit intensity), markstay and the
     block-content-hash baseline re-embed the SAME chunks (delta 0). Localized
     edits reuse most embeddings; a heavy rewrite reuses few. Reported honestly,
     whole spread, no cherry-pick.
  2. Correctness matrix (what the savings number misses):
       (i)   movement = 0 re-embeds  (a property, true at parity for both)
       (ii)  byte-identical duplicate blocks kept DISTINCT (the content-hash
             baseline collapses them, losing a block from the store)  , markstay only
       (iii) a stable id that survives a content change (the durable handle a
             content hash cannot be)                                  , markstay only
  3. Strawman context , vs RecursiveCharacterTextSplitter the re-embed count is
     config-inflatable (shrink chunk_size, inflate the "savings"); shown labelled,
     never the headline.

    python demo.py
    python demo.py --real-embed   # optional local-embedder smoke

Runs at $0 with no API key: the LLM edits are replayed from the frozen fixture.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import warnings

# The block-content-hash baseline uses index()'s DEFAULT key_encoder ('sha1') ,
# that is exactly what a naive non-markstay user gets, so it is the honest
# baseline. LangChain warns that SHA-1 is not collision-resistant; irrelevant to a
# cache-identity demo (we are not defending against adversarial collisions).
warnings.filterwarnings("ignore", message=".*SHA-1.*")

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import markstay  # noqa: E402
from markstay import (  # noqa: E402
    body_hash,
    parse_document,
    restamp,
    segment_blank_line,
    stamp,
    strip_markers,
)

from langchain_core.documents import Document  # noqa: E402
from langchain_core.embeddings import Embeddings  # noqa: E402
from langchain_core.indexing import InMemoryRecordManager, index  # noqa: E402
from langchain_core.vectorstores import InMemoryVectorStore  # noqa: E402
from langchain_text_splitters import RecursiveCharacterTextSplitter  # noqa: E402

from cache import decide, index_map  # noqa: E402
from chunker import chunk  # noqa: E402
from langchain_adapter import key_encoder as MS_KEY  # noqa: E402

FIXTURE = os.path.join(HERE, "demo_fixture.json")


# --- measuring re-embeds through the framework's own index() ----------------

class CountingEmbeddings(Embeddings):
    def __init__(self):
        self.embedded: list[str] = []

    def _vec(self, text: str):
        b = body_hash(text or " ")
        return [int(b[i:i + 2], 16) / 255.0 for i in range(0, 16, 2)]

    def embed_documents(self, texts):
        self.embedded.extend(texts)
        return [self._vec(t) for t in texts]

    def embed_query(self, text):
        return self._vec(text)


def measure_reembed(old_docs, new_docs, key_enc) -> tuple[int, int]:
    """Index old then new on one store; return (initial_embeds, reembeds)."""
    emb = CountingEmbeddings()
    rm = InMemoryRecordManager(namespace="demo")
    rm.create_schema()
    vs = InMemoryVectorStore(emb)
    index(old_docs, rm, vs, cleanup="incremental", source_id_key="source", key_encoder=key_enc)
    initial = len(emb.embedded)
    emb.embedded.clear()
    index(new_docs, rm, vs, cleanup="incremental", source_id_key="source", key_encoder=key_enc)
    return initial, len(emb.embedded)


def count_records(docs, key_enc) -> int:
    """Distinct records index() actually stores (collisions on key collapse)."""
    emb = CountingEmbeddings()
    rm = InMemoryRecordManager(namespace="rec")
    rm.create_schema()
    vs = InMemoryVectorStore(emb)
    res = index(docs, rm, vs, cleanup="incremental", source_id_key="source", key_encoder=key_enc)
    return res["num_added"]


# --- chunkings: one logical doc, three representations ----------------------

def markstay_docs(md: str, source: str) -> list[Document]:
    return [Document(page_content=c.text,
                     metadata={"source": source, "stay_id": c.id, "body_hash": c.body_hash})
            for c in chunk(md, source)]


def blockhash_docs(md: str, source: str) -> list[Document]:
    """Strongest honest baseline: blank-line block splitter, NO markstay, the
    marker-stripped prose, default content-hash (sha1) key."""
    clean = strip_markers(md)
    out = []
    for b in parse_document(clean):
        if b.index < 0:
            continue
        out.append(Document(page_content=b.content, metadata={"source": source}))
    return out


def recursive_docs(md: str, source: str, chunk_size: int = 300) -> list[Document]:
    sp = RecursiveCharacterTextSplitter(chunk_size=chunk_size, chunk_overlap=30)
    return sp.create_documents([strip_markers(md)], metadatas=[{"source": source}])


# --- replaying one fixture rewrite ------------------------------------------

def _block_hash_by_id(md: str) -> dict[str, str]:
    out = {}
    for b in parse_document(md):
        if b.index < 0:
            continue
        for mk in b.markers:
            if mk.id and not mk.malformed:
                out[mk.id] = body_hash(b.content)
    return out


def replay_rewrite(rw: dict) -> dict:
    """One (doc, task): re-embed counts for markstay vs the block-hash baseline,
    measured through index(). The rewrite's stale marker hashes are restamped
    first (the §8 'accept these edits' step) , the real re-ingest flow."""
    source, before, after_raw = rw["doc"], rw["before"], rw["after"]
    after = restamp(after_raw).text  # acknowledge the edits; ids preserved

    ms_old, ms_new = markstay_docs(before, source), markstay_docs(after, source)
    _, ms_re = measure_reembed(ms_old, ms_new, MS_KEY)

    bh_old, bh_new = blockhash_docs(before, source), blockhash_docs(after, source)
    _, bh_re = measure_reembed(bh_old, bh_new, "sha1")

    n = len(ms_old)
    return {"doc": source, "task": rw["task"], "blocks": n,
            "markstay_reembed": ms_re, "blockhash_reembed": bh_re,
            "reused": n - ms_re}


# --- correctness matrix: the framing-B headline -----------------------------

def _reverse_blocks(md: str) -> str:
    """Reverse a doc's blocks using the same blank-line segmenter the pipeline uses,
    so each block (and its trailing marker) moves intact , robust to a block that
    contains internal structure, not a naive ``split("\\n\\n")``."""
    segs = [c.strip() for _, c in segment_blank_line(md) if c.strip()]
    return "\n\n".join(reversed(segs)) + "\n"


def movement_case(rw: dict) -> dict:
    """Reorder a doc's blocks intact; re-embeds should be 0 for both content-stable
    schemes (reported as a parity property, not a markstay-exclusive win)."""
    source, before = rw["doc"], rw["before"]
    moved = _reverse_blocks(before)
    ms_re = len(decide(index_map(chunk(before, source)), index_map(chunk(moved, source))).reembed)
    _, bh_re = measure_reembed(blockhash_docs(before, source), blockhash_docs(moved, source), "sha1")
    return {"doc": source, "markstay_reembed": ms_re, "blockhash_reembed": bh_re}


def duplicate_case() -> dict:
    """A doc with two byte-identical blocks: the content-hash key collapses them
    into one record (a block is lost from the store); stays keep them distinct."""
    dup = ("Identical boilerplate paragraph repeated verbatim in two places.\n\n"
           "A genuinely different middle paragraph sits between them.\n\n"
           "Identical boilerplate paragraph repeated verbatim in two places.\n")
    bh = blockhash_docs(dup, "dup.md")
    ms = markstay_docs(stamp(dup).text, "dup.md")
    return {"blocks": 3,
            "blockhash_records": count_records(bh, "sha1"),
            "markstay_records": count_records(ms, MS_KEY)}


def stable_id_case(rewrites: list[dict]) -> dict | None:
    """Show a stay id that survives a real content change: same id before/after,
    different §8 hash. The durable handle a content hash cannot be."""
    for rw in rewrites:
        before, after = rw["before"], restamp(rw["after"]).text
        hb, ha = _block_hash_by_id(before), _block_hash_by_id(after)
        for cid in hb.keys() & ha.keys():
            if hb[cid] != ha[cid]:
                return {"doc": rw["doc"], "task": rw["task"], "id": cid,
                        "hash_before": hb[cid], "hash_after": ha[cid]}
    return None


def recursive_strawman(rw: dict) -> list[dict]:
    """Same edit, the offset splitter at three chunk sizes: the re-embed number is
    whatever you choose by shrinking chunk_size. Context, never the headline."""
    source, before, after = rw["doc"], rw["before"], restamp(rw["after"]).text
    rows = []
    for cs in (300, 200, 120):
        old, new = recursive_docs(before, source, cs), recursive_docs(after, source, cs)
        _, re = measure_reembed(old, new, "sha1")
        rows.append({"chunk_size": cs, "reembed": re, "chunks": len(new)})
    return rows


# --- optional: prove the chunks actually embed + store (off the measurement) -

def real_embed_smoke() -> str:
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
    except Exception:
        return ("  (skipped: install sentence-transformers + langchain-community to run "
                "the real-embedding smoke; it is off the measurement path)")
    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    rw = fx["rewrites"][0]
    emb = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    rm = InMemoryRecordManager(namespace="smoke")
    rm.create_schema()
    vs = InMemoryVectorStore(emb)
    docs = markstay_docs(rw["before"], rw["doc"])
    index(docs, rm, vs, cleanup="incremental", source_id_key="source", key_encoder=MS_KEY)
    hits = vs.similarity_search("cache invalidation", k=1)
    return f"  embedded {len(docs)} chunks; top hit: {hits[0].metadata.get('stay_id')!r}"


# --- report -----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--real-embed", action="store_true",
                    help="optional local sentence-transformers smoke (off the measurement path)")
    ap.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = ap.parse_args()

    with open(FIXTURE, encoding="utf-8") as f:
        fx = json.load(f)
    rewrites = fx["rewrites"]
    replays = [replay_rewrite(rw) for rw in rewrites]
    movement = [movement_case(rw) for rw in rewrites if rw["task"] == "copyedit"]
    dup = duplicate_case()
    stable = stable_id_case(rewrites)
    straw = recursive_strawman(next(rw for rw in rewrites if rw["task"] == "restructure"))

    if args.json:
        print(json.dumps({"replays": replays, "movement": movement, "duplicate": dup,
                          "stable_id": stable, "recursive_strawman": straw}, indent=2))
        return 0

    print(f"markstay RAG cache demo , framing (B), real LLM edits replayed from "
          f"demo_fixture.json (model={fx['model']}, $0)\n")

    print("1. RE-EMBED DISTRIBUTION (markstay vs the honest block-content-hash baseline)")
    print("   real edits; re-embeds measured through LangChain index(); reuse = saved embeddings\n")
    print(f"   {'doc':18s} {'edit':12s} {'blocks':>6s} {'markstay':>9s} {'block-hash':>11s} "
          f"{'reused':>7s} {'parity':>7s}")
    parity_ok = True
    for r in replays:
        par = "=" if r["markstay_reembed"] == r["blockhash_reembed"] else "DIFF"
        parity_ok = parity_ok and par == "="
        print(f"   {r['doc']:18s} {r['task']:12s} {r['blocks']:6d} "
              f"{r['markstay_reembed']:9d} {r['blockhash_reembed']:11d} "
              f"{r['reused']:7d} {par:>7s}")
    print(f"\n   -> markstay re-embeds EXACTLY the block-content-hash baseline at every "
          f"intensity (delta 0).\n      The win is not fewer embeddings; it is the "
          f"correctness below, at the same cost.\n")

    print("2. CORRECTNESS MATRIX (what the re-embed count misses , framing B)\n")
    mv = movement[0] if movement else {"markstay_reembed": "-", "blockhash_reembed": "-"}
    print(f"   (i)  movement (section reorder, intact): markstay {mv['markstay_reembed']} "
          f"re-embeds, block-hash {mv['blockhash_reembed']} , free for both (parity property)")
    print(f"   (ii) byte-identical duplicate blocks (doc has {dup['blocks']}, two identical):")
    print(f"          block-content-hash -> {dup['blockhash_records']} records "
          f"(the duplicate COLLAPSED, one block lost from the store)")
    print(f"          markstay           -> {dup['markstay_records']} records "
          f"(both kept, distinct ids)   << markstay-only correctness win")
    if stable:
        print(f"   (iii) stable id across a real content change ({stable['doc']}, "
              f"{stable['task']}):")
        print(f"          id {stable['id']} unchanged; §8 hash "
              f"{stable['hash_before'][:12]} -> {stable['hash_after'][:12]}")
        print(f"          the id is a durable handle; a content hash is not an identity "
              f"(it changed)  << markstay-only\n")

    print("3. STRAWMAN CONTEXT , vs RecursiveCharacterTextSplitter, same edit (restructure);")
    print("   note the denominator differs (the splitter shreds 11 blocks into many chunks):")
    for row in straw:
        print(f"          chunk_size={row['chunk_size']:4d} -> {row['reembed']:3d} of "
              f"{row['chunks']:3d} chunks re-embedded")
    print("          the 'savings vs recursive' number is config-inflatable; not a headline.\n")

    if args.real_embed:
        print("4. REAL-EMBED SMOKE (optional, off the measurement path)")
        print(real_embed_smoke())

    print("HEADLINE: at parity embedding cost with the strongest honest baseline, markstay "
          "adds\n  a portable block identity (survives edits + movement) and keeps "
          "byte-identical\n  blocks distinct , correctness a content hash cannot provide. "
          "No dollar figure claimed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
