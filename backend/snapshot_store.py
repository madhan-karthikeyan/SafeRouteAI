"""
Ring buffer for replay timeline.

Stores the last N snapshots in memory so the frontend can scrub
backward in time. Thread-safe via a simple lock.
"""

import threading
from .models import Snapshot

MAX_SNAPSHOTS = 600


class SnapshotStore:
    def __init__(self, max_snapshots: int = MAX_SNAPSHOTS):
        self._buffer: list[Snapshot] = []
        self._max = max_snapshots
        self._lock = threading.Lock()

    def push(self, snapshot: Snapshot):
        with self._lock:
            self._buffer.append(snapshot)
            if len(self._buffer) > self._max:
                self._buffer = self._buffer[-self._max:]

    def get_all(self) -> list[Snapshot]:
        with self._lock:
            return list(self._buffer)

    def get_range(self, from_ms: int, to_ms: int) -> list[Snapshot]:
        with self._lock:
            return [s for s in self._buffer if from_ms <= s.t <= to_ms]

    def latest(self) -> Snapshot | None:
        with self._lock:
            return self._buffer[-1] if self._buffer else None

    def clear(self):
        with self._lock:
            self._buffer.clear()
