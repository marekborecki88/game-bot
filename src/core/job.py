from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Callable, Any, Optional, Dict

from src.core.task import Task


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"

#TODO: need refactor, different kind of jobs should extend Job class
@dataclass
class Job:
    task: Task
    scheduled_time: datetime
    expires_at: datetime
    status: JobStatus = JobStatus.PENDING
    # Optional metadata to carry auxiliary information (e.g. village_id) for executor/cleanup
    metadata: Optional[Dict[str, Any]] = None

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def should_execute(self) -> bool:
        return (
            self.status == JobStatus.PENDING
            and not self.is_expired()
            and datetime.now() >= self.scheduled_time
        )
