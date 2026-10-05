"""Runs ~100 concurrent request handlers through app.py's cache and shows what the DB experiences.

    python3 run.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, ms, percentile, red, yellow  # noqa: E402
import backend  # noqa: E402

app = load_impl(HERE)
header(f"{backend.THREADS} handlers for {backend.SECONDS:.0f}s; 90% of traffic on {backend.HOT_PRODUCTS} hot products; "
       f"DB capacity {backend.CAPACITY} concurrent queries")
r = backend.simulate(app)
db = r["db"]

# Concurrent DB queries over time, as a bar chart in 100ms buckets.
print(bold("DB queries in flight (peak per 200ms):"))
buckets = {}
for t, load in db.timeline:
    b = int((t - r["start"]) * 5)
    buckets[b] = max(buckets.get(b, 0), load)
for b in range(int(backend.SECONDS * 5)):
    load = buckets.get(b, 0)
    bar = "#" * min(load, 70) + ("+" if load > 70 else "")
    color = red if load > backend.CAPACITY * 2.5 else yellow if load > backend.CAPACITY else green
    print(f"  {b / 5:4.1f}s {load:>4} {color(bar)}")

header("Summary")
p50, p99 = percentile(r["latencies"], 50), percentile(r["latencies"], 99)
print(f"requests: {len(r['latencies']):,}   DB queries: {db.calls:,}   peak DB concurrency: "
      f"{(red if db.peak_inflight > 2.5 * backend.CAPACITY else green)(db.peak_inflight)}")
print(f"request latency: p50 {ms(p50)}  p99 {(red if p99 > 0.2 else green)(ms(p99))}")
print(f"data age served: p99 {percentile(r['ages'], 99):.2f}s  max {max(r['ages']):.2f}s  (TTL {r['ttl']}s)")
if r["errors"]:
    print(red(f"errors: {len(r['errors'])}, e.g. {r['errors'][0]}"))
print(dim("\nLook at the timing of the spikes. What happens every TTL seconds?"))
