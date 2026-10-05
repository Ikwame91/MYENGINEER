"""Grades ProfileService on consistency guarantees and on the cost of providing them."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl, ms, percentile  # noqa: E402
import traffic  # noqa: E402

app = load_impl(HERE)
check = Checker("Lab 03: read replicas")
r = traffic.simulate(app)
p99 = percentile(r["latencies"], 99)

check.expect(not r["errors"], "no errors", r["errors"][0] if r["errors"] else "")
check.expect(r["stale_own"] == 0, "read-your-writes: nobody sees their old name after saving",
             f"{r['stale_own']} stale own reads")
check.expect(r["time_travel"] == 0, "monotonic reads: nobody sees data older than something they already saw",
             f"{r['time_travel']} time-travel reads")
check.expect(r["primary_share"] <= 0.25, "the primary serves at most 25% of reads",
             f"{r['primary_share']:.0%}")
check.expect(p99 <= 0.150, "get_name p99 latency within 150ms", ms(p99))
check.done()
