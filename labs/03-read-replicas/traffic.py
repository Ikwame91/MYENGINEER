"""Simulated user traffic against ProfileService, graded read by read (provided)."""

import random
import threading
import time

from cluster import Cluster, Session

USERS = 40
SECONDS = 6.0
BUCKET = 0.5


def key(user_id):
    return f"user:{user_id}:name"


def simulate(app, seconds=SECONDS, seed=0):
    cluster = Cluster(seed)
    for u in range(USERS):
        cluster.primary.write(key(u), f"user{u}-v0")
    while any(r.applied_lsn < cluster.primary.current_lsn for r in cluster.replicas):
        time.sleep(0.01)
    for node in cluster.nodes:
        node.reads = 0

    service = app.ProfileService(cluster)
    history = cluster.primary._history
    lock = threading.Lock()
    start = time.monotonic()
    buckets = [dict(reads=0, stale_own=0, time_travel=0, lag={}) for _ in range(int(seconds / BUCKET) + 1)]
    totals = dict(reads=0, own_after_write=0, stale_own=0, time_travel=0, errors=[], examples=[], latencies=[])

    def timed_get(session, user_id):
        t0 = time.perf_counter()
        value = service.get_name(session, user_id)
        elapsed = time.perf_counter() - t0
        with lock:
            totals["latencies"].append(elapsed)
        return value

    def grade(session, my_write_lsn, last_seen, user_id, value, after_write):
        k = key(user_id)
        version = history.get((k, value), -1)
        b = buckets[min(len(buckets) - 1, int((time.monotonic() - start) / BUCKET))]
        stale = user_id == session.user_id and version < my_write_lsn
        travel = version < last_seen.get(k, 0)
        last_seen[k] = max(last_seen.get(k, 0), version)
        with lock:
            totals["reads"] += 1
            b["reads"] += 1
            totals["own_after_write"] += after_write
            if stale:
                totals["stale_own"] += 1
                b["stale_own"] += 1
                if len(totals["examples"]) < 3:
                    totals["examples"].append(
                        f"user {user_id} saved a new name, then saw {value!r} (written at LSN {version}, "
                        f"their save was LSN {my_write_lsn})")
            if travel:
                totals["time_travel"] += 1
                b["time_travel"] += 1

    def user(user_id):
        rng = random.Random(seed * 1000 + user_id)
        session = Session(user_id)
        my_write_lsn, last_seen, version = 0, {}, 0
        while time.monotonic() - start < seconds:
            try:
                roll = rng.random()
                if roll < 0.05:
                    version += 1
                    name = f"user{user_id}-v{version}"
                    service.update_name(session, user_id, name)
                    my_write_lsn = history[(key(user_id), name)]
                    grade(session, my_write_lsn, last_seen, user_id,
                          timed_get(session, user_id), True)       # the reload after "Save"
                elif roll < 0.40:
                    grade(session, my_write_lsn, last_seen, user_id, timed_get(session, user_id), False)
                else:
                    other = rng.randrange(USERS)
                    grade(session, my_write_lsn, last_seen, other, timed_get(session, other), False)
            except Exception as e:  # noqa: BLE001
                with lock:
                    totals["errors"].append(f"{type(e).__name__}: {e}")
                time.sleep(0.05)
            time.sleep(rng.uniform(0.005, 0.020))

    def monitor():
        while time.monotonic() - start < seconds:
            b = buckets[min(len(buckets) - 1, int((time.monotonic() - start) / BUCKET))]
            for r in cluster.replicas:
                b["lag"][r.name] = max(b["lag"].get(r.name, 0), cluster.primary.current_lsn - r.applied_lsn)
            time.sleep(0.02)

    threads = [threading.Thread(target=user, args=(u,)) for u in range(USERS)] + [threading.Thread(target=monitor)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    cluster.shutdown()

    reads_by_node = {n.name: n.reads for n in cluster.nodes}
    totals["reads_by_node"] = reads_by_node
    totals["primary_share"] = reads_by_node["primary"] / max(1, sum(reads_by_node.values()))
    totals["buckets"] = buckets[: int(seconds / BUCKET)]
    totals["replicas"] = [r.name for r in cluster.replicas]
    return totals


def failover_drill(seconds_before_crash=2.2, writers=20):
    """Heavy write traffic, then the primary dies. Promote the most up-to-date replica."""
    cluster = Cluster(seed=1)
    acked, lock = [], threading.Lock()
    stop = time.monotonic() + seconds_before_crash

    def writer(w):
        n = 0
        while time.monotonic() < stop:
            n += 1
            lsn = cluster.primary.write(f"cart:{w}", f"item-{n}")
            with lock:
                acked.append(lsn)       # the client was told "Saved!"
            time.sleep(0.002)

    threads = [threading.Thread(target=writer, args=(w,)) for w in range(writers)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    cluster.primary.alive = False                      # power loss
    cluster.shutdown()                                 # replicas stop receiving the log
    applied = {r.name: r.applied_lsn for r in cluster.replicas}
    promoted = max(cluster.replicas, key=lambda r: r.applied_lsn)
    lost = sum(1 for lsn in acked if lsn > promoted.applied_lsn)
    return dict(acked=len(acked), primary_lsn=cluster.primary.current_lsn, applied=applied,
                promoted=promoted.name, lost=lost)
