## Hint 1
The 98% hit rate is an *average*. The damage happens in the 2% of moments when a hot key
expires and every handler misses **at the same time**. That's a *cache stampede* (or thundering herd).

## Hint 2
For each key, only **one** caller should load from the DB. Everyone else who misses on that key
should wait for that load and use its result. This is called *single flight* or *request coalescing*.

## Hint 3
You'll need a lock to protect the cache dict and the "who's loading what" bookkeeping, but
**never hold one global lock while calling the DB**. That serializes every miss behind every
other miss (try it and watch p99). Hold the lock only to decide; do the slow work outside it.
`threading.Event` is a convenient way to let waiters sleep until the loader finishes.

## Hint 4
Make sure waiters wake up even if the DB call raises (`try/finally`), otherwise one failed load
hangs every request for that key forever.

## Hint 5
With single-flight you'll still see a spike about 1 TTL after start: every product was warmed in
the same instant, so they all expire in the same instant. Randomize each entry's TTL a little
(e.g. ±20%) so expirations spread out. That's *jitter*.
