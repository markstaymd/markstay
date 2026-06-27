# markstay render-survival corpus: hash-bearing marker

The marker below carries a `hash=` attribute (SPEC.md §8). The round-trip oracle
must see the whole marker (id + hash) survive: a tool that drops the `hash`
attribute but keeps the id, or HTML-escapes the whole comment, is a finding. A
hash *drift* (the formatter reflows the body so the stored hash no longer matches)
is allowed and not a failure.

A paragraph whose identity is pinned with a content hash, long enough that a
reflowing formatter might rewrap it onto different lines without changing a single
word of its meaning.

<!-- stay:hh1 hash=sha256:7a9c -->
