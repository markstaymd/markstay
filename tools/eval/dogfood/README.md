# Dogfood simulation: does a stay help preserve the block it names?

The marker-survival study (`../`) asks whether an LLM keeps a `stay:` token at all.
This study asks the next question: when an agent updates real documentation, does a
stay actually help preserve the block it names, and is the post-edit linter catch a
useful guard or mostly friction?

It runs over two open corpora bundled in `corpus/` so the result is reproducible and
inspectable offline: a 12-page sample of the FastAPI docs and a 12-chapter sample of
the Rust Book, each stamped with stays. Findings: `FINDINGS.md`; per-cell tables:
`results.md`.

## How it works

For every (doc × task × model × arm) cell:

1. Read a seeded document as `before` (markers present).
2. Ask a model to perform a realistic update (`append` / `status` / `consolidate`,
   ordered low -> high churn) and return the whole document.
3. Run the linter's `lint_diff` (`before` -> `after`), the exact catch the pre-commit
   hook uses.
4. Split every `DROPPED_ID` into a **content drop** (the section is genuinely gone,
   the catch earns its keep) or a **marker strip** (the section survived, only its
   `stay:` marker was lost, a false-positive nag). An LLM judge reads the whole edited
   document and rules survived/deleted on each removed section. A string best-match
   can't do this: it reads a deleted section as surviving whenever a textually similar
   sibling is still present.

Arms: `naive` (no marker instruction) vs `instructed` (the `PRESERVE.md` guidance
prepended). The naive-vs-instructed gap is the direct evidence for whether wiring in
the preservation instruction is worth it.

## Files

| File | What |
|------|------|
| `corpus/` | the bundled stamped corpus (`fastapi/`, `rust-book/`) + `manifest.json` (pinned upstream commits) + `NOTICE` (attribution) |
| `prepare_public_corpus.py` | regenerate `corpus/` from the pinned upstream commits |
| `dogfood_sim.py` | update tasks, prompt build, structural classification, the survival judge |
| `run_dogfood.py` | runner over (doc × task × model × arm); truncation-aware; writes the report |
| `llm_io.py` | shared truncation-aware model call (Anthropic `stop_reason`) |
| `PRESERVE.md` | the section 11 preservation instruction used by the `instructed` arm |
| `results.md`, `FINDINGS.md` | the published per-cell tables and the writeup |

The harness reuses the reference linter (`../../linter/markstay_lint.py`) and the
shared providers (`../providers.py`).

## Inspect without running anything

The corpus and the per-cell results (`results.md`) ship in this directory, so the
numbers are inspectable with no clone, no network, and no API key, the same way the
marker-survival eval ships its `results.json`. A key is only needed to *re-run*.

## Reproduce

```bash
pip install markstay                  # the published stamper (or: npm install -g markstay)
python prepare_public_corpus.py       # rebuild corpus/ from the pinned commits

export ANTHROPIC_API_KEY=...          # only needed to re-run the models
# run once per corpus (the two result tables are per-corpus):
python run_dogfood.py --docs-dir corpus/fastapi   --sample 12 \
    --models sonnet,haiku --arms naive,instructed --preserve-file PRESERVE.md \
    --out /tmp/fastapi-sim
python run_dogfood.py --docs-dir corpus/rust-book --sample 12 \
    --models sonnet,haiku --arms naive,instructed --preserve-file PRESERVE.md \
    --out /tmp/rust-sim
```

`prepare_public_corpus.py` mints fresh stay ids on each run; block boundaries and
hashes are deterministic, so a regenerated corpus is structurally identical to the
committed copy and the results reproduce within model noise. `--smoke` runs a single
cheap cell to sanity-check the wiring before the full run.
