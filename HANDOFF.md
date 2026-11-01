# Handoff: Lab 01 learning sessions (October 2026)

This hands over the work done in a series of tutoring sessions on this repository (Oct 11 to Nov 1, 2026).
It is for whoever picks this up next: the repo owner, or a new AI session helping them.

> **Spoiler warning.** Section 9 contains the Lab 01 solution, and section 4 describes the
> fixes. If you are about to redo Lab 01 from scratch, read only sections 1, 5, 7 and 8.

---

## 1. TL;DR

- **MYENGINEER** is a set of hands-on systems engineering labs: run a broken system, measure it,
  fix it, then pass an automated check. It was built with Claude before these sessions.
- These sessions focused **only on Lab 01 (The Slow Dashboard)**. The owner is a software developer,
  but database internals were new to them. We went step by step from "what is SCAN vs SEARCH" to a
  full solution.
- **Lab 01 passes all 10 checks** with the owner's own code, committed on `claude/festive-noether-kxzazk`
  (commit `c07c2a1`, "lab 1 walkthrough").
- **Two things need attention** (section 8): committing the solved `app.py` broke `python3 lab.py reset 01`
  (it now "restores" the solved version), and `python3 lab.py selftest` now reports `PROBLEM` for lab 01.
  The journal `journal/01.md` was committed but is still the empty template.

---

## 2. What the project is (built before these sessions)

| Path | What it is |
|---|---|
| `lab.py` | The CLI. Every command is `python3 lab.py <command> <lab number>` |
| `labkit.py` | Shared helpers (colours, tables, `Checker`, `load_impl`). Never needs editing |
| `labs/01-slow-dashboard/` … `labs/07-overload/` | Seven labs. Each has `README.md` (the incident), `app.py` (the only file the learner edits), `run.py` (shows symptoms), `check.py` (pass/fail), `hints.md`, `solution/app.py` + `solution/NOTES.md` |
| `labs/01-slow-dashboard/GUIDE.md` | Ten-step walkthrough, shown one step at a time by `lab.py guide 01`. Only Lab 01 has one |
| `labs/01-slow-dashboard/playground.py` | Interactive SQL prompt on the lab database (`lab.py play 01`) that prints rows, timing and query plan |
| `design/` | Paper-first system design drills (`lab.py drill`, `lab.py review N`) and an estimation quiz (`lab.py estimate`) |
| `journal/TEMPLATE.md` | Template for investigation notes. `lab.py journal NN` copies it to `journal/NN.md` |
| `PRINCIPLES.md` | The philosophy: do the first attempt of each lab without AI, and use AI as a sparring partner afterwards |
| `.progress.json` | Local, git-ignored. Records passed labs, hints revealed and guide position |

**Command map** (what `lab.py` actually runs):

| Command | Runs | Purpose |
|---|---|---|
| `python3 lab.py` | list in `lab.py` | Labs and progress |
| `run 01 [--explain]` | `labs/01-slow-dashboard/run.py` | Replay traffic; show latency, statements/request, work/request, and (with `--explain`) query plans |
| `check 01` | `labs/01-slow-dashboard/check.py` | Acceptance test; marks the lab passed in `.progress.json` |
| `guide 01 [next/back/N]` | prints `GUIDE.md` steps | Walkthrough |
| `play 01` | `playground.py` | SQL playground (indexes created there are wiped next run) |
| `hint 01` | `hints.md`, one at a time | Progressive hints |
| `journal 01` | copies template | Creates `journal/01.md` |
| `notes 01` | `solution/NOTES.md` | Senior-engineer debrief (prompts if the lab isn't passed) |
| `reset 01` | `git checkout HEAD -- labs/01-slow-dashboard/app.py` | Restore the broken version (**currently broken, see section 8**) |
| `selftest` | every `check.py` against git `HEAD`'s `app.py` and the reference solution | Maintainer check |

### How Lab 01 works inside

```
data.py     builds labs/01-slow-dashboard/data.db (SQLite, ~12 MB, git-ignored):
            users (10,000 rows): id, name, country, created_at
            orders (300,000 rows): id, user_id, amount_cents, status, created_at ('YYYY-MM-DD HH:MM:SS')
            It drops every index each time it opens the DB, so each run starts index-free.
harness.py  "production": 0.5 ms network cost per SQL statement, 2 s request timeout,
            counts "work" (thousands of SQLite VM steps, a proxy for rows touched)
app.py      migrate(conn) + three page functions: recent_orders, daily_revenue, top_customers
run.py      replays a fixed workload (seed 7) and prints the table
check.py    computes correct answers in plain Python, then checks correctness, no SCAN of orders,
            no TEMP B-TREE sort in recent_orders, ≤2 statements for top_customers, work budgets
            (50k / 50k / 1,000k)
```

Useful facts about the data (measured): 85% of orders are `paid` (254,936), 10% `pending`,
5% `refunded`. Users per country: NG 1,977, GH 1,491, US 1,188 … JP 304, CA 222.
A typical user has ~23–30 orders. Users 1–100 are "heavy buyers" (e.g. user 5 has 324).

---

## 3. Timeline of the sessions

1. **Orientation.** The owner felt lost in the repo. We explained what was built, why everything
   runs through `python3 lab.py …`, which files matter (`README.md`, `app.py`, the `run` output),
   and how to read the run table (p50/p99, statements/req, work/req, timeouts).
2. **SCAN vs SEARCH.** We used the phone-book analogy and a measured demo on `users.name`
   (SCAN ~30,000 steps, 13 ms → SEARCH ~0 steps, 0.06 ms).
3. **Playground practice.** The owner indexed `users(name)` and saw SCAN become SEARCH, then saw
   `WHERE country = 'GH'` still SCAN ("the index is sorted by name, not country").
4. **Back to basics.** On the owner's request we covered where the DB lives, both tables and their
   columns, what `CREATE INDEX x ON t (col)` builds, and why indexes are separate from the schema.
   We also explained why the `country` index only sped up the GH query a little: the index makes
   *finding* rows fast, but 1,491 full rows (15% of users) still have to be *fetched*. Measured:
   `COUNT(*)` was 14× faster, `SELECT *` under 2× faster.
5. **What `conn` is.** It's the sqlite3 connection the harness creates and passes in, so it can
   count statements and enforce timeouts. We also covered `?` placeholders, `fetchall`/`fetchone`
   and SQL injection.
6. **First fix: `recent_orders`.** `orders(user_id)` took work from 900k to 0k. A side effect:
   `top_customers` stopped timing out and showed its real N+1 (1,978 statements, ~1 s).
7. **Composite index.** `orders(user_id, created_at[, id])` removed `USE TEMP B-TREE FOR ORDER BY`.
   Measured on a heavy user (324 orders): ~3,400 → ~200 steps, so the cost stays flat as history grows.
8. **COALESCE** (`SUM` of zero rows is NULL, so COALESCE turns it into 0).
9. **`daily_revenue` bugs.** First a `TypeError: execute expected at most 2 arguments, got 3`
   (a leftover `(day,)` tuple). Then a silent correctness bug: `datetime.isoformat()` produces
   `'2025-10-10T00:00:00'`, the stored data uses a space, and text comparison sorts `' '` before
   `'T'`, so the query returned **0 instead of 8,249,922**.
10. **Why `date(created_at) = ?` can't use an index (sargability).** Measured with an index on
    `created_at`: function form ~1,200,000 steps (SCAN), range form ~1,200 steps (SEARCH), same
    404 rows. We used a dictionary analogy ("starts with pre" vs "ends with e").
11. **The fixed `daily_revenue`** (given at the owner's request): a `[day, next_day)` range using
    `datetime.date` arithmetic. Work went from 1,665k to 2k.
12. **N+1 and `top_customers`.** A step-by-step playground ladder: JOIN → filter → GROUP BY →
    SUM → ORDER BY/LIMIT. The owner wrote the single query themselves (correct, including the
    tie-break).
13. **Planner statistics.** With the `status` index present, the planner drove `top_customers`
    from `orders` via `status='paid'` (2,516k, failing its 1,000k budget). The owner added `ANALYZE`
    and the plan flipped to `SCAN u` + `SEARCH o USING INDEX orders_user_id`, at 369k p50 / 710k max.
    **All 10 checks passed.**
14. **Playground arrow keys.** They don't work (plain `input()` with no `readline`). We suggested
    adding `import readline` to `playground.py`, or using `sqlite3 labs/01-slow-dashboard/data.db`
    with `.eqp on`. Neither has been done.
15. **Engineering summary**: what this means for system design and decision making
    (the full text is in the chat; the gist is in section 6 below).
16. **This handoff.**

---

## 4. Decisions made, and why

### Teaching decisions

| Decision | Why |
|---|---|
| Focus only on Lab 01 | The owner asked to master one lab until they "can spot the changes myself" |
| Don't hand out fixes; explain concepts, give playground experiments, ask for predictions | `PRINCIPLES.md` and the README's AI rule: the learning comes from catching mistakes yourself. Exceptions were made only when the owner explicitly asked (`daily_revenue` final code) |
| Use real measurements from this database instead of generic claims | Builds trust in "work beats latency" and makes each concept concrete |
| Practise on `users` in the playground before touching `orders` in `app.py` | It mirrors the guide and avoids handing over the lab answer |
| Explain the unexpected (like the GH index only speeding up a little) instead of skipping it | Surprises are the lesson. That one taught "finding vs fetching" and selectivity |
| Warn about Step 9 before it happened | So the later FAIL would read as an expected lesson, not a regression the owner caused by mistake |

### Technical decisions in the owner's `app.py`

| Choice | Why | Trade-off |
|---|---|---|
| `orders(user_id, created_at)` | Equality column first, sort column second, so My Orders reads ≤20 rows already in order and `LIMIT` stops early. Also serves `top_customers`' per-user lookups (leading column) | Slows every `INSERT` into orders a little; disk space |
| `id` dropped from that index | SQLite stores rowid at the end of every index, so it's implicit | On Postgres/MySQL you'd think about tie-breaking explicitly |
| `daily_revenue` as a half-open range `created_at >= day AND created_at < next_day` | A bare column is sargable. Half-open ranges never overlap or leave gaps. `'2025-10-10'` sorts before `'2025-10-10 00:00:00'`, so the bare date works as the lower bound | Depends on timestamps being stored as sortable text in one consistent format |
| `next_day` computed in Python with `datetime.date` (not `datetime`) | No `T` in the output; correct month and year rollover | — |
| `orders(status, created_at)` | Equality column (`status`) then range (`created_at`), giving a 2k-work range read | It hijacked `top_customers`' plan until `ANALYZE` (status is 85% `paid`, so it's not selective) |
| `top_customers` as one `JOIN … GROUP BY u.id … ORDER BY total DESC, u.name ASC LIMIT ?` | Removes N+1: 1,978 round trips become 1 | `COALESCE` there is redundant (the `paid` filter guarantees ≥1 row per group), but harmless |
| `ANALYZE` at the end of `migrate()` | Gives the planner real statistics, so it stops choosing the 85%-selective status index | Statistics go stale as data changes. Production databases re-run it (Postgres does it automatically) |
| Old N+1 code left commented out in `top_customers` | The owner's choice, as a learning reference | Clutter. Fine for a learning repo |

---

## 5. Current state of the project

### Git

| Branch | Head | Contents |
|---|---|---|
| `claude/festive-noether-kxzazk` (the remote's default `HEAD`) | `c07c2a1` "lab 1 walkthrough", by the owner, Oct 11 2026 | Original labs + the owner's **solved** `labs/01-slow-dashboard/app.py` + `journal/01.md` (empty template) |
| `claude/youthful-davinci-mp59lt` (this session's branch) | `c07c2a1` + the commit adding this `HANDOFF.md` | Fast-forwarded to the owner's commit, then this file added. No other changes |

The original broken `app.py` is still in history at `9d3df09` (and `015d99b`).

### Lab status

| Lab | Status |
|---|---|
| 01 The Slow Dashboard | **Passes all 10 checks** (verified Nov 1 2026 on `c07c2a1`). `notes 01` probably not read yet (unconfirmed). Journal empty |
| 02–07 | Not started |
| Design drills / estimate | Not started |

`check 01` numbers on the committed solution: recent_orders max 1k, daily_revenue max 2k,
top_customers max 710k (budget 1,000k), top_customers 1 statement.

### Local-only state on the owner's machine (not in git)

- `~/development/Projects/Engineer_Lab/MYENGINEER/.progress.json`: whether lab 01 is marked
  passed, guide position and hints revealed. Unknown from here.
- `labs/01-slow-dashboard/data.db`: rebuilt automatically if missing.
- Any indexes made in the playground are wiped on the next run, so they don't matter.

---

## 6. What the owner should take away (condensed)

1. SCAN reads everything; SEARCH jumps via an index. Always ask "a SCAN of *what*, how big?"
2. An index is a sorted copy of columns, chosen to match the app's questions.
3. Composite order: `=` columns first, then the sort/range column.
4. Keep indexed columns bare in `WHERE` (sargable); put the math on the other side.
5. N+1 is a round-trip problem, not an index problem. Fix it with one set-based query.
6. The planner relies on statistics; `ANALYZE` (and stale stats) can change plans with no deploy.
7. Every index can change every plan on its table; it costs disk and write speed.
8. Trust work and rows touched, not laptop latency. Ask "does this cost grow with the data?"
9. Correctness first: a fast wrong finance number is worse than a slow right one.

Design use: list access patterns first and index for the hottest reads. In design reviews,
use "bounded vs grows-with-data" as the key question. In code review, flag queries in loops,
functions around indexed columns, `ORDER BY … LIMIT` without a matching index, and new indexes
that nobody re-checked against other queries. Fix query shape before reaching for caches,
replicas or shards (Labs 03, 04, 06).

---

## 7. Open tasks (in suggested order)

1. **Fix the reset/selftest problem** (section 8.1) before attempting the redo.
2. **Run `python3 lab.py notes 01`** and compare it with the owner's own understanding. Before reading it,
   try to answer: "what further change would remove `SCAN u` from `top_customers`?"
3. **Fill in `journal/01.md`** in the owner's own words: symptoms with numbers, the README's 4 questions,
   root cause per page, the cost of each fix, and what the notes added.
4. **Optional: playground arrow keys.** Add `import readline` near the top of
   `labs/01-slow-dashboard/playground.py`, or use `sqlite3 labs/01-slow-dashboard/data.db` + `.eqp on`.
5. **Redo Lab 01 from scratch after a week**, with no guide, no hints and no AI, then check again.
6. **Then Lab 02 (The Flash Sale)**. It has no guide on purpose; use the same loop
   (measure → plan/inspect → hypothesise → change one thing → re-measure).
7. Later: `python3 lab.py estimate` regularly, and `design/numbers.md`. The README suggests
   Lab 01 in week 1, alongside DDIA chapter 3.

---

## 8. Unresolved issues and risks

### 8.1 `reset 01` and `selftest` broke when the solved `app.py` was committed (verified)

- `lab.py reset 01` runs `git checkout HEAD -- labs/01-slow-dashboard/app.py`. `HEAD` now holds
  the **solved** file, so "reset" restores the solution, not the broken code. The planned
  "redo in a week" would start already solved.
- `lab.py selftest` treats `HEAD:app.py` as the broken version. It now prints
  `01 The Slow Dashboard  broken fails: False  solution passes: True  PROBLEM`
  (verified Nov 1 2026; labs 02–07 are OK).

**Options (owner's choice, nothing has been changed):**

- a) **Recommended:** keep the default branch with the *original* `app.py` files and keep solved work
  on a personal branch (e.g. `my-solutions`). Commit journals freely; they don't affect reset.
- b) Save the solution as a separate file (e.g. `journal/01-solution.py`) and restore the original
  in the main branch: `git checkout 9d3df09 -- labs/01-slow-dashboard/app.py`, then commit.
- c) For a one-off redo without changing git: `git show 9d3df09:labs/01-slow-dashboard/app.py > labs/01-slow-dashboard/app.py`.
- d) Change `cmd_reset`/`cmd_selftest` in `lab.py` to use the first commit that introduced each lab
  instead of `HEAD`. This is more robust but changes the tool.

### 8.2 Journal not written

`journal/01.md` was committed as the unfilled template. The reflection step (where most of the
retention comes from) hasn't happened yet.

### 8.3 Questions put to the owner that were never answered

These are good self-test prompts:
- Predict, then check: does `CREATE INDEX users_country ON users(country)` make
  `WHERE country='GH'` use SEARCH, and why is the speedup smaller than for `name`? (Partly explored.)
- The first two `run --explain` outputs had no `TEMP B-TREE` but the third did. The likely cause is
  a two-column index that was later reverted. Never confirmed.
- Why did the original `top_customers` stop at 157 statements instead of 1,492 for GH? (The 2 s timeout killed it.)
- What would remove `SCAN u` from `top_customers`? (Answered in `notes 01`.)

### 8.4 Branch naming / workflow

The owner's work lives on `claude/festive-noether-kxzazk`, which is also the remote's default `HEAD`.
That is an auto-generated session branch name. Consider creating a clearly named default branch
(e.g. `main`) holding the pristine labs, and decide where personal solutions live (see 8.1).

### 8.5 Minor

- `orders_status_created_at ON orders(status, created_at )` has a stray space before `)`. Harmless.
- The owner's local clone may not have this `HANDOFF.md` until they fetch
  `claude/youthful-davinci-mp59lt` (or merge it).

---

## 9. Reference: the owner's passing `app.py` (spoiler)

This is identical to `labs/01-slow-dashboard/app.py` at `c07c2a1`, minus the commented-out old loop:

```python
import datetime


def migrate(conn):
    conn.execute("CREATE INDEX IF NOT EXISTS orders_user_id ON orders(user_id, created_at)")
    conn.execute("CREATE INDEX IF NOT EXISTS orders_status_created_at ON orders(status, created_at )")
    conn.execute("ANALYZE")  # give the planner statistics about the data distribution


def recent_orders(conn, user_id, limit=20):
    return conn.execute(
        "SELECT id, amount_cents, status, created_at FROM orders "
        "WHERE user_id = ? ORDER BY created_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()


def daily_revenue(conn, day):
    next_day = (datetime.date.fromisoformat(day) + datetime.timedelta(days=1)).isoformat()
    row = conn.execute(
        "SELECT COALESCE(SUM(amount_cents), 0) FROM orders "
        "WHERE status = 'paid' AND created_at >= ? AND created_at < ?",
        (day, next_day),
    ).fetchone()
    return row[0]


def top_customers(conn, country, limit=10):
    return conn.execute(
        "SELECT u.name, COALESCE(SUM(o.amount_cents), 0) AS total "
        "from orders o join users u on o.user_id = u.id "
        "where u.country = ? and o.status = 'paid' "
        "group by u.id "
        "order by total desc, u.name asc "
        "limit ?",
        (country, limit)
    ).fetchall()
```

**Compared with the reference solution** (`labs/01-slow-dashboard/solution/app.py`): the reference also
adds `INDEX users(country)` and a covering `INDEX orders(user_id, status, amount_cents)`, which
would cut `top_customers` work below the current 369k p50 / 710k max. `notes 01` explains why.

---

## 10. Notes for the next helper (human or AI)

- **Who the learner is:** a working software developer, new to database internals and systems concepts.
  They learn best with plain-English analogies, real numbers from this database, and short
  playground experiments. They sometimes ask for "short answer"; respect that.
- **Do not hand out lab solutions unprompted.** Explain, give an experiment, ask for a prediction.
  Only give code when they explicitly ask, and say that you're doing it.
- **They run everything on their own machine** (`~/development/Projects/Engineer_Lab/MYENGINEER`).
  A cloud session's copy can differ from theirs, so ask them to paste code and output, or
  fetch their latest branch before commenting.
- **Verify before claiming.** Every number in this document was measured on this repo's `data.db`.
  Re-measure rather than guess (`run 01 --explain`, `check 01`, small scripts using `data.connect()`).
