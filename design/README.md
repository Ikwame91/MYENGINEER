# System design practice

The labs teach *mechanisms* (indexes, replication, caching, idempotency, partitioning, queueing)
by letting you break and fix them. Design drills teach you to **combine** mechanisms under
constraints, and to defend the trade-offs.

## How to do a drill

1. `python3 lab.py drill N` shows only the prompt. Set a 45-minute timer. Paper or whiteboard.
   **No AI, no searching.**
2. Work through these steps, in order, out loud or in writing:

   | Step | Output | Time |
   |---|---|---|
   | 1. Requirements | Functional (what it does) and non-functional (scale, latency, consistency, availability, durability). Ask: what's explicitly *out* of scope? | 5 min |
   | 2. Estimates | QPS (avg and peak), storage per year, bandwidth, read:write ratio. `python3 lab.py estimate` for practice. | 5 min |
   | 3. API | The 3–5 most important endpoints, with request/response. Which are idempotent? | 5 min |
   | 4. Data model | Tables or collections, keys, indexes. What's the **shard key**, and why? | 5 min |
   | 5. High-level design | Boxes and arrows for the main read path and write path. | 10 min |
   | 6. Deep dives | The 2 hardest parts. This is where seniors earn their title. | 10 min |
   | 7. Failure modes | For each box: what if it's slow? down? returns garbage? What's the blast radius? | 5 min |

3. `python3 lab.py review N` shows the questions a staff engineer would ask. Answer each one
   **in writing**. A question you can't answer is a gap. Find which lab or reading covers it.
4. Redo the same drill 2 weeks later, from scratch. You should be faster and go deeper.

## What reviewers actually look for

- **Numbers drive decisions.** "We need a cache" is a guess. "Reads are 50k QPS at peak and one
  Postgres primary handles ~5k with this query, so we need replicas or a cache" is engineering.
- **Trade-offs are stated, not hidden.** Every choice costs something. Name the cost and why it's
  acceptable *here*.
- **Simplicity first.** Start with the simplest design that meets the numbers. Add complexity
  only when a requirement forces it, and say which requirement.
- **The hard part is identified.** Every system has one or two genuinely difficult problems.
  Finding them matters more than drawing many boxes.
- **Failure is designed for.** Timeouts, retries, idempotency, overload, data loss, and how you'd
  know (monitoring) and recover (rollback, backfill).

## The mechanism map (which lab teaches what you'll need)

| You're designing... | You'll need | Lab |
|---|---|---|
| Any read-heavy API | Indexes, query plans, avoiding N+1 | 01 |
| Inventory, bookings, counters | Atomic updates, isolation, locks | 02 |
| Anything that scales reads | Replicas, lag, session consistency | 03 |
| Anything with hot data | Caching, stampedes, invalidation | 04 |
| Payments, orders, anything over a network | Idempotency, retries, timeouts | 05 |
| Anything bigger than one machine | Partitioning, shard keys, hot keys | 06 |
| Anything with traffic spikes | Queues, backpressure, load shedding | 07 |

See `numbers.md` for the latency and throughput numbers to know by heart.
