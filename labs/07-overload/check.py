"""Grades the RequestQueue: useful work during overload, fast recovery, no harm when healthy."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl, ms, percentile  # noqa: E402
import server  # noqa: E402

app = load_impl(HERE)
check = Checker("Lab 07: overload")
r = server.simulate(app)
normal, spike, after = (server.phase_stats(r, p) for p in ("normal", "spike", "after"))
spike_p99 = percentile(spike["latencies"], 99) if spike["latencies"] else float("inf")

check.expect(normal["ok_fraction"] >= 0.99, "healthy traffic is untouched: >= 99% ok before the spike",
             f"{normal['ok_fraction']:.1%}")
check.expect(spike["ok_rate"] >= 0.75 * server.CAPACITY,
             f"during the spike, goodput stays >= 75% of capacity ({0.75 * server.CAPACITY:.0f}/s)",
             f"{spike['ok_rate']:.0f}/s")
check.expect(spike_p99 <= 0.250, "during the spike, requests that succeed are fast (p99 <= 250ms)", ms(spike_p99))
check.expect(after["ok_fraction"] >= 0.95, "the server recovers as soon as the spike ends: >= 95% ok after",
             f"{after['ok_fraction']:.1%}")
check.expect(r["wasted"] <= 0.02 * max(1, r["processed"]), "<= 2% of work is done for clients who already gave up",
             f"{r['wasted']} of {r['processed']}")
check.done()
