"""Exercises app.py's ShardRouter through a company's worth of operational events.

    python3 run.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import bold, dim, green, header, load_impl, red, yellow  # noqa: E402
import sim  # noqa: E402

app = load_impl(HERE)
ROW_BYTES = 2_000            # avg size of one user's data
PROD_KEYS = 500_000_000      # production has 500M users


def tb(fraction):
    return f"{fraction * PROD_KEYS * ROW_BYTES / 1e12:.1f} TB"


def pct(x, bad):
    return (red if x > bad else green)(f"{x:.1%}")


header(f"1. Day one: {len(sim.KEYS):,} users on {len(sim.NODES)} shards")
router = app.ShardRouter(sim.NODES)
before, seconds = sim.timed_routing(router)
counts, ratio = sim.balance(before)
for node, n in sorted(counts.items()):
    print(f"  {node}: {n:>7,} keys  " + dim("#" * int(40 * n / max(counts.values()))))
print(f"  busiest shard / average: {(red if ratio > 1.25 else green)(f'{ratio:.2f}x')}   "
      + dim(f"(routing {len(sim.KEYS):,} keys took {seconds:.2f}s)"))

header("2. Tuesday's deploy: every service restarts (new processes)")
mismatch = sim.restart_mismatch()
print(f"  keys the restarted service looks for on a DIFFERENT shard than before: {pct(mismatch, 0)}")
if mismatch:
    print(red("  -> users 'disappear' after every deploy; writes land on shards nobody reads."))

header("3. Black Friday: add a 5th shard")
router.add_node("db-4")
after_add = sim.route(router)
moved, pointless = sim.movement(before, after_add, new_node="db-4")
_, ratio5 = sim.balance(after_add)
print(f"  keys that must be migrated: {pct(moved, 0.25)}   (ideal: ~{1 / 5:.0%}, only the new shard's share)")
print(f"  keys moved between OLD shards (pure waste): {(red if pointless else green)(f'{pointless:,}')}")
print(f"  at production scale that migration copies {yellow(tb(moved))}")
print(f"  busiest shard / average after: {(red if ratio5 > 1.25 else green)(f'{ratio5:.2f}x')}")

header("4. db-1's disk is failing: decommission it")
router.remove_node("db-1")
after_remove = sim.route(router)
moved_r, pointless_r = sim.movement(after_add, after_remove, removed_node="db-1")
print(f"  keys that must be migrated: {pct(moved_r, 0.25)}   (ideal: only db-1's keys, ~{1 / 5:.0%})")
print(f"  keys moved that were never on db-1 (pure waste): {(red if pointless_r else green)(f'{pointless_r:,}')}")

header("5. A celebrity joins (traffic, not keys)")
load = sim.hot_key_traffic(app.ShardRouter(sim.NODES))
total = sum(load.values())
for node, n in sorted(load.items()):
    print(f"  {node}: {n / total:>6.1%} of requests  " + dim("#" * int(60 * n / total)))
print(dim("  Even perfect key balance can't fix this. Why not? What would you do? (see NOTES after you pass)"))
