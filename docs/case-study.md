# Findings: what happens when an LLM rewrites a living document?

The [marker-survival study](evaluation.md) used synthetic fixtures to ask whether a
`stay:` marker survives an LLM pass at all. This one moves to the harder, messier
question: on **real, actively-maintained documents**, the kind an agent is asked to
"update" week after week, does a stay actually buy you anything? Does a routine update
ever silently drop a tracked section, and is the post-edit catch a genuine guard or
just a nag?

Rather than wait weeks for a passive pilot to answer that organically, the question was
front-loaded: simulate many realistic update passes over a corpus of real planning and
tracker documents and measure the catch directly.

!!! question "The question"
    On living documents under realistic update tasks, (a) how often does an LLM
    silently drop a tracked section, (b) does markstay's post-edit catch earn its keep,
    and (c) does the §11 preservation instruction change the answer?

## Method

The corpus is a set of real, continuously-edited planning and tracker documents (not
synthetic fixtures), each seeded with one stay per heading. For each
(document × task × model × arm) cell the harness reads the document as `before`, asks a
model to perform a realistic update and return the whole document, then runs the
linter's regeneration diff (`before` → `after`, the exact pre-commit catch). Every
`DROPPED_ID` is split into a **content drop** (the section's information is genuinely
gone, a true positive) or a **marker strip** (the section survived, only its `stay:`
marker was lost, a false-positive nag). The split is an LLM judge reading the whole
edited document, not a string heuristic, since a textual best-match misreads a deleted
section as surviving whenever a similar sibling is still present.

- **3 tasks**, low to high churn: `append` (log one entry), `status` (refresh
  statuses), `consolidate` (aggressive full rewrite).
- **3 models**: Claude Haiku 4.5, Sonnet 4.6, and Opus 4.8.
- **2 arms**: `naive` (no instruction) and `instructed` (the §11 preservation
  instruction prepended, the same text the [adoption surface](get-started.md) ships).

That is **216 cells, 1836 seeded stays**, run with zero harness failures.

!!! note "This is a case study, not a re-runnable eval"
    Unlike the [marker-survival](evaluation.md) and attachment studies, which ship
    their fixtures and harness for anyone to re-run, this corpus is private working
    documents. The harness records only metrics and opaque ids (no document content),
    and document names are anonymized. The numbers below are reported, not reproducible
    from this site.

## What the data says

**1. Identity loss happens only under an aggressive full rewrite. Routine edits
essentially never touch it.** Logging an entry (`append`) produced zero drops, zero
strips, zero would-be-blocks. Refreshing statuses (`status`) produced a single marker
strip and no real drops. Every content drop, and all but one strip, came from
`consolidate`, the "tidy and merge the whole document" rewrite.

| Task | Stays | Content drops | Marker strips | Would-block |
|------|------:|--------------:|--------------:|------------:|
| append | 612 | 0 | 0 | 0 |
| status | 612 | 0 | 1 | 1 |
| consolidate | 612 | 5 | 103 | 32 |

**2. Real section deletion is rare: 5 of 1836 stays (0.3%), every one a naive,
aggressive rewrite.** It is not a weak-model-only failure (haiku dropped real content
3 times, sonnet and opus once each), but it is small, and **no drop occurred in any
instructed cell, for any model.**

**3. As a standalone net, the catch is mostly a nag.** Of 33 commits it would have
blocked, **29 (88%) were marker strips or relocations on content that survived**; only
4 were genuine guards (the naive-rewrite drops). On this surface the hook overwhelmingly
stops a commit where no information was actually lost.

**4. The §11 preservation instruction is the lever, and it works for every model.**
This is the most model-independent result in the data:

| Arm | Stays | Content drops | Marker strips | Would-block |
|-----|------:|--------------:|--------------:|------------:|
| naive | 918 | 5 | 100 | 26 |
| instructed | 918 | 0 | 4 | 7 |

Prepending the instruction removed real drops entirely (5 → 0, across haiku, sonnet
*and* opus) and cut marker stripping by ~96% (100 → 4). The handful of remaining
instructed flags are relocations and residual strips on full rewrites, not content
loss. **The prevention half is far more effective than the passive catch.**

**5. Model choice changes the rate, not the shape.** All three behave the same way,
only `consolidate` fires and the instruction fixes it. They differ in how freely a
naive rewrite strips markers: haiku 82 strips, opus 16, sonnet 6. Benign in-place edits
(a non-blocking hash drift) were the dominant outcome everywhere.

## The boundary you must know: protection is section-granular

A stay sits on a whole top-level block, so a table is one stay and a list is one stay.
A row dropped from a table, or a bullet dropped from a tight list, leaves the block's
stay in place and only drifts its hash, a non-blocking warning, not a caught loss. A
companion run measured exactly this on the most table- and list-heavy documents in the
corpus: **96 cells, 10,608 rows and bullets.**

**Within-collection items are dropped ~30x more often than sections, and the catch
never blocks it.** 922 of 10,608 rows/bullets (9%) were silently dropped, versus 0.3%
of whole sections. Zero blocking findings were ever caused by a row or bullet drop,
only non-blocking hash drift. Even a routine `status` refresh, which dropped 0 sections,
drops 10% of rows and bullets.

**And the instruction does not help here, it makes the loss quieter.** For
within-collection items the §11 instruction is inert (drop rate 10% → 8%), and the
instructed arm has *more* silent-loss cells (18 vs 9): by faithfully keeping each
section's heading stay, the rewrite drops fewer whole sections, which removes the
coincidental `DROPPED_ID` that was the only thing flagging those cells at all.

**The fix is structural, not textual.** Make each durable item its own block:

```text
LOOSE list, drop one item:  DROPPED_ID  (blocking, caught)
TIGHT list, drop one item:  HASH_DRIFT  (non-blocking, silent)
```

A *loose* list (blank lines between items) segments into one block per item, so
stamping gives each bullet its own stay and dropping one trips a blocking error. **Table
rows cannot be made addressable this way**, a Markdown table is inherently one block, so
per-row identity needs either restructuring the rows into blocks or a future spec
extension for intra-block addressing (the [named next step](index.md)).

## Conclusions

- **Lead with the instruction, not the hook.** The preservation instruction eliminates
  real section drops across every model tested and nearly eliminates marker stripping.
  It is the mechanism that earns markstay its keep on living documents. Install it into
  whatever an editing agent reads (`AGENTS.md`, `CLAUDE.md`, a system prompt); see
  [Get started](get-started.md).
- **Treat the post-edit catch as a cheap backstop**, valuable for the weak-model,
  full-rewrite corner, not as a standalone guard. On realistic edits it rarely fires,
  and when it does it is usually a nag.
- **Seed for the granularity you need.** A headings-only seed protects section identity
  and nothing finer. If your durable units are rows or bullets (status tables,
  checklists, item registries), use loose lists so each item carries its own stay, or
  treat intra-table identity as out of scope today.

## Limitations

- **A marker strip is identity loss, just not content loss.** The section's text
  survives but downstream tooling can no longer address it by id (the resolver can
  often recover it from hash + quote; see the attachment study). "Nag" is from the
  content-preservation viewpoint, not markstay's identity mission.
- **The simulation forces full-document regeneration; real sessions edit surgically.**
  Asking for the whole rewritten document is the worst case for marker survival, so
  these drop and strip rates are an upper bound on reality.
- **Judge-based split.** The content-drop / marker-strip call is an LLM judge over the
  edited document; the structural counts (dropped, relocated, hash-drift) are exact.
- **Single-generation cells**, so the small per-model drop counts carry run-to-run
  noise. The *pattern*, rare, naive-rewrite-only, zeroed by the instruction, is stable;
  the exact per-model count is not.
