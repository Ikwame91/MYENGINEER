"""Runs simulated users against app.py's ProfileService and grades every read.

    python3 run.py              6 seconds of traffic, with a timeline
    python3 run.py --failover   a different drill: the primary dies under write load
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, ms, percentile, red, table, yellow  # noqa: E402
import traffic  # noqa: E402

if "--failover" in sys.argv:
    header("Failover drill: 20 clients writing; the primary loses power at t=2.2s")
    r = traffic.failover_drill()
    print(f"Writes acknowledged to clients ('Saved!'): {r['acked']:,}   (primary was at LSN {r['primary_lsn']:,})")
    for name, lsn in r["applied"].items():
        print(f"  {name} had applied up to LSN {lsn:,}  ({r['primary_lsn'] - lsn:,} behind)")
    print(f"Promoted {bold(r['promoted'])} (the most up-to-date replica) to primary.")
    print(red(bold(f"{r['lost']:,} acknowledged writes no longer exist.")) +
          " Every one of those users saw 'Saved!'.")
    print(dim("\nThink: what would it cost to make this number zero? Who pays that cost, and when?"))
    sys.exit(0)

app = load_impl(HERE)
header(f"{traffic.USERS} users browsing for {traffic.SECONDS:.0f}s "
       "(5% of actions: save a new name, then reload the page)")
r = traffic.simulate(app)

rows = []
for i, b in enumerate(r["buckets"]):
    lag = "  ".join(f"{name}: {b['lag'].get(name, 0):>4}" for name in r["replicas"])
    rows.append([f"{i * traffic.BUCKET:.1f}s", b["reads"],
                 red(b["stale_own"]) if b["stale_own"] else "0",
                 red(b["time_travel"]) if b["time_travel"] else "0", lag])
table(["time", "reads", "stale own reads", "time-travel reads", "replica lag (writes behind)"], rows)

header("Summary")
reads = r["reads"]
print(f"reads: {reads:,}   own reads right after saving: {r['own_after_write']:,}")
print(f"stale own reads (saved, reloaded, saw the OLD name): "
      f"{(red if r['stale_own'] else green)(r['stale_own'])}")
print(f"time-travel reads (saw a value OLDER than one seen before): "
      f"{(red if r['time_travel'] else green)(r['time_travel'])}")
share = r["primary_share"]
print(f"reads served by primary: {(yellow if share > 0.25 else green)(f'{share:.0%}')}  "
      + dim(str(r["reads_by_node"])))
p99 = percentile(r["latencies"], 99)
print(f"get_name latency: p50 {ms(percentile(r['latencies'], 50))}  p99 {(yellow if p99 > 0.15 else green)(ms(p99))}")
for e in r["examples"]:
    print(dim("  e.g. " + e))
if r["errors"]:
    print(red(f"errors: {len(r['errors'])}, e.g. {r['errors'][0]}"))
print(dim("\nConstraints: the primary is sized for writes and can take at most 25% of reads;"
          "\npage views have a 150ms p99 budget for get_name."))
