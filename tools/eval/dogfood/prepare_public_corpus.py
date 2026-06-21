"""Regenerate the public dogfood corpus from pinned upstream commits.

The dogfood study runs over two open documentation corpora: a sample of FastAPI
docs and a sample of Rust Book chapters. This script rebuilds that corpus
deterministically so the numbers in `results.md` / `FINDINGS.md` can be reproduced
from a fresh clone:

  1. fetch each upstream repo at a PINNED commit (recorded below),
  2. copy the selected sample (the smallest-by-words substantial prose pages; the
     selection is pinned alongside the commit so the sample is stable as upstream
     drifts),
  3. stamp each file with `markstay stamp -w` so it carries stays,
  4. write the stamped sample under <out>/{fastapi,rust-book}/ + a manifest.json.

A stamped copy of this corpus is committed next to this script (so the study is
inspectable offline, no clone/network/key needed). Re-running mints FRESH stay ids:
the block boundaries and hashes are identical (stamping is deterministic; the id
token is random), so the structural results reproduce within model noise even
though the corpus is not byte-identical to the committed copy.

Usage:

    pip install markstay        # the published stamper (or: npm install -g markstay)
    python prepare_public_corpus.py
    # then, per corpus:
    python run_dogfood.py --docs-dir corpus/fastapi --sample 12 \
        --models sonnet,haiku --arms naive,instructed \
        --preserve-file PRESERVE.md
"""

from __future__ import annotations

import argparse
import json
import shlex
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

# --- pinned upstream (commit + sample). Editing either invalidates the numbers. ---

CORPORA = {
    "fastapi": {
        "repo": "https://github.com/fastapi/fastapi",
        "commit": "0cb4a8e284b450abbccb71c543ad7757de46c0b2",  # 2026-06-20
        "subdir": "docs/en/docs",
        "license": "MIT",
        # smallest-by-words eligible prose pages at the pinned commit (doc01..doc12)
        "files": [
            "advanced/path-operation-advanced-configuration.md",
            "advanced/additional-responses.md",
            "tutorial/extra-models.md",
            "tutorial/body.md",
            "tutorial/request-files.md",
            "tutorial/body-nested-models.md",
            "how-to/custom-docs-ui-assets.md",
            "advanced/openapi-callbacks.md",
            "advanced/events.md",
            "fastapi-people.md",
            "tutorial/schema-extra-example.md",
            "advanced/advanced-dependencies.md",
        ],
    },
    "rust-book": {
        "repo": "https://github.com/rust-lang/book",
        "commit": "05d114287b7d6f6c9253d5242540f00fbd6172ab",  # 2026-02-03
        "subdir": "src",
        "license": "MIT OR Apache-2.0",
        "files": [
            "ch10-00-generics.md",
            "ch12-01-accepting-command-line-arguments.md",
            "ch01-01-installation.md",
            "ch06-03-if-let.md",
            "ch15-03-drop.md",
            "ch07-02-defining-modules-to-control-scope-and-privacy.md",
            "ch20-04-advanced-functions-and-closures.md",
            "ch09-01-unrecoverable-errors-with-panic.md",
            "ch18-01-what-is-oo.md",
            "ch11-02-running-tests.md",
            "ch13-03-improving-our-io-project.md",
            "ch03-01-variables-and-mutability.md",
        ],
    },
}


def resolve_stamp_cmd(arg: str) -> list[str]:
    if arg:
        return shlex.split(arg)
    # 1. the published CLI on PATH (pip install markstay  /  npm i -g markstay)
    if shutil.which("markstay"):
        return ["markstay"]
    # 2. the local JS reference impl, if this script runs inside the source tree
    js = Path(__file__).resolve().parents[2] / "impl" / "js" / "bin" / "cli.js"
    if js.is_file() and shutil.which("node"):
        return ["node", str(js)]
    sys.exit("no stamper found: `pip install markstay` (or `npm i -g markstay`), "
             "or pass --stamp-cmd")


def fetch_commit(repo: str, commit: str, dest: Path) -> None:
    """Fetch exactly the pinned commit (no full history)."""
    dest.mkdir(parents=True, exist_ok=True)
    run = lambda *a: subprocess.run(a, cwd=dest, check=True,
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    run("git", "init", "-q")
    run("git", "remote", "add", "origin", repo)
    run("git", "fetch", "--depth", "1", "origin", commit)
    run("git", "checkout", "-q", "FETCH_HEAD")


def stamp(stamp_cmd: list[str], path: Path) -> None:
    subprocess.run([*stamp_cmd, "stamp", str(path), "-w"], check=True,
                   stdout=subprocess.DEVNULL)


def prepare(args: argparse.Namespace) -> dict:
    out = args.out.expanduser().resolve()
    stamp_cmd = resolve_stamp_cmd(args.stamp_cmd)
    if out.exists():
        shutil.rmtree(out)

    manifest: dict = {"stamp_cmd": " ".join(stamp_cmd), "corpora": {}}
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        for name, spec in CORPORA.items():
            clone = tmp / name
            print(f"[{name}] fetching {spec['commit'][:12]} ...")
            fetch_commit(spec["repo"], spec["commit"], clone)
            src = clone / spec["subdir"]
            dst = out / name
            entries = []
            for rel in spec["files"]:
                s = src / rel
                if not s.is_file():
                    sys.exit(f"[{name}] missing at pinned commit: {rel}")
                d = dst / rel
                d.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s, d)
                stamp(stamp_cmd, d)
                stays = sum(1 for ln in d.read_text().splitlines()
                            if ln.lstrip().startswith("<!-- stay:"))
                entries.append({"doc": rel, "stays": stays})
                print(f"  {rel}: {stays} stays")
            manifest["corpora"][name] = {
                "repo": spec["repo"], "commit": spec["commit"],
                "subdir": spec["subdir"], "license": spec["license"],
                "files": entries,
            }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path,
                    default=Path(__file__).resolve().parent / "corpus",
                    help="output corpus dir (default ./corpus)")
    ap.add_argument("--stamp-cmd", default="",
                    help="stamper command (default: `markstay` on PATH, else the "
                         "local impl/js CLI)")
    args = ap.parse_args()
    m = prepare(args)
    n = sum(len(c["files"]) for c in m["corpora"].values())
    print(f"\nwrote {args.out} ({n} stamped docs across "
          f"{len(m['corpora'])} corpora)")


if __name__ == "__main__":
    main()
