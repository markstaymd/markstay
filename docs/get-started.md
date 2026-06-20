# Get started

markstay is two things: a [specification](spec.md) and a set of
[implementations](implementations.md) of it. Putting it to work in a repo is the two
mandatory mitigations the [evaluation](evaluation.md) settled on, tell the editing
agent to keep the markers, and catch any silent loss at commit time.

## Add a stay to a block

A stay is recorded as a trailing HTML comment, invisible in rendered Markdown and
preserved in the source:

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

## Install the safety net in a repo

The [`tools/adopt/`](https://github.com/markstaymd/markstay/tree/master/tools/adopt)
directory packages both mitigations so a repo can pick them up without wiring
anything by hand.

**The pre-commit hook** (mitigation #2). An installer vendors the
[reference linter](linter.md) into the target repo and installs a git pre-commit
hook that lints each staged Markdown file and runs the regeneration diff against the
committed version, so a commit that drops, duplicates, or relocates a stay is blocked
before it lands. Hash drift is a warning and does not block; files with no markstay
markers pass silently.

```bash
cd tools/adopt
./install.sh /path/to/your/repo        # vendor the linter + install the hook
# now: edit a .md, drop a stay: marker, `git commit` -> blocked
```

**The preservation instruction** (mitigation #1). The
[AI editing contract](spec.md#ai-editing-contract) is only honoured if the editing
agent is told to honour it, the single biggest lever on whether markers survive a
rewrite. `markstay_preserve.py` is the canonical source of that instruction:

```bash
python3 markstay_preserve.py                   # print it (seed a system prompt / AGENTS.md)
python3 markstay_preserve.py --wrap notes.md   # wrap a doc into a ready editing prompt
```

Together they are the durable deliverable the [evaluation](evaluation.md) pointed
at: instruct the agent up front, then catch any silent loss at commit time.

## Build on it in code

To depend on markstay from a program rather than as a commit hook, install one of
the [implementations](implementations.md), Python, JavaScript, a remark adapter, or
Rust. Each exposes the same lint, diff, and recovery surface, gated by the shared
conformance corpus.
