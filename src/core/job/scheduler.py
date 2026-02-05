import heapq
from datetime import datetime

from src.core.job.job import Job


class ScheduledJobQueue:
    def __init__(self) -> None:
        self._heap: list[tuple[datetime, int, Job]] = []
        self._sequence: int = 0

    def push(self, job: Job) -> None:
        self._sequence += 1
        heapq.heappush(self._heap, (job.scheduled_time, self._sequence, job))

    def pop_due(self, now: datetime) -> Job | None:
        if not self._heap:
            return None
        scheduled_time, _, job = self._heap[0]
        if scheduled_time > now:
            return None
        heapq.heappop(self._heap)
        return job

    def peek_next_time(self) -> datetime | None:
        if not self._heap:
            return None
        return self._heap[0][0]

    def __len__(self) -> int:
        return len(self._heap)
