"""Drives app.py's RequestQueue through normal traffic, a 1.5x-capacity spike, and the aftermath.

    python3 run.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, ms, percentile, red, table, yellow  # noqa: E402
import server  # noqa: E402

app = load_impl(HERE)
header(f"Capacity {server.CAPACITY:.0f} req/s ({server.WORKERS} workers x {server.SERVICE_TIME * 1000:.0f}ms). "
       f"Clients time out at {server.CLIENT_TIMEOUT * 1000:.0f}ms.")
print(dim("Phases: " + ", then ".join(f"{name} {rate} req/s for {s:.0f}s" for name, s, rate in server.PHASES)))
r = server.simulate(app)

print(bold("\nTimeline (per 0.5s, by arrival time):"))
rows, BUCKET = [], 0.5
total = sum(s for _, s, _ in server.PHASES)
for b in range(int(total / BUCKET)):
    lo, hi = r["start"] + b * BUCKET, r["start"] + (b + 1) * BUCKET
    reqs = [q for q in r["requests"] if lo <= q.arrived < hi]
    ok = [q for q in reqs if q.outcome == "ok"]
    timeouts = sum(q.outcome == "timeout" for q in reqs)
    rejected = sum(q.outcome == "rejected" for q in reqs)
    p99 = percentile([q.finished - q.arrived for q in ok], 99) if ok else None
    rows.append([f"{b * BUCKET:.1f}s", reqs[0].phase if reqs else "", len(reqs),
                 (green if len(ok) >= 0.9 * len(reqs) else red)(len(ok)),
                 yellow(rejected) if rejected else "0", red(timeouts) if timeouts else "0",
                 ms(p99) if p99 is not None else "-"])
table(["time", "phase", "arrived", "ok", "rejected (fast 503)", "timed out", "p99 of ok"], rows)

header("Summary by phase")
rows = []
for name, _, rate in server.PHASES:
    s = server.phase_stats(r, name)
    rows.append([name, f"{rate}/s", f"{s['ok_rate']:.0f}/s", f"{s['ok_fraction']:.0%}", s["rejected"], s["timeout"],
                 ms(percentile(s["latencies"], 99)) if s["latencies"] else "-"])
table(["phase", "offered", "goodput", "ok %", "rejected", "timed out", "p99 of ok"], rows)
print(f"\nwork done after the client had already given up: "
      f"{(red if r['wasted'] else green)(r['wasted'])} of {r['processed']} requests processed")
print(dim("Goodput = useful responses per second. The server was busy the whole time. Busy doing what?"))
