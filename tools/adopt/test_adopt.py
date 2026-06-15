#!/usr/bin/env python3
"""Self-tests for the markstay adoption surface. Runnable two ways:

    python test_adopt.py        # plain asserts
    pytest test_adopt.py        # also works (functions are test_*)

The helper tests are pure. The hook tests spin up a throwaway git repo, run
install.sh against it, and drive real `git commit`s, so they need `git` and
`bash` on PATH (no API credentials, no network)."""

import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import markstay_preserve as P  # noqa: E402


# --- preservation instruction (mitigation #1) -----------------------------

def test_instruction_covers_the_contract():
    text = P.INSTRUCTION.lower()
    # the six §11 obligations, in the words the instruction uses
    for needle in ("stay:", "preserve", "attached", "mint", "reuse", "report", "duplicate"):
        assert needle in text, f"instruction is missing {needle!r}"


def test_wrap_orders_task_instruction_doc():
    w = P.wrap("THE DOCUMENT BODY", task="Rewrite this to be clearer.")
    assert "Rewrite this to be clearer." in w
    assert P.INSTRUCTION in w
    assert "THE DOCUMENT BODY" in w
    # task before instruction before document
    assert w.index("Rewrite this") < w.index(P.INSTRUCTION) < w.index("THE DOCUMENT BODY")
    assert P.RETURN_ONLY in w


def test_wrap_without_task_still_carries_instruction():
    w = P.wrap("doc only")
    assert w.lstrip().startswith(P.INSTRUCTION[:20])
    assert "doc only" in w


def test_cli_print_emits_instruction():
    out = subprocess.run([sys.executable, os.path.join(HERE, "markstay_preserve.py")],
                         capture_output=True, text=True)
    assert out.returncode == 0
    assert "stay:" in out.stdout and "MUST" in out.stdout


# --- pre-commit hook (mitigation #2) --------------------------------------

def _git(repo, *args):
    env = dict(os.environ,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null")
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env)


def _install(repo):
    r = subprocess.run(["bash", os.path.join(HERE, "install.sh"), repo],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr
    return r


def _fresh_repo():
    repo = tempfile.mkdtemp(prefix="markstay-hook-")
    _git(repo, "init", "-q")
    _git(repo, "checkout", "-q", "-b", "main")
    return repo


def _write(repo, name, text):
    with open(os.path.join(repo, name), "w", encoding="utf-8") as fh:
        fh.write(text)


def test_install_lays_down_files():
    repo = _fresh_repo()
    try:
        _install(repo)
        assert os.path.exists(os.path.join(repo, ".markstay", "markstay_lint.py"))
        assert os.path.exists(os.path.join(repo, ".markstay", "PRESERVE.md"))
        hook = os.path.join(repo, ".git", "hooks", "pre-commit")
        assert os.access(hook, os.X_OK)
        assert "markstay adoption hook" in open(hook).read()
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_blocks_dropped_stay():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        ok = _git(repo, "commit", "-m", "init")
        assert ok.returncode == 0, ok.stdout + ok.stderr   # clean baseline commits

        # rewrite Beta without its marker -> a dropped stay
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n\nBeta block, reworded.\n")
        _git(repo, "add", "a.md")
        blocked = _git(repo, "commit", "-m", "drop b2")
        assert blocked.returncode != 0
        assert "DROPPED_ID" in (blocked.stdout + blocked.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_allows_preserved_edit():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        # edit the prose but keep both markers -> allowed (in-place drift only)
        _write(repo, "a.md", "Alpha block, revised.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "-m", "reword").returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_blocks_malformed_on_first_commit():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "A paragraph.\n<!-- stay:note=hello -->\n")  # no id
        _git(repo, "add", "a.md")
        blocked = _git(repo, "commit", "-m", "bad marker")
        assert blocked.returncode != 0
        assert "MALFORMED_MARKER" in (blocked.stdout + blocked.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_blocks_duplicate_id():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "One.\n<!-- stay:dup -->\n\nTwo.\n<!-- stay:dup -->\n")
        _git(repo, "add", "a.md")
        blocked = _git(repo, "commit", "-m", "dup")
        assert blocked.returncode != 0
        assert "DUPLICATE_ID" in (blocked.stdout + blocked.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_ignores_plain_markdown():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "plain.md", "# Title\n\nJust prose, no markstay markers here.\n")
        _git(repo, "add", "plain.md")
        assert _git(repo, "commit", "-m", "plain").returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_no_verify_bypasses_hook():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "A paragraph.\n<!-- stay:note=hello -->\n")  # malformed
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "--no-verify", "-m", "bypass").returncode == 0
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_uninstall_removes_everything():
    repo = _fresh_repo()
    try:
        _install(repo)
        r = subprocess.run(["bash", os.path.join(HERE, "install.sh"), "--uninstall", repo],
                           capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr
        assert not os.path.exists(os.path.join(repo, ".markstay"))
        assert not os.path.exists(os.path.join(repo, ".git", "hooks", "pre-commit"))
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_install_backs_up_foreign_hook():
    repo = _fresh_repo()
    try:
        hook = os.path.join(repo, ".git", "hooks", "pre-commit")
        with open(hook, "w") as fh:
            fh.write("#!/bin/sh\necho mine\n")
        os.chmod(hook, 0o755)
        _install(repo)
        assert "markstay adoption hook" in open(hook).read()
        assert os.path.exists(hook + ".pre-markstay")
        assert "echo mine" in open(hook + ".pre-markstay").read()
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ok   {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL {t.__name__}: {e}")
        except Exception as e:  # noqa: BLE001
            failed += 1
            print(f"  ERR  {t.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
