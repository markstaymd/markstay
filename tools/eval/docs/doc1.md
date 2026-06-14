# Order Pipeline Overview

The order pipeline ingests messages from external partners, normalizes them, and writes them to the transactional store. Each stage emits a structured event so downstream consumers can react without polling.

Messages arrive on a queue and are validated before any persistence happens. Invalid payloads are routed to a dead-letter queue with the original headers preserved for replay.

The validation stage checks three things:

- The partner identifier resolves to an active organization.
- The order references a known product catalogue entry.
- Pricing fields are present and internally consistent.

A failed check produces a typed error rather than a generic exception, which lets the dispatcher decide whether to retry or quarantine.

```python
def validate(order):
    org = resolve_org(order.partner_id)
    if not org.active:
        raise InactiveOrg(order.partner_id)
    return order
```

The table below summarizes the retry policy applied at each stage.

| Stage | Retries | Backoff |
|-------|---------|---------|
| ingest | 3 | exponential |
| persist | 5 | exponential |

Operators can override the defaults per partner when a partner has known latency problems, but overrides expire after thirty days to avoid silent drift.
