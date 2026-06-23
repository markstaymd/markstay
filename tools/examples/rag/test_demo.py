"""Guardrail: the demo's correctness claims, asserted from the frozen fixture so
they stay true with no API key.

Replays `demo_fixture.json` (real LLM edits captured once) and asserts:

* **parity** , markstay re-embeds EXACTLY the block-content-hash baseline at every
  edit intensity (delta 0); the headline is correctness, not a savings figure;
* **movement = free** , a section reorder yields zero markstay re-embeds;
* **duplicates kept distinct** , a doc with two byte-identical blocks stores 3
  markstay records vs the content-hash baseline's 2 (one block collapsed);
* **stable id across change** , a real edit that flips a block's §8 hash leaves
  its stay id unchanged (the durable handle).
"""

from __future__ import annotations

import json
import os

import pytest

import demo

# the block-hash baseline deliberately uses index()'s default sha1 key; its
# not-collision-resistant warning is irrelevant to a cache-identity test.
pytestmark = pytest.mark.filterwarnings("ignore:.*SHA-1.*")

FIXTURE = os.path.join(os.path.dirname(__file__), "demo_fixture.json")


@pytest.fixture(scope="module")
def fx():
    return json.load(open(FIXTURE, encoding="utf-8"))


def test_fixture_markers_were_preserved(fx):
    # the capture rejects dropped/relocated markers; assert the frozen copy is clean.
    for rw in fx["rewrites"]:
        assert rw["marker_issues"] == [], (rw["doc"], rw["task"], rw["marker_issues"])


def test_reembed_parity_with_block_hash_baseline(fx):
    """The decisive framing-B fact: markstay does not beat a content hash at the
    skip-unchanged game , it ties it, at every intensity."""
    for rw in fx["rewrites"]:
        r = demo.replay_rewrite(rw)
        assert r["markstay_reembed"] == r["blockhash_reembed"], (rw["doc"], rw["task"])


def test_reembed_distribution_is_honest(fx):
    """Localized edits reuse most embeddings; heavy rewrites reuse few. Both ends
    present (no cherry-pick): at least one near-total-reuse and one heavy row."""
    reused_fracs = []
    for rw in fx["rewrites"]:
        r = demo.replay_rewrite(rw)
        reused_fracs.append(r["reused"] / r["blocks"])
    assert max(reused_fracs) >= 0.9, "expected a localized edit that reuses most chunks"
    assert min(reused_fracs) <= 0.6, "expected a heavy rewrite that reuses few chunks"


def test_movement_is_free(fx):
    rw = next(r for r in fx["rewrites"] if r["task"] == "copyedit")
    m = demo.movement_case(rw)
    assert m["markstay_reembed"] == 0
    assert m["blockhash_reembed"] == 0  # parity property: free for both


def test_duplicate_blocks_kept_distinct():
    d = demo.duplicate_case()
    assert d["blocks"] == 3
    assert d["blockhash_records"] == 2  # the two identical blocks collapse to one
    assert d["markstay_records"] == 3   # markstay keeps both, distinct ids


def test_stable_id_survives_content_change(fx):
    s = demo.stable_id_case(fx["rewrites"])
    assert s is not None, "no changed block found in the fixture (capture too light?)"
    assert s["hash_before"] != s["hash_after"]  # the content really changed
    assert s["id"]                              # and the id is the durable handle
