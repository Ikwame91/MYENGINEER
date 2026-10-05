"""Runs several flash sales and audits every invariant the business cares about."""

import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl  # noqa: E402
import shop  # noqa: E402

RUNS = 3
app = load_impl(HERE)
check = Checker(f"Lab 02: the flash sale ({RUNS} sales; a race may hide in any one)")

reports = [shop.run_sale(app, seed) for seed in range(RUNS)]


def every(predicate):
    return all(predicate(r) for r in reports)


def worst(f):
    return max(f(r) for r in reports)


check.expect(every(lambda r: not r["errors"]), "no exceptions escape buy() (no 'database is locked')",
             f"max errors in one sale: {worst(lambda r: len(r['errors']))}")
check.expect(every(lambda r: len(r["orders"]) <= shop.STOCK), "never oversold: orders <= stock",
             f"max orders: {worst(lambda r: len(r['orders']))}")
check.expect(every(lambda r: r["stock"] >= 0), "stock never negative")
check.expect(every(lambda r: r["stock"] + len(r["orders"]) == shop.STOCK),
             f"books balance: stock left + orders == {shop.STOCK}")
check.expect(every(lambda r: r["stock"] == 0), "everything sells: no units leaked by declined cards",
             f"max stock left: {worst(lambda r: r['stock'])}")
check.expect(every(lambda r: Counter(r["charged"]) - Counter(r["refunded"]) == Counter(r["orders"])),
             "every charged customer has exactly one order, and every order was paid for")
check.expect(every(lambda r: sorted(r["told_success"]) == sorted(r["orders"])),
             "buy() returned True exactly for the customers who got an order")
check.done()
