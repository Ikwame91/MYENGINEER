"""Simulates a few minutes of traffic against app.py and shows what users experience.

    python3 run.py            latency + statements per request, per endpoint
    python3 run.py --explain  also print the query plan of every distinct statement
"""

import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, header, load_impl, ms, percentile, red, table, yellow  # noqa: E402
import harness  # noqa: E402

app = load_impl(HERE)
db = harness.boot(app)

header("Traffic replay (each statement pays a 0.5ms network round trip; requests time out at 2s)")
rows, seen = [], {}
for endpoint, calls in harness.workload().items():
    fn = getattr(app, endpoint)
    times, counts, work, timeouts = [], [], [], 0
    for args in calls:
        result, seconds = db.call(fn, *args)
        times.append(seconds)
        counts.append(len(db.statements))
        work.append(db.work)
        timeouts += isinstance(result, TimeoutError)
        for sql in db.statements[:3]:
            seen.setdefault(re.sub(r"\b\d+\b|'[^']*'", "?", sql), sql)
        if timeouts and seconds >= harness.REQUEST_TIMEOUT:
            break  # no point hammering a dead endpoint
    rows.append([
        endpoint,
        len(times),
        ms(percentile(times, 50)),
        ms(percentile(times, 99)),
        max(counts),
        f"{percentile(work, 50):,}k",
        red(f"{timeouts} TIMEOUT") if timeouts else "0",
    ])
table(["endpoint", "requests", "p50", "p99", "statements/req (max)", "work/req (p50)", "timeouts"], rows)
print(dim("work = thousands of database VM steps per request (roughly: how many rows it touched)"))

if "--explain" in sys.argv:
    header("Query plans (EXPLAIN QUERY PLAN) for each distinct statement")
    for sql in seen.values():
        if not sql.lstrip().upper().startswith("SELECT"):
            continue
        print(bold(sql))
        for _, parent, _, detail in db.conn.execute("EXPLAIN QUERY PLAN " + sql):
            line = f"   {'  ' if parent else ''}{detail}"
            print(yellow(line) if detail.startswith("SCAN") or "TEMP B-TREE" in detail else line)
        print()
else:
    print(dim("\nTip: python3 run.py --explain shows how SQLite executes each query."))
