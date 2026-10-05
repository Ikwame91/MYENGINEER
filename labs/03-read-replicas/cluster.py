"""A primary database with asynchronously replicated read replicas (provided; don't edit).

Every write gets a log sequence number (LSN). Replicas apply the log in order, after a delay.
Like Postgres's pg_current_wal_lsn() / pg_last_wal_replay_lsn() or MySQL GTIDs, you can ask
any node how far along it is.
"""

import collections
import random
import threading
import time


class Node:
    def __init__(self, name):
        self.name = name
        self._data = {}            # key -> (value, lsn that wrote it)
        self._applied_lsn = 0
        self._lock = threading.Lock()
        self.reads = 0

    @property
    def applied_lsn(self):
        """Every write with LSN <= this is visible on this node."""
        return self._applied_lsn

    def read(self, key):
        """Returns the value of key on this node (None if absent)."""
        with self._lock:
            self.reads += 1
            entry = self._data.get(key)
        return entry[0] if entry else None

    def _apply(self, lsn, key, value):
        with self._lock:
            self._data[key] = (value, lsn)
            self._applied_lsn = lsn

    def _version(self, key):  # used by the harness to grade staleness, not by app code
        entry = self._data.get(key)
        return entry[1] if entry else 0


class Primary(Node):
    def __init__(self):
        super().__init__("primary")
        self._write_lock = threading.Lock()
        self._subscribers = []
        self._history = {}         # (key, value) -> lsn; used by the harness for grading
        self.alive = True

    def write(self, key, value):
        """Commits the write and returns its LSN. Replication to replicas is asynchronous."""
        if not self.alive:
            raise ConnectionError("primary is down")
        with self._write_lock:
            lsn = self._applied_lsn + 1
            self._history[(key, value)] = lsn
            self._apply(lsn, key, value)
            now = time.monotonic()
            for subscriber in self._subscribers:
                subscriber.put((now, lsn, key, value))
        return lsn

    @property
    def current_lsn(self):
        return self._applied_lsn


class Replica(Node):
    """Applies the primary's log in order, `lag()` seconds after each write committed."""

    def __init__(self, name, primary, lag):
        super().__init__(name)
        self._lag = lag
        self._queue = collections.deque()
        self._ready = threading.Condition()
        self._stopped = False
        primary._subscribers.append(self)
        threading.Thread(target=self._replay, daemon=True).start()

    def put(self, entry):
        with self._ready:
            self._queue.append(entry)
            self._ready.notify()

    def stop(self):
        with self._ready:
            self._stopped = True
            self._ready.notify()

    def _replay(self):
        while True:
            with self._ready:
                while not self._queue and not self._stopped:
                    self._ready.wait()
                if self._stopped:
                    return
                committed_at, lsn, key, value = self._queue[0]
            delay = committed_at + self._lag() - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            with self._ready:
                if self._stopped:
                    return
                self._queue.popleft()
            self._apply(lsn, key, value)


class Cluster:
    def __init__(self, seed=0):
        rng = random.Random(seed)
        self.primary = Primary()
        start = time.monotonic()

        def steady():                      # a healthy replica: 10-60ms behind
            return rng.uniform(0.010, 0.060)

        def spiky():                       # healthy, except while someone's analytics query
            phase = (time.monotonic() - start) % 3.0   # blocks replay: 1.5s behind, 1s of every 3s
            return 1.5 if 1.5 < phase < 2.5 else rng.uniform(0.010, 0.060)

        self.replicas = [Replica("replica-1", self.primary, steady),
                         Replica("replica-2", self.primary, spiky)]

    @property
    def nodes(self):
        return [self.primary, *self.replicas]

    def shutdown(self):
        for r in self.replicas:
            r.stop()


class Session:
    """One logged-in user's browser session. `state` is yours: store whatever you need in it."""

    def __init__(self, user_id):
        self.user_id = user_id
        self.state = {}
