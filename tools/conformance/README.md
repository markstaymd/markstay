# The conformance corpus

Language-neutral vectors that hold every markstay implementation to the same
answers. Each vector is JSON: an input, and what a conforming tool must produce
from it. No implementation is the authority; `SPEC.md` is, and a `spec/` vector
the reference fails is a reference bug rather than a corpus error.

Four **full runners** consume it, one per implementation:

| runner | implementation |
|---|---|
| `conformance/run_py.py` | the canonical Python reference (`linter/` + `eval/attachment/`) |
| `impl/py/tests/test_conformance.py` | the packaged Python reference |
| `impl/js/test/conformance.test.js` | the JavaScript reference |
| `impl/rs/tests/conformance.rs` | the Rust reference |

`impl/remark-stay/test/parity.test.js` is deliberately **not** one: it routes the
categories whose comparison is tree-shaped and asserts the exact counts it
routes, so narrowing that set fails rather than quietly testing less.

The core finding comparisons exclude the `info`-level `OUTSIDE_SUBSET` advisory
(§5.4): it requires the optional CommonMark parser, so dependency-free runners do
not emit it. Both Python runners retain every other finding, including other
informational findings; their unit suites test this advisory separately. This
filter applies to lint, diff, and commit-check reports.

## Tiers

- **`spec/`** , hand-authored from the spec prose, asserting what the *words*
  require. Authority.
- **`gen/`** , emitted from the reference by `generate.py` for breadth and
  regression. A `gen/` failure means the reference changed since generation;
  regenerate only when the change was intended.
- **`rows/`** , the optional profiles, `rows` and `items` (below).
- **`tree/`** , §5.2-only vectors consumed solely by the remark adapter. The
  string runners would fail them by design, so they are not part of the core.

Core count today: **531** (291 `spec/` + 240 `gen/`, 22 files).

## Optional profiles

A corpus file MAY declare a top-level `"profile"`. There are two, both in
`rows/`:

- `rows` (`rows/rows.json`): SPEC.md §5.6 table-row identity, 32 vectors.
- `items` (`rows/items.json`): SPEC.md §5.5 list-item identity, 9 vectors. It
  shares the directory and not the name, because these vectors are not rows: a
  runner that advertised `rows` would otherwise claim list items it never
  implemented.

§16 keeps §5.5 and §5.6 child segmentation **optional**, so declining a profile
is conforming. Running fewer than every core vector is not. **The four FULL
runners** (canonical Python, packaged Python, JavaScript, Rust) therefore carry
these declarations and assert against them. Two of the four are advertising
runners and two are declining ones, so not every declaration appears in every
runner, and the note on each says which:

- `KNOWN_PROFILES` , every profile the corpus may contain. A file declaring a
  profile a runner has never heard of is a **failure**, not a skip. Without this,
  adding a category to the corpus without touching the runners would pass as
  silence, which is the exact failure this project exists to catch.
- `ADVERTISED_PROFILES` , what this runner implements. Both Python references
  advertise both profiles and report `572/572 (531 core, 9 items, 32 rows)`.
  JavaScript and Rust decline both and report `531/531 core`.
- `CORE_VECTORS` , the core count, asserted so a whole file dropping out of
  collection is caught by something other than a smaller number nobody read.
- `PROFILE_VECTORS` , the same guarantee for each ADVERTISED profile, so a runner
  that implements `rows` cannot quietly run 31 of its 32. The declared set must
  equal `ADVERTISED_PROFILES`: reading it with a `.get()` and skipping a missing
  entry would reinstate exactly the hole the count closes. **Only the two Python
  runners carry it**, because only they advertise a profile; JavaScript and Rust
  pin the declined counts directly instead, asserting
  `declined == ["items:9", "rows:32"]`.

A declining runner still **vendors** the profile's vectors. A runner that cannot
see a profile cannot prove it declined one.

**`remark-stay` is the exception, and the exception is about PROFILES only.** It is
a category-routed PARITY harness over the `parse`, `lint`, `diff`, `anchors` and
`resolve` categories, not a full corpus runner: its loader reads `spec/` and `gen/`
only, and it asserts nothing about profiles. `sync-corpus.sh` ships it `rows/` all
the same, so those vectors are present and unread, and the sentence above does not
hold for it. `sync-corpus.sh --check` does notice a missing `rows/` there, but
`sync-mirror-js.sh --check` excludes `conformance/`, so nothing checks that the
harness ever looks at the profile it was given. So do not count remark among the
runners the profile-decline guarantee covers.

**The CORE half of that gap is closed.** Asserting the routed per-category counts
pins the five categories the harness knows about and says nothing about one it has
never heard of, so a new `spec/` or `gen/` category would simply not be routed and
the suite would stay green while testing less than the corpus holds. The harness now
inventories both tiers: every category on disk is either routed or named as
DECLINED with its reason, and one that is neither fails the suite by name. Adding a
category to the core corpus is therefore a decision someone records rather than an
omission nobody sees.

The `rows` category holds three operation shapes behind one `op` field
(`children`, `stamp`, `resolve`), because row identity is not one function:
recognition and attachment, the transactional write path with its migration
probe, and §9.2 child recovery. Three separate categories would let a runner
advertise the profile while implementing only the half it found easy.

The `items` category uses two of those shapes. Its first two `resolve` vectors are
`eval/attachment/item_eval.py`'s `in-place-edit` cells on the near-duplicate
shapes, with every marker gone: the edited item's siblings commit by sibling hash
and are claimed, and the edited item then commits at the quote tier because §9.2
removes a claimed sibling from the quote pool. That is the rule §9.1's tier 3
deliberately does not share, which keeps claimed blocks as rivals; kept as rivals
here, the near-duplicate siblings hold the margin and both vectors detach. Six
more `resolve` vectors pin §9.2 tier 0, the container ladder, where it differs from
§9.1 (v1.11): the first carrier of a duplicated container id, the first anchor read
for a container id the baseline repeats, no historical uniqueness, claimed blocks
out of the quote pool, context read among the unclaimed blocks, and no merge
exemption. Each is failed by the one scratch-copy fault that gives tier 0 §9.1's
rule on its point, and by no other. Its `stamp` vector pins §5.3's write refusal per child: list items that start in a
refused frontmatter-shaped span get no marker, whatever happens to their
container.

**§3.4 has no vectors of its own, and its row half lives in this profile.** The
section requires lexical **placement decisions**, rather than guaranteeing that
every write preserves rendering. The `stamp` vectors here pin a capturing
character in a cell, the container-wide scope, the flush delimiter clause, a
plain marker being masked and an ordinary comment not being. These vectors bind
implementations that advertise row identity; JavaScript and Rust decline this
optional profile and do not insert child carriers. Rendering effects need both
a CommonMark parser and an HTML parser, so they are measured separately in
`eval/write_safety/`. §5.5's
child-carrier refusals are not in the `items` profile, which carries recovery and
the §5.3 refusal only; they are pinned by the Python reference's own tests.

The adapters do not insert child carriers either. `remark-stay` records existing
stays in `file.data.stay`; `rehype-stay` sets HTML `id` properties. Neither writes
marker comments. `plate-stay` writes block markers only on separate lines and
rejects list-item and table wrappers. Thus §3.4's child-carrier refusal vectors
do not apply to these adapters. The §16 rule against attributing a child marker
to its container still applies to every reader.

## The mutation battery

`mutation_check.py` is the other half of the gate. Reverting a rule catches a
positive vector, but it can never move a **negative** one, and a negative vector
pinning where a rule stops is exactly what a corpus is worst at proving. So the
battery patches each rule's seam with a misreading an implementer could arrive at
honestly, and requires a named vector to catch it:

```sh
python3 conformance/mutation_check.py --differential
```

`79/79 mutations behaved as declared` is the passing line, alongside
`ok differential: 400 stripped and 400 marked generated pairs match
resolver.resolve`, which also prints how often the marked pairs reached a
duplicated id, a tier-1 claim, a contest and a committed merge, and fails if any
of those is zero.

The `resolve` battery includes §9.1's exclusive assignment (v1.11): first-carrier
wins and fall-through for a duplicated id, tier 2 without historical uniqueness
or without its claimed filter, claimed blocks removed from the ranking rather
than kept as rivals, context scored against the unclaimed list, a claimed block's
score reported for a detached stay, one-at-a-time commits, and six readings of
the merge test (none, containment, greedy, closed spans, equal quotes counted
once, the cap missing or at 15, UTF-16 lengths), and two readings of a baseline
that repeats an id (the first anchor read wins; no collapse, so tier 2 counts
each recording). Every one is caught by a named
`spec/resolve.json` vector, and `generate.py` asserts that each `gen/` resolve
scenario reaches the gate its name claims, reading the resolver's own reason
(`threshold`, `margin`, `contested`, or `no-candidates` when every block is
claimed).

**A mutation battery measures the seam it patches, not the rule it names.** A
refactor that moves a decision out from under a patched function retires that
mutation silently: the rule still holds, the suites stay green, and the battery
quietly stops asking. That has happened here once. It is why each rule's decision
lives in a named function both Python references spell identically, and why every
phase gate runs this file even when it adds no vectors.

## Adding vectors

The runner inventory and mirror-sync commands below describe the development
checkout. The public `tools/` tree includes the canonical Python runner, its
import dependencies, corpus and mutation battery; it does not include the other
language checkouts or release-mirror scripts.

Add to `spec/` when the spec prose requires something; add to `gen/` by
regenerating. Then run all four full runners, the remark parity harness, and the
mutation battery.

**A new category is a two-part change in every vendored copy**: the corpus files
*and* the runner that verifies them, since the per-category verifier lives in the
runner. Land both halves in the same release prep, and rely on the `--check` gates
rather than on the mirror's suite to notice: a stale runner crashes only on a
category added inside `spec/` or `gen/`, which it already enumerates. A new TIER
directory such as `rows/` is invisible to it, so the mirror stays green while
running none of the new vectors. It takes BOTH gates, and they are not a clean
split: `sync-corpus.sh --check` compares corpus directories ONLY, so it passes on a
mirror whose runner is stale. `sync-mirror-*.sh --check` is what catches that
runner, and it is the wider gate rather than a runner-only one, `sync-mirror-py.sh`
diffs the whole `impl/py` tree (its vendored corpus included), while the JS and Rust
gates compare their source-owned surfaces and runners. `./sync-corpus.sh --only impl/py` refreshes the copy tracked in this
repo without touching the nested release mirrors.
