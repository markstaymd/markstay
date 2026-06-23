// Pins the Phase 2 demo's headline contract so it can't silently regress (the demo
// rides eval/attachment/llm/demo_fixture.json , a real captured sonnet rewrite). If
// the fixture is recaptured the exact counts may shift; the invariants asserted here
// are the ones the worked example actually claims.

import { test } from "node:test";
import assert from "node:assert/strict";

import { computeContrast } from "./demo.js";

test("demo: markstay detects drift, Plate cannot", () => {
  const c = computeContrast();
  assert.ok(c.drift.markstayCount > 0, "markstay must flag at least one HASH_DRIFT");
  assert.equal(c.drift.plate, 0, "Plate carries no hash, so zero detectable drift");
  // Every drift finding is a real HASH_DRIFT object on a bridged block.
  assert.ok(c.drift.markstay.every((f) => f.code === "HASH_DRIFT" && f.id));
});

test("demo: §9 recovery beats exact-match, never misattaches", () => {
  const c = computeContrast();
  assert.equal(c.wrong, 0, "no block may be misattached (the §10 forbidden outcome)");
  assert.ok(c.recovered >= c.exactOnly, "recovery must be >= exact-content matches");
  assert.ok(c.recovered > c.exactOnly, "the quote tier must recover reworded blocks too");
});

test("demo: the list and table are reported as skipped, not silently dropped", () => {
  const c = computeContrast();
  assert.ok(c.nSupported < c.nTotal, "some blocks are below block granularity");
  assert.equal(c.nSupported + c.skipped.length, c.nTotal);
});
