# Lab 04 notes: what was wrong, and what a senior engineer sees

## Root cause

Three effects stacked:

1. **Stampede.** When a hot key expired, all ~100 handlers missed simultaneously and each sent its
   own DB query: 100 queries for data that needed 1.
2. **Synchronized expiry.** The deploy warmed every key in the same instant, so they all expired
   in the same instant. Same for any batch load.
3. **Overload amplification.** Past capacity, every query gets slower. Slow loads mean more
   handlers pile in before the key is refilled, which means even slower loads.

A 98% hit rate hid all of this. **Averages hide spikes; look at peaks and percentiles.**

## The fix

- **Single flight per key**: the first miss becomes the loader. Others wait on an `Event`, then
  re-read the cache. The lock only guards bookkeeping and is never held across the DB call.
- **TTL jitter (±20%)**: entries loaded together expire spread out over time.
- `try/finally` so a failed load wakes the waiters instead of hanging them forever.

Peak DB concurrency drops from 100 to ~14, p99 from ~600ms to ~45ms, and DB queries are roughly halved.

## What a senior engineer also notices

1. **Stale-while-revalidate.** Even better for hot keys: keep serving the old value while *one*
   background refresh runs, so no request ever waits. You trade a little freshness (bounded) for
   zero latency spikes. Same idea: refresh probabilistically *before* expiry ("XFetch").
2. **This was an in-process cache. With 50 servers, you have 50 stampedes.** Each server
   coalesces its own misses, so the DB still sees up to 50 loads per expiry. Fixes: a shared cache
   (Redis or Memcached) with a short **lock key** (`SET key:lock NX PX 500`) so one loader in the
   whole fleet refreshes, or a *request coalescing* layer.
3. **Cache invalidation races.** If writes do "update DB, then delete cache key", a slow reader can
   load the *old* value before the update, then put it back *after* the delete. Now it's stale until
   the TTL. That's why TTLs are a safety net even when you invalidate on write, and why some systems
   use versioned keys or leases (see Facebook's "Scaling Memcache" paper).
4. **Cold start is an outage.** If the cache cluster restarts empty, the DB takes 100% of traffic.
   Can it? If not, you need warm-up, admission control, or load shedding (Lab 07). "The cache is an
   optimization" stops being true the moment the DB can't survive without it.
5. **Negative caching.** Requests for products that *don't exist* miss every time and hit the DB
   every time. Cache "not found" too (briefly), or a bot can melt your DB with random IDs.
6. **Measure the right thing.** Alert on DB concurrency and saturation, and on cache miss *rate
   per second* (not hit ratio), and track p99/p999 latency. Not averages.

## Self-test

- Draw what happens in the 50ms after a hot key expires, before and after single flight.
- Why does holding one global lock around the DB call pass the concurrency check but fail p99?
- Product now wants prices at most 100ms stale. What would you tell them, with numbers?
