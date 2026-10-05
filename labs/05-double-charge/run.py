"""Runs a batch of real checkouts through app.py against a local HTTP payment provider, then audits the ledger.

    python3 run.py
"""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, red, table, yellow  # noqa: E402
import provider  # noqa: E402

app = load_impl(HERE)
header(f"{provider.ORDERS} checkouts, {provider.WORKERS} at a time, against the payment provider (localhost HTTP)")
r = provider.run_checkouts(app)
charges = Counter(order_id for order_id, _ in r["charges"])
attempts = Counter(order_id for _, order_id, _, _ in r["attempts"])
outcome_kinds = Counter(o[0] for o in r["outcomes"].values())

double = {o: n for o, n in charges.items() if n > 1}
declined = [o["id"] for o in r["orders"] if o["card"] == provider.DECLINED_CARD]
uncharged = [o["id"] for o in r["orders"] if o["card"] != provider.DECLINED_CARD and not charges[o["id"]]]
charged_but_failed = [o for o in charges if r["outcomes"][o][0] != "ok"]

print(bold("What checkout() reported:  ") + ", ".join(f"{k}: {v}" for k, v in outcome_kinds.items()))
print(bold("What actually happened:    ") +
      f"{len(r['charges'])} charges for {len(charges)} orders  ·  "
      + (red(f"{len(double)} orders charged more than once") if double else green("no double charges")))
if uncharged:
    print(red(f"{len(uncharged)} valid orders never got charged") + dim(f"  e.g. {uncharged[:3]}"))
if charged_but_failed:
    print(red(f"{len(charged_but_failed)} customers were charged, but checkout() said it failed")
          + dim(f"  e.g. {charged_but_failed[:3]}"))
print(f"requests sent to provider: {len(r['attempts'])} for {provider.ORDERS} orders")
print(f"declined cards: {len(declined)}, requests for them: "
      + yellow(str(sum(attempts[o] for o in declined))))

header("Attempts timeline (provider's view): one row per 100ms")
buckets = Counter()
for t, _, status, _ in r["attempts"]:
    buckets[(int(t * 10), status)] += 1
statuses = sorted({s for _, s in buckets})
rows = []
for b in range(max((k[0] for k in buckets), default=0) + 1):
    row = [f"{b / 10:.1f}s"]
    for s in statuses:
        n = buckets[(b, s)]
        row.append((red if s in (503, 409, 402) and n else str)(n) if n else dim("."))
    rows.append(row)
table(["time", *(str(s) for s in statuses)], rows)
print(dim(f"The provider had an outage from {provider.OUTAGE[0]}s to {provider.OUTAGE[1]}s."))

if double:
    header("A double-charged order, step by step (provider's log)")
    oid = next(iter(double))
    for t, order_id, status, prompt in r["attempts"]:
        if order_id == oid:
            print(f"  t={t:.3f}s  {oid}  -> {status}" + ("" if prompt else dim("  (response sent ~1s later)")))
    print(dim("What did the client see for each of those? (Hint: TIMEOUT is 0.5s.)"))
