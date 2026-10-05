# Lab 02: The Flash Sale

**Concepts:** race conditions, lost updates, read-modify-write, atomic conditional updates,
transactions and locks, why in-process locks fail across servers, compensating actions,
never holding a lock across a network call.

## The page

> **#incident-sneakers** · 12:00:04
> **Support:** We sold 900 pairs of the limited sneakers. We had 100.
> **Finance:** All 900 customers were charged.
> **DBA:** The `items` table says we still have **99** left???

The sale runs on 4 app servers × 16 request-handler threads. 1000 people click **Buy** at the
same moment. ~10% of cards get declined. You own `app.py`.

## Run it

```bash
python3 lab.py run 02 --runs 5     # several sales: races are nondeterministic
python3 lab.py check 02
```

## Investigate before you touch code

In `journal/02.md`:

1. Write out, step by step, an interleaving of **two** buyers that produces 2 orders but only
   reduces stock by 1. Use a table: time | buyer A | buyer B | stock in DB.
2. Why does stock end at **99** and not at some random number? (Hint: what value did almost
   everyone read?)
3. This bug can't happen with one buyer at a time. List the ways you could make "check stock"
   and "decrement stock" impossible to interleave. For each one, predict whether it works across
   **4 separate server processes**.
4. If a card is declined *after* you've taken a unit, what must happen to that unit?

## Rules

- Change only `app.py`.
- Try at least one fix you *suspect* is wrong, to see how it fails. (Suggestion: a
  `threading.Lock`. Then an explicit `BEGIN`.) Reading about a deadlock teaches you less than
  causing one.

## Done when

`python3 lab.py check 02` passes all invariants on 3 consecutive sales: never oversold, books
balance, every unit sells, every charge matches exactly one order, no errors.

## After you pass

Compare your duration with `BEGIN IMMEDIATE` around everything, versus an atomic conditional
`UPDATE`. Then read `solution/NOTES.md`.
