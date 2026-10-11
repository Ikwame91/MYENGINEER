# MYENGINEER

**Learn systems engineering by breaking real systems and fixing them yourself.**

This isn't a course you read. Each lab is a small, running system with a production bug of the
kind that pages engineers at 3am: a full table scan, overselling, stale reads after a write, a
cache stampede, double charges, a resharding disaster, a server that stays dead after a traffic
spike. You run it, watch it fail with real numbers, investigate, fix it, and an automated check
tells you whether your fix holds up under load and concurrency. Then you read what a senior
engineer would *also* have caught.

Everything is plain Python 3.9+ with **no dependencies** (Linux, macOS, or WSL on Windows). Real SQLite databases, real threads and
processes, real HTTP servers on localhost, real TCP timeouts. It runs on any laptop.

```bash
python3 lab.py            # list labs and your progress
python3 lab.py guide 01   # new here? a step-by-step walkthrough of the first lab
```

## The loop (this is the whole method)

```
 run ──► observe ──► hypothesize ──► investigate ──► fix ──► check ──► read the notes ──► self-test
  │                       ▲                                    │
  └───────────────────────┴──── wrong? good. write down why ◄──┘
```

1. **Read the lab's `README.md`**: the incident, and the questions to answer.
2. **Run it**: `python3 lab.py run NN`. Look at the numbers. Don't touch code yet.
3. **Journal it**: `python3 lab.py journal NN` creates `journal/NN.md`. Write the symptoms and
   your hypotheses *before* fixing. Being wrong in writing is how the evaluating muscle grows.
4. **Fix `app.py`** (it's the only file you change), and rerun as often as you like.
5. **Check**: `python3 lab.py check NN`. It runs your code under adversarial conditions and
   tells you which property is violated, not how to fix it.
6. **Stuck for 20+ minutes?** `python3 lab.py hint NN` reveals one hint at a time.
7. **Passed?** `python3 lab.py notes NN`: root cause, wrong fixes and why they fail, what a
   senior engineer would *also* notice, and self-test questions. This is where most of the learning is.
8. **Reset and redo it a week later** without hints: `python3 lab.py reset NN`.

### The one rule about AI

Do each lab's first attempt **without AI**. The labs exist to build the muscle that catches
the mistake, and AI would do the lifting for you. *After* you pass, use AI as a sparring partner:
"why does X happen?", "what would break my fix?", "how does Postgres do this?". See
[`PRINCIPLES.md`](PRINCIPLES.md).

## The labs

| # | Lab | The incident | You'll learn |
|---|---|---|---|
| 01 | [The Slow Dashboard](labs/01-slow-dashboard) | Dashboard times out; "nothing was deployed" | Indexes, composite index order, query plans, N+1, sargable predicates, planner statistics, covering indexes |
| 02 | [The Flash Sale](labs/02-flash-sale) | 900 pairs sold, 100 in stock | Race conditions, lost updates, atomic updates, transactions, why in-process locks fail across servers, compensation |
| 03 | [Read Replicas](labs/03-read-replicas) | "I saved my name and it changed back!" | Replication lag, read-your-writes, monotonic reads, LSNs, consistency vs cost, failover data loss |
| 04 | [The Cache Stampede](labs/04-cache-stampede) | DB melting at a 98% cache hit rate | TTLs, thundering herd, single-flight, synchronized expiry, jitter, overload amplification |
| 05 | [The Double Charge](labs/05-double-charge) | Customers charged twice by a retry | Timeouts, unknown outcomes, idempotency keys, retryable vs final errors, backoff + jitter, retry storms |
| 06 | [Sharding](labs/06-sharding) | Users vanish after every deploy | Partitioning, stable hashing, resharding cost, consistent hashing, virtual nodes, hot keys |
| 07 | [Overload](labs/07-overload) | Still 0% success after the spike ended | Queueing, Little's law, goodput, load shedding, deadlines, backpressure, metastable failures |

Each one reproduces a mechanism behind real outages at large companies. Each check has been
tested against the plausible-but-wrong fixes (a `threading.Lock` across 4 processes, "primary
for 1 second after a write", a UUID idempotency key per attempt, a giant bounded queue...), so
those fail and teach you why.

## System design practice

The labs teach mechanisms; design drills teach combining them under constraints.

```bash
python3 lab.py drill        # 5 drills: URL shortener, ticket sale, news feed, wallet ledger, rate limiter
python3 lab.py drill 2      # the prompt only: design it on paper, 45 minutes
python3 lab.py review 2     # then: the questions a staff engineer would ask you
python3 lab.py estimate     # back-of-envelope estimation quiz (new numbers every time)
```

Method and rubric: [`design/README.md`](design/README.md). Numbers to know: [`design/numbers.md`](design/numbers.md).

## A suggested path (about 6 weeks, a few hours a week)

| Week | Do | Read alongside |
|---|---|---|
| 1 | Lab 01 · `estimate` daily · `design/numbers.md` | *Designing Data-Intensive Applications* (DDIA) ch. 3 (storage, indexes) |
| 2 | Lab 02 · Lab 03 | DDIA ch. 5 (replication), ch. 7 (transactions) |
| 3 | Lab 04 · Drill 1 | Facebook, *Scaling Memcache at Facebook* (NSDI '13) |
| 4 | Lab 05 · Drill 2 · Drill 4 | Stripe engineering blog, *Designing robust and predictable APIs with idempotency* |
| 5 | Lab 06 · Drill 3 | DDIA ch. 6 (partitioning); Amazon *Dynamo* paper (2007) |
| 6 | Lab 07 · Drill 5 · redo your weakest lab from scratch | Google *SRE Book*, ch. 21–22 (overload, cascading failures); *Metastable Failures in Distributed Systems* (HotOS '21) |

Then keep the muscle strong (from `PRINCIPLES.md`): debug something hard by hand, design on paper
before prompting, and read a well-regarded codebase. Redis's source is small, readable C and
covers caching, data structures, and replication.

## Repository layout

```
lab.py              the CLI
labkit.py           shared helpers (no need to read)
labs/NN-name/
  README.md         the incident and your investigation questions   ← start here
  app.py            the broken code you fix                         ← the only file you edit
  run.py            reproduces the symptoms
  check.py          the acceptance test
  hints.md          progressive hints (use `lab.py hint`, not cat)
  solution/         reference fix + NOTES.md (read after passing)
  *.py              the simulated environment (worth reading once you've passed)
design/             drills, method, numbers, estimation quiz
journal/            your investigation notes (commit them: it's your learning record)
```

Maintainers: `python3 lab.py selftest` verifies every lab's original code fails its check and
every reference solution passes.
