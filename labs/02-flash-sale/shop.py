"""The flash-sale environment (provided; you don't need to edit this)."""

import multiprocessing
import os
import random
import sqlite3
import tempfile
import threading
import time

STOCK = 100          # units of the item on sale
BUYERS = 1000        # people clicking "Buy" at 12:00:00
SERVERS = 4          # app server processes behind the load balancer
THREADS = 16         # request handler threads per server
ITEM_ID = 1


class PaymentDeclined(Exception):
    pass


class PaymentProvider:
    """Pretend card processor: ~3ms per call, declines ~10% of cards. Thread-safe ledger."""

    def __init__(self, seed=0):
        self._lock = threading.Lock()
        self._rng = random.Random(seed)
        self.charged = []     # user_ids successfully charged
        self.refunded = []    # user_ids refunded

    def charge(self, user_id):
        time.sleep(0.003)
        with self._lock:
            if self._rng.random() < 0.10:
                raise PaymentDeclined(f"card of user {user_id} declined")
            self.charged.append(user_id)

    def refund(self, user_id):
        time.sleep(0.003)
        with self._lock:
            self.refunded.append(user_id)


def create_db():
    path = os.path.join(tempfile.mkdtemp(prefix="flash-sale-"), "shop.db")
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(f"""
        CREATE TABLE items (id INTEGER PRIMARY KEY, name TEXT NOT NULL, stock INTEGER NOT NULL);
        CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL, item_id INTEGER NOT NULL);
        INSERT INTO items VALUES ({ITEM_ID}, 'Limited sneakers', {STOCK});
    """)
    conn.commit()
    conn.close()
    return path


def connect(path):
    # Each request handler gets its own connection, like a connection pool would hand out.
    # timeout = how long to wait for a lock held by another connection before raising "database is locked".
    return sqlite3.connect(path, timeout=10)


def _server(app, path, seed, server_id, next_user, gate, out):
    """One app server process: THREADS handlers pulling buyers off the shared line."""
    payments = PaymentProvider(seed * 100 + server_id)
    errors, results = [], []
    lock = threading.Lock()

    def handler():
        conn = connect(path)
        gate.wait()  # every handler on every server starts at exactly 12:00:00
        while True:
            with next_user.get_lock():
                user_id = next_user.value
                next_user.value += 1
            if user_id > BUYERS:
                break
            try:
                ok = app.buy(conn, payments, user_id, ITEM_ID)
                with lock:
                    results.append((user_id, ok))
            except Exception as e:  # noqa: BLE001 - report anything that escapes buy()
                with lock:
                    errors.append(f"user {user_id}: {type(e).__name__}: {e}")
                try:
                    conn.rollback()
                except sqlite3.Error:
                    pass
        conn.close()

    threads = [threading.Thread(target=handler) for _ in range(THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    out.put((errors, results, payments.charged, payments.refunded))


def run_sale(app, seed=0):
    """Fires BUYERS purchase attempts at app.buy() from SERVERS processes. Returns a report dict."""
    if "fork" not in multiprocessing.get_all_start_methods():
        raise SystemExit("Lab 02 runs 4 server processes via fork(), which needs Linux, macOS or WSL.")
    path = create_db()
    ctx = multiprocessing.get_context("fork")
    next_user = ctx.Value("i", 1)
    gate = ctx.Barrier(SERVERS * THREADS)
    out = ctx.Queue()
    start = time.perf_counter()
    procs = [ctx.Process(target=_server, args=(app, path, seed, i, next_user, gate, out)) for i in range(SERVERS)]
    for p in procs:
        p.start()
    parts = [out.get() for _ in procs]
    for p in procs:
        p.join()
    elapsed = time.perf_counter() - start

    conn = sqlite3.connect(path)
    stock = conn.execute("SELECT stock FROM items WHERE id = ?", (ITEM_ID,)).fetchone()[0]
    order_users = [u for (u,) in conn.execute("SELECT user_id FROM orders")]
    conn.close()
    return {
        "elapsed": elapsed,
        "stock": stock,
        "orders": order_users,
        "errors": [e for p in parts for e in p[0]],
        "told_success": [u for p in parts for u, ok in p[1] if ok],
        "charged": [u for p in parts for u in p[2]],
        "refunded": [u for p in parts for u in p[3]],
    }
