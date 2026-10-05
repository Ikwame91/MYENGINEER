# Lab 04: The Cache Stampede

**Concepts:** caching and TTLs, the thundering herd / cache stampede, single-flight (request
coalescing), synchronized expiry and TTL jitter, overload amplification, the staleness vs load
trade-off.

## The page

> **#incident-catalog** · 20:01
> **Pager:** `product-db CPU 100%`, `p99 latency > 500ms`. Firing every few seconds, then resolving.
> **Teammate:** Weird, the cache hit rate is 98%. How can the DB be melting with a 98% hit rate?
> **Another teammate:** Just raise the TTL to an hour?
> **Product:** Prices change during sales. Customers must never see a price older than 1.5s.

100 request handlers share one in-process `ProductCache` (`app.py`). 90% of traffic is for 3
front-page deals. The DB runs 8 queries at full speed. Past that, every query slows down for everyone.

## Run it

```bash
python3 lab.py run 04       # a chart of DB queries in flight over time, plus latency and data age
python3 lab.py check 04
```

## Investigate before you touch code

In `journal/04.md`:

1. Look at the chart. When do the spikes start, relative to the TTL? Why are there no spikes
   at all for the first second?
2. A hot key expires. 100 handlers ask for it in the next millisecond. How many DB queries does
   the current code send for that *one* key? How many are actually needed?
3. Why does the overload make itself worse? (What happens to the next expiry if queries are slow?)
4. The deploy script warms all 50 products at once. What does that do to *when* they expire?
5. Why is "raise the TTL to an hour" not an answer here? And what would it be an answer to?

## Rules

- Change only `app.py`. Keep `TTL` as a class attribute (the checker reads it).
- No new dependencies. `threading` has everything you need.

## Done when

`python3 lab.py check 04` passes: peak DB concurrency ≤ 20, request p99 ≤ 200ms, about one DB
load per product per TTL, no price older than 1.5s, and handlers not stuck waiting.

## After you pass

Read `solution/NOTES.md`.
