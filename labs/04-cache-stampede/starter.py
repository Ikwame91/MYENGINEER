"""
Product cache in front of a slow database.

get() is called concurrently by ~100 request-handler threads. You may change anything in this
file, but keep the class name, the TTL attribute, and get()'s signature and return value.
"""

import time


class ProductCache:
    TTL = 1.0  # seconds: product prices may be at most ~this stale (product team requirement)

    def __init__(self, db):
        self.db = db
        self._entries = {}  # product_id -> (product, expires_at)

    def get(self, product_id):
        entry = self._entries.get(product_id)
        if entry is not None and entry[1] > time.monotonic():
            return entry[0]
        product = self.db.get_product(product_id)
        self._entries[product_id] = (product, time.monotonic() + self.TTL)
        return product
