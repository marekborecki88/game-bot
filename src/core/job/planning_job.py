from dataclasses import dataclass
from typing import Protocol

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


class PlanningContext(Protocol):
    def run_planning(self) -> None:
        ...


@dataclass(kw_only=True)
class PlanningJob(Job):
    planning_context: PlanningContext

    def execute(self, driver: DriverProtocol) -> bool:
        self.planning_context.run_planning()
        return True
