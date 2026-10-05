# Lab 07 notes: what was wrong, and what a senior engineer sees

## Root cause

An **unbounded FIFO queue** in front of a fixed-capacity server. During the spike the queue grew
~100 requests/s. Within a second, queueing delay exceeded the client timeout, so the server spent
100% of its capacity producing responses nobody received: **throughput stayed high, goodput went
to zero**. After the spike, the backlog of dead requests kept new requests waiting past their
deadlines too, so the failure **sustained itself** with normal traffic. That's a *metastable
failure*, and why "restart fixes it": a restart throws away the queue.

## The fix

1. **Bounded queue (20)** sized with Little's law: 200 req/s × 0.1s acceptable wait = 20.
2. **Load shedding**: when full, reject *immediately*. A fast 503 lets the client retry elsewhere
   or later. A slow timeout wastes everyone's time.
3. **Deadline-aware dequeue**: skip requests whose client will be gone before you can answer.

Result: goodput ≈ capacity during the spike (~200/s), successes stay fast (p99 ~120ms), and
recovery is instant.

## Half-fixes, and why they fail

| Attempt | Result |
|---|---|
| Drop expired requests only | Recovers, but successes take ~500ms: you're serving people just before they give up |
| Bounded but huge queue (500) | Same: the bound is longer than the timeout, so it doesn't help |
| Bounded queue with blocking `put()` | The listener stalls; the queue moves into the socket backlog; same collapse |

## What a senior engineer also notices

1. **Queues belong where you can see and bound them.** Unbounded queues hide in thread pools,
   connection pools, socket backlogs, message brokers, and `asyncio` tasks. Every one needs a
   bound and a metric (depth, age of oldest item).
2. **Propagate deadlines.** The client's deadline should travel with the request (gRPC does this
   natively). Every downstream call gets the *remaining* budget, not a fresh timeout. Otherwise
   the database keeps working on queries for a user who left 3 seconds ago.
3. **LIFO under overload.** Some systems switch to newest-first when the queue is long. The newest
   requests are the ones whose clients are still waiting. CoDel-style adaptive queues (used by
   Facebook) drop based on queueing *time*, not length.
4. **Retries make this worse.** Every timed-out client retries, so 300/s of real demand becomes
   600/s of offered load. Combine shedding with client-side backoff and retry budgets (Lab 05).
5. **Capacity planning is a queueing problem.** Latency doesn't rise linearly with utilization; it
   explodes as utilization → 100%. Plan for peak, keep headroom (~60-70% target utilization), and
   autoscale *before* the queue forms, because autoscaling takes minutes and the spike takes seconds.
6. **Prioritize.** When shedding, shed the least valuable traffic first: background sync before
   checkout, anonymous before logged-in, retries before first attempts.
7. **Load test like the internet.** Many load tools are *closed-loop* (each virtual user waits for
   a response before sending the next), so they slow down when your server does and hide this
   failure entirely. Real users are open-loop: they keep arriving.

## Self-test

- Using Little's law: an API handles 1,000 req/s with average latency 200ms. How many requests
  are in flight? What happens to that number if latency rises to 2s?
- Why is a 100% CPU graph during an incident not evidence that the server is doing useful work?
- Your service calls a dependency that's overloaded. Where in *your* service would you shed load?
