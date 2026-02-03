from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from src.core.protocols.driver_protocol import DriverProtocol


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


@dataclass(kw_only=True)
class Job(ABC):
    scheduled_time: datetime
    expires_at: datetime
    success_message: str
    failure_message: str
    status: JobStatus = JobStatus.PENDING
    duration: int = 0

    @abstractmethod
    def execute(self, driver: DriverProtocol) -> bool:
        pass

    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at

    def should_execute(self) -> bool:
        return (
            self.status == JobStatus.PENDING
            and not self.is_expired()
            and datetime.now() >= self.scheduled_time
        )
