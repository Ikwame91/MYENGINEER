# Lab 01 notes: what was wrong, and what a senior engineer sees

## Root causes

| Endpoint | Problem | Fix |
|---|---|---|
| `recent_orders` | Full scan, then sorting all of the user's rows in a temp B-tree | `INDEX (user_id, created_at, id)`: equality column first, then the sort columns |
| `daily_revenue` | `date(created_at) = ?` is **not sargable**: a function on the column hides it from the index | Half-open range `created_at >= d AND created_at < d+1` + `INDEX (status, created_at)` |
| `top_customers` | **N+1**: 1 query for users + 1 per user, each a full scan | One `JOIN ... GROUP BY`; `INDEX users(country)`; covering `INDEX orders(user_id, status, amount_cents)` |
| (the trap) | Adding `(status, created_at)` made the planner drive `top_customers` from `status = 'paid'` (85% of rows) | `ANALYZE`, so the planner knows the real selectivity |

## What a senior engineer also notices

1. **"Nothing was deployed" is a clue, not an alibi.** Data growth is a deploy. A query plan
   that was fine at 10k rows is a different system at 10M. Ask "what's O(n) in a request path?"
2. **Measure work, not just latency.** Your laptop's cache hides full scans. In production, use
   rows examined vs rows returned: Postgres `EXPLAIN (ANALYZE, BUFFERS)` and `pg_stat_statements`;
   MySQL's slow log `Rows_examined`. A ratio of 100,000:20 is the bug report.
3. **Indexes aren't free.** This solution adds 4 indexes. Every `INSERT` into `orders` now updates
   5 B-trees, so writes get slower and storage grows. On a write-heavy table, ask whether each one
   pays for itself. Remove `orders_user_created` and check whether `orders_user_status_amount` could
   serve `recent_orders` too. (It can't avoid the sort. Do you see why?)
4. **Adding an index changes other queries' plans.** That's what happened in the trap. In
   production, stale statistics after a bulk load or a big delete cause sudden plan flips at 3am.
   Postgres autovacuum runs `ANALYZE`, but not instantly.
5. **Creating an index on a big live table can lock it.** Postgres `CREATE INDEX` blocks writes;
   use `CREATE INDEX CONCURRENTLY`. MySQL has online DDL, with caveats. Indexes ship as
   migrations, and you need to know how long they lock.
6. **N+1 hides inside ORMs.** `for user in users: user.orders.sum()` looks innocent. Count
   statements per request in tests: a test that asserts "this endpoint makes ≤ 3 queries" stops
   the regression from coming back.
7. **Timestamps and time zones.** `daily_revenue` assumes UTC days. Finance in Lagos and finance
   in San Francisco mean different "days". Ask whose day it is before you build the report.
8. **Should this query even run on the primary?** A dashboard aggregating across many users is
   analytics, not OLTP. At scale it belongs on a read replica (Lab 03) or in a warehouse, or it's
   precomputed (a rollup table updated as orders arrive).

## Self-test

- Why does `(user_id, created_at)` serve `ORDER BY created_at` but `(created_at, user_id)` doesn't
  serve `WHERE user_id = ?` well?
- Name one change to the requirements that would make your index useless.
- How would you roll back each part of your fix? (Dropping an index is fast. Is it safe?)
