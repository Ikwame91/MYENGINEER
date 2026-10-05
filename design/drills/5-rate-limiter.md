# Drill 5: Distributed rate limiter

## The prompt

Design the rate limiter for a public API.

- Each API key has a limit, e.g. 1,000 requests/minute, some with bursts allowed.
- The API runs on 200 servers in 3 regions. Traffic is 2M requests/second total.
- The limiter must add **< 2ms** to each request.
- Over-limit requests get `429 Too Many Requests` with a `Retry-After` header.

**Deliver:** the algorithm, where state lives, what happens when the limiter's state store is
slow or down, and how accurate it is.

Related labs: 04 (hot keys in a cache), 06 (partitioning), 07 (load shedding).

<!-- REVIEW -->

## Reviewer's questions

1. Fixed window, sliding log, sliding window counter, token bucket: what are the trade-offs in
   memory, accuracy, and burst behavior? Which did you pick and why?
2. With a fixed 1-minute window, how many requests can a client get through in 2 seconds?
   (Think about the window boundary.)
3. Where's the counter? If it's a central Redis: 2M ops/s, is that one node? How is it partitioned? (Lab 06.)
4. One huge customer is 30% of traffic. Their key is a hot key on one Redis shard. What now?
5. The limiter's store is down. Fail open (allow everything) or fail closed (reject everything)?
   Who decides, and does it differ per endpoint?
6. 3 regions: is the limit global or per region? What does a global limit cost in latency?
7. Could each server limit locally (limit / 200) with no shared state? When is that good enough?
8. How does a client know when to retry? What should well-behaved clients do on 429? (Lab 05.)
9. Is rate limiting the same as load shedding? When would you need both? (Lab 07.)
10. How do you test that the limit is enforced to within 5%?

## Common mistakes

- A synchronous network call to a central store on every request, with no timeout or fallback.
- Ignoring clock skew between servers in window-based algorithms.
- Treating "per-customer fairness" (rate limiting) and "protect the server" (load shedding) as one thing.

## Sketch of a strong answer

Token bucket per API key (bursty but bounded, O(1) state). State in a sharded Redis cluster, keyed
by API key, updated with an atomic Lua script (refill + take in one step). To keep the latency
under 2ms and survive store problems, each server keeps a **local token cache**: it leases tokens
in batches from Redis (e.g. 50 at a time) and serves requests locally. That trades a few % of
accuracy for far fewer round trips and makes hot keys cheap. Limits are per region (each region
gets a share, rebalanced periodically) unless a global guarantee is contractual. If Redis is
unreachable, fall back to local-only limits (limit / N servers), which is neither fully open nor closed.
Load shedding stays a separate, server-protecting layer.
