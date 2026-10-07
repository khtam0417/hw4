"""In-memory request limits (Homework 4, Problem 12).

SlidingWindow counts events per key over the last few seconds. main.py uses one to cap chat messages per
client address, and auth.py one to cap failed logins per email and address. The counts live in memory, so
a restart clears them, and a few hundred bytes per active key is all they hold.
"""

from __future__ import annotations

import time
from collections import deque

MAX_KEYS = 10_000  # past this many keys, keys with no recent events are dropped


class SlidingWindow:
    def __init__(self, limit: int, seconds: float) -> None:
        self.limit = limit
        self.seconds = seconds
        self._events: dict[str, deque[float]] = {}

    def _recent(self, key: str) -> deque[float]:
        now = time.monotonic()
        if len(self._events) > MAX_KEYS:
            self._events = {k: v for k, v in self._events.items() if v and now - v[-1] < self.seconds}
        events = self._events.setdefault(key, deque())
        while events and now - events[0] >= self.seconds:
            events.popleft()
        return events

    def full(self, key: str) -> bool:
        """Whether the key has reached the limit within the window."""
        return len(self._recent(key)) >= self.limit

    def add(self, key: str) -> None:
        self._recent(key).append(time.monotonic())

    def hit(self, key: str) -> bool:
        """Count one event if the key is under the limit. Returns False, counting nothing, if it isn't."""
        events = self._recent(key)
        if len(events) >= self.limit:
            return False
        events.append(time.monotonic())
        return True

    def clear(self, key: str) -> None:
        self._events.pop(key, None)
