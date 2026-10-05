## Hint 1
Start with `--explain`. Every `SCAN orders` reads all 300k rows. Your goal is to turn each one
into a `SEARCH ... USING INDEX`. Which columns appear in each `WHERE` and `ORDER BY`?

## Hint 2
In a composite index, column order matters. An index on `(a, b)` is a phone book sorted by
last name, then first name. It can find `a = ?` and then return rows already sorted by `b`.
It cannot efficiently find `b = ?` on its own.

## Hint 3
`date(created_at) = ?` wraps the column in a function. The index stores `created_at`, not
`date(created_at)`, so the planner can't use it. Rewrite the condition as a range on the bare
column: `created_at >= 'day' AND created_at < 'next day'`.

## Hint 4
`top_customers` does one query to list users, then one more *per user*: that's N+1.
Let the database do the join and aggregation in a single statement (`JOIN` + `GROUP BY`).

## Hint 5
Did adding an index make `top_customers` worse? Look at its plan: which table does the planner
drive the join from? The planner guesses selectivity. Without statistics it doesn't know that
85% of orders are `paid`. Look up SQLite's `ANALYZE`.

## Hint 6
To go faster still: if an index contains *every* column a query needs, the table itself is never
read (a *covering* index). Which three columns of `orders` does the `top_customers` aggregation need?
