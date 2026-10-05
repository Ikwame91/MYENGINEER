# Lab 05 notes: what was wrong, and what a senior engineer sees

## Root causes

| Symptom | Cause |
|---|---|
| Double charges | Timeout → blind retry. The first request *had* charged; the response was just late. |
| "Payment failed" but charged | Retries exhausted → `PaymentFailed`, even though an earlier attempt succeeded. |
| Declined cards hammered 5× | `except Exception` retries a 402, which is a final answer. |
| Orders lost in the outage | 5 attempts with no delay used up in ~5ms, long before the 0.5s outage ended. |

## The fix

1. **Idempotency key per logical operation**, derived from the order (`order-charge:<id>`), sent
   on every attempt. Retrying is now *safe*: the provider dedupes, and a replay returns the
   original charge id.
2. **Classify errors**: answered + final (402, 4xx) → stop. Answered + transient (409, 429, 5xx)
   → retry. No answer (timeout, connection error) → outcome unknown → retry, only because of the key.
3. **Exponential backoff with jitter**, and enough attempts that the total wait outlasts a blip.

## What a senior engineer also notices

1. **"Exactly once" doesn't exist over a network; "at least once + idempotency" does.** This is
   the same idea behind Kafka producer idempotence, SQS dedupe IDs, and every payments API. When
   you design an API that changes state, **design the idempotency key into it**.
2. **Your own endpoints need this too.** The browser calling *your* `/checkout` will also time
   out and retry (or the user double-clicks). Accept an idempotency key from the client, store it
   with a unique constraint, and return the stored result.
3. **Where is the key stored, and for how long?** The provider must keep keys at least as long
   as clients might retry (Stripe: 24h). A key store with a short TTL turns slow retries back into
   double charges.
4. **PaymentFailed isn't the end.** After giving up, the outcome is *still* unknown. Real systems
   record the order as `payment_unknown` and reconcile: query the provider by key/order id, or
   process its webhooks. Never tell the customer "failed" when you mean "don't know".
5. **Retries multiply.** If the browser retries 3×, your API retries 3×, and your service retries
   the DB 3×, one click is 27 DB calls during an outage. Retry at **one** layer, use **retry
   budgets** (e.g. retries ≤ 10% of requests), and use **circuit breakers** to stop calling a
   dependency that's clearly down.
6. **Timeouts are a design parameter.** 0.5s was chosen for *our* SLO, but the provider sometimes
   takes 1s. Are we timing out on work that would have succeeded? Look at the provider's latency
   distribution (p99), and set timeouts from data, with a deadline for the whole operation, not
   just per attempt.
7. **Jitter matters at scale.** Without it, every client that failed at 18:46:00.000 retries at
   exactly :00.100, :00.300, :00.700: synchronized waves (compare Lab 04's TTL jitter).

## Self-test

- Explain to a support agent why a customer was charged twice even though "we only charge once".
- Your service crashes right after the provider charged but before you saved the charge id.
  Walk through what happens on restart with your design.
- Which of these are idempotent, and how would you make the others idempotent:
  `SET balance = 100`, `balance += 10`, `send email`, `DELETE /orders/7`, `POST /orders`?
