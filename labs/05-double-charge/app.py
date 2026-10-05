"""
Checkout: charges the customer's card through the payment provider's HTTP API.

checkout() runs concurrently for many orders. You may change anything in this file, but keep
checkout()'s signature and its contract:
  * return the provider's charge_id when the customer was charged,
  * raise CardDeclined when the card was declined,
  * raise PaymentFailed when you give up (the order will be retried later by a human).

The provider's API is documented at the top of provider.py.
"""

import json
import urllib.request

TIMEOUT = 0.5  # seconds: our own SLO doesn't allow waiting longer for one HTTP call
MAX_ATTEMPTS = 5


class CardDeclined(Exception):
    pass


class PaymentFailed(Exception):
    pass


def checkout(order, provider_url):
    body = json.dumps({"order_id": order["id"], "amount_cents": order["amount_cents"],
                       "card": order["card"]}).encode()
    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            request = urllib.request.Request(provider_url + "/charges", data=body, method="POST",
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
                return json.loads(response.read())["charge_id"]
        except Exception as e:  # anything went wrong? try again
            last_error = e
    raise PaymentFailed(f"gave up after {MAX_ATTEMPTS} attempts: {last_error}")
