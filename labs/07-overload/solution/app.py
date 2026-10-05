"""Reference solution: bounded queue + load shedding + deadline-aware dequeue. Read solution/NOTES.md."""

import queue
import time

# Little's law: items in queue = arrival rate x time in queue. At our 200 req/s capacity, a 20-deep
# queue means at most ~100ms of waiting, well inside the client's 500ms timeout.
MAX_QUEUE = 20
SERVICE_TIME = 0.020   # if less than this is left before the deadline, the client will be gone


class RequestQueue:
    def __init__(self):
        self._queue = queue.Queue(maxsize=MAX_QUEUE)

    def offer(self, request):
        try:
            self._queue.put_nowait(request)     # never block the listener
            return True
        except queue.Full:
            return False                        # shed load: a fast 503 beats a slow timeout

    def take(self, timeout):
        give_up = time.monotonic() + timeout
        while True:
            remaining = give_up - time.monotonic()
            if remaining <= 0:
                return None
            try:
                request = self._queue.get(timeout=remaining)
            except queue.Empty:
                return None
            if request.deadline - time.monotonic() >= SERVICE_TIME:
                return request
            # The client will have hung up before we could answer: skip it, don't waste a worker on it.
