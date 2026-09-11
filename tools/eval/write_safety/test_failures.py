"""A broken measurement must not look like a successful zero-result run."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

import incremental
import subset_check


def fail(*args, **kwargs):
    raise RuntimeError("measurement failed")


def test_subset_parse_error_aborts_without_summary(monkeypatch, capsys):
    monkeypatch.setattr(subset_check.L, "parse_document", fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        subset_check.check(["A paragraph.\n"], "fixture")
    assert not capsys.readouterr().out


def test_subset_stamp_error_aborts(monkeypatch, capsys):
    monkeypatch.setattr(subset_check, "generated", lambda: ["A paragraph.\n"])
    monkeypatch.setattr(subset_check, "corpus", lambda *args: ["A paragraph.\n"])
    monkeypatch.setattr(subset_check.M, "stamp", fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        subset_check.main(["subset_check.py", "unused.txt"])
    assert "corpus, stamped" not in capsys.readouterr().out


def test_incremental_parse_error_is_not_a_zero_measurement(monkeypatch):
    monkeypatch.setattr(incremental.M, "parse_document", fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        incremental.probe("A paragraph.\n", "commonmark")


def test_incremental_stamp_error_aborts(monkeypatch, capsys):
    monkeypatch.setattr(incremental, "corpus", lambda *args: ["A paragraph.\n"])
    monkeypatch.setattr(incremental.M, "stamp", fail)
    with pytest.raises(RuntimeError, match="measurement failed"):
        incremental.main(["incremental.py", "unused.txt"])
    assert "stamped children" not in capsys.readouterr().out


@pytest.mark.parametrize("script", ["subset_check.py", "incremental.py"])
@pytest.mark.parametrize("missing_parser", [False, True])
def test_cli_requires_a_working_parser(tmp_path, script, missing_parser):
    directory = Path(__file__).resolve().parent
    document = tmp_path / "document.md"
    document.write_text("- one\n- two\n")
    listing = tmp_path / "corpus.txt"
    listing.write_text(str(document) + "\n")
    env = dict(os.environ, PYTHONPATH=str(directory.parents[1] / "impl/py/src"))
    # -S removes site-packages, including the optional CommonMark parser, while
    # PYTHONPATH keeps the local markstay package available in both arms.
    command = [sys.executable] + (["-S"] if missing_parser else [])
    result = subprocess.run(
        command + [str(directory / script), str(listing)],
        env=env, capture_output=True, text=True, check=False,
    )
    if missing_parser:
        assert result.returncode != 0
        assert "markdown_it" in result.stderr
        assert "ModuleNotFoundError" in result.stderr
        assert "0 documents" not in result.stdout
        assert "of 0 stamped children" not in result.stdout
    else:
        assert result.returncode == 0, result.stderr
        if script == "subset_check.py":
            assert "1331 documents" in result.stdout
            assert "corpus, stamped: 1 documents" in result.stdout
        else:
            assert "commonmark: of 2 stamped children" in result.stdout


@pytest.mark.parametrize("script", ["subset_check.py", "incremental.py"])
@pytest.mark.parametrize("case", [
    "missing_document", "invalid_utf8", "missing_listing", "empty_listing", "oversized",
])
def test_cli_rejects_unreadable_or_empty_corpus(tmp_path, script, case):
    directory = Path(__file__).resolve().parent
    document = tmp_path / "document.md"
    listing = tmp_path / "corpus.txt"
    if case != "missing_listing":
        listing.write_text(str(document) + "\n", encoding="utf-8")
    if case == "invalid_utf8":
        document.write_bytes(b"\xff")
    elif case == "empty_listing":
        listing.write_text("\n \n", encoding="utf-8")
    elif case == "oversized":
        document.write_text("x" * 200_001, encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(directory / script), str(listing)],
        env=dict(os.environ, PYTHONPATH=str(directory.parents[1] / "impl/py/src")),
        capture_output=True, text=True, check=False,
    )
    assert result.returncode != 0
    if case in ("missing_document", "invalid_utf8"):
        assert f"Cannot read corpus document {document}" in result.stderr
    elif case == "missing_listing":
        assert "FileNotFoundError" in result.stderr
        assert str(listing) in result.stderr
    else:
        assert "contains no eligible documents" in result.stderr
    assert "corpus, as found" not in result.stdout
    assert "stamped children" not in result.stdout


@pytest.mark.parametrize("module", [subset_check, incremental])
def test_corpus_preserves_deduplication_and_size_exclusion(tmp_path, module):
    paths = [tmp_path / name for name in ("first.md", "duplicate.md", "large.md", "last.md")]
    for path, text in zip(paths, ("one", "one", "x" * 200_001, "two")):
        path.write_text(text, encoding="utf-8")
    listing = tmp_path / "corpus.txt"
    listing.write_text("\n".join(map(str, paths)), encoding="utf-8")
    assert list(module.corpus(listing)) == ["one", "two"]
    assert list(module.corpus(listing, limit=1)) == ["one"]
