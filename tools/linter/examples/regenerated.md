# Order Pipeline Overview
<!-- stay:ovw1 -->

A quick recap of the overview for new readers.
<!-- stay:ovw1 -->

The pipeline ingests partner messages and normalizes them before writing to the store.

The validation stage runs the partner, catalogue, and pricing checks before persistence.

```python
def validate(order):
    org = resolve_org(order.partner_id)
    if not org.active:
        raise InactiveOrg(order.partner_id)
    return order
```

Operators can override the defaults per partner; overrides expire after thirty days.
<!-- stay:ovrd -->

A newly added note about monitoring and alerting.
<!-- stay:mon1 -->
