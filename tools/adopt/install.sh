#!/usr/bin/env bash
# markstay adoption installer.
#
# Wires the markstay post-edit safety net into a target git repo:
#   1. vendors the reference linter to  <repo>/.markstay/markstay_lint.py
#      (dependency-free; commit it so the whole team shares one checker),
#   2. drops the preservation instruction to  <repo>/.markstay/PRESERVE.md
#      (the §11 text, generated from markstay_preserve.py so it never drifts),
#   3. installs the pre-commit hook to  <repo>/.git/hooks/pre-commit
#      (backs up any existing foreign hook first).
#
# Usage:
#   ./install.sh [TARGET_REPO]        # install into TARGET_REPO (default: cwd)
#   ./install.sh --uninstall [TARGET] # remove the hook + .markstay/ (restores backup)
#
# Dependencies: bash, git, python3. NOT `set -e`; we report failures ourselves.
set -o pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SENTINEL="markstay adoption hook"   # identifies a hook we own (idempotent reinstall)

UNINSTALL=0
TARGET="."
for arg in "$@"; do
  case "$arg" in
    --uninstall) UNINSTALL=1 ;;
    -h|--help)
      sed -n '2,20p' "${BASH_SOURCE[0]}" | sed 's/^# \{0,1\}//'
      exit 0 ;;
    -*) echo "ERROR: unknown option: $arg" >&2; exit 2 ;;
    *)  TARGET="$arg" ;;
  esac
done

ROOT="$(git -C "$TARGET" rev-parse --show-toplevel 2>/dev/null)"
if [ -z "$ROOT" ]; then
  echo "ERROR: '$TARGET' is not inside a git repository." >&2
  exit 1
fi

HOOK_DST="$ROOT/.git/hooks/pre-commit"
VENDOR="$ROOT/.markstay"

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
if [ -z "$LINT_SRC" ]; then
  echo "ERROR: cannot find markstay_lint.py near $SCRIPT_DIR" >&2
  exit 1
fi

mkdir -p "$VENDOR" || { echo "ERROR: cannot create $VENDOR" >&2; exit 1; }
cp "$LINT_SRC" "$VENDOR/markstay_lint.py"
if ! python3 "$SCRIPT_DIR/markstay_preserve.py" > "$VENDOR/PRESERVE.md"; then
  echo "ERROR: failed to generate PRESERVE.md (is python3 on PATH?)" >&2
  exit 1
fi

if [ -e "$HOOK_DST" ] && ! grep -q "$SENTINEL" "$HOOK_DST" 2>/dev/null; then
  mv "$HOOK_DST" "$HOOK_DST.pre-markstay"
  echo "backed up existing pre-commit -> pre-commit.pre-markstay"
fi
cp "$SCRIPT_DIR/hooks/pre-commit" "$HOOK_DST"
chmod +x "$HOOK_DST"

cat <<EOF
markstay adoption installed in $ROOT
  linter      -> .markstay/markstay_lint.py   (commit this so the team shares it)
  instruction -> .markstay/PRESERVE.md        (paste into your agent's system prompt / AGENTS.md)
  hook        -> .git/hooks/pre-commit        (blocks a commit that drops/relocates a stay)

Next:
  - try it:        edit a .md, drop a 'stay:' marker, 'git commit' -> blocked
  - commonmark:    MARKSTAY_MODE=commonmark git commit ...   (needs markdown-it-py)
  - bypass once:   git commit --no-verify
  - uninstall:     $SCRIPT_DIR/install.sh --uninstall $ROOT
EOF
