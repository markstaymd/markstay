Every deployment follows the same four stages, and the checks below are run in
order with no step skipped.

# Deployment Runbook

## Ingest

Before promoting a build, confirm the ingest worker has drained its queue and
that no message has been in flight for longer than five minutes.

Ingest holds a replay buffer sized to four hours of traffic, which is the window
the upstream vendor guarantees for redelivery.

If the ingest stage reports errors after promotion, roll the deployment back to
the previous tag and leave the failed pods running for inspection.

## Persist

Before promoting a build, confirm the persist worker has drained its queue and
that no message has been in flight for longer than five minutes.

Persist writes through to the primary and acknowledges only after the replica
has confirmed, so a promotion during replica lag will appear as a write stall.

If the persist stage reports errors after promotion, roll the deployment back to
the previous tag and leave the failed pods running for inspection.

## Dispatch

Before promoting a build, confirm the dispatch worker has drained its queue and
that no message has been in flight for longer than five minutes.

Dispatch fans out to partner endpoints in parallel and treats any non-2xx as
retriable, which means a partner outage looks identical to a deploy failure.

If the dispatch stage reports errors after promotion, roll the deployment back
to the previous tag and leave the failed pods running for inspection.

## Archive

Before promoting a build, confirm the archive worker has drained its queue and
that no message has been in flight for longer than five minutes.

Archive compacts yesterday's partitions during the promotion window, so a long
deploy and a long compaction will contend for the same disk budget.

If the archive stage reports errors after promotion, roll the deployment back to
the previous tag and leave the failed pods running for inspection.

## Reconcile

Before promoting a build, confirm the reconcile worker has drained its queue and
that no message has been in flight for longer than five minutes.

Reconcile compares yesterday's totals against the partner's statement and will
report a false mismatch if it runs while the archive compaction is still going.

If the reconcile stage reports errors after promotion, roll the deployment back
to the previous tag and leave the failed pods running for inspection.

## Retry Policy

The connector retries a failed call three times with exponential backoff before
routing the payload to the dead-letter queue for manual review.

The connector retries a failed call five times with exponential backoff before
routing the payload to the dead-letter queue for manual review.

The connector retries a failed call seven times with exponential backoff before
routing the payload to the dead-letter queue for manual review.

Overrides are set per partner and expire after thirty days, so a tuning change
made during an incident cannot quietly become permanent.

## Development

### Rollback

Roll back by re-pointing the alias at the previous revision, then confirm the
health endpoint returns two hundred within thirty seconds.

### Access

Anyone on the engineering rota can deploy here without approval, and the
environment is rebuilt from scratch every Sunday night.

## Production

### Rollback

Roll back by re-pointing the alias at the previous revision, then confirm the
health endpoint returns two hundred within thirty seconds.

### Access

Two approvals are required before any promotion, and the deploying engineer must
remain reachable for the following hour.

## Staging

### Rollback

Roll back by re-pointing the alias at the previous revision, then confirm the
health endpoint returns two hundred within thirty seconds.

### Access

Anyone on the engineering rota can deploy here without approval, and the
environment is rebuilt from scratch every Sunday night.

Appendix
--------

Contact the platform team through the on-call rota rather than direct message,
because direct messages are not captured in the incident timeline.
