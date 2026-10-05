"""Audits checkout() against the provider's ledger: money, honesty, and politeness under failure."""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl  # noqa: E402
import provider  # noqa: E402

RUNS = 2
app = load_impl(HERE)
check = Checker(f"Lab 05: the double charge ({RUNS} batches of {provider.ORDERS} checkouts)")

double, missing, dishonest, wrong_kind, retried_decline, unexpected, storm, total = 0, 0, 0, 0, 0, [], 0, 0
for seed in range(RUNS):
    r = provider.run_checkouts(app, seed)
    charges = Counter(o for o, _ in r["charges"])
    charge_ids = {}
    for o, cid in r["charges"]:
        charge_ids.setdefault(o, set()).add(cid)
    total += len(r["attempts"])
    storm = max(storm, sum(1 for t, *_ in r["attempts"] if provider.OUTAGE[0] <= t < provider.OUTAGE[1]))
    told_declined = set()   # orders whose client promptly received a 402
    for t, o, status, prompt in sorted(r["attempts"]):
        retried_decline += o in told_declined
        if status == 402 and prompt:
            told_declined.add(o)
    for order in r["orders"]:
        oid = order["id"]
        kind, detail, _ = r["outcomes"][oid]
        if kind not in ("ok", "CardDeclined", "PaymentFailed"):
            unexpected.append(f"{oid}: {kind}: {detail}")
        double += charges[oid] > 1
        if order["card"] == provider.DECLINED_CARD:
            wrong_kind += kind != "CardDeclined"
        else:
            missing += charges[oid] == 0 or kind != "ok"
        dishonest += (charges[oid] > 0) != (kind == "ok") or (kind == "ok" and detail not in charge_ids.get(oid, ()))

check.expect(not unexpected, "checkout() only returns a charge id or raises CardDeclined / PaymentFailed",
             unexpected[0] if unexpected else "")
check.expect(double == 0, "nobody is charged twice", f"{double} orders double-charged")
check.expect(missing == 0, "every valid order ends up charged (survives timeouts, 503s and the outage)",
             f"{missing} valid orders not charged or not reported ok")
check.expect(dishonest == 0, "checkout()'s answer matches reality (charged <=> returned that charge id)",
             f"{dishonest} mismatches")
check.expect(wrong_kind == 0, "declined cards raise CardDeclined", f"{wrong_kind} didn't")
check.expect(retried_decline == 0, "a declined card is never retried (402 is final)",
             f"{retried_decline} requests after the client received a 402")
check.expect(storm <= 120, "no retry storm: <= 120 requests during the 0.5s outage",
             f"{storm} requests during the outage")
check.expect(total <= RUNS * provider.ORDERS * 3, "total requests stay under 3 per order",
             f"{total / (RUNS * provider.ORDERS):.1f} per order")
check.done()
