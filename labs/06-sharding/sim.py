"""Measurements shared by run.py and check.py (provided)."""

import json
import os
import random
import subprocess
import sys
import time
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
NODES = ["db-0", "db-1", "db-2", "db-3"]
KEYS = [f"user:{i}" for i in range(200_000)]


def route(router, keys=KEYS):
    return [router.node_for(k) for k in keys]


def balance(placement):
    counts = Counter(placement)
    return counts, max(counts.values()) / (len(placement) / len(counts))


def restart_mismatch(count=20_000):
    """Route the same keys in two fresh processes (as two deploys would) and compare."""
    results = []
    for seed in ("1", "2"):
        env = dict(os.environ, PYTHONHASHSEED=seed)
        out = subprocess.run([sys.executable, os.path.join(HERE, "probe.py"), json.dumps(NODES), str(count)],
                             env=env, capture_output=True, text=True, check=True)
        results.append(json.loads(out.stdout))
    return sum(a != b for a, b in zip(*results)) / count


def movement(before, after, new_node=None, removed_node=None):
    moved = [(b, a) for b, a in zip(before, after) if b != a]
    pointless = sum(1 for b, a in moved
                    if (new_node is not None and a != new_node) or (removed_node is not None and b != removed_node))
    return len(moved) / len(before), pointless


def timed_routing(router):
    start = time.perf_counter()
    placement = route(router)
    return placement, time.perf_counter() - start


def hot_key_traffic(router, requests=200_000, seed=0):
    """One celebrity account gets 15% of all reads; everyone else is evenly spread."""
    rng = random.Random(seed)
    load = Counter()
    for _ in range(requests):
        if rng.random() < 0.15:
            key = "user:celebrity"
        else:
            key = KEYS[rng.randrange(len(KEYS))]
        load[router.node_for(key)] += 1
    return load
