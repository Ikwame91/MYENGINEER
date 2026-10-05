# Lab 03: Read Replicas

**Concepts:** primary/replica replication, asynchronous replication lag, read-your-writes,
monotonic reads, log sequence numbers (LSNs), session consistency, the cost of consistency,
failover and lost acknowledged writes.

## The page

> **#incident-profiles** · 14:30
> **Support:** Users say "I changed my name, hit Save, and it changed back!" Some say the name
> *flickers* between old and new when they refresh. Started right after we moved reads to replicas.
> **Infra:** Replicas are healthy. Replica-2 falls behind for about a second every 3 seconds,
> while the analytics job runs. That's normal.
> **Your manager:** We can't just send reads back to the primary. That's why we added replicas.
> The primary can take at most 25% of reads.

You own `app.py` (`ProfileService`). The cluster is in `cluster.py`: one primary, two replicas,
asynchronous replication. Read `cluster.py`. It's short, and it's the "documentation" of your
database.

## Run it

```bash
python3 lab.py run 03              # 40 users for 6s, with a timeline of replica lag vs anomalies
python3 lab.py run 03 --failover   # separate drill: what async replication costs when the primary dies
python3 lab.py check 03
```

## Investigate before you touch code

In `journal/03.md`:

1. Look at the timeline. Which anomaly tracks replica-2's lag spikes, and which happens *all the
   time*, even when lag is ~15 writes? Why?
2. Define **read-your-writes** and **monotonic reads** in your own words, with a user story for each.
3. "Send the user to the primary for 1 second after they write." Predict exactly how this fails.
   Then try it.
4. Every node exposes `applied_lsn`, and every write returns an LSN. What could a *session*
   remember so that any node could decide whether it's fresh enough for that session?
5. Run `--failover`. Explain why 500 users lost data that they were told was saved.

## Rules

- Change only `app.py`.
- `session.state` is yours. In a real app it would be a cookie or a field in the auth token.
- Don't read the private attributes (`_data`, `_history`) of cluster nodes. A real database
  doesn't give you those.

## Done when

`python3 lab.py check 03` passes: zero stale own reads, zero time-travel reads, primary serves
≤ 25% of reads, get_name p99 ≤ 150ms.

## After you pass

Read `solution/NOTES.md`, then answer the question the failover drill asks.
