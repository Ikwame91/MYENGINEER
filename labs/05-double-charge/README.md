# Lab 05: The Double Charge

**Concepts:** timeouts and the "unknown outcome" problem, at-least-once vs exactly-once,
idempotency keys, which errors are retryable, exponential backoff with jitter, retry storms,
honest error reporting.

## The page

> **#incident-payments** · 18:47
> **Support:** 19 customers charged twice. One charged three times. They're furious.
> **Also support:** And some customers got "payment failed" but their bank shows the charge!
> **Payments provider status page:** "18:46: brief elevated error rates, resolved."
> **Teammate:** We added retries last sprint exactly for those provider blips...

`app.py` calls a payment provider over **real HTTP**. `provider.py` starts it on localhost. Read
the API docs at the top of `provider.py`. Learning from an API's documentation what a status code
promises is part of the job.

## Run it

```bash
python3 lab.py run 05      # ledger audit + the provider's view of every request over time
python3 lab.py check 05
```

## Investigate before you touch code

In `journal/05.md`:

1. Pick a double-charged order from the output. Write the timeline from **both** sides: what the
   provider did, and what `checkout()` saw at each moment.
2. When `urlopen` raises a timeout, did the charge happen? Can you know? This is the core
   problem. Write down what "unknown outcome" means for a money-moving operation.
3. Classify every response in the API docs: retry or not, and *why*. What's the difference
   between a 402 and a 503?
4. During the outage (1.0s–1.5s) look at the request rate. What do 10,000 clients doing this
   do to a provider that's trying to recover?
5. What would make it **safe** to retry a request whose outcome you don't know?

## Rules

- Change only `app.py`. Keep `checkout(order, provider_url)` and its contract.
- Standard library only (`urllib` is fine).

## Done when

`python3 lab.py check 05` passes: no double charges, every valid order charged, answers match
reality, declines not retried, no retry storm.

## After you pass

Read `solution/NOTES.md`. Then reread Lab 02's notes, point 4.
