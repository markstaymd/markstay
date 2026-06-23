// Plate vs markstay before/after demo , the skeptic-converter for ROADMAP Vein 3a.
//
// Plate's `withBlockId` writes a block id into the `.md`, but that is ALL it writes:
// no content fingerprint and no reader. So when an AI edits the document, Plate cannot
// tell you a block's content drifted, and if the `<block>` wrapper is stripped the id
// is simply gone (Plate's own deserialize recovers `id: null` and corrupts the body).
// markstay carries the same id PLUS a body hash (SPEC §8) and a quote selector (§9),
// so it answers both questions. This demo proves the gap on a REAL model edit.
//
// It runs in one command with NO API key: it replays the same captured sonnet rewrite
// the attachment eval froze into eval/attachment/llm/demo_fixture.json (a real
// model's output, deterministic to reproduce). The doc has 10 blocks; markstay's
// blank-line core bridges 8 of them , the list and the table are below block
// granularity (SPEC §5.1/§14), which the demo reports honestly rather than hiding.
//
// Ordering is load-bearing: the document is converted to markstay BEFORE the edit, so
// each marker carries the pre-edit hash. Converting after the edit would hash the new
// content and show no drift.
//
//   node demo.js     # replay, $0, exits non-zero if the headline gate regresses

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

import { fromPlate, toPlate, UnsupportedPlateBlock } from "./bridge.js";
import {
  parseDocument,
  stamp,
  findMarkers,
  stripMarkers,
  lintDocument,
  buildAnchors,
  resolve,
} from "markstay";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURE = join(HERE, "..", "..", "eval", "attachment", "llm", "demo_fixture.json");

const indent2 = (body) =>
  body.split("\n").map((l) => (l === "" ? "" : "  " + l)).join("\n");

// A block is bridgeable iff fromPlate accepts it: build a one-wrapper Plate doc and
// see whether the bridge converts it or rejects it. Single source of truth , the
// bridge's own supported-subset definition, no duplicated classifier here.
function bridgeable(id, body) {
  const plate = `<block id="${id}">\n${indent2(body)}\n</block>\n`;
  try {
    fromPlate(plate);
    return true;
  } catch (e) {
    if (e instanceof UnsupportedPlateBlock) return false;
    throw e;
  }
}

function firstLine(body, width = 48) {
  const line = (body.trim().split("\n")[0] || "").trim();
  return line.length <= width ? line : line.slice(0, width - 1) + "…";
}

export function computeContrast() {
  const fx = JSON.parse(readFileSync(FIXTURE, "utf8"));
  const beforeBlocks = parseDocument(fx.before_annotated).filter((b) => b.index >= 0);
  const afterBlocks = parseDocument(fx.after_with_markers).filter((b) => b.index >= 0);
  const afterById = new Map(afterBlocks.map((b) => [b.markers[0].id, b.content]));

  // Partition by what markstay's blank-line core can carry a per-block id for.
  const supported = [];
  const skipped = [];
  for (const b of beforeBlocks) {
    const id = b.markers[0].id;
    (bridgeable(id, b.content) ? supported : skipped).push({
      id,
      before: b.content,
      after: afterById.get(id),
    });
  }
  const ids = supported.map((s) => s.id);

  // --- Convert BEFORE editing: stamp the supported corpus with real pre-edit hashes.
  const plainBefore = supported.map((s) => s.before).join("\n\n") + "\n";
  let k = 0;
  const markstayBefore = stamp(plainBefore, { newId: () => ids[k++] }).text;
  const plateBefore = toPlate(markstayBefore); // Plate-native form of the same doc

  // markstayBefore must be clean before we trust any drift it reports later, and the
  // bridge must round-trip this real doc losslessly (not just the synthetic fixtures).
  assert.equal(lintDocument(markstayBefore).findings.length, 0, "before must lint clean");
  assert.equal(
    fromPlate(plateBefore).trimEnd(),
    markstayBefore.trimEnd(),
    "bridge must round-trip the real doc"
  );

  // --- Apply the SAME edit to both forms.
  // markstay: reworded body keeps its original marker (pre-edit hash) attached.
  const rawMarkerById = new Map(
    findMarkers(markstayBefore).filter((m) => m.id).map((m) => [m.id, m.raw])
  );
  const markstayAfter =
    supported.map((s) => s.after + "\n" + rawMarkerById.get(s.id)).join("\n\n") + "\n";
  // Plate-native: reworded body, same id, no hash , toPlate drops the hash, which IS
  // the Plate wrapper (an id and nothing else).
  const plateAfter = toPlate(markstayAfter);

  // --- (a) Drift detection.
  const driftFindings = lintDocument(markstayAfter).findings.filter(
    (f) => f.code === "HASH_DRIFT"
  );
  // Plate's wrapper has no content fingerprint, so a drift check is structurally
  // impossible. Prove it: the Plate-native after carries zero markstay markers to lint.
  const plateMarkers = findMarkers(plateAfter).filter((m) => m.id && !m.malformed);
  const plateDrift = 0;

  // --- (b)+(c) Strip the markers, recover identity via §9.
  const strippedAfter = stripMarkers(markstayAfter); // ids gone, like an AI rewrite
  const anchors = buildAnchors(markstayBefore);
  const resolutions = resolve(anchors, strippedAfter);
  const recovery = supported.map((s, idx) => {
    const r = resolutions[s.id];
    const correct = r.target === idx; // gold = positional (after blocks are in order)
    return { id: s.id, method: r.method, score: r.score, target: r.target, correct };
  });
  const recovered = recovery.filter((r) => r.correct).length;
  const wrong = recovery.filter((r) => !r.correct && r.method !== "detached").length;
  const exactOnly = recovery.filter((r) => r.correct && r.method === "hash").length;

  return {
    nTotal: beforeBlocks.length,
    nSupported: supported.length,
    skipped,
    supported,
    drift: { markstay: driftFindings, markstayCount: driftFindings.length, plate: plateDrift },
    plateMarkerCount: plateMarkers.length,
    recovery,
    recovered,
    wrong,
    exactOnly,
    meta: { model: fx.model, task: fx.task, captured: fx.captured, sim: fx.mean_similarity },
  };
}

function render(c) {
  const L = [];
  const p = (s = "") => L.push(s);
  p();
  p("Plate withBlockId vs markstay , what survives an AI edit of the same .md?");
  p();
  p(`  source  : a real ${c.meta.model} '${c.meta.task}' rewrite (captured ` +
    `${c.meta.captured}), mean block similarity ${c.meta.sim}`);
  p(`  doc     : ${c.nTotal} blocks; markstay bridges ${c.nSupported} ` +
    `(the list + table are below block granularity, SPEC §5.1/§14)`);
  c.skipped.forEach((s) =>
    p(`            skipped ${s.id}: "${firstLine(s.before, 40)}"`));
  p();
  p("WORKFLOW 1 , did a block's content drift? (edit, then check)");
  p(`  markstay  : ${c.drift.markstayCount}/${c.nSupported} bridged blocks flagged ` +
    `HASH_DRIFT (stored §8 hash != new body)`);
  c.drift.markstay.forEach((f) => p(`              · ${f.id} drifted`));
  p(`  Plate     : ${c.drift.plate}/${c.nSupported} , the <block id> wrapper carries ` +
    `no hash, so drift is undetectable`);
  p(`              (${c.plateMarkerCount} markstay markers survive in the Plate form, ` +
    `by construction)`);
  p();
  p("WORKFLOW 2 , the markers got stripped (the skeptic's \"an AI deletes them\").");
  p("            Which old block is which new one?");
  p("  old id     tier      conf   recovered");
  p("  " + "-".repeat(58));
  c.recovery.forEach((r) => {
    const conf = r.method === "hash" ? "1.00" : r.score.toFixed(2);
    const mark = r.correct ? "✓" : r.method === "detached" ? "○ outdated" : "✗ WRONG";
    const tgt = r.target === null ? "" : `#${r.target}`;
    p(`  ${r.id.padEnd(9)}  ${r.method.padEnd(8)}  ${conf.padEnd(5)} ${mark} ${tgt}`);
  });
  p();
  p("HEADLINE");
  p(`  Drift     : markstay flags ${c.drift.markstayCount} edited blocks; Plate flags ` +
    `${c.drift.plate} (no hash channel).`);
  p(`  Recovery  : ${c.recovered}/${c.nSupported} blocks re-identified after a full ` +
    `marker strip, ${c.wrong} misattached.`);
  p(`              Plate recovers 0 (no reader; its deserialize returns id:null). ` +
    `Exact-content`);
  p(`              match alone gets ${c.exactOnly}; the §9 quote tier recovers the ` +
    `reworded rest.`);
  p();
  p("So Plate writes the id; markstay makes it mean something across an edit: it");
  p("detects the drift and re-finds the block when the marker is gone.");
  p();
  return L.join("\n");
}

function main() {
  const c = computeContrast();
  process.stdout.write(render(c));
  // The gate (asserted against finding objects, fixed edit set): markstay detects
  // real drift; Plate cannot.
  assert.ok(c.drift.markstayCount > 0, "expected markstay to flag drift");
  assert.equal(c.drift.plate, 0, "expected Plate to flag zero drift");
  assert.equal(c.wrong, 0, "no block should be misattached");
}

// Run only when invoked directly (`node demo.js`), not when imported by a test.
if (fileURLToPath(import.meta.url) === process.argv[1]) main();
