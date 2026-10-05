"""An API server with a fixed worker pool, fed by an open-loop traffic generator (provided; don't edit).

  traffic generator --offer(request)--> [ your RequestQueue ] --take(timeout)--> 4 worker threads

* Each request takes a worker SERVICE_TIME seconds, so capacity is WORKERS / SERVICE_TIME = 200 req/s.
* offer() returning False means the request is rejected immediately (the client gets a fast 503).
* Clients give up after CLIENT_TIMEOUT. Work finished after that is wasted: nobody is listening.
* request.arrived and request.deadline are time.monotonic() timestamps.
"""

import random
import threading
import time

WORKERS = 4
SERVICE_TIME = 0.020
CLIENT_TIMEOUT = 0.5
CAPACITY = WORKERS / SERVICE_TIME
PHASES = [("normal", 2.0, 120), ("spike", 4.0, 300), ("after", 3.0, 120)]   # (name, seconds, req/s)


class Request:
    __slots__ = ("id", "phase", "arrived", "deadline", "started", "finished", "outcome")

    def __init__(self, rid, phase, arrived):
        self.id = rid
        self.phase = phase
        self.arrived = arrived
        self.deadline = arrived + CLIENT_TIMEOUT
        self.started = self.finished = None
        self.outcome = None          # "ok" | "rejected" | "timeout"


def simulate(app, seed=0):
    rng = random.Random(seed)
    queue = app.RequestQueue()
    requests, processed = [], []
    lock = threading.Lock()
    done = threading.Event()
    start = time.monotonic()

    def worker():
        while not done.is_set():
            req = queue.take(timeout=0.05)
            if req is None:
                continue
            req.started = time.monotonic()
            time.sleep(SERVICE_TIME)                      # the actual work
            req.finished = time.monotonic()
            with lock:
                processed.append(req)

    workers = [threading.Thread(target=worker) for _ in range(WORKERS)]
    for w in workers:
        w.start()

    # Open-loop arrivals: clients don't wait for the server before sending more (like the real internet).
    t, rid = start, 0
    for name, seconds, rate in PHASES:
        phase_end = t + seconds
        while True:
            t += rng.expovariate(rate)
            if t >= phase_end:
                t = phase_end
                break
            delay = t - time.monotonic()
            if delay > 0:
                time.sleep(delay)
            rid += 1
            req = Request(rid, name, t)
            requests.append(req)
            if not queue.offer(req):
                req.outcome = "rejected"

    time.sleep(CLIENT_TIMEOUT + 0.05)    # every outstanding client has now given up
    done.set()
    for w in workers:
        w.join()

    for req in requests:
        if req.outcome is None:
            req.outcome = "ok" if req.finished is not None and req.finished <= req.deadline else "timeout"
    wasted = sum(1 for req in processed if req.finished > req.deadline)
    return dict(start=start, requests=requests, processed=len(processed), wasted=wasted)


def phase_stats(result, phase):
    reqs = [r for r in result["requests"] if r.phase == phase]
    seconds = next(s for name, s, _ in PHASES if name == phase)
    ok = [r for r in reqs if r.outcome == "ok"]
    return dict(
        offered=len(reqs),
        ok=len(ok),
        ok_rate=len(ok) / seconds,
        ok_fraction=len(ok) / max(1, len(reqs)),
        rejected=sum(r.outcome == "rejected" for r in reqs),
        timeout=sum(r.outcome == "timeout" for r in reqs),
        latencies=[r.finished - r.arrived for r in ok],
    )
