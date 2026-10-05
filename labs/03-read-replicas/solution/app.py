"""Reference solution. Read solution/NOTES.md for the reasoning."""

import random
import time

CATCH_UP_WAIT = 0.1   # how long a read may wait for a replica before falling back to the primary


class ProfileService:
    def __init__(self, cluster):
        self.cluster = cluster

    def update_name(self, session, user_id, name):
        lsn = self.cluster.primary.write(f"user:{user_id}:name", name)
        self._observe(session, lsn)

    def get_name(self, session, user_id):
        node = self._node_for(session)
        # Note the node's position *before* reading: whatever we read is at least that fresh,
        # so any node at or past it can serve this session next without going back in time.
        seen = node.applied_lsn
        value = node.read(f"user:{user_id}:name")
        self._observe(session, seen)
        return value

    # The session carries a watermark: the newest LSN it has written or observed.
    # In a web app this lives in the session cookie or token.

    def _observe(self, session, lsn):
        session.state["min_lsn"] = max(session.state.get("min_lsn", 0), lsn)

    def _node_for(self, session):
        need = session.state.get("min_lsn", 0)
        deadline = time.monotonic() + CATCH_UP_WAIT
        while True:
            fresh = [r for r in self.cluster.replicas if r.applied_lsn >= need]
            if fresh:
                return random.choice(fresh)
            if time.monotonic() >= deadline:
                return self.cluster.primary   # every replica is too far behind: pay for a primary read
            time.sleep(0.002)
