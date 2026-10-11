# Lab 01: The Slow Dashboard

**Concepts:** indexes (B-trees), composite index column order, query plans, N+1 queries,
sargable predicates, planner statistics, covering indexes.

## The page

> **#incident-shop** · 09:12
> **Ops lead:** The Top Customers dashboard has been timing out all morning. Finance says the
> daily revenue report is "sluggish". And the mobile team says the *My Orders* screen got slower
> since we passed 300k orders. Nothing was deployed. Can someone look?

You own `app.py`, the queries behind those three pages. The database is SQLite with 300k orders
and 10k users. The harness acts like production: every statement pays a 0.5ms network round
trip, and requests are killed after 2 seconds.

> **First time doing this kind of thing?** Run `python3 lab.py guide 01`. It walks you through
> the lab one step at a time, with practice in a SQL playground (`python3 lab.py play 01`)
> before you touch the real code.

## Run it

```bash
python3 lab.py run 01               # replay traffic: latency, statements per request, work per request
python3 lab.py run 01 --explain     # ...plus the query plan for each statement
python3 lab.py check 01             # the acceptance test
```

`work` is thousands of database VM steps per request. It roughly counts rows touched, and it
doesn't depend on how fast your laptop is. **Latency lies on small data; work does not.**

## Investigate before you touch code

Open `journal/01.md` (copy `journal/TEMPLATE.md`) and answer these from evidence, not guesses:

1. Which endpoint is *actually* worst? Rank them by work, not by latency. Why do the two rankings differ?
2. In the plan, what does `SCAN orders` mean, compared with `SEARCH orders USING INDEX`?
   What does `USE TEMP B-TREE FOR ORDER BY` cost you?
3. `top_customers` makes ~137 statements before it dies. Where does that number come from,
   and how would it grow with the number of users in a country?
4. `daily_revenue` has a `WHERE` on `created_at`. If you add an index on `created_at`,
   will it be used? Predict first, then try it.

## Rules

- Change only `app.py`. Keep the function signatures and return values.
- Indexes go in `migrate()`.
- After every change, rerun `--explain` and check that the plan changed the way you predicted.
  If you can't predict the plan, you don't understand the index yet.

## Done when

`python3 lab.py check 01` passes: correct results, no full scans of `orders`, no sort for
*My Orders*, no N+1, and each endpoint within its work budget.

Stuck for more than 20 minutes? `python3 lab.py hint 01` reveals one hint at a time.

## After you pass

Read `solution/NOTES.md`. It covers what a senior engineer would *also* catch here, and how
this looks on Postgres or MySQL in production.
