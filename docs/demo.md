# Demo: identity survives an LLM rewrite

The objection markstay always meets first:

> An LLM will just delete your `<!-- stay -->` comments, so the ids are useless.

So this demo deletes them. It takes a document, has a real model (Claude Sonnet)
rewrite every prose block, **strips out every marker**, and then asks markstay to say
which new block is which original one, from the content hash and quote selector alone
(the [recovery model](spec.md), sections 8 and 9).

!!! success "Headline"
    On a heavy rewrite (mean block similarity 0.71), with every marker removed:
    **8 of 10 blocks re-identified, 0 misattached.** Exact content matching alone
    recovers only 3 of 10; the quote selector recovers 5 more, and the two it cannot
    place confidently are flagged outdated rather than attached to the wrong block.

## Run it

It runs in one command with **no API key**. It replays a real Sonnet rewrite captured
once into `demo_fixture.json`, so the number is a genuine model's output while the
demo stays deterministic and free to reproduce.

```text
$ python demo.py

markstay attachment demo , can a block's identity survive an LLM
rewrite that DELETES the markers?

  document : docs/doc1.md (10 blocks)
  rewrite  : a real sonnet 'restructure' rewrite, then every marker stripped out
  drift    : mean block text similarity before->after = 0.71
             (every prose block reworded; only verbatim code/tables match)

  old id     tier      conf   recovered block
  ----------------------------------------------------------------
  b0-0ef9    hash      1.00  ✓ #0   "# Order Pipeline Overview"
  b1-453e    quote     0.75  ✓ #1   "Incoming messages from external partners are …"
  b2-172a    quote     0.65  ✓ #2   "All messages enter through a queue and must p…"
  b3-6484    detached  0.45  ○  flagged outdated (was "The validation stage checks three things:")
  b4-91e5    quote     0.78  ✓ #4   "- The partner identifier must map to an organ…"
  b5-6088    quote     0.70  ✓ #5   "When a check fails, a typed error is raised i…"
  b6-7c6e    hash      1.00  ✓ #6   "```python"
  b7-1f32    detached  0.50  ○  flagged outdated (was "The table below summarizes the retry policy a…")
  b8-1f07    hash      1.00  ✓ #8   "| Stage | Retries | Backoff |"
  b9-4451    quote     0.58  ✓ #9   "When a partner exhibits known latency issues,…"

HEADLINE
  8/10 blocks re-identified, 0 misattached  (recovery 80%, false-attach 0%)

  Without markstay (exact content match only): 3/10 recover.
  The quote selector + the id recover 5 more reworded block(s) that a
  content hash alone would miss, and the §9 commit rule (score + margin)
  turns the unrecoverable ones into a safe "outdated", never a wrong guess.
```

## What you are seeing

Each row is one original block, with its marker deleted, being re-found in the rewrite:

- **`hash`** , the block survived byte-for-byte (here the title, the code block, and
  the table), so its content hash matches exactly. This is all a plain
  content-addressed scheme would recover: 3 of 10.
- **`quote`** , the block was reworded, so the hash misses, but the stored quote
  selector still matches it as the clear best candidate. This is markstay's
  contribution in the no-marker case: 5 reworded blocks recovered that a hash alone
  cannot.
- **`detached`** , two blocks were reworded past confident recognition. The section 9
  commit rule (a minimum score **and** a margin over the runner-up) refuses to guess
  and flags them outdated. That is the point: a missed block is recoverable by a human;
  a block silently attached to the wrong content is a corruption you never see.

The whole run produces **zero wrong attachments**. That property, not the raw recovery
rate, is what makes the recovery model safe to rely on.

## How honest is this number

The recovery is best-effort and degrades as a rewrite drifts further from the original;
the full [LLM attachment study](evaluation.md) measures it across 336 ids and three
models, where it falls from 100% at high similarity to about a third at 0.3 to 0.5
similarity, but the false-attachment rate stays near zero in every band. The single
residual failure mode is near-duplicate blocks, where content recovery can bind to the
wrong twin.

So in normal use you would also give the model the section 11 preservation instruction,
so the markers rarely get stripped at all (that is what the
[dogfood case study](dogfood.md) measures). This demo is the worst case, markers fully
gone, and identity still holds.

## Reproduce it

The demo, its fixture, and the full attachment eval ship in
[`tools/eval/attachment/llm/`](https://github.com/markstaymd/markstay/tree/master/tools/eval/attachment/llm),
so the number above is inspectable with no clone of anything private, no network, and
no API key:

```bash
git clone https://github.com/markstaymd/markstay
cd markstay/tools/eval/attachment/llm
python demo.py                        # replay the captured rewrite ($0, no key)
python test_demo.py                   # the offline self-tests

export ANTHROPIC_API_KEY=...          # only needed to rewrite live
python demo.py --live --model sonnet  # prove it is not cherry-picked
```

`--live` rewrites the document fresh against the model instead of replaying the fixture;
`--capture` regenerates `demo_fixture.json`. The recovery code is the same reference
resolver published in the [`markstay` package](implementations.md).
