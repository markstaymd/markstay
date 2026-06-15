# markstay

Stable identity for Markdown blocks. A logical block (a paragraph, list, table, or
code fence) carries a **stay**: a stable address that other tools can point at and
keep pointing at across edits, moves, and AI rewrites. The address stays put while
the content around it changes.

This repository is the source for the specification site at
**[markstay.org](https://markstay.org/)**, plus the runnable reference tooling that
backs it.

A block carries its marker on the line after it, as a trailing HTML comment that is
invisible in rendered Markdown and preserved in the source:

```md
Users authenticate with an API key in the Authorization header.
<!-- stay:8f24 -->
```

The id is the identity. An optional `hash` detects drift and an optional `quote`
helps recover a detached marker, but neither is ever identity. See the
[specification](https://markstay.org/spec/) for the full grammar, attachment model,
hashing rule, and recovery ladder. The current version is **1.1** (settled).

## Layout

```text
docs/            MkDocs site source (the pages published to markstay.org)
mkdocs.yml       site config (Material theme)
requirements.txt mkdocs-material
tools/           runnable reference tooling (linter + evals + adoption hook)
.github/workflows/deploy.yml   builds and publishes Pages on push to master
```

`tools/` has its own [README](tools/README.md) covering the linter, the two
marker-survival evals, and the installable pre-commit hook.

## Build the site locally

```bash
pip install -r requirements.txt
mkdocs serve            # live preview at http://127.0.0.1:8000/
mkdocs build --strict   # one-off build into site/ (matches CI)
```

Pushing to `master` triggers the GitHub Actions workflow, which runs the same
`mkdocs build --strict` and deploys to GitHub Pages.

## License

Prose and result write-ups are released under
[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Code samples and the
tooling under `tools/` are under the MIT license.

Issues and counter-arguments are welcome.
