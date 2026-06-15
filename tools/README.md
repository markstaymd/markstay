# markstay reference tooling

Runnable code behind the [reference linter](https://markstay.org/linter/) and
[evaluation](https://markstay.org/evaluation/) pages. Everything here is reference
tooling that backs the [specification](https://markstay.org/spec/) with measurements
and a deterministic checker, not a production library.

## Layout

```
tools/
  linter/                  reference well-formedness + regeneration-diff checker
  eval/                    marker-survival eval (does the id token survive LLM editing?)
    attachment/            attachment-survival eval (does it stay on the RIGHT block?)
  adopt/                   adoption surface: preservation-instruction helper +
                           installable pre-commit hook (packages the two mitigations)
```

The two evals are split across `eval/` and `eval/attachment/` because they answer
different questions and the second builds on the first. `eval/` (root) is the
marker-survival study; `eval/attachment/` is the attachment-survival study, which
reuses the linter's parser and hash via a relative import (`../../linter`), so the
directory layout is load-bearing, keep `linter/` a sibling of `eval/`.

## linter/

Dependency-free (Python standard library only), no network, no credentials. Checks
a single document for malformed / orphan / duplicate-id / hash-drift markers, and
runs a before->after regeneration diff that flags dropped, duplicated, or relocated
ids with a non-zero exit, so it can gate a git hook or an agent's post-edit step.

```bash
cd linter
python3 test_lint.py                       # 19/19 self-tests
python3 markstay_lint.py examples/annotated.md
python3 markstay_lint.py --before examples/annotated.md examples/regenerated.md
```

## eval/ , marker-survival

Measures whether a marker survives when an LLM rewrites the document, across 8
syntaxes x 4 tasks x 5 models (3 vendor families), naive vs instructed. Findings: `eval/FINDINGS.md`;
raw data: `eval/results.{json,md}`. Needs API keys to re-run (set
`ANTHROPIC_API_KEY` / `OPENAI_API_KEY` / `MOONSHOT_API_KEY` for the families you
want); the committed results reproduce the published numbers without re-running.

```bash
cd eval
python3 run_eval.py --models haiku,gpt4o-mini          # full matrix for those models
python3 run_eval.py --models haiku --smoke             # one cell per model
```

## eval/attachment/ , attachment-survival

Deterministic, no credentials. Asks the harder question: after an edit moves /
splits / merges / edits / deletes blocks, does the marker->hash->quote resolver
re-attach each id to the *correct* block, and does it refuse to guess when it
cannot? Ground truth is exact (deterministic edit operators), so there is no judge
in the loop. Findings: `eval/attachment/FINDINGS.md`; raw data:
`eval/attachment/results.{json,md}`.

```bash
cd eval/attachment
python3 test_attach.py                      # 32/32 self-tests
python3 run_attach_eval.py                  # regenerates results.{json,md}
```

## adopt/ , adoption surface

Packages the two mandatory mitigations into something a repo installs. No network,
no credentials; the hook path is dependency-free (CommonMark mode is the one opt-in
extra).

- `markstay_preserve.py` , the single source of the AI editing contract phrased as
  an agent instruction (mitigation #1). Prints the instruction to seed a system
  prompt / `AGENTS.md`, or `--wrap`s a document into a ready editing prompt.
- `install.sh` + `hooks/pre-commit` , the linter's regeneration diff wired into a
  git pre-commit hook (mitigation #2). `install.sh` vendors the linter into a target
  repo's `.markstay/`, generates the preservation instruction, and installs the hook
  so a commit that drops, duplicates, or relocates a stay is blocked.

```bash
cd adopt
python3 test_adopt.py                       # 13/13 (helper + temp-repo hook tests)
python3 markstay_preserve.py                # print the preservation instruction
./install.sh /path/to/your/repo             # vendor linter + install the hook
```

## License

Code under MIT; prose and result write-ups under CC BY 4.0, matching the site.
