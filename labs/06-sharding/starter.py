"""
Shard router: decides which database shard owns each key.

Every service in the company imports this to find a user's data. You may change anything in
this file, but keep the class name and method signatures.
"""


class ShardRouter:
    def __init__(self, nodes):
        """nodes: shard names, e.g. ["db-0", "db-1", "db-2", "db-3"]."""
        self.nodes = list(nodes)

    def node_for(self, key):
        """The shard that owns `key` (a string like "user:123")."""
        return self.nodes[hash(key) % len(self.nodes)]

    def add_node(self, node):
        """A new shard joins (scale out). Keys that now belong to it get migrated to it."""
        self.nodes.append(node)

    def remove_node(self, node):
        """A shard is decommissioned. Its keys get migrated to the remaining shards."""
        self.nodes.remove(node)
