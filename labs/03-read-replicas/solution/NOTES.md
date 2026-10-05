# Lab 03 notes: what was wrong, and what a senior engineer sees

## Root cause

Replication is **asynchronous**: the primary acknowledges a write before replicas have it. Moving
reads to replicas silently changed the app's consistency model from "you always see the latest
data" to "you see *some* past state". Nothing in the code changed; the guarantee did.

## The fix: session consistency via LSN watermarks

The session remembers the highest log position it has **written or observed** (`min_lsn`). A read
goes to any replica with `applied_lsn >= min_lsn`. If none qualifies, wait briefly (≤100ms) for
one to catch up, and only then fall back to the primary.

- Read-your-writes ✔ your write's LSN is in the watermark.
- Monotonic reads ✔ you never read from a node behind something you already saw.
- Primary share ≈ 0% ✔ and p99 ≈ 50ms (the cost of the occasional wait).

This is how real systems do it: MongoDB causally consistent sessions (`afterClusterTime`), MySQL
`WAIT_FOR_EXECUTED_GTID_SET`, Postgres (track `pg_current_wal_lsn()` on write, compare against
`pg_last_wal_replay_lsn()` on replicas), and DynamoDB/Cosmos "session" consistency.

## Why the obvious fixes fail

| Attempt | Result |
|---|---|
| All reads to primary | Correct, 100% primary load: you've undone the scaling |
| Primary for 1s after a write | Lag spikes exceed 1s → stale; frequent writers stay on primary → 95% load |
| Sticky replica per user | Fixes flicker only while that replica is healthy; still stale right after a write |
| Watermark, fall back to primary immediately | Correct, but reading from the primary raises your watermark to the newest LSN, so you get stuck there (~60% load) |

## What a senior engineer also notices

1. **Consistency is a product decision with a price tag.** Show the options as a table: what
   users see, what it costs in latency, load, and complexity. Your manager's 25% rule is a real
   constraint; good designs satisfy correctness *and* cost.
2. **Not every read needs the same guarantee.** Your own profile needs read-your-writes. Someone
   else's profile can be a few seconds stale. A bank balance check *before a withdrawal* must
   never use a replica. Never make a decision that guards a write using replica data.
3. **Lag is unbounded.** Monitor it (`replication lag seconds` is a standard alert), and pull a
   replica out of the read pool when it's too far behind. Replica-2 here should have been.
4. **Failover loses acknowledged writes with async replication.** The drill showed it. The options:
   *synchronous* replication (every write waits for a replica: slower, and a slow replica stalls
   writes), *semi-sync* (wait for at least one of N), or quorum systems (Raft or Paxos: Spanner,
   CockroachDB, etcd). The trade-off is write latency against durability. **RPO** (how much data
   you can lose) and **RTO** (how long you can be down) are the numbers that drive this choice.
5. **Split brain.** If the old primary comes back thinking it's still primary, two nodes accept
   writes. Real failover needs fencing (STONITH, epoch numbers, leases).
6. **Caches have the same problem.** A cache in front of a DB is a replica with its own lag, and
   the same session reasoning applies.

## Self-test

- Explain to a product manager, without jargon, why "saved" data disappeared after the failover.
- Your app moves to 3 regions, each with local replicas. What changes about the watermark approach?
- What happens to your solution if replica-1 dies? (Try it: edit `cluster.py` locally.)
