# Get started

markstay is two things: a [specification](spec.md) and a set of
[implementations](implementations.md) of it. Putting it to work in a repo is the two
mandatory mitigations the [evaluation](evaluation.md) settled on, tell the editing
agent to keep the markers, and catch any silent loss at commit time.

They are not equal partners, so this page does them in the order the evidence puts
them. The instruction prevents loss; the commit check only reports it afterwards.

## Install

Same CLI, same subcommands, three ecosystems. Pick whichever your repo already has.

```bash
npx markstay --help          # npm, no install
npm install -g markstay      # or globally
pip install markstay         # PyPI
cargo install markstay       # crates.io, a single static binary
```

## 1. Tell the editing agent (the lever)

The [AI editing contract](spec.md#ai-editing-contract) is only honoured if the agent
is told to honour it. This is the single biggest control on whether markers survive a
rewrite, and it is not close: a naive "clean this up" rewrite keeps about **5%** of
markers, the same rewrite carrying the instruction keeps **~96-100%**, measured
[across five models and three vendors](evaluation.md). That gap is far wider than the
gap between a cheap model and a frontier one, so the instruction matters more than
which model you use.

```bash
markstay preserve                       # print it: paste into AGENTS.md,
                                        #   CLAUDE.md, or a system prompt
markstay preserve --wrap notes.md       # the instruction wrapped around a document,
                                        #   as a complete editing prompt
markstay preserve --wrap notes.md --task "Rewrite this to be clearer."
```

The same text is available as a library constant (`PRESERVE_INSTRUCTION`) with a
composer (`preserve_wrap` / `preserveWrap`) for building the prompt in code. It is
byte-identical across all three packages, held there by the
[shared conformance corpus](implementations.md) rather than by convention.

If you do one thing on this page, do this one.

## Add a stay to a block

A stay is recorded as a trailing HTML comment, invisible in rendered Markdown and
preserved in the source ([measured across the common formatters and
renderers](compat.md), so you can check your toolchain before you stamp):

```md
## Installation
Install the package.
<!-- stay:install-step -->
```

Write markers by hand, or mint them with the npm CLI:

```bash
npx markstay stamp FILE -w      # mint a stay for each unmarked block
```

### Which blocks should carry a stay?

Add a stay to a block when something will point at it or detect its loss, not to
every block by reflex. Two coverage models:

- **Authored landmarks (the default for hand-written docs).** Mark only the blocks
  that are durable units worth addressing, a tracked item, an instruction, a section
  other documents link to. Human-readable ids (`stay:install-step`) read well here.
- **Dense automatic coverage (for tooling).** A tool that wants to address every
  block can `stamp` the whole document; short generated ids keep that cheap.

A marker earns its keep only when there is a consumer for the address. The
pre-commit hook below is the simplest one: it gives every stay a reason to exist by
catching the moment one silently vanishes.

## 2. Catch what gets through (the backstop)

`check-staged` reads the commit you are about to make and compares each document
against the version it is replacing, so a commit that drops, duplicates, or relocates
a stay is blocked before it lands. Hash drift is a warning and never blocks; files
with no markstay markers pass silently.

It works on a commit rather than on files because catching a dropped stay means
diffing against the same document *before* the edit, and only git knows what that
was. It resolves each document's baseline by stay id rather than by filename, which
is what makes it survive a rewrite git records as a delete plus a create. The
[agent loop](agent-loop.md) page explains why that distinction decides whether the
check works at all.

Wire it into the hook manager your repo already runs.

=== "npm (husky + lint-staged)"

    ```jsonc
    // package.json
    {
      "lint-staged": {
        "*.{md,markdown}": "markstay check-staged"
      }
    }
    ```

    ```bash
    # .husky/pre-commit
    npx lint-staged
    ```

=== "Python (pre-commit framework)"

    ```yaml
    # .pre-commit-config.yaml
    repos:
      - repo: https://github.com/markstaymd/markstay-py
        rev: v0.5.0
        hooks:
          - id: markstay
    ```

Either way: edit a `.md`, drop a `stay:` marker, `git commit` is blocked.

There is also `check-worktree`, the same check against the files on disk whether or
not they are staged. That is the one to run as an agent's post-edit step, because it
reports the loss while the agent is still in the loop rather than at the next commit.
See [the agent loop](agent-loop.md).

If your repo has neither hook manager, the
[`tools/adopt/`](https://github.com/markstaymd/markstay/tree/master/tools/adopt)
installer vendors the [reference linter](linter.md) and writes a plain git
pre-commit hook, with no npm or pip dependency:

```bash
cd tools/adopt
./install.sh /path/to/your/repo
```

Together the two mitigations are the durable deliverable the
[evaluation](evaluation.md) pointed at: instruct the agent up front, then catch any
silent loss at commit time.

## Build on it in code

To depend on markstay from a program rather than as a commit hook, install one of
the [implementations](implementations.md), Python, JavaScript, a remark adapter, or
Rust. Each exposes the same lint, diff, and recovery surface, gated by the shared
conformance corpus.
