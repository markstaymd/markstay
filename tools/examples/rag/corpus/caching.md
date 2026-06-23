# Caching strategies for read-heavy services
<!-- stay:pITD9gg5 hash=sha256:434dcf91de4b -->

A cache sits between a client and a slower source of truth. When a service reads the
same data far more often than it writes, a cache turns most reads into cheap in-memory
lookups instead of round trips to a database or an upstream API. The art is not adding
a cache, it is deciding when an entry is allowed to go stale and how the system notices.
<!-- stay:GGLcjD5y hash=sha256:88669a8b6809 -->

## Cache-aside
<!-- stay:OZoAAY5s hash=sha256:fcbb831cf126 -->

The most common pattern is cache-aside, sometimes called lazy loading. The application
checks the cache first. On a hit it returns the cached value. On a miss it reads the
source of truth, stores the result in the cache, and returns it. The cache only ever
holds data that has actually been requested, so memory tracks the working set rather
than the whole dataset.
<!-- stay:VGiayjA3 hash=sha256:ecc2609e25b5 -->

The weakness of cache-aside is the window between a write to the source and the next
read. If a record changes in the database but the cached copy is not evicted, readers
keep seeing the old value until the entry expires. Teams usually pair cache-aside with
an explicit invalidation step on write, or a short time-to-live that bounds how stale
a value can get.
<!-- stay:b4y0juaJ hash=sha256:1242651a0d6e -->

## Write-through and write-behind
<!-- stay:pdcx3cIW hash=sha256:aea64a12885d -->

A write-through cache accepts the write itself, persists it to the source of truth, and
updates its own copy in the same operation. Reads after a write are always consistent
because the cache was part of the write path. The cost is write latency: every write
now pays for both the cache and the backing store.
<!-- stay:56caDnqS hash=sha256:c7c36eff7dc0 -->

Write-behind relaxes that by acknowledging the write immediately and flushing to the
source asynchronously. Throughput improves and write latency drops, but a crash before
the flush loses data, so write-behind suits metrics and counters more than orders and
payments.
<!-- stay:DlawgOHC hash=sha256:f5ddc23e0a5c -->

## Invalidation
<!-- stay:LNd9a7gu hash=sha256:5483bf1b3a15 -->

Phil Karlton's quip that there are only two hard problems in computer science, cache
invalidation and naming things, has survived because it is true. The safest default is
a time-to-live short enough that stale reads are tolerable and long enough that the hit
rate stays high. Event-driven invalidation, where a write publishes a message that
evicts the affected keys, is more precise but adds a moving part that can fail silently
and leave the cache serving stale data with no expiry to save it.
<!-- stay:EBbxHXpf hash=sha256:703d21f69911 -->

Whatever the scheme, measure the hit rate in production. A cache with a low hit rate is
pure overhead: it pays the cost of an extra lookup on every read and rarely avoids the
expensive path it was meant to protect.
<!-- stay:scEyHzyH hash=sha256:cc8b69af499a -->
