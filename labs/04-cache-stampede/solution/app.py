"""Reference solution. Read solution/NOTES.md for the reasoning."""

import random
import threading
import time


class ProductCache:
    TTL = 1.0
    JITTER = 0.2   # each entry lives TTL * (1 ± 20%), so entries loaded together don't expire together

    def __init__(self, db):
        self.db = db
        self._entries = {}        # product_id -> (product, expires_at)
        self._loading = {}        # product_id -> threading.Event, set when the in-flight load finishes
        self._lock = threading.Lock()

    def get(self, product_id):
        while True:
            with self._lock:
                entry = self._entries.get(product_id)
                if entry is not None and entry[1] > time.monotonic():
                    return entry[0]
                pending = self._loading.get(product_id)
                if pending is None:
                    # This caller becomes the single loader for the key ("single flight").
                    pending = self._loading[product_id] = threading.Event()
                    break
            pending.wait()      # someone else is loading it: wait, then re-read the cache
        try:
            product = self.db.get_product(product_id)
            ttl = self.TTL * random.uniform(1 - self.JITTER, 1 + self.JITTER)
            with self._lock:
                self._entries[product_id] = (product, time.monotonic() + ttl)
            return product
        finally:
            with self._lock:
                del self._loading[product_id]
            pending.set()       # wake the waiters even if the load failed (they'll retry the load)
