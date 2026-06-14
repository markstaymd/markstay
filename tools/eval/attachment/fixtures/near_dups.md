# Retry Policy Reference

The ingest stage retries failed operations three times with exponential backoff before routing the message to the dead-letter queue for manual review.

The persist stage retries failed operations five times with exponential backoff before routing the message to the dead-letter queue for manual review.

The dispatch stage retries failed operations seven times with exponential backoff before routing the message to the dead-letter queue for manual review.

Operators can override these defaults per partner, but every override expires after thirty days so that stale tuning never silently persists in production.

The checklist before a deployment is short and must be completed in order without skipping any step.

The checklist before a rollback is short and must be completed in order without skipping any step.

Each completed run is recorded in the audit log together with the operator name, the affected partner, and the exact timestamp of the change.
