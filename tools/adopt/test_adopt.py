#!/usr/bin/env python3
"""Self-tests for the markstay adoption surface. Runnable two ways:

    python test_adopt.py        # plain asserts
    pytest test_adopt.py        # also works (functions are test_*)

The helper tests are pure. The hook tests spin up a throwaway git repo, run
install.sh against it, and drive real `git commit`s, so they need `git` and
`bash` on PATH (no API credentials, no network)."""

import json
import os
import runpy
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import markstay_preserve as P  # noqa: E402

# The shared conformance corpus. This file has two homes: the umbrella (where the
# corpus sits beside it) and the published tools/ tree (where it does not). The
# umbrella is identified by SPEC.md, which the published copy never carries, so
# the skip below can only fire in the published tree. Keying the skip on the
# corpus file itself would have made deleting that file turn this test green.
_PARENT = os.path.dirname(HERE)
_IN_UMBRELLA = os.path.exists(os.path.join(_PARENT, "SPEC.md"))
_CORPUS = os.path.join(_PARENT, "conformance", "spec", "preserve.json")
_CHECK_CORPUS = os.path.join(_PARENT, "conformance", "spec", "check.json")


def _corpus_vectors():
    if not _IN_UMBRELLA:
        return None
    assert os.path.exists(_CORPUS), (
        f"running in the umbrella but {_CORPUS} is missing; the vendored instruction "
        "is unguarded"
    )
    with open(_CORPUS, encoding="utf-8") as fh:
        return json.load(fh)["vectors"]


# --- preservation instruction (mitigation #1) -----------------------------

def test_vendored_copy_matches_the_shared_corpus():
    """This file is the standalone copy an adopter vendors; the same text and the
    same composition ship as `markstay preserve` in three packages. The corpus is
    what holds them byte-identical, so drift here is a test failure rather than a
    silently divergent instruction, which is the exact failure class markstay
    exists to catch."""
    vectors = _corpus_vectors()
    if vectors is None:
        return  # published tools/ copy: no corpus ships beside it
    checked = 0
    for v in vectors:
        if v["fn"] == "instruction":
            got = P.INSTRUCTION
        elif v["fn"] == "return_only":
            got = P.RETURN_ONLY
        elif v["fn"] == "wrap":
            got = P.wrap(v["doc"], v.get("task"))
        else:
            raise AssertionError(f"unknown preserve fn: {v['fn']!r}")
        assert got == v["expected"], f"drift on corpus vector {v['name']!r}"
        checked += 1
    assert checked, "corpus carried no preserve vectors"


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


def test_vendored_hook_matches_the_shared_check_corpus():
    """The standalone hook owns a fourth baseline resolver. Drive the same
    commit-shaped vectors through it so package parity cannot leave adopters on a
    silently different algorithm."""
    if not _IN_UMBRELLA:
        return  # published tools/ copy: no corpus ships beside it
    assert os.path.exists(_CHECK_CORPUS), (
        f"running in the umbrella but {_CHECK_CORPUS} is missing; the hook's "
        "baseline resolver is unguarded"
    )

    linter_dir = os.path.join(_PARENT, "linter")
    sys.path.insert(0, linter_dir)
    try:
        import markstay_lint as L
    finally:
        sys.path.pop(0)
    hook = runpy.run_path(os.path.join(HERE, "hooks", "pre-commit"))
    check_entries = hook["check_entries"]
    with open(_CHECK_CORPUS, encoding="utf-8") as fh:
        vectors = json.load(fh)["vectors"]

    for vector in vectors:
        entries = [(
            e["status"], e["src"], e["dst"], e.get("before"), e.get("after")
        ) for e in vector["entries"]]
        result = check_entries(entries, L, scope=vector.get("scope"))
        got = {
            "pairings": [{"path": path, "baseline": baseline}
                         for path, baseline in result["pairings"]],
            "reports": [
                {
                    "label": label,
                    "findings": [
                        {"level": finding.level, "code": finding.code,
                         "id": finding.id, "line": finding.line}
                        for finding in L.sort_findings(findings)
                    ],
                }
                for label, findings in result["reports"]
            ],
            "notes": result["notes"],
            "hasErrors": result["has_errors"],
        }
        assert got == vector["expected"], (
            f"hook drift on check vector {vector['name']!r}: got={got}"
        )


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


# --- hash-drift routing (quiet by default, MARKSTAY_SHOW_DRIFT to list) --------
# Hash drift is non-blocking and non-actionable in the hook channel, so a commit
# whose only finding is an in-place edit prints nothing; MARKSTAY_SHOW_DRIFT=1
# surfaces it. The blocking checks are unaffected (covered by the tests above).

def _git_env(repo, env_extra, *args):
    env = dict(os.environ,
               GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@e",
               GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@e",
               GIT_CONFIG_GLOBAL="/dev/null", GIT_CONFIG_SYSTEM="/dev/null",
               **env_extra)
    return subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True, env=env)


def test_hook_drift_only_commit_is_silent_and_passes():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        # edit prose in place, keep both markers -> the only finding is hash drift
        _write(repo, "a.md", "Alpha block, revised.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        r = _git(repo, "commit", "-m", "reword")
        assert r.returncode == 0
        out = r.stdout + r.stderr
        assert "HASH_DRIFT" not in out          # drift line hidden
        assert "hash-drift" not in out          # nothing markstay printed at all
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_show_drift_env_lists_the_drift():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _write(repo, "a.md", "Alpha block, revised.\n<!-- stay:a1 -->\n\nBeta block.\n<!-- stay:b2 -->\n")
        _git(repo, "add", "a.md")
        r = _git_env(repo, {"MARKSTAY_SHOW_DRIFT": "1"}, "commit", "-m", "reword")
        assert r.returncode == 0
        assert "HASH_DRIFT" in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


# --- install into a repo whose hooks git actually runs -------------------------

def test_install_honours_core_hookspath():
    """husky and lefthook set core.hooksPath, and git then never runs
    .git/hooks/pre-commit. Installing there would report success and check
    nothing."""
    repo = _fresh_repo()
    try:
        _git(repo, "config", "core.hooksPath", ".husky")
        _install(repo)
        assert os.access(os.path.join(repo, ".husky", "pre-commit"), os.X_OK)
        assert not os.path.exists(os.path.join(repo, ".git", "hooks", "pre-commit"))
        # and it really gates: the check runs where git looks for it
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n")
        _git(repo, "add", "a.md")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _write(repo, "a.md", "Alpha block, rewritten with no marker.\n")
        _git(repo, "add", "a.md")
        blocked = _git(repo, "commit", "-m", "drop a1")
        assert blocked.returncode != 0
        assert "DROPPED_ID" in (blocked.stdout + blocked.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_install_refuses_to_clobber_a_managed_hook():
    """Overwriting husky's own pre-commit would silently drop every other check the
    repo runs, so the installer integrates instead of taking the file."""
    repo = _fresh_repo()
    try:
        os.makedirs(os.path.join(repo, ".husky"))
        husky = os.path.join(repo, ".husky", "pre-commit")
        with open(husky, "w") as fh:
            fh.write("#!/bin/sh\necho '[husky] other checks'\n")
        os.chmod(husky, 0o755)
        _git(repo, "config", "core.hooksPath", ".husky")

        r = subprocess.run(["bash", os.path.join(HERE, "install.sh"), repo],
                           capture_output=True, text=True)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out                      # loud, not a silent pass
        assert "ACTION REQUIRED" in out, out
        assert "[husky] other checks" in open(husky).read()  # untouched
        assert os.path.exists(os.path.join(repo, ".markstay", "hook.py"))
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_install_fails_loudly_when_the_hook_source_is_missing():
    """The published tools/ tree shipped without hooks/pre-commit for five weeks and
    the installer still printed 'markstay adoption installed'."""
    stage = tempfile.mkdtemp(prefix="markstay-partial-")
    repo = _fresh_repo()
    try:
        # an adopt/ copy with everything EXCEPT the hook
        for f in ("install.sh", "markstay_preserve.py"):
            shutil.copy(os.path.join(HERE, f), os.path.join(stage, f))
        shutil.copy(os.path.join(HERE, os.pardir, "linter", "markstay_lint.py"),
                    os.path.join(stage, "markstay_lint.py"))
        r = subprocess.run(["bash", os.path.join(stage, "install.sh"), repo],
                           capture_output=True, text=True)
        out = r.stdout + r.stderr
        assert r.returncode != 0, out
        assert "adoption installed" not in out, out
        assert "cannot find the hook" in out, out
    finally:
        shutil.rmtree(stage, ignore_errors=True)
        shutil.rmtree(repo, ignore_errors=True)


def test_install_keeps_bytecode_out_of_the_adopters_commits():
    repo = _fresh_repo()
    try:
        _install(repo)
        assert "__pycache__" in open(os.path.join(repo, ".markstay", ".gitignore")).read()
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n")
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "adopt").returncode == 0
        tracked = _git(repo, "ls-files").stdout
        assert "__pycache__" not in tracked, tracked
    finally:
        shutil.rmtree(repo, ignore_errors=True)


# --- baseline pairing: the document, not the path ------------------------------
# A stay's identity is not positional, so neither is the hook's baseline. These
# cover the cases path-keyed pairing gets wrong.

def _doc(n, prefix="s"):
    """A stamped document with n sections, ids <prefix>0..<prefix>n-1."""
    return "# Doc\n\n" + "\n".join(
        f"## Section {i}\n\nBody text for section {i}, long enough to hash.\n"
        f"<!-- stay:{prefix}{i} -->\n" for i in range(n))


def test_hook_blocks_drop_hidden_by_a_rename():
    """The failure this pairing exists for: git scores the rewrite too low to call
    it a rename, records delete + create, and path-keyed pairing finds no
    baseline. A measured real case scored 2% similarity."""
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "STATUS.md", _doc(9))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0

        _git(repo, "mv", "STATUS.md", "PHASE1.md")
        _write(repo, "PHASE1.md",
               "# Doc\n\n## Phase 1 (complete)\n\nAll nine done.\n<!-- stay:s0 -->\n")
        _git(repo, "add", "-A")
        # git itself sees no rename here, which is the whole point
        assert "R" not in _git(repo, "diff", "--cached", "--name-status").stdout.split()[0]

        blocked = _git(repo, "commit", "-m", "collapse into a renamed file")
        out = blocked.stdout + blocked.stderr
        assert blocked.returncode != 0, out
        assert out.count("DROPPED_ID") == 8, out
        assert "baseline STATUS.md" in out, out   # says where the ids came from
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_allows_pure_rename():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "STATUS.md", _doc(5))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _git(repo, "mv", "STATUS.md", "RENAMED.md")
        _git(repo, "add", "-A")
        r = _git(repo, "commit", "-m", "pure rename")
        assert r.returncode == 0, r.stdout + r.stderr
        assert "DROPPED_ID" not in (r.stdout + r.stderr)
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_reports_cross_document_move_without_blocking():
    """A stay that moved to another document in the same commit is not lost, so a
    deliberate reorganisation must not block."""
    repo = _fresh_repo()
    try:
        _install(repo)
        moved = ("## Section 2\n\nBody text for section 2, long enough to hash.\n"
                 "<!-- stay:s2 -->\n")
        _write(repo, "a.md", _doc(3))
        _write(repo, "b.md", _doc(2, "t"))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0

        _write(repo, "a.md", _doc(3).replace(moved, ""))
        _write(repo, "b.md", _doc(2, "t") + "\n" + moved)
        _git(repo, "add", "-A")
        r = _git(repo, "commit", "-m", "move a section between documents")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "DROPPED_ID" not in out, out
        assert "s2: moved out of a.md into b.md" in out, out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_notes_stays_lost_to_a_deletion_without_blocking():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "doomed.md", _doc(4, "d"))
        _write(repo, "keep.md", _doc(1, "k"))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _git(repo, "rm", "-q", "doomed.md")
        r = _git(repo, "commit", "-m", "remove the document")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "deleted with 4 stay(s)" in out, out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_notes_a_rename_out_of_markdown_without_blocking():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "notes.md", _doc(2))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _git(repo, "mv", "notes.md", "notes.txt")
        r = _git(repo, "commit", "-m", "leave markdown tracking")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "renamed to notes.txt, leaving Markdown tracking" in out, out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_ignores_its_own_vendored_files():
    """The first thing an adopter does after install is commit .markstay/, which the
    README asks for. PRESERVE.md shows the marker form twice, so linting the
    installer's own output would block that first commit with DUPLICATE_ID."""
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "a.md", "Alpha block.\n<!-- stay:a1 -->\n")
        _git(repo, "add", "-A")               # sweeps in .markstay/PRESERVE.md
        r = _git(repo, "commit", "-m", "adopt markstay")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "DUPLICATE_ID" not in out, out
    finally:
        shutil.rmtree(repo, ignore_errors=True)


def test_hook_treats_a_genuinely_new_file_as_having_no_baseline():
    repo = _fresh_repo()
    try:
        _install(repo)
        _write(repo, "keep.md", _doc(1, "k"))
        _git(repo, "add", "-A")
        assert _git(repo, "commit", "-m", "init").returncode == 0
        _write(repo, "brand-new.md", _doc(3, "n"))
        _git(repo, "add", "-A")
        r = _git(repo, "commit", "-m", "add a new document")
        out = r.stdout + r.stderr
        assert r.returncode == 0, out
        assert "DROPPED_ID" not in out and "baseline" not in out, out
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
