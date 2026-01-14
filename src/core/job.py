from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Any


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


@dataclass
class Job:
    task: Callable[[], Any]
    scheduled_time: datetime
    expires_at: datetime
    status: JobStatus = JobStatus.PENDING

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def should_execute(self) -> bool:
        return (
            self.status == JobStatus.PENDING
            and not self.is_expired()
            and datetime.now() >= self.scheduled_time
        )
