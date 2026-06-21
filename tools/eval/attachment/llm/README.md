# LLM-driven attachment-survival eval

## 20-second demo (no API key)

```bash
python demo.py
```

Answers the one objection markstay always gets , *"an LLM will just delete your
`<!-- stay -->` comments"* , by deleting them and showing markstay re-attach each
original id anyway, from content hash + quote alone. It replays a **real** sonnet
rewrite (captured once in `demo_fixture.json`, markers stripped) so the headline
number is a genuine model's output but the demo is deterministic and free to run:

```
HEADLINE
  8/10 blocks re-identified, 0 misattached  (recovery 80%, false-attach 0%)
  Without markstay (exact content match only): 3/10 recover.
```

Per-block it prints which tier recovered each id (hash / quote) and which blocks
were reworded past confident match and so flagged outdated rather than guessed.
Reproduce against a live model (needs a key): `python demo.py --live --model sonnet`;
regenerate the fixture with `python demo.py --capture --model sonnet --task restructure`.

## The full eval

Does the SPEC.md §9 resolution model hold up under **real** low-similarity LLM
rewrites? The deterministic eval one dir up (`../`) covers structural edits with
exact ground truth but tops out at ~0.7 text similarity. This eval drives genuine
LLM rewrites down into the 0.3-0.5 regime, keeping ground truth judge-free.

## How it works

1. Annotate a clean doc (every block gets a `stay:` marker).
2. Have a model rewrite the prose **with** the §11 preserve instruction, so it
   keeps every marker on the same block, that placement is the gold label.
3. Validate the label with the linter's `lint_diff` (drop / duplicate / relocate
   excluded).
4. **Strip** the markers and hand the bare prose to the resolver, which must
   recover each id from hash + quote alone (the naive-rewrite failure mode).
5. Score recovery against the gold block, bucketed by measured block similarity.

The result the deterministic eval could not produce: recovery and false-attach
rate as a function of real rewrite similarity. See `FINDINGS.md`.

## Files

| File | What |
|------|------|
| `demo.py` | one-command skeptic demo (replays the frozen fixture; `--live`/`--capture` hit a model) |
| `demo_fixture.json` | a real sonnet rewrite of `doc1` (markers preserved then stripped) for offline replay |
| `test_demo.py` | offline self-tests for the demo's replay path (no key) |
| `llm_attach.py` | rewrite tasks, ground-truth extraction, strip, scoring, similarity banding |
| `run_llm_attach_eval.py` | async runner over (doc × task × model); writes `results.{json,md}` |
| `test_llm_attach.py` | offline self-tests (LLM faked with controlled strings; no API key) |
| `results.{json,md}` | last run's raw data + report |
| `FINDINGS.md` | write-up |

Reuses `../resolver.py`, `../quote.py`, `../perturb.py` (annotate/serialize),
`../../linter/markstay_lint.py`, and `../../providers.py` (shared LLM providers).

## Run

```bash
python test_llm_attach.py                                  # offline, no key

source ~/.credentials/unlock.sh                            # ANTHROPIC/OPENAI keys
python run_llm_attach_eval.py --models sonnet --smoke      # one cheap cell
python run_llm_attach_eval.py --models sonnet,gpt4o,opus --docs doc1,doc2 --adversarial
```

`--adversarial` adds the near-duplicate fixture (`../fixtures/near_dups.md`), the
one place false attachment still occurs. `--threshold` / `--margin` re-score the
§9 commit rule at other values.
