## Hint 1
A timeout doesn't mean "it failed". It means "I don't know". The provider may have charged the
card and just been slow to answer. Retrying blindly turns "I don't know" into "charged twice".

## Hint 2
Read the `Idempotency-Key` section of the API docs in `provider.py`. If you send the same key
again, the provider returns the *original* result instead of charging again.

## Hint 3
The key must be the same for every retry of the **same logical charge**. A new `uuid4()` per
attempt is the most common mistake (try it, and watch the double charges stay). Where could
the key come from so that it's still the same even if your process crashes and restarts?

## Hint 4
`urllib.error.HTTPError` means the server *answered*: you know what happened. 402 is final;
409 and 503 are worth retrying. Other errors (timeouts, connection refused) are the "unknown"
case. Watch out: `HTTPError` is a subclass of `URLError`, so the order of your `except` clauses
matters.

## Hint 5
Retrying immediately during an outage burns your attempts in milliseconds and hammers the
provider. Wait between attempts, longer each time (exponential backoff), with randomness
(jitter) so thousands of clients don't retry in lockstep. Make sure the total wait across your
attempts outlasts a short outage.
