"""Reference solution: consistent hashing with virtual nodes. Read solution/NOTES.md."""

import bisect
import hashlib

VNODES = 256   # points per shard on the ring; more points = smoother balance, bigger ring


def _hash(text):
    # A stable hash: same input, same output, in every process, on every machine, forever.
    # (Python's built-in hash() of a str is randomized per process.)
    return int.from_bytes(hashlib.md5(text.encode()).digest()[:8], "big")


class ShardRouter:
    def __init__(self, nodes):
        self._ring = []     # sorted [(point, node)]
        self._points = []   # just the points, for bisect
        for node in nodes:
            self.add_node(node)

    @property
    def nodes(self):
        return sorted({node for _, node in self._ring})

    def node_for(self, key):
        # Walk clockwise from the key's position to the first shard point.
        i = bisect.bisect(self._points, _hash(key)) % len(self._ring)
        return self._ring[i][1]

    def add_node(self, node):
        for v in range(VNODES):
            bisect.insort(self._ring, (_hash(f"{node}#{v}"), node))
        self._points = [p for p, _ in self._ring]

    def remove_node(self, node):
        self._ring = [(p, n) for p, n in self._ring if n != node]
        self._points = [p for p, _ in self._ring]
