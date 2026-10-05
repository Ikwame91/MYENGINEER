"""Instrumented 'production' environment for the lab (provided)."""

import random
import time

import data

NETWORK_RTT = 0.0005      # the database lives on another machine: every statement costs a round trip
REQUEST_TIMEOUT = 2.0     # the load balancer kills requests that take longer than this


class Instrumented:
    """Wraps a connection: records statements, measures work, simulates network latency, enforces timeouts.

    "work" counts thousands of SQLite VM instructions: a rough, machine-independent measure of
    how many rows a query had to touch. Latency hides problems on small data; work does not.
    """

    def __init__(self, conn):
        self.conn = conn
        self.statements = []
        self.work = 0
        self.deadline = float("inf")
        conn.set_trace_callback(self._trace)
        conn.set_progress_handler(self._progress, 1000)

    def _trace(self, sql):
        self.statements.append(sql)
        time.sleep(NETWORK_RTT)

    def _progress(self):
        self.work += 1
        return time.perf_counter() > self.deadline  # non-zero aborts the query

    def call(self, fn, *args):
        """Run one 'request'. Returns (result, seconds); result is TimeoutError if it was killed."""
        self.statements, self.work = [], 0
        start = time.perf_counter()
        self.deadline = start + REQUEST_TIMEOUT
        try:
            result = fn(self.conn, *args)
        except Exception as e:  # sqlite3.OperationalError('interrupted')
            if "interrupt" not in str(e):
                raise
            result = TimeoutError()
        finally:
            self.deadline = float("inf")
        return result, time.perf_counter() - start


def boot(app):
    conn = data.connect()
    app.migrate(conn)
    conn.commit()
    return Instrumented(conn)


def workload(seed=7):
    """The arguments real traffic uses for each endpoint."""
    rng = random.Random(seed)
    return {
        "recent_orders": [(rng.randint(1, data.USERS),) for _ in range(40)],
        "daily_revenue": [(f"2025-{rng.randint(1, 12):02d}-{rng.randint(1, 28):02d}",) for _ in range(15)],
        "top_customers": [(c,) for c in ["NG", "GH", "US", "KE", "CA"]],
    }
