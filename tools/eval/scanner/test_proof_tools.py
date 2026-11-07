"""Regressions for proof preflight and independent random-tail coverage."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import pytest


spec = importlib.util.spec_from_file_location(
    "child_proof_tools", Path(__file__).with_name("prove_child_quadratics.py")
)
proof = importlib.util.module_from_spec(spec)
spec.loader.exec_module(proof)


@pytest.mark.parametrize("size", ["-1", "0", "1"])
def test_sizes_below_two_are_argparse_errors(size, monkeypatch, capsys, tmp_path):
    work = tmp_path / "work"
    monkeypatch.setattr("sys.argv", ["proof", "--sizes", size, "--work-dir", str(work)])
    with pytest.raises(SystemExit) as error:
        proof.main()
    assert error.value.code == 2
    assert "--sizes requires N >= 2" in capsys.readouterr().err
    assert not work.exists()


def test_fixed_only_count_is_an_argparse_error(monkeypatch, capsys):
    monkeypatch.setattr("sys.argv", ["proof", "--count", str(proof.FIXED_CASE_COUNT)])
    with pytest.raises(SystemExit) as error:
        proof.main()
    assert error.value.code == 2
    assert "--count must be at least 19" in capsys.readouterr().err


@pytest.mark.parametrize("explicit_work_dir", [False, True])
@pytest.mark.parametrize("dirty_copy", proof.PYTHON_COPIES)
def test_dirty_source_refusal_creates_no_work_dir(
    explicit_work_dir, dirty_copy, monkeypatch, tmp_path
):
    for path in proof.PYTHON_COPIES:
        source = tmp_path / path
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_bytes(b"dirty" if path == dirty_copy else b"committed")
    monkeypatch.setattr(proof, "ROOT", tmp_path)
    monkeypatch.setattr(
        proof.subprocess, "run",
        lambda command, **kwargs: SimpleNamespace(
            stdout="candidate" if command[1] == "rev-parse" else b"committed"
        ),
    )
    work = tmp_path / "work"
    args = ["proof"] + (["--work-dir", str(work)] if explicit_work_dir else [])
    monkeypatch.setattr("sys.argv", args)
    with pytest.raises(SystemExit, match=f"Uncommitted candidate source: {dirty_copy}"):
        proof.main()
    assert not work.exists()
    assert not (tmp_path / "eval/scanner/proof-runs").exists()


def test_fixed_coverage_cannot_mask_empty_random_tail():
    module = proof.load_python(proof.ROOT / proof.PYTHON_COPIES[0], "coverage_linter")
    cases = list(proof.documents(proof.FIXED_CASE_COUNT, 201102))
    # The fixed prefix covers every counter. Harmless random-tail stand-ins
    # must still fail, even though old and new outputs are identical.
    cases.extend([{"text": "plain text\n", "excluded_lines": []}] * 3)
    with pytest.raises(AssertionError, match="vacuous random-tail coverage"):
        proof.equivalence([module, module], cases, "same source")
