from typing import Protocol

from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState
from src.core.job.job import Job


class Strategy(Protocol):

    def __init__(self):
        self.calculator = None

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        ...