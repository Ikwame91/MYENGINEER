"""Grades ShardRouter on stability, balance, and how much data each topology change moves."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, HERE)

from labkit import Checker, load_impl  # noqa: E402
import sim  # noqa: E402

app = load_impl(HERE)
check = Checker("Lab 06: sharding")

router = app.ShardRouter(sim.NODES)
before, seconds = sim.timed_routing(router)
_, ratio4 = sim.balance(before)
mismatch = sim.restart_mismatch()

router.add_node("db-4")
after_add = sim.route(router)
moved_add, pointless_add = sim.movement(before, after_add, new_node="db-4")
_, ratio5 = sim.balance(after_add)

router.remove_node("db-1")
after_remove = sim.route(router)
moved_rm, pointless_rm = sim.movement(after_add, after_remove, removed_node="db-1")

valid = set(after_remove) <= {"db-0", "db-2", "db-3", "db-4"}

check.expect(mismatch == 0, "same key -> same shard in every process (survives restarts and deploys)",
             f"{mismatch:.1%} of keys move on restart")
check.expect(ratio4 <= 1.25, "balanced on 4 shards: busiest <= 1.25x average", f"{ratio4:.2f}x")
check.expect(ratio5 <= 1.25, "balanced after adding a 5th shard: busiest <= 1.25x average", f"{ratio5:.2f}x")
check.expect(moved_add <= 0.25, "adding a shard migrates <= 25% of keys", f"{moved_add:.1%}")
check.expect(pointless_add == 0, "adding a shard only moves keys TO the new shard", f"{pointless_add:,} wasted moves")
check.expect(moved_rm <= 0.25, "removing a shard migrates <= 25% of keys", f"{moved_rm:.1%}")
check.expect(pointless_rm == 0, "removing a shard only moves keys that were ON it", f"{pointless_rm:,} wasted moves")
check.expect(valid, "keys only route to shards that exist")
check.expect(seconds <= 5.0, "routes 200k keys in under 5s", f"{seconds:.2f}s")
check.done()
