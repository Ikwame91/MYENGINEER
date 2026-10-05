"""Verifies app.py: correct results, no full scans of `orders`, no N+1, bounded work per request."""

import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl  # noqa: E402
import harness  # noqa: E402

# Max work (thousands of VM steps) per request. A full scan of orders is ~900k-1700k.
WORK_BUDGET = {"recent_orders": 50, "daily_revenue": 50, "top_customers": 1000}

app = load_impl(HERE)
db = harness.boot(app)
check = Checker("Lab 01: the slow dashboard")

# Ground truth, computed in plain Python from a full read of the tables.
users = {uid: (name, country) for uid, name, country in db.conn.execute("SELECT id, name, country FROM users")}
by_user, paid_by_day, paid_by_user = defaultdict(list), defaultdict(int), defaultdict(int)
for oid, uid, amount, status, created in db.conn.execute(
        "SELECT id, user_id, amount_cents, status, created_at FROM orders"):
    by_user[uid].append((oid, amount, status, created))
    if status == "paid":
        paid_by_day[created[:10]] += amount
        paid_by_user[uid] += amount


def expected(endpoint, arg):
    if endpoint == "recent_orders":
        return sorted(by_user[arg], key=lambda o: (o[3], o[0]), reverse=True)[:20]
    if endpoint == "daily_revenue":
        return paid_by_day[arg]
    ranked = sorted(((users[u][0], t) for u, t in paid_by_user.items() if users[u][1] == arg),
                    key=lambda r: (-r[1], r[0]))
    return ranked[:10]


timeouts, wrong, full_scans, sorted_in_temp = set(), [], set(), False
max_statements, max_work = defaultdict(int), defaultdict(int)
for endpoint, calls in harness.workload().items():
    for (arg,) in calls:
        result, _ = db.call(getattr(app, endpoint), arg)
        max_statements[endpoint] = max(max_statements[endpoint], len(db.statements))
        max_work[endpoint] = max(max_work[endpoint], db.work)
        for sql in {s for s in db.statements if s.lstrip().upper().startswith("SELECT")}:
            for row in db.conn.execute("EXPLAIN QUERY PLAN " + sql):
                if re.match(r"SCAN (TABLE )?orders\b", row[3]):
                    full_scans.add(endpoint)
                if endpoint == "recent_orders" and "TEMP B-TREE" in row[3]:
                    sorted_in_temp = True
        if isinstance(result, TimeoutError):
            timeouts.add(endpoint)
            break
        got = [tuple(r) for r in result] if isinstance(result, list) else result
        if got != expected(endpoint, arg):
            wrong.append(f"{endpoint}({arg!r})")

check.expect(not timeouts, "no request hits the 2s timeout", ", ".join(sorted(timeouts)))
check.expect(not wrong, "every endpoint returns correct results", ", ".join(wrong[:3]))
for endpoint in WORK_BUDGET:
    check.expect(endpoint not in full_scans, f"{endpoint} never scans the whole orders table")
check.expect(not sorted_in_temp, "recent_orders reads rows already in order (no temp B-tree sort)")
check.expect(max_statements["top_customers"] <= 2, "top_customers uses at most 2 round trips (no N+1)",
             f"max seen: {max_statements['top_customers']}")
for endpoint, budget in WORK_BUDGET.items():
    check.expect(max_work[endpoint] <= budget and endpoint not in timeouts,
                 f"{endpoint} stays within its work budget ({budget:,}k)",
                 f"max seen: {max_work[endpoint]:,}k" + (" before timeout" if endpoint in timeouts else ""))
check.done()
