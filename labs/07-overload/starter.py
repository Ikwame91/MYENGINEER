"""
The request queue between the server's network listener and its worker threads.

You may change anything in this file, but keep the class name and method signatures.
Read the docstring at the top of server.py first.
"""

import queue


class RequestQueue:
    def __init__(self):
        self._queue = queue.Queue()

    def offer(self, request):
        """Called by the listener for every incoming request. Return False to reject it right away."""
        self._queue.put(request)
        return True

    def take(self, timeout):
        """Called by idle workers. Return the next request to process, or None if there's nothing
        to do within `timeout` seconds."""
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None
