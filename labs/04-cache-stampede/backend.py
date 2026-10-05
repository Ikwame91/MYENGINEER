"""The product database and the traffic that hits your cache (provided; don't edit)."""

import random
import threading
import time

CAPACITY = 8          # queries the DB can run at full speed at once
BASE_LATENCY = 0.050  # one product query on an idle DB
HOT_PRODUCTS = 3      # today's front-page deals
PRODUCTS = 50
THREADS = 100         # concurrent request handlers
SECONDS = 6.0
WARM_AT_DEPLOY = True


class ProductDB:
    """Slow, and gets slower as concurrent queries pile up past CAPACITY (like a real DB under load)."""

    def __init__(self):
        self._lock = threading.Lock()
        self.inflight = 0
        self.peak_inflight = 0
        self.calls = 0
        self.timeline = []          # (t, inflight) samples
        self.snapshot_mode = False  # deploy-time bulk load: served from a snapshot, instantly

    def get_product(self, product_id):
        with self._lock:
            self.calls += 1
            self.inflight += 1
            self.peak_inflight = max(self.peak_inflight, self.inflight)
            load = self.inflight
            self.timeline.append((time.monotonic(), load))
        try:
            if self.snapshot_mode:
                return {"id": product_id, "name": f"Product {product_id}", "price_cents": 1000 + product_id,
                        "loaded_at": time.monotonic()}
            # Past capacity, every query slows down for everyone (CPU, locks, disk contention).
            time.sleep(BASE_LATENCY * max(1.0, load / CAPACITY))
            return {"id": product_id, "name": f"Product {product_id}", "price_cents": 1000 + product_id,
                    "loaded_at": time.monotonic()}
        finally:
            with self._lock:
                self.inflight -= 1


def simulate(app, seconds=SECONDS, seed=0):
    db = ProductDB()
    cache = app.ProductCache(db)
    lock = threading.Lock()
    latencies, ages, errors = [], [], []

    if WARM_AT_DEPLOY:  # the deploy script pre-loads every product so the first users don't wait
        db.snapshot_mode = True
        for pid in range(1, PRODUCTS + 1):
            cache.get(pid)
        db.snapshot_mode = False
    db.calls, db.peak_inflight, db.timeline = 0, 0, []
    start = time.monotonic()

    def handler(i):
        rng = random.Random(seed * 1000 + i)
        while time.monotonic() - start < seconds:
            pid = rng.randint(1, HOT_PRODUCTS) if rng.random() < 0.9 else rng.randint(1, PRODUCTS)
            t0 = time.monotonic()
            try:
                product = cache.get(pid)
                t1 = time.monotonic()
                with lock:
                    latencies.append(t1 - t0)
                    ages.append(t1 - product["loaded_at"])
                    if product["id"] != pid:
                        errors.append(f"asked for {pid}, got {product['id']}")
            except Exception as e:  # noqa: BLE001
                with lock:
                    errors.append(f"{type(e).__name__}: {e}")
            time.sleep(rng.uniform(0.001, 0.005))

    threads = [threading.Thread(target=handler, args=(i,)) for i in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    return dict(db=db, start=start, latencies=latencies, ages=ages, errors=errors, ttl=app.ProductCache.TTL)
