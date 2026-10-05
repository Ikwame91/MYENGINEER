# Lab 02 notes: what was wrong, and what a senior engineer sees

## Root cause

A **lost update** from read-modify-write. Every handler read `stock = 100` at 12:00:00, charged
the card, and wrote `stock = 99`. Each write silently overwrote the others. The `if stock <= 0`
check was correct for a world where nobody else exists.

## The fix

```sql
UPDATE items SET stock = stock - 1 WHERE id = ? AND stock > 0   -- check + change, atomically
```
`rowcount == 1` means you got a unit. Then charge **outside** any transaction. If the charge is
declined, compensate with `stock = stock + 1`. Then insert the order.

## Wrong fixes, and why they fail

| Attempt | What happens |
|---|---|
| `threading.Lock()` | Protects one process. 4 servers → still oversold. Same with any in-memory cache or "singleton". |
| `BEGIN` then `SELECT` then `UPDATE` | Two transactions hold shared locks and both want to write → deadlock → "database is locked". |
| `BEGIN IMMEDIATE` around everything, including the charge | **Correct**, but every buyer waits while one buyer talks to the payment provider: ~2× slower here, and unbounded when the provider gets slow. |
| Check `stock` again just before the `UPDATE` | Makes the window smaller, not zero. Races that are "rare" happen daily at scale. |

## What a senior engineer also notices

1. **Postgres's default isolation (READ COMMITTED) has the exact same bug.** `REPEATABLE READ` or
   `SERIALIZABLE` turn it into errors you must **retry**: the transaction aborts instead of
   silently corrupting data. Know your database's default isolation level and what it does and
   doesn't prevent (dirty reads, non-repeatable reads, phantoms, write skew).
2. **Never hold a lock or transaction across a network call.** The payment provider's p99 becomes
   your lock hold time. When the provider has a bad day, your whole database queues behind it.
3. **What if the process crashes between "reserve" and "insert order"?** The unit is gone forever.
   Real systems use **reservations with an expiry** (`reserved_until`), or record the order as
   `pending` in the same transaction as the reservation and reconcile later. "What if it dies
   *here*?" is the question to ask about every line.
4. **What if the charge times out?** You don't know if it succeeded. Retrying might charge twice.
   That's Lab 05 (idempotency).
5. **Hot rows.** Every buyer updates the *same row*, so throughput is capped by how fast one row
   can be locked and updated. At very large scale: pre-split stock into N buckets (rows), pick
   one at random, or put the counter in Redis with `DECR` and reconcile.
6. **Constraints as a safety net.** `CHECK (stock >= 0)` on the column makes the database reject
   the impossible state, even if a future developer reintroduces the bug.
7. **Testing concurrency.** One run passing proves little. The checker runs 3 sales with 64
   concurrent handlers and a start barrier, to *maximize* contention. Your unit tests should
   do the same.

## Self-test

- Draw the interleaving that oversells. Draw why the conditional `UPDATE` can't.
- Your company moves the counter to Redis. What's the equivalent atomic operation, and what
  new failure modes come with it?
- How would you know in production that this was happening, *before* support tickets?
  (What metric or invariant would you alert on?)
