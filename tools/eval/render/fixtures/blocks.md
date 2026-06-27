# markstay render-survival corpus: one stay per block kind

Every block below carries a stay as a *marker-only chunk* (blank line, then the
comment on its own line). This is the placement a formatter most often reflows,
and the one `impl/py/tests/test_mdformat_safety.py` exercises.

First paragraph about the thing.

<!-- stay:p1 -->

## A heading that owns an id

<!-- stay:h1 -->

* item one
* item two
* item three

<!-- stay:l1 -->

```python
def f():
    return 1
```

<!-- stay:c1 -->

> a quoted line
> second quoted line

<!-- stay:q1 -->

| a | b |
|---|---|
| 1 | 2 |

<!-- stay:t1 -->
