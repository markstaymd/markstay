# Attachment-survival eval

Does a markstay id stay attached to the **correct** block after an edit moves,
splits, merges, edits, or deletes content, and does the resolver refuse to guess
when it cannot? This is the test of the resolution model (`id` / `hash` / `quote`
from `../../SPEC.md` §2.1, §9), distinct from the marker-survival eval
(`../FINDINGS.md`), which only checked that the id *token* survives.

No network, no API key, no install: every edit is a deterministic block operator
with exact ground truth, so each id is scored right or wrong with no judge.

## Run

```bash
python run_attach_eval.py        # writes results.{json,md}
python run_attach_eval.py --granularity item   # writes results_item.{json,md}
python test_attach.py            # self-tests
```

Options: `--threshold` and `--margin` tune the quote-recovery tier;
`--docs doc1,doc2` selects the realistic fixtures (reused from `../docs/`).

### The multi-section fixture

```bash
python run_attach_eval.py --fixture cross-section   # writes results_crosssection_fixture.{json,md}
```

Every other fixture here carries a single heading, so every edit operator acts
*within* one section and two edit classes cannot be expressed at all: a block
that moves between sections, and a heading renamed or deleted above blocks that
themselves do not change. `../../SPEC.md` §2.2 requires a stay to survive
movement within a document, so that first class is a guarantee the spec makes
and the older fixtures cannot test.

`fixtures/cross_section_dups.md` is a deployment runbook shaped the way
repetition actually occurs: sibling stage sections sharing near-identical
paragraphs, three environment sections whose rollback bodies are byte-identical
under *different* parents, a retry-policy section of same-section twins, an
un-headed preamble, and a setext heading. Five operators come with it in
`perturb.SECTION_OPERATORS` (`cross_section_move`, `cross_section_move_edit`,
`section_move`, `heading_rename`, `heading_delete`); they are kept out of
`perturb.OPERATORS` so the headline `results.md` numbers stay measured over the
same operator set they always were.

`cross_section_move_edit` exists because `cross_section_move` cannot price a
structural signal, which took running the arms to notice: a block that moves with
its text intact is recovered at the **hash** tier, so the quote tier never sees
it. The edit variant moves the document's least twin-like paragraph *and* drifts
it, so recovery has to happen at tier 3 from another section, which is the
guarantee `../../SPEC.md` §2.2 makes and a heading-path filter cannot keep.

The generated report counts the fixture's shape rather than asserting it, since
a hand-written count rots the first time the fixture is edited: how many blocks
have a rival at or over threshold in *another* section (the case a structural
signal could act on), how many have rivals only within their own section (the
control that no such signal may claim to fix), and how many have no rival at all.

### Heading path as a third contextual signal (experimental)

```bash
python run_attach_eval.py --arms            # writes results_headingpath.{json,md}
python run_attach_eval.py --heading-path penalty --fixture cross-section
```

Selectors already carry two contextual signals, `prefix` and `suffix`
(`../../SPEC.md` §9). A block's enclosing **heading path** would be a third, and
`--heading-path off|bonus|penalty|filter` (plus `--heading-bonus`,
`--heading-gate` and `--unclamp`) is where it is priced. `off` is the default and
reproduces the shipped resolver bit for bit; `filter` is revdown's hard gate to
equal-path candidates. `--arms` runs all thirteen combinations over four corpora:
the multi-section fixture, `near_dups` and a headings-removed copy of `doc1` as
negative controls, and the distinct-prose docs as the regression guard.

The verdict, and why the two forms of the same preference behave differently, is
finding 8 in `FINDINGS.md`. Nothing here is spec behaviour: the derivation lives
in the reference linter as `heading_paths` / `canonical_heading`, marked
experimental and canonical-Python-only, and no other implementation has it.

`build_anchors` and `resolve` take a `mode=` argument (`"blank-line"` default,
`"commonmark"` for `../../SPEC.md` §5.2 segmentation), which MUST match between
the two calls. CommonMark mode lets a whole loose list or a blank-line-containing
fence attach as a single block; the self-tests cover the recovery of each as one
block. It is the linter's optional `markdown-it-py` extra, inherited through the
reused `parse_document`.

### Block-tier exclusivity and duplicated ids (experimental)

```bash
python excl_arms.py          # writes results_exclusivity.{json,md}, about fifteen seconds
python test_excl_arms.py     # its self-tests (pytest runs them too)
```

`../../SPEC.md` §9.2 assigns child blocks exclusively, with historical uniqueness
at the hash tiers; §9.1 does neither for blocks, and its tier 1 does not say what
happens when one id's marker sits on two blocks. `excl_arms.py` prices both as
opt-in arms over the same corpora: tier 2 exclusive, tiers 2 and 3 exclusive,
two forms of a merge exemption, claimed blocks kept as margin rivals, and three
tier-1 rules for a duplicated id
(treat it as absent, resolve only among its carriers, detach it). Its `resolve`
with every flag off returns what `ladder_v110.resolve` returns, which the tests
assert over every corpus and operator. `t23dk+carriers` is every chosen rule at once,
and `resolver.py` is that form as the reference from v1.11: `test_attach.py` checks
the two agree, reasons included, on the near-duplicate and cross-section fixtures.

`ladder_v110.py` freezes the §9.1 ladder as v1.10 shipped it, so a change to
`resolver.py` moves no control and no dated number. `excl_arms`, `heading_arms`,
`twin_corpus`, `measure_context`, `clamp_on_sections`, `llm/llm_attach`,
`llm/run_llm_attach_eval` and `../replay` read it. `run_attach_eval`, `test_attach`,
`llm/demo` and `../../conformance` stay on `resolver.py`, because they describe what
ships. `heading_arms` runs through `run_attach_eval.run_case`, so it passes the frozen
`resolve` in, and `resolve_variant` is frozen beside it, since `mutation_check.py`'s
copy moves with the spec. `audit_cross_section` carries its own ladder, and
`../dogfood` and `../openknowledge/score.py` read only the linter.

The partly-marked run keeps every anchor and leaves a marker on every other id in the
edited document, once for each parity, with all fourteen operators on all three
corpora. It is the run where tiers 2 and 3 meet blocks claimed at tier 1. It was
registered after a probe of the same sweep, so it is not blind, which finding 9 says.

The merge exemption decides placement like this. Let q1 to qk be the contending
stays' quotes and B the body of the block they contend for, each after §9's quote
normalization (ASCII letters lowercased, runs of ASCII whitespace collapsed to one
space, ends trimmed), not §8's hash normalization. Offsets and lengths count
Unicode code points of those normalized strings, and an occurrence of q at offset
p is the half-open span [p, p + len(q)), so two occurrences may touch without
overlapping. The contenders are indexed, so two stays with the same quote text are
two contenders that need two occurrences. If any qi is empty the exemption fails;
with no contenders it holds. Otherwise it holds when the k occurrences can be
chosen so that no two overlap, decided as follows. For each subset S of the
contenders, end(S) is the smallest offset e such that every quote in S has an
occurrence inside B[0, e), no two overlapping. end of the empty set is 0. end(S)
is the minimum, over each qi in S whose end(S without qi) is defined and for
which find(qi, end(S without qi)) exists, of that find plus len(qi), where
find(q, p) is the smallest offset at or after p at which q occurs in B; end(S) is
undefined when no qi qualifies. The exemption holds when end of the full set is
defined. When the quotes' total length exceeds the length of B, it fails
immediately, which never changes the answer. The procedure makes 2^k times k
substring searches, each linear in the length of B under a linear-time search
algorithm. That is exponential only in the number of contenders, the handful of stays that
reached one block, and independent of how often a quote occurs. `resolver.py` and the
conformance corpus fail the exemption outright when more than 16 stays contend,
checked before the length check (FINDINGS.md finding 9; at §9's defaults no more than
four can reach the test); the arm has no cap, which differs only above 16 contenders
at a caller's lower threshold.

The operators it needs live in `perturb.EXCL_OPERATORS`, kept out of `OPERATORS`
so `results.md` is still measured over the operator set it always was: `replace`
(unrelated text in a block's slot, so the old id must detach), `replace_related`
(a same-topic replacement whose detach truth is semantic), `swap_edit`, and twelve
`copy_*` operators that paste a marked paragraph above or below it or at either
end of the document, verbatim, with the copy edited, or with the original edited.
`perturb.TWIN_EDIT_OPERATORS` holds `edit_into_twin`, which rewrites one marked paragraph
into another's exact text, each keeping its own id: the one shape that reaches exclusive
tier 2's claimed filter. It runs only partly marked, apart from `EXCL_OPERATORS`, whose
published sweeps it would otherwise move. The arms also run on a half-stamped variant where
only every other block carries a marker. The verdict is finding 9 in `FINDINGS.md`.

### Detached diagnostics

`Resolution.method` keeps the stable `marker | hash | quote | detached` axis.
A detached result now also says why:

- `ambiguous`: the best quote cleared the threshold but failed the required
  margin over another plausible block.
- `unmatched`: no quote cleared the threshold, including an empty document.

Only `ambiguous` carries candidates. They are the contenders that explain the
failed margin, in the resolver's historical `(score, index)` descending order.
Sub-threshold candidates are deliberately omitted from `unmatched`, since
surfacing weak matches would invite callers to treat noise as a repair. Candidate
evidence and labels are diagnostic, not protocol or attachment authority. A
detached result never commits a target.

The packaged child resolver adds `unscored`, `unaddressed`, and `contested` for
paths that cannot be described honestly as a failed quote match. Its candidate
provenance distinguishes independent block scoring from parent and child
tier-start snapshots. Snapshot context evidence is labelled as adjacency within
that filtered candidate snapshot, not as physical document adjacency. A
same-tier contest still continues to weaker tiers as §9.2 requires. If no weaker
tier attaches the stay, the final detached result retains the strongest contest.

## Files

| File | Role |
|------|------|
| `resolver.py` | the evidence ladder: marker -> hash -> quote -> DETACHED, with detached reasons and diagnostic candidates. Reuses the linter's `parse_document` / `body_hash`. |
| `ladder_v110.py` | that ladder and its parameterised form as spec v1.10 shipped them, frozen for the arms and dated records. |
| `quote.py` | W3C `TextQuoteSelector`-style recovery: similarity + exact-containment + prefix/suffix tiebreak, with a compatibility wrapper over ranked candidates. |
| `perturb.py` | deterministic edit operators (reorder, edit, heavy-paraphrase, split, merge, delete, insert, decoy, clone) with ground-truth tracking. |
| `run_attach_eval.py` | harness, scoring, report. |
| `item_eval.py` | opt-in list-item identity: a shape x operation matrix (6 list shapes x 9 edit operations), gated per shape so benign families cannot dilute an adversarial failure. |
| `results_item.{json,md}` | the item-granularity result, with the 95% Clopper-Pearson bound on the false-attach rate. |
| `fixtures/near_dups.md` | adversarial near-duplicate blocks (the danger case). |
| `fixtures/cross_section_dups.md` | the same danger spread across sections, plus twins that are byte-identical under different parents. |
| `results_crosssection_fixture.{json,md}` | that fixture's control baseline under the shipped resolver, with the fixture's measured shape. |
| `heading_arms.py` | the heading-path arms: thirteen configurations x four corpora, with Clopper-Pearson intervals and a case-by-case regression list against the control. |
| `results_headingpath.{json,md}` | what those arms measured. |
| `excl_arms.py` | the exclusivity and duplicated-id arms, with Clopper-Pearson intervals and a case-by-case comparison against the control. |
| `results_exclusivity.{json,md}` | what those arms measured. |
| `test_excl_arms.py` | the arms' and the identity-boundary operators' self-tests. |
| `FINDINGS.md` | what the data says and what it means for the spec. |

## Headline

On lexically distinct prose: 99% correct re-attachment, 0% false attachment
(hash does 81% of the work, exactly). On near-duplicate blocks the v1.10 ladder
attaches falsely (3% with the guard, 8% without), worst on merge. v1.11's
exclusive assignment (SPEC.md §9.1) detaches those collisions instead, and
`results.md` now reads 0 of 72 wrong both ways, its two merge errors become two
misses. That second number is in-sample: this fixture is one of the three
corpora the rule was chosen on (`FINDINGS.md` finding 9). Takeaway: content
recovery is best-effort evidence, not authority; the surviving id token and exact
hash are the trustworthy signals, and the margin guard (default to DETACHED on a
near-tie) is mandatory, since a near-duplicate with no stay of its own has
nothing to contest it. See `FINDINGS.md`.

The experimental item-granularity matrix measures 95.0% recovery, 0.0% false
attachment (0/324), and 5.0% detach on surviving items, with a 95%
Clopper-Pearson upper bound of 0.92% on the false-attach rate. The n is the point:
with zero observed events that bound is `1 - 0.05**(1/n)`, so roughly 300
resolutions are the minimum at which a clean run can certify a ~1% bar, and an
earlier 55-resolution form could not have done so at any score.

An earlier run measured 3.6% false attachment from a near-duplicate wrong-parent
cascade. That was a resolver defect rather than a granularity limit: parents were
resolved per anchor, so a deleted list could quote-match onto its surviving
near-duplicate sibling at a wide margin, precisely because the edit had removed
the only rival that would have contested the match. Parent tiers now assign
exclusively. Re-running this matrix against the pre-fix resolver still reports six
false attachments across two shapes, so the clean result is a behaviour change and
not a weaker test.

Real LLM rewrites agree from an independent direction: `llm/` at
`--granularity item` scores 256 resolutions on gpt4o at 92.2% recovery and 0.0%
false attachment (bound 1.16%), with the attach floor landing on §9's 0.5
threshold. See `llm/FINDINGS.md`.

The prototype stays opt-in regardless. Both safety bars are met; what is still
unmeasured is the benefit half, catch precision on real item drops against the
`COLLECTION_SHRANK` count heuristic it would replace.
