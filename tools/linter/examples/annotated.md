# Order Pipeline Overview
<!-- stay:ovw1 -->

The order pipeline ingests messages from external partners, normalizes them, and writes them to the transactional store.
<!-- stay:ingest -->

The validation stage checks the partner, the catalogue entry, and pricing before anything is persisted.
<!-- stay:checks -->

```python
def validate(order):
    org = resolve_org(order.partner_id)
    if not org.active:
        raise InactiveOrg(order.partner_id)
    return order
```
<!-- stay:code1 -->

Operators can override the defaults per partner, but overrides expire after thirty days to avoid silent drift.
<!-- stay:ovrd -->
