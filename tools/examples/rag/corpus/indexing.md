# How database indexes work
<!-- stay:b1eSVBcI hash=sha256:e8e45f27be40 -->

An index is a separate data structure that lets the database find rows without scanning
the whole table. Without one, a query that filters on a column must read every row and
test the predicate, which is linear in the size of the table. With an index on that
column, the database walks a sorted structure and jumps straight to the matching rows.
<!-- stay:X5oqxwzC hash=sha256:0d810dc9f72c -->

## B-trees
<!-- stay:TcWXqm8G hash=sha256:783124944320 -->

Most relational databases use a B-tree as the default index. A B-tree keeps keys sorted
and balanced so that lookups, range scans, and ordered traversal all run in logarithmic
time. Because the keys are sorted, a B-tree serves equality lookups, range queries, and
ORDER BY on the indexed column from the same structure.
<!-- stay:gR9JC0Cb hash=sha256:c7b7619c8d13 -->

The trade-off is write cost. Every insert, update, or delete that touches an indexed
column must also update the index, and a heavily indexed table pays that cost on every
write. A table optimized purely for write throughput keeps its index count low; a table
optimized for reads accepts more indexes to serve more query shapes.
<!-- stay:RW96GShV hash=sha256:3325de01273b -->

## Composite indexes and column order
<!-- stay:NIq6XcS4 hash=sha256:bd1998460f78 -->

An index on multiple columns is a composite index, and the order of the columns matters.
An index on (tenant_id, created_at) can serve a query that filters on tenant_id alone,
or on tenant_id and created_at together, because those are leftmost prefixes of the key.
It cannot efficiently serve a query that filters only on created_at, because created_at
is not a prefix. This leftmost-prefix rule is the single most common reason a query that
"has an index" still runs slowly.
<!-- stay:AG0OqD5K hash=sha256:706ecfbf653d -->

## Covering indexes
<!-- stay:3m2eCXd3 hash=sha256:ec95293bce52 -->

If an index contains every column a query reads, the database can answer the query from
the index alone and never touch the table. This is a covering index, and it can turn a
two-step lookup into one. The cost is a wider index that duplicates more data and slows
writes further, so covering indexes are worth it for hot queries and wasteful for rare
ones.
<!-- stay:zmhIEfDU hash=sha256:df35e954e8dd -->

## When not to index
<!-- stay:K1lbTHo0 hash=sha256:f0c2e56096e3 -->

Indexes are not free, and more is not better. An index on a low-cardinality column, such
as a boolean flag where almost every row has the same value, rarely helps because the
database still reads most of the table. The right indexes come from looking at the slow
queries the application actually runs, not from indexing every column in advance.
<!-- stay:kny6D1Dr hash=sha256:0bbf2350abcd -->
