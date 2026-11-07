# History replay

Do markstay's inline ids beat id-free matching on real edits? Every other
attachment comparison here (`../attachment/`) runs on synthetic edit operators.
This one replays the umbrella's own stamped Markdown, which agents have edited for
months under a linter that requires ids to be kept, and uses the ids as ground
truth. The [site comparison](https://markstay.org/evaluation/#ids-against-id-free-matching)
reports what the data says.

No network, no API key, no install: stdlib Python, the reference linter, and this
the pinned private git history (see **Public copy** below).

## Public copy

The [site's comparison](https://markstay.org/evaluation/#ids-against-id-free-matching)
reports the findings. The public `tools/eval/replay/` copy contains this README,
aggregate within-document `results.{json,md}`, `arms.py`, `replay.py`, `crossfile.py`,
`relocation_recall.py`, `test_replay.py` and `test_crossfile.py`. It excludes the
findings report, sanity files, relocation cases and judgments, and
`test_relocation_recall.py`, whose census test requires those private artifacts.

The default replay, recall probe and history-dependent tests require the private
pinned history. They cannot reproduce these measurements from the public repo.
To use the replay on another repository, supply `--root`, `--glob` and `--out`.
When exploring with `--rev`, also supply `--out DIR` to keep the published reports:
without it a completed run replaces `results.{json,md}` beside the script.
The cross-file synthetic suite, `python3 test_crossfile.py`, needs no private history.
The file inventory below describes the full research checkout, including files
intentionally absent from the public copy.

## Run

```bash
python replay.py          # writes results.json, results.md, sanity.md (about 4 minutes on 20 cores)
python test_replay.py     # self-tests (about 3 minutes; reads git history)
```

`--rev` moves the corpus off its pinned commit, `--ks` picks the commit gaps
(default `1,5,20,50`), `--jobs` sets the pool size, and `--dump PATH` writes every
k = 20 misattachment under the repaired truth as JSON for reading.
`--root REPO --glob GLOB --out DIR` runs the same replay over another
repository's history; `--out` is required there, so nothing lands in this tree.

Moves between documents have their own harness, because the within-document
pairs never see one:

```bash
python crossfile.py --root REPO --glob 'docs/**/*.md' --out DIR --label A
python test_crossfile.py  # synthetic fixtures and a throwaway repository, seconds
```

It walks the first-parent chain of commits touching the glob, finds every id whose
real marker leaves one document and is a real marker in another at that commit or
within the next k - 1 (k = 1, 5, 20), and scores child-stay and block-stay arms
against the id's new block: the §9.2 ladder over the source document only, the same
ladder pooled over every document, and hash-only and quote-only over every document.
A move that changes kind (a block stay arriving as an item's stay) is counted and not
scored. A large store is sampled, seeded, with full population counts reported beside
the sample: one move per commit per stay kind by default, a smaller `--moves` if that
is too many, and `--deletions` for a simple sample of deletions. `--profile` times a
few groups first and stops if the estimate exceeds `--budget-min`; that estimate has
been wrong by large factors in both directions on a real store, so `--profile 0` skips
it and the group lines show real progress. An interrupted run resumes from the groups
it scored, kept in `DIR` until the run finishes (`--keep-answers` keeps them, so a
change to the statistics need not rescore; delete them after a change to the scoring). `--rev` pins the replay to a commit. It writes aggregate counts to `DIR/crossfile-<label>.json`, and with
`--sanity N` also sampled moves for reading by hand, so `DIR` belongs outside any
repository; inside the replayed one it is refused.

The call uses population-weighted estimates and a design interval (`design_ci`), and
is one of `ids-not-needed`, `ids-pay` or `insufficient-evidence`. The same rule on
raw counts is reported beside it as `verdict_raw_counts`, for comparison only. Moves no
draw speaks for (commits never drawn, kind-changing moves) widen the interval to their
worst case, so they can withhold a call.

Every score is the exact §9 metric. numpy is optional and changes no number:
`ro_matches` runs difflib's algorithm on it, which is what makes a store with 90 KB
lists practical. For a store-scale run:

```bash
python3 -m venv --system-site-packages VENV && VENV/bin/pip install numpy==2.1.3
```

## What it does

1. **Corpus.** Every tracked Markdown file at the pinned commit, outside fixtures,
   generated reports, mirrors and vendored corpora, with at least two **stamped**
   revisions on the first-parent chain (`git log --first-parent --follow`). A
   revision is stamped when block ids cover half its content blocks. A marker inside
   an inline code span is a quoted example and is left out. A revision `--follow`
   reaches through two files belongs to the file whose own path it is.
2. **Pairs.** For each gap k, every pair (stamped revision i, stamped revision
   i + k) of one document.
3. **Truth.** An id in both revisions names its block in the newer one; an id in
   the older only is gone, unless another document carries it at the newer commit
   (a cross-file move, scored apart). Duplicated ids are excluded and counted.
4. **Arms** (`arms.py`) see the older revision's stored evidence and the newer
   revision's bodies with markers stripped: `ladder` (the v1.10 ladder,
   `../attachment/ladder_v110.py`, with tier 1 gone), `hash`, `quote`, `heading+quote`, `structural`, `lcs`. Two id
   arms sit beside them: `markers only` (the marker tier itself) and `ids+ladder`
   (the marker tier, then the v1.10 ladder for an id whose marker is gone), which
   is markstay as designed and the row the question turns on.
5. **Repaired truth.** The ids are wrong about the block in two ways the history
   shows: an id lost while its block survives, and an id relocated onto a block
   inserted above its marker. `replay.repair` points those at the surviving block,
   one id per block. Both truths are scored; `sanity.md` checks a sample of each,
   and every relocation, by hand.
6. **Cost.** Marker bytes at the pinned commit, and what happened to every id over
   every consecutive revision pair.

## Files

| File | Role |
|------|------|
| `replay.py` | corpus, pairs, ground truth and its repair, scoring, cost, report |
| `arms.py` | the id-free arms, fast ports of the v1.10 ladder and the identity-survival prototype's structural matchers |
| `test_replay.py` | checks each port against the code it ports on real revision pairs, the repair rules, and the statistics |
| `crossfile.py` | moves between documents: the scan, the pooled ladders, the arms, the sample, the call |
| `test_crossfile.py` | the pooled ladder against the shipped one on one document, the arms on synthetic moves, the scan on a throwaway repository |
| `results.{json,md}` | the numbers |
| `sanity.md` | 30 id correspondences, 30 repairs and all 14 relocations, each judged by hand |
| `sanity_judgments.json` | those judgments, merged into `sanity.md` on every run |
| `relocation_recall.py` | pinned linter-terms probe and comparison with the replay's candidate population |
| `relocation_cases.json` | full old/current bodies, three strongest alternative blocks, commits and population membership for the candidate census |
| `relocation_judgments.json` | hand judgments of the candidate census, keyed like `sanity_judgments.json`; `same: yes` means the id still names its logical block |
| `FINDINGS.md` | what the numbers mean |

To reproduce the relocation census without changing the replay or its results:

```bash
python3 eval/replay/relocation_recall.py > cases.json
```

Run from the repository root (the script also accepts an absolute path from any
directory). This reads only the pinned umbrella history, with no network or API.
The linter population uses the original probe's full `git log` revision sequence,
blank-line parsing and `quote.body_score`. The replay population uses its
first-parent history, stamped older revisions, real markers and pruned score table.
The output records differences by id and revision pair; `FINDINGS.md` states which
population supplies the recall denominator and the criterion used to judge it.
