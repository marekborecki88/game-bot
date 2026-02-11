from typing import Protocol

from src.config.config import HeroConfig, LogicConfig
from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState
from src.core.job.job import Job


class Strategy(Protocol):

    def __init__(self, logic_config: LogicConfig, hero_config: HeroConfig):
        self.logic_config = logic_config
        self.hero_config = hero_config

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        ...