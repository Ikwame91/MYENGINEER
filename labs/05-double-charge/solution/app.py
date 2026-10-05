"""Reference solution. Read solution/NOTES.md for the reasoning."""

import json
import random
import time
import urllib.error
import urllib.request

TIMEOUT = 0.5
MAX_ATTEMPTS = 8
BASE_BACKOFF = 0.1     # seconds before the first retry; doubles each time
MAX_BACKOFF = 1.0
RETRYABLE = {409, 429, 500, 502, 503, 504}   # 409 here means "your earlier attempt is still running"


class CardDeclined(Exception):
    pass


class PaymentFailed(Exception):
    pass


def checkout(order, provider_url):
    body = json.dumps({"order_id": order["id"], "amount_cents": order["amount_cents"],
                       "card": order["card"]}).encode()
    # One key per *logical* charge, reused on every retry, and derived from the order so it's
    # still the same key if this process crashes and the order is retried tomorrow.
    key = f"order-charge:{order['id']}"
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        if attempt:
            time.sleep(_backoff(attempt))
        request = urllib.request.Request(
            provider_url + "/charges", data=body, method="POST",
            headers={"Content-Type": "application/json", "Idempotency-Key": key})
        try:
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read())["charge_id"]
        except urllib.error.HTTPError as e:          # the provider answered: we know what happened
            if e.code == 402:
                raise CardDeclined(order["id"]) from e
            if e.code not in RETRYABLE:
                raise PaymentFailed(f"provider rejected the request: HTTP {e.code}") from e
            last_error = e
        except (urllib.error.URLError, OSError) as e:  # timeout / connection error: outcome UNKNOWN
            last_error = e                             # safe to retry only because of the idempotency key
    raise PaymentFailed(f"gave up after {MAX_ATTEMPTS} attempts: {last_error}")


def _backoff(attempt):
    """Exponential backoff with jitter: 0.1, 0.2, 0.4, ... capped, then randomized to 50-100%."""
    ceiling = min(MAX_BACKOFF, BASE_BACKOFF * 2 ** (attempt - 1))
    return random.uniform(ceiling / 2, ceiling)
