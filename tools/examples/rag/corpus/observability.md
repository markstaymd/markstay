# The three pillars of observability
<!-- stay:vQzzf99d hash=sha256:c80ecdf73c1b -->

Observability is the property of a system that lets you understand its internal state
from the outside. A service is observable when an operator can answer a new question
about its behaviour without shipping new code to expose the answer. The practice rests on
three kinds of telemetry: logs, metrics, and traces.
<!-- stay:ogdWsP51 hash=sha256:d45ac5db6bc4 -->

## Logs
<!-- stay:3uLGRZMJ hash=sha256:c8d9d134a246 -->

A log is a timestamped record of a discrete event. Logs are the oldest and most flexible
signal because a line can carry arbitrary context, but that flexibility is also their
weakness: unstructured text is hard to query at scale. Structured logging, where each
line is a set of key-value fields rather than a sentence, makes logs searchable and
aggregatable, and is the baseline expectation for any service running in production.
<!-- stay:KE4WJuGd hash=sha256:2d407f53c8ad -->

The discipline with logs is volume. A chatty service can generate gigabytes an hour, and
the cost of storing and indexing that quickly dwarfs the value. Log at the level the
question demands, sample high-volume events, and keep the noisy debug output behind a
flag you can turn on when you need it.
<!-- stay:3RZWyH5n hash=sha256:eb55c2ca6e16 -->

## Metrics
<!-- stay:b0AJJZZt hash=sha256:0452266c781f -->

A metric is a numeric measurement aggregated over time, such as request rate, error
rate, or latency. Metrics are cheap to store and fast to query because they are
pre-aggregated, which makes them the right tool for dashboards and alerts. The classic
starting set is the four golden signals: latency, traffic, errors, and saturation.
<!-- stay:O9W5cTAr hash=sha256:2a7914958255 -->

The limitation of a metric is that it summarizes. A latency metric tells you the
ninety-ninth percentile got worse; it cannot tell you which user or which code path
caused it. For that you need a signal that follows a single request.
<!-- stay:LImGwYmI hash=sha256:bddabc4a2066 -->

## Traces
<!-- stay:rsKnE54d hash=sha256:76b386f19db6 -->

A distributed trace follows one request across every service it touches, recording the
time spent in each. In a system of many small services, a trace is the only signal that
shows where a slow request actually spent its time, rather than which service merely
reported high latency. Each step is a span, and the spans together form a tree rooted at
the original request.
<!-- stay:qew04XhV hash=sha256:1acaac8266b7 -->

Used together, the three pillars answer different halves of the same question. Metrics
tell you something is wrong and alert you to it. Traces tell you where. Logs tell you
why. A team that invests in one and neglects the others ends up able to see the symptom
but never the cause.
<!-- stay:78j9laGT hash=sha256:696f7fa02dd6 -->
