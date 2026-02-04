from typing import Protocol

from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState
from src.core.job.job import Job


class Strategy(Protocol):

    def __init__(self, minimum_storage_capacity_in_hours: int):
        self.minimum_storage_capacity_in_hours = minimum_storage_capacity_in_hours
        # self.calculator: TravianCalculator | None = None

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        ...