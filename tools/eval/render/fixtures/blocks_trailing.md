# markstay render-survival corpus: trailing-marker placement

Same block kinds as `blocks.md`, but each marker sits on the line *directly after*
its block with no blank line in between (it rides the block's own chunk). This is
the denser placement; some formatters insert a blank line before it (turning it
into a marker-only chunk), which attachment must survive.

First paragraph about the thing.
<!-- stay:p2 -->

## A heading that owns an id
<!-- stay:h2 -->

* item one
* item two
* item three
<!-- stay:l2 -->

```python
def f():
    return 1
```
<!-- stay:c2 -->

> a quoted line
> second quoted line
<!-- stay:q2 -->

| a | b |
|---|---|
| 1 | 2 |
<!-- stay:t2 -->
