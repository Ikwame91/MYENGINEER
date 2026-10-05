"""A fake card processor running as a real HTTP server on localhost (provided; don't edit).

API (modelled on real payment APIs such as Stripe):

    POST /charges
    Content-Type: application/json
    Idempotency-Key: <optional, any string up to 255 chars>
    {"order_id": "...", "amount_cents": 1234, "card": "4242..."}

    200 {"charge_id": "ch_..."}      charged (or an idempotent replay of an earlier success)
    402 {"error": "card_declined"}   the card was declined; retrying won't change that
    409 {"error": "in_progress"}     a request with this Idempotency-Key is still being processed
    422 {"error": "key_reused"}      this Idempotency-Key was used with a different request body
    503 {"error": "unavailable"}     temporary problem; nothing was charged

The server's real-world quirks:
  * Sometimes it's slow: it charges the card, then takes ~1s to respond.
  * Sometimes it returns 503 for a request or two.
  * Once in a while it has a short outage where everything gets 503.
"""

import hashlib
import json
import random
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

DECLINED_CARD = "4000000000000002"
OUTAGE = (1.0, 1.5)        # seconds after start: everything returns 503
SLOW_RESPONSE = 1.0        # seconds a slow response takes (after the charge has happened)


class Provider:
    def __init__(self, seed=0):
        self.seed = seed
        self.lock = threading.Lock()
        self.charges = []       # (order_id, charge_id)
        self.attempts = []      # (t, order_id, status, responded_promptly)
        self.idempotency = {}   # key -> {"body": hash, "state": "in_progress"|"done", "status", "response"}
        self.seen = {}          # order_id -> number of requests received
        self.started = time.monotonic()

    def _trait(self, order_id, name):
        digest = hashlib.sha256(f"{self.seed}:{order_id}:{name}".encode()).digest()
        return digest[0] / 255

    def handle(self, body, key):
        """Returns (status, response_dict, delay_seconds)."""
        order_id = body.get("order_id")
        now = time.monotonic() - self.started
        with self.lock:
            n = self.seen[order_id] = self.seen.get(order_id, 0) + 1

            def record(status, prompt=True):
                self.attempts.append((now, order_id, status, prompt))

            if key is not None:
                body_hash = hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()
                existing = self.idempotency.get(key)
                if existing:
                    if existing["body"] != body_hash:
                        record(422)
                        return 422, {"error": "key_reused"}, 0
                    if existing["state"] == "in_progress":
                        record(409)
                        return 409, {"error": "in_progress"}, 0
                    record(existing["status"])
                    return existing["status"], existing["response"], 0

            if OUTAGE[0] <= now < OUTAGE[1] or (n <= 2 and self._trait(order_id, "flaky") < 0.15):
                record(503)
                return 503, {"error": "unavailable"}, 0  # nothing stored: safe to retry with the same key

            if body.get("card") == DECLINED_CARD:
                status, response = 402, {"error": "card_declined"}
            else:
                charge_id = "ch_" + uuid.uuid4().hex[:12]
                self.charges.append((order_id, charge_id))
                status, response = 200, {"charge_id": charge_id}
            slow = n == 1 and self._trait(order_id, "slow") < 0.25
            record(status, prompt=not slow)
            if key is not None:
                self.idempotency[key] = {"body": body_hash, "state": "in_progress" if slow else "done",
                                         "status": status, "response": response}
        return status, response, (SLOW_RESPONSE if slow else 0)

    def finish(self, key):
        if key is not None:
            with self.lock:
                self.idempotency[key]["state"] = "done"


def serve(seed=0):
    """Starts the provider on a free localhost port. Returns (provider, url, shutdown_fn)."""
    provider = Provider(seed)

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self):
            if self.path != "/charges":
                self.send_error(404)
                return
            try:
                body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", 0))))
            except (ValueError, TypeError):
                self._reply(400, {"error": "bad_json"})
                return
            key = self.headers.get("Idempotency-Key")
            status, response, delay = provider.handle(body, key)
            if delay:
                time.sleep(delay)          # the charge already happened; the response is just late
                provider.finish(key)
            self._reply(status, response)

        def _reply(self, status, payload):
            data = json.dumps(payload).encode()
            try:
                self.send_response(status)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
            except (BrokenPipeError, ConnectionResetError):
                pass  # the client gave up waiting; it never sees this response

        def log_message(self, *args):
            pass

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 128  # listen backlog; the default (5) drops SYNs under bursts -> 1s client stalls

        def handle_error(self, request, client_address):
            pass

    server = Server(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    provider.started = time.monotonic()
    return provider, f"http://127.0.0.1:{server.server_address[1]}", server.shutdown


ORDERS = 80
WORKERS = 16
ARRIVAL_GAP = 0.025   # a new order every 25ms -> 80 orders arrive over 2 seconds


def make_orders(seed=0):
    rng = random.Random(seed)
    return [{"id": f"order-{i:03d}", "amount_cents": rng.randint(500, 50_000),
             "card": DECLINED_CARD if rng.random() < 0.06 else "4242424242424242"}
            for i in range(ORDERS)]


def run_checkouts(app, seed=0):
    """Starts the provider, runs every order through app.checkout() concurrently, returns a report."""
    provider, url, shutdown = serve(seed)
    orders = make_orders(seed)
    outcomes, lock = {}, threading.Lock()
    queue = list(reversed(list(enumerate(orders))))
    start = time.monotonic()

    def worker():
        while True:
            with lock:
                if not queue:
                    return
                i, order = queue.pop()
            wait = start + i * ARRIVAL_GAP - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            t0 = time.monotonic()
            try:
                result = ("ok", app.checkout(order, url))
            except Exception as e:  # noqa: BLE001
                result = (type(e).__name__, str(e))
            with lock:
                outcomes[order["id"]] = (*result, time.monotonic() - t0)

    threads = [threading.Thread(target=worker) for _ in range(WORKERS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    time.sleep(SLOW_RESPONSE + 0.2)  # let in-flight slow requests land in the ledger
    shutdown()
    return dict(orders=orders, outcomes=outcomes, charges=provider.charges, attempts=provider.attempts)
