from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import uuid

from src.domain.protocols.driver_protocol import DriverProtocol


class JobStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    EXPIRED = "expired"


@dataclass(kw_only=True)
class Job(ABC):
    job_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    scheduled_time: datetime
    success_message: str
    failure_message: str
    status: JobStatus = JobStatus.PENDING
    duration: int = 0

    @abstractmethod
    def execute(self, driver: DriverProtocol) -> bool:
        pass

    def should_execute(self) -> bool:
        return (
            self.status == JobStatus.PENDING
            and datetime.now() >= self.scheduled_time
        )
