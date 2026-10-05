"""Grades ProductCache under concurrent load: protects the DB, stays fast, stays fresh."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl, ms, percentile  # noqa: E402
import backend  # noqa: E402

MAX_AGE = 1.5   # product requirement: never show a price older than this (seconds)
MAX_INFLIGHT = int(2.5 * backend.CAPACITY)  # brief bursts past capacity are survivable; 100 is not
app = load_impl(HERE)
check = Checker("Lab 04: the cache stampede")
r = backend.simulate(app)
db = r["db"]
p99 = percentile(r["latencies"], 99)
max_age = max(r["ages"]) if r["ages"] else float("inf")
# Each product needs roughly one load per TTL; allow for jitter and for a few misses.
query_budget = int(backend.PRODUCTS * (backend.SECONDS / (0.75 * r["ttl"]) + 1)) if r["ttl"] else 0

check.expect(not r["errors"], "no errors, every request gets the product it asked for",
             r["errors"][0] if r["errors"] else "")
check.expect(db.peak_inflight <= MAX_INFLIGHT,
             f"peak DB concurrency stays within {MAX_INFLIGHT} (DB capacity is {backend.CAPACITY})",
             f"peak: {db.peak_inflight}")
check.expect(p99 <= 0.200, "request p99 latency within 200ms", ms(p99))
check.expect(db.calls <= query_budget, f"DB queries within budget (~1 per product per TTL: {query_budget})",
             f"{db.calls} queries")
check.expect(max_age <= MAX_AGE, f"no product served older than {MAX_AGE}s", f"oldest: {max_age:.2f}s")
check.expect(len(r["latencies"]) > 10_000, "throughput: handlers aren't stuck waiting",
             f"{len(r['latencies']):,} requests served")
check.done()
