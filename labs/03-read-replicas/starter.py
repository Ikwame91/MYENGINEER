"""
Profile service.

Reads were moved to replicas last quarter to take load off the primary. You may change anything
in this file, but keep the method signatures.

Useful facts about the cluster (see cluster.py):
  cluster.primary.write(key, value) -> lsn      commits on the primary, returns its log position
  cluster.primary.current_lsn                   latest committed LSN
  node.read(key)                                read from the primary or any replica
  node.applied_lsn                              every write with LSN <= this is visible on that node
  cluster.replicas                              list of replica nodes
  session.state                                 a dict you can use per user session
"""

import random


class ProfileService:
    def __init__(self, cluster):
        self.cluster = cluster

    def update_name(self, session, user_id, name):
        """Called when a user saves their display name. The browser then reloads the profile page."""
        self.cluster.primary.write(f"user:{user_id}:name", name)

    def get_name(self, session, user_id):
        """Called on every page view that shows a name (one's own, or someone else's)."""
        replica = random.choice(self.cluster.replicas)
        return replica.read(f"user:{user_id}:name")
