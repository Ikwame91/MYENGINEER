"""Runs the flash sale against app.py and audits the books.

    python3 run.py           one sale
    python3 run.py --runs 5  several sales (race conditions are nondeterministic!)
"""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, red, table  # noqa: E402
import shop  # noqa: E402

app = load_impl(HERE)
runs = int(sys.argv[sys.argv.index("--runs") + 1]) if "--runs" in sys.argv else 1

header(f"Flash sale: {shop.STOCK} units, {shop.BUYERS} buyers, {shop.SERVERS} app servers x {shop.THREADS} handler threads")
rows = []
for seed in range(runs):
    r = shop.run_sale(app, seed)
    net_charged = Counter(r["charged"]) - Counter(r["refunded"])
    oversold = len(r["orders"]) - shop.STOCK
    rows.append([
        seed + 1,
        f"{r['elapsed']:.2f}s",
        r["stock"],
        len(r["orders"]),
        red(f"+{oversold}") if oversold > 0 else green(str(oversold)),
        sum(net_charged.values()),
        len(r["errors"]),
    ])
table(["run", "duration", "stock left", "orders", "oversold", "customers charged", "errors"], rows)
if r["errors"]:
    print(red(f"\nSample errors ({len(r['errors'])} total):"))
    for e in r["errors"][:5]:
        print("  " + e)
print(dim(f"\nInvariant: stock left + orders == {shop.STOCK}, and charged customers == customers with orders."))
print(bold("Question:") + " how did stock and orders disagree, when every buy() reads the stock first?")
