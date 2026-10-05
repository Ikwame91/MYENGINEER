# Drill 4: Wallet and ledger

## The prompt

Design the money-movement core for a mobile wallet (think M-Pesa, Cash App, Venmo).

- Users hold a balance. They can top up from a card, send money to other users, and withdraw to a bank.
- 20M users. Peak 5,000 transfers/second (salary day).
- **Money must never be created or destroyed.** Every balance must be explainable by history.
- Regulators may ask: "what was this user's balance at 14:03 last March 3rd, and why?"

**Deliver:** data model, the transfer flow, how you guarantee correctness under concurrency and
failure, and how you'd detect if something went wrong anyway.

Related labs: 02 (atomicity), 05 (idempotency), 03 (replicas), 06 (sharding).

<!-- REVIEW -->

## Reviewer's questions

1. Do you store a `balance` column, a list of transactions, or both? How do you answer the
   regulator's question?
2. Alice sends Bob 100 while also withdrawing her whole balance. Walk through how you prevent
   her going negative. (Lab 02.)
3. Alice and Bob are on different shards. How is a transfer atomic? (2PC? Saga? Something else?)
   What does Bob see mid-transfer?
4. The mobile app retries a "send 100" request after a timeout. How do you make sure Bob gets
   100, not 200? (Lab 05.)
5. A top-up: the card network says "approved", then your service crashes before recording it.
   What happens? How is it fixed, and by whom?
6. What's **double-entry bookkeeping**, and why do financial systems insist on it?
7. How do you detect a bug that creates money? Which invariant do you check, how often, and what
   happens when it fails?
8. Can balance reads use replicas? Which ones can and which can't? (Lab 03.)
9. Salary day: 5k transfers/s, many *into* one employer's payout account. Hot row? (Labs 02, 06.)
10. Which numbers are your RPO and RTO, and what does your replication setup need to be to meet them?

## Common mistakes

- `UPDATE balance = balance - x` on one account and `+ x` on the other in separate transactions.
- Floats for money.
- No idempotency on the API: retries create duplicate transfers.
- No reconciliation: trusting that the code is right.

## Sketch of a strong answer

An append-only **double-entry ledger** (every transfer is ≥ 2 entries that sum to zero, written in
one transaction) is the source of truth. Balances are a derived, cached projection updated in the
same transaction, guarded by `balance >= amount` conditional updates. Amounts are integers in
minor units, with currency. Every API mutation needs a client idempotency key, stored with a unique
constraint. Cross-shard transfers use a saga with a pending/hold state on the source account
(funds reserved, then credited, then settled), with compensations. External money (cards, banks) is
reconciled against provider reports daily, and anything unknown is `pending` until reconciled.
Continuous invariant checks (sum of all entries = 0 per currency; balances = sum of entries) alert
immediately. Synchronous replication or a quorum store for the ledger: RPO = 0.
