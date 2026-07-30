#!/usr/bin/env bash
# markstay adoption installer.
#
# Wires the markstay post-edit safety net into a target git repo:
#   1. vendors the reference linter to  <repo>/.markstay/markstay_lint.py
#      (dependency-free; commit it so the whole team shares one checker),
#   2. drops the preservation instruction to  <repo>/.markstay/PRESERVE.md
#      (the §11 text, generated from markstay_preserve.py so it never drifts),
#   3. installs the pre-commit hook into the repo's hook directory
#      (backs up any existing foreign hook first).
#
# Step 3 respects `core.hooksPath`. A repo managed by husky or lefthook points that
# at a tracked directory, and git then never runs `.git/hooks/pre-commit`, so
# writing there would report success and check nothing. When a hook manager already
# owns the file, this installer leaves it alone and prints the line to add.
#
# Usage:
#   ./install.sh [TARGET_REPO]        # install into TARGET_REPO (default: cwd)
#   ./install.sh --uninstall [TARGET] # remove the hook + .markstay/ (restores backup)
#
# Dependencies: bash, git, python3. NOT `set -e`; we report failures ourselves,
# and a failed step must never reach the success banner.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTINEL="markstay adoption hook"   # identifies a hook we own (idempotent reinstall)

die() { echo "ERROR: $*" >&2; exit 1; }

UNINSTALL=0
TARGET="."
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    -h|--help)
      sed -n '2,22p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    -*) echo "ERROR: unknown option: $arg" >&2; exit 2 ;;
    *)  TARGET="$arg" ;;
  esac
done

ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)"
[ -n "$ROOT" ] || die "'$TARGET' is not inside a git repository."

VENDOR="$ROOT/.markstay"

# Where git will actually look for hooks. A relative core.hooksPath is interpreted
# relative to the top of the working tree.
HOOKS_PATH="$(git -C "$ROOT" config --get core.hooksPath 2>/dev/null)"
if [ -n "$HOOKS_PATH" ]; then
  case "$HOOKS_PATH" in
    /*) HOOKS_DIR="$HOOKS_PATH" ;;
    *)  HOOKS_DIR="$ROOT/$HOOKS_PATH" ;;
  esac
  MANAGED=1
else
  HOOKS_DIR="$ROOT/.git/hooks"
  MANAGED=0
fi
HOOK_DST="$HOOKS_DIR/pre-commit"

if [ "$UNINSTALL" = 1 ]; then
  if [ -e "$HOOK_DST" ] && grep -q "$SENTINEL" "$HOOK_DST" 2>/dev/null; then
    rm -f "$HOOK_DST"
    echo "removed hook: $HOOK_DST"
    if [ -e "$HOOK_DST.pre-markstay" ]; then
      mv "$HOOK_DST.pre-markstay" "$HOOK_DST"
      echo "restored prior hook from pre-commit.pre-markstay"
    fi
  else
    echo "no markstay hook at $HOOK_DST (nothing to remove)"
  fi
  rm -rf "$VENDOR"
  echo "removed $VENDOR"
  exit 0
fi

# Locate the linter source: sibling linter/ in the umbrella, or vendored next to
# this script (so the installer keeps working from a published tools/ copy).
LINT_SRC=""
for c in "$SCRIPT_DIR/../linter/markstay_lint.py" "$SCRIPT_DIR/markstay_lint.py"; do
  if [ -f "$c" ]; then LINT_SRC="$c"; break; fi
done
[ -n "$LINT_SRC" ] || die "cannot find markstay_lint.py near $SCRIPT_DIR"

HOOK_SRC="$SCRIPT_DIR/hooks/pre-commit"
[ -f "$HOOK_SRC" ] || die "cannot find the hook at $HOOK_SRC (incomplete copy of the adopt/ tree?)"

mkdir -p "$VENDOR" || die "cannot create $VENDOR"
cp "$LINT_SRC" "$VENDOR/markstay_lint.py" || die "cannot vendor the linter into $VENDOR"
python3 "$SCRIPT_DIR/markstay_preserve.py" > "$VENDOR/PRESERVE.md" \
  || die "failed to generate PRESERVE.md (is python3 on PATH?)"
# The hook imports the vendored linter, so python writes bytecode next to it. Keep
# that out of the adopter's commits.
printf '__pycache__/\n' > "$VENDOR/.gitignore" || die "cannot write $VENDOR/.gitignore"

# A hook manager owns the hook file: integrate, do not clobber. Overwriting husky's
# pre-commit would silently drop every other check the repo runs.
if [ "$MANAGED" = 1 ] && [ -e "$HOOK_DST" ] && ! grep -q "$SENTINEL" "$HOOK_DST" 2>/dev/null; then
  cat >&2 <<EOF
markstay: vendored the linter and instruction into $VENDOR

ACTION REQUIRED: this repo sets core.hooksPath=$HOOKS_PATH, so git runs
$HOOK_DST and never .git/hooks/pre-commit. That file already exists and is
not ours, so it was left untouched. Add the check to it yourself:

  python3 "\$(git rev-parse --show-toplevel)/.markstay/hook.py" || exit 1

The hook body was copied to $VENDOR/hook.py for that purpose.
EOF
  cp "$HOOK_SRC" "$VENDOR/hook.py" || die "cannot stage the hook at $VENDOR/hook.py"
  chmod +x "$VENDOR/hook.py"
  exit 3
fi

mkdir -p "$HOOKS_DIR" || die "cannot create the hook directory $HOOKS_DIR"
if [ -e "$HOOK_DST" ] && ! grep -q "$SENTINEL" "$HOOK_DST" 2>/dev/null; then
  mv "$HOOK_DST" "$HOOK_DST.pre-markstay" || die "cannot back up the existing hook"
  echo "backed up existing pre-commit -> pre-commit.pre-markstay"
fi
cp "$HOOK_SRC" "$HOOK_DST" || die "cannot install the hook to $HOOK_DST"
chmod +x "$HOOK_DST" || die "cannot make $HOOK_DST executable"

WHERE="$HOOK_DST"
[ "$MANAGED" = 1 ] && WHERE="$HOOK_DST  (core.hooksPath=$HOOKS_PATH)"

cat <<EOF
markstay adoption installed in $ROOT
  linter      -> .markstay/markstay_lint.py   (commit this so the team shares it)
  instruction -> .markstay/PRESERVE.md        (paste into your agent's system prompt / AGENTS.md)
  hook        -> $WHERE

Next:
  - try it:        edit a .md, drop a 'stay:' marker, 'git commit' -> blocked
  - commonmark:    MARKSTAY_MODE=commonmark git commit ...   (needs markdown-it-py)
  - bypass once:   git commit --no-verify
  - uninstall:     $SCRIPT_DIR/install.sh --uninstall $ROOT
EOF
