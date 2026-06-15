# markstay adoption surface

The two durable deliverables the marker-survival eval (`../eval/FINDINGS.md`)
pointed at, packaged so a repo can pick them up. The eval's headline is that stays
break almost entirely at machine-edit time, and that the marker *syntax* barely
matters; what matters is a two-part contract (SPEC.md §11):

1. **Tell the editing agent to keep the markers** , a preservation instruction.
   With it, marker survival goes from near-zero on a naive rewrite to 100% across
   every inline syntax and every vendor family tested.
2. **Catch silent loss after the edit** , a post-edit lint that exits non-zero.
   The reference linter already does this; here it is wired into a commit hook so
   the catch is automatic.

Neither needs network access or API credentials. The linter path is dependency-free
(Python 3.8+ stdlib); CommonMark mode is the one optional extra.

## Install into a repo

```bash
# from this directory, target any git repo (default: current repo)
./install.sh /path/to/your/repo
```

That vendors the linter, generates the preservation instruction, and installs the
pre-commit hook:

```
your-repo/
  .markstay/
    markstay_lint.py     # the reference linter (commit it; the team shares one checker)
    PRESERVE.md          # the §11 preservation instruction (paste into your agent prompt)
  .git/hooks/pre-commit  # blocks a commit that drops / relocates / duplicates a stay
```

Uninstall (removes the hook and `.markstay/`, restores any backed-up hook):

```bash
./install.sh --uninstall /path/to/your/repo
```

## 1. Preservation instruction (mitigation #1)

`markstay_preserve.py` is the single source of the SPEC.md §11 contract phrased as
an agent instruction. Use it to seed whatever an editing agent reads as context.

```bash
# print the instruction (paste into a system prompt, AGENTS.md, CLAUDE.md, ...)
python3 markstay_preserve.py

# wrap a document into a ready editing prompt and send it to a model
python3 markstay_preserve.py --wrap notes.md --task "Rewrite this to be clearer." \
  | your-llm-cli
```

Importable too: `from markstay_preserve import INSTRUCTION, wrap`. The instruction
folds in the exact wording the eval measured as effective, so the adopted text is
the one shown to work.

## 2. Pre-commit hook (mitigation #2)

The installed hook runs on `git commit`. For every staged `.md` / `.markdown` file
it lints the staged version (malformed / orphan / duplicate id, hash drift) and
runs a regeneration diff of the committed-vs-HEAD content, the check that catches a
stay an edit dropped, duplicated, or relocated. Any **error**-level finding blocks
the commit; hash drift is a warning and does not. Files with no markstay markers
pass silently, so the hook is safe to install in a repo that only partly uses
stays.

```bash
MARKSTAY_MODE=commonmark git commit ...   # segment over the CommonMark tree (§5.2)
git commit --no-verify                     # bypass the check once
```

Sharing the hook across a team: `.git/hooks/` is not version-controlled, so each
clone runs `install.sh` once, or point `core.hooksPath` at a committed directory
holding the hook.

## 3. CI / non-hook use

The same check runs anywhere the linter does, no install step needed:

```bash
# fail the build if an edit dropped a stay between two refs
git show HEAD~1:doc.md > /tmp/before.md
python3 .markstay/markstay_lint.py --before /tmp/before.md doc.md

# well-formedness sweep over all docs
python3 .markstay/markstay_lint.py docs/**/*.md
```

The linter exits non-zero on any error-level finding (SPEC.md §16), so it gates a
CI step directly.

## Tests

```bash
python3 test_adopt.py     # plain asserts; spins up a throwaway git repo for the hook
pytest test_adopt.py      # also works
```
