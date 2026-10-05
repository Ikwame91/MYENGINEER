"""Routes keys in a *fresh process* and prints the result as JSON (used to simulate a deploy)."""

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(os.path.dirname(HERE)))

from labkit import load_impl  # noqa: E402

app = load_impl(HERE)
nodes, count = json.loads(sys.argv[1]), int(sys.argv[2])
router = app.ShardRouter(nodes)
print(json.dumps([router.node_for(f"user:{i}") for i in range(count)]))
