# Lab 06 notes: what was wrong, and what a senior engineer sees

## Root causes

1. **`hash()` is randomized per process.** Every deploy reshuffled 75% of keys. It never showed up
   locally because one process is always consistent with itself. *Bugs that need two processes
   to reproduce don't show up in single-process tests.*
2. **`% N` couples every key to N.** Change N and ~(1 − 1/N) of keys move, mostly between
   *existing* shards, which is pure waste.

## The fix

Consistent hashing with virtual nodes (256 per shard), using a stable hash (MD5 here, chosen for
distribution, not security). Adding shard 5 moves ~20% of keys, all of them *to* the new shard.
Removing a shard moves only its own keys. Rendezvous hashing passes too. It's simpler, but O(N)
per lookup.

## What a senior engineer also notices

1. **The router is the easy part; the migration is the project.** Moving 20% of keys still means
   copying ~200 GB live. The usual sequence: dual-write to old and new owner → backfill → verify
   (checksums) → flip reads → stop dual-writes → delete. Every step needs a rollback plan, and a
   key mid-migration must be readable from somewhere at all times.
2. **Many real systems avoid hashing directly to nodes.** Instead: hash to a **fixed, large number
   of logical partitions** (e.g. 4096), and keep a **mapping table** partition → node. Rebalancing
   is then "move partition 1234 from db-2 to db-4" and update the table. That's Kafka partitions,
   Cassandra/DynamoDB token ranges, Vitess, CockroachDB ranges. Pick the partition count once, and
   generously; it's hard to change.
3. **Hash vs range partitioning.** Hashing spreads load but destroys locality: "all users created
   this week" or "orders between X and Y" becomes a scatter-gather across every shard. Range
   partitioning keeps scans cheap but creates hot spots (everyone writes to "now"). Choose the
   **shard key** for your access patterns. A wrong shard key is one of the most expensive mistakes
   to undo.
4. **Cross-shard operations get expensive.** Joins, transactions, and unique constraints across
   shards need scatter-gather, two-phase commit, or design changes. A good shard key keeps a
   request's data together (e.g. shard by `tenant_id` so a whole customer lives on one shard).
5. **Hot keys can't be fixed by hashing.** Key balance isn't load balance. The celebrity's one key
   lives on one shard. Options:
   - **cache** the hot key in front of the shard (reads),
   - **replicate** hot keys to several shards and spread reads across them,
   - **split** the key (`celebrity#0..#9`) and fan out or aggregate (counters, followers lists),
   - **detect** hot keys automatically (top-k sampling) because you won't predict them all.
6. **Resharding before you need it.** Shards fill gradually and then all at once. Plan capacity
   from growth curves, and reshard at ~50-60% capacity, not 95%, because migration itself needs headroom.

## Self-test

- Prove (informally) that adding a node on the ring only moves keys to the new node.
- Your shard key is `user_id`. Product asks for "global leaderboard of top 100 users by points".
  How do you serve it without querying every shard on every request?
- A shard dies with no replica. With consistent hashing, its keys "move" to the next node.
  What do users see? (Routing isn't replication.)
