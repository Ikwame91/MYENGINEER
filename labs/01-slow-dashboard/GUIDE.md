# Lab 01 guided walkthrough

Read this one step at a time with `python3 lab.py guide 01`. Each step ends with something to
**do**. Don't skip ahead: every step builds the idea the next one needs.

## Step 1: Only three things matter

The folder looks like a lot of files. You only need three of them:

| File | What it is | You... |
|---|---|---|
| `README.md` | The incident: what users are complaining about | read it once |
| `app.py` | The code behind the 3 slow pages (about 50 lines) | **edit this** |
| the output of `run` | What "production" looks like right now | read it after every change |

Everything else (`harness.py`, `data.py`, `check.py`, `run.py`) is the simulated world around your
code. Ignore those files for now.

The whole lab is this loop, repeated:

```
change app.py  ->  python3 lab.py run 01  ->  did the numbers change the way I expected?
```

**Do:** open `labs/01-slow-dashboard/app.py` and read it top to bottom. There are 4 functions:
`migrate` (empty), `recent_orders`, `daily_revenue`, `top_customers`. For each of the last three,
write one sentence in plain English saying what it fetches. Don't worry about *how* yet.

## Step 2: Reading the run output

Run `python3 lab.py run 01`. You'll see something like:

```
endpoint       requests  p50       p99       statements/req (max)  work/req (p50)  timeouts
recent_orders  40        14.2ms    17.9ms    1                     900k            0
daily_revenue  15        49.2ms    94.8ms    1                     1,665k          0
top_customers  1         2000.2ms  2000.2ms  138                   122,994k        1 TIMEOUT
```

Each row is one page of the website. The columns:

- **requests**: how many times that page was loaded in the test.
- **p50**: the *typical* load time. Half of the requests were faster than this.
- **p99**: the *bad-day* load time. 99% were faster; 1 in 100 users waited this long or longer.
  Engineers care about p99 because at a million users, "1 in 100" is 10,000 unhappy people.
- **statements/req**: how many SQL queries one page load sent to the database.
- **work/req**: how much effort the database spent, roughly how many rows it had to look at
  (in thousands). **This is the most honest column.** Your laptop is fast, so the times look
  OK-ish, but 900k means the database looked at ~900,000 things to show one user 20 orders.
- **timeouts**: requests killed for taking over 2 seconds. A user saw an error page.

**Do:** answer in your journal (`python3 lab.py journal 01`):
1. Which page is broken outright?
2. `recent_orders` shows 20 orders. Its work is ~900k. What does that ratio tell you?

## Step 3: How a database finds rows (the phone book)

The `orders` table has 300,000 rows. To answer `WHERE user_id = 5306`, the database has two options:

- **Scan:** read all 300,000 rows and keep the ones that match. Like finding a phone number
  by reading the phone book from page 1. Always works, and gets slower as the table grows.
- **Index:** an index is a separate, *sorted* copy of one or more columns, pointing back to
  the rows. Like a phone book sorted by name: you jump straight to the right page. Finding 1 row
  among 300,000 takes about 18 steps instead of 300,000.

A table has **no indexes** (except its primary key `id`) until someone creates one. Nobody has here.

The database decides which option to use for each query. That decision is the **query plan**,
and you can ask to see it.

**Do:** run `python3 lab.py run 01 --explain`. Under each query you'll see either
`SCAN orders` (read everything) or `SEARCH ... USING INDEX` (jump straight there).
How many SCANs are there?

## Step 4: Practise in the playground first

Before changing `app.py`, practise the technique on a query that is *not* part of the lab.

**Do:** run `python3 lab.py play 01` and type these one at a time (each ends with `;`):

```sql
SELECT * FROM users WHERE name = 'user_04242';
```
Look at three things: **took** (time), and **plan**, which says `SCAN users` in red. It read all
10,000 users to find one. Now create an index on the column you're searching:

```sql
CREATE INDEX users_name ON users (name);
SELECT * FROM users WHERE name = 'user_04242';
```

The plan should now say `SEARCH users USING INDEX users_name (name=?)` in green, and the time
should drop. **That's the core skill of this lab: read the plan, make an index match the WHERE,
and confirm the plan changed.**

Try one more experiment and predict the answer *before* you press Enter:

```sql
SELECT * FROM users WHERE country = 'GH';
```

Does it use `users_name`? Why not? (The index is sorted by name. Is that useful for finding a country?)

Type `.quit` to leave. Indexes you made in the playground are wiped next time; they never affect `app.py`.

## Step 5: Your first real fix (recent_orders)

Now apply it for real. Look at the query in `recent_orders`:

```sql
SELECT ... FROM orders WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?
```

It searches by `user_id`. Indexes for the lab go in `migrate()` in `app.py`. It runs once at
startup, like a database migration in a real project. The pattern is:

```python
def migrate(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS some_name ON some_table (some_column)")
```

**Do:**
1. Add an index on `orders` for the column `recent_orders` searches by.
2. `python3 lab.py run 01 --explain`. Did `recent_orders` change from `SCAN` to `SEARCH`? Did
   its **work** column drop? Write the before and after numbers in your journal.
3. `python3 lab.py check 01`. One or two lines should flip from FAIL to PASS.

You'll probably still see `USE TEMP B-TREE FOR ORDER BY` for that query. That's the next step.

## Step 6: Sorting for free (composite indexes)

`USE TEMP B-TREE FOR ORDER BY` means: "I found this user's rows, but now I have to sort them
myself before I can return the newest 20." For a user with many orders, that's wasted work.

An index can have **several columns**. Think of a phone book sorted by *last name, then first name*:

- It finds everyone named "Mensah" instantly (first column), and they're **already in
  first-name order** (second column), with no sorting needed.
- But it can't help you find everyone whose first name is "Kwame": they're scattered across
  every last name. **Column order matters.**

**Do:** in the playground, practise on users (not orders):

```sql
SELECT * FROM users WHERE country = 'GH' ORDER BY name LIMIT 5;
CREATE INDEX users_country_name ON users (country, name);
SELECT * FROM users WHERE country = 'GH' ORDER BY name LIMIT 5;
```

Compare the two plans. Then go back to `app.py` and change your `recent_orders` index so the
database finds a user's orders *and* gets them already in `created_at, id` order. Run with
`--explain` until the TEMP B-TREE line disappears for that query.

## Step 7: Why an index can be ignored (daily_revenue)

`daily_revenue` filters on `date(created_at) = ?`. Try adding an index on `created_at` and look at
the plan. It still SCANs. Why?

The index stores values like `2025-10-10 14:03:22`, sorted. The query asks about
`date(created_at)`, a *computed* value, `2025-10-10`. The database would have to compute
`date()` for every row to compare, which means reading every row. **Wrapping a column in a
function hides it from its index.**

**Do:** see it in the playground first:

```sql
CREATE INDEX IF NOT EXISTS users_name ON users (name);
SELECT * FROM users WHERE upper(name) = 'USER_04242';
SELECT * FROM users WHERE name = 'user_04242';
```

Same rows, but the first one SCANs. Now fix `daily_revenue`: rewrite the `WHERE` so `created_at`
is compared *directly*, with no function around it. Hint: "all timestamps on 2025-10-10" means
"greater than or equal to the start of that day, and less than the start of the next day."
You'll need Python to compute the next day (`datetime.date.fromisoformat(day) + datetime.timedelta(days=1)`).

Then check: correct results, and no SCAN. `python3 lab.py check 01` tells you if you broke the totals.

## Step 8: The N+1 problem (top_customers)

Read `top_customers` again. It runs **1** query to get all users in a country, then **1 more
query per user** inside the `for` loop. Ghana has ~1,500 users, so that's ~1,500 queries for
one page load. This pattern is called **N+1**.

Why it's slow even with good indexes: each query is a network round trip to the database
(the harness charges 0.5ms each, which is realistic). 1,500 × 0.5ms = 750ms of pure waiting,
before any real work. Look at **statements/req** in the run output to see it.

The fix is to let the database do the loop for you, in **one** query, using `JOIN` (combine two
tables) and `GROUP BY` (one result row per group, with `SUM()` adding up the group).

**Do:** practise `GROUP BY` and `JOIN` in the playground:

```sql
SELECT country, COUNT(*) FROM users GROUP BY country;
SELECT u.name, COUNT(*) AS n FROM users u JOIN orders o ON o.user_id = u.id
  WHERE u.country = 'JP' GROUP BY u.id ORDER BY n DESC LIMIT 5;
```

The second one is slow and its plan says `SCAN o`: the playground has no index on
`orders.user_id`. That's expected. Your `migrate()` indexes are what make this fast in the lab.
Read it slowly: for every order, take its user; keep only Japanese users; make one
group per user; count each group; show the top 5. Now write `top_customers` as one query in that
shape. It needs **paid** orders only, **SUM of amount_cents** instead of COUNT, ties broken by name.
Return the rows directly (`conn.execute(...).fetchall()`).

Check it: `statements/req` for `top_customers` should be 1, and `check 01` should say results are correct.

## Step 9: When adding an index makes things worse

If you indexed `orders (status, created_at)` for `daily_revenue`, `top_customers` may now fail its
**work budget**, even though it was fine before. Look at its plan with `--explain`: which table
does it start from, and which index does it use?

The planner *guesses* how many rows `status = 'paid'` matches. It doesn't know that 85% of
orders are paid, so it thinks that index is a great shortcut, when really it touches most of
the table. Databases keep **statistics** about the data to make better guesses, but someone has
to collect them. In SQLite that's a one-word statement. Look up what `ANALYZE` does, and try it
at the end of `migrate()`.

This is the sort of thing a senior engineer catches: **every index you add can change the plan
of every other query on that table.** Always re-check *all* the plans, not just the one you fixed.

## Step 10: Finish like an engineer

1. `python3 lab.py check 01` until everything passes.
2. Fill in the rest of your journal: root cause per page, and what each fix costs. (Hint: every
   index makes every `INSERT` slower and uses disk.)
3. `python3 lab.py notes 01`: read what a senior would *also* notice. Compare it with your journal.
4. The self-test: without looking, explain to an imaginary teammate **why** each fix works,
   **how** it could fail, and **what** you'd change if the requirements shifted.
5. In a week: `python3 lab.py reset 01` and do it again without this guide.

Then move on to Lab 02. It has no guide on purpose. Use the same loop:
**read the output, form a guess, test it small, then change the code.**
