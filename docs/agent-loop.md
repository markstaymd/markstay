# The agent loop

Most markstay adoption advice stops at "install a pre-commit hook". That advice is
incomplete in a way worth being specific about, because the gap it leaves is exactly
where real losses happen.

A commit hook is a *backstop*. It reports a loss that already happened, at the moment
you try to record it. Between the edit and the commit, the agent has moved on, its
context is gone, and the person reviewing the block is reading a diff rather than
watching a rewrite. This page is about closing that distance.

!!! question "The question"
    An agent rewrites a document and some `stay:` markers do not survive. What
    actually notices, and how long does it take?

## Three places to stand

| where | verb | what it does |
|---|---|---|
| in the prompt, before the edit | `preserve` | prevents the loss |
| after the edit, before the commit | `check-worktree` | reports it while the agent is still in the loop |
| at the commit | `check-staged` | blocks it from being recorded |

They are ordered by value, not by convenience. The
[evaluation](evaluation.md) measured the first at roughly a twentyfold improvement in
marker survival, and the
[dogfood study](dogfood.md) found the third does not earn its keep as a *standalone*
guard. Run all three if you can, but if you run one, run `preserve`.

## What a real loss looked like

The following is from a private documentation repo that had markstay installed and a
pre-commit hook running. It is the case that produced the fixes described below.

| | |
|---|---|
| stays lost in one commit | **21** |
| time the loss sat undetected in a working tree | **12 days** |
| size of the commit that recorded it | **406 lines** |
| stays repo-wide, before and after | 1246 to 1128 |

The document was rewritten wholesale by an agent session that never mentioned
markstay, and the markers went with the prose. Nothing surfaced it for twelve days,
because nothing looked until commit time, and by then the change was one file inside a
large commit that read as an ordinary docs update.

Two things went wrong, and only one of them was the hook.

### The check that could not see a rename

The hook resolved each document's baseline **by filename**: list the staged paths, ask
git for the previous version at that path, compare. For a renamed file git reports
only the new path, so the lookup for the old content failed, the baseline came back
empty, and the regeneration diff never ran at all.

The failure was invisible because the *other* half of the report still worked.
Well-formedness findings need no baseline, so the hook still printed drift warnings
and exited cleanly. It looked like a document that had been checked and passed. It was
a document that had never been compared to anything.

Lowering git's rename-detection threshold does not fix this. The real commit scored
**2%** content similarity: at `-M50%` and `-M10%` git calls it a delete plus a create,
and only at `-M1%` does it call it a rename, by which point every unrelated
added/deleted pair in a commit looks like one too.

That is structural rather than unlucky:

!!! warning "The more a rewrite destroys, the less it looks like a rename"
    The bigger the rewrite, the more stays it can drop, **and** the less content
    similarity survives for git to match on. Content similarity is anti-correlated
    with the failure mode, so a filename-keyed check degrades exactly where it is
    needed most.

The fix is the thing this specification is about. The baseline is now resolved **by
stay id**: a modified path uses its own previous version, a rename uses the old path,
and a file git reports as newly added is paired with the document deleted in the same
commit that shares the most stay ids. A surviving id anchored the pairing at 2%
similarity, where nothing content-based could have. An id that moved to a different
document is reported as a *move* rather than a loss, which also stopped the check from
blocking legitimate cross-file reorganisation.

The hook had been keying identity by path, which is the one thing this specification
says is not identity. It was the same failure class markstay exists to fix, one level
up from the documents it was checking.

### The check that was too late anyway

The second problem is not a bug, and no amount of fixing the hook addresses it.

Replaying the fixed check against the original commit reports all 21 dropped ids, so
the hook would have blocked it. But the loss was already twelve days old by then. It
had been sitting in a working tree since the session that caused it, and the person
who could have said "no, keep those" had long since stopped thinking about that
document.

`check-worktree` exists for that gap. It runs the same comparison against the files on
disk, staged or not, so an agent can run it as a post-edit step and get the answer
while the rewrite is still on screen:

```bash
markstay check-worktree
```

Wire it wherever your agent finishes a turn. In Claude Code that is a `Stop` hook; in
other harnesses it is whatever runs after a tool call completes. Two properties make
this practical rather than annoying: it is inert in repos that have no stays, and it
is worth suppressing repeat reports of an identical finding set within a session, so
that a deliberate restructure cannot trap the agent in a loop.

## What to take from this

The honest summary is not "install the hook and you are safe".

- **The instruction is the control.** It is the only one of the three that prevents
  anything. Everything else reports.
- **A backstop that reports success without having looked is worse than no backstop**,
  because it converts an open question into a false answer. This one printed warnings
  the whole time it was failing to compare anything.
- **Latency is part of correctness.** A check that is right twelve days late did not
  prevent the loss, it documented it.

For the wiring, see [Get started](get-started.md). For the numbers behind the
instruction, see the [marker survival study](evaluation.md) and the
[public dogfood case study](dogfood.md).
