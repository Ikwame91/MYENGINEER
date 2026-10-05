# Lab 07: Overload

**Concepts:** capacity, utilization, queueing, Little's law (L = λW), open vs closed-loop load,
goodput vs throughput, unbounded queues, load shedding, deadline propagation, backpressure,
metastable failures.

## The page

> **#incident-api** · 11:02
> **Pager:** `api p99 latency > 500ms`, `api success rate < 10%`
> **Marketing:** Oh, the newsletter went out at 11:00. Traffic jumped 2.5×.
> **11:06 — Teammate:** Traffic is back to normal, but we're *still* at 0% success. CPU is pegged.
> Restarting the pods fixed it last time...

The server has 4 workers, each request takes 20ms: **200 req/s capacity**. Clients hang up after
500ms. You own `app.py`: the queue between the network listener and the workers.

## Run it

```bash
python3 lab.py run 07      # timeline through normal -> spike (300/s) -> after (120/s)
python3 lab.py check 07
```

## Investigate before you touch code

In `journal/07.md`:

1. During the spike, requests arrive at 300/s and leave at 200/s. How long does the queue get
   after 1s? After 4s? How long does a new arrival wait at the end of the spike?
2. **Little's law**: L = λ × W (items in system = arrival rate × time in system). Use it to say how
   long the queue can be before the *average* request waits longer than the client's timeout.
3. Why does the server stay broken **after** traffic returns to normal? What is it spending
   its time on? (Look at the "work done after the client gave up" line.)
4. Why does "restart the pods" fix it? What does a restart throw away?
5. You can't make the server faster today. During the spike, which is better for users:
   300 slow answers that all time out, or 200 fast answers and 100 instant "try again later"s?

## Rules

- Change only `app.py`.
- `offer()` is called by the listener. If it blocks, you've moved the queue upstream, not removed it.

## Done when

`python3 lab.py check 07` passes: healthy traffic unaffected, goodput ≥ 150/s during the spike,
fast successes (p99 ≤ 250ms), immediate recovery after the spike, and almost no wasted work.

## After you pass

Read `solution/NOTES.md`.
