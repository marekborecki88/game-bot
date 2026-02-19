import logging

from src.domain.config import LogicConfig, HeroConfig, Strategy as StrategyType
from src.domain.calculator.calculator import TravianCalculator
from src.domain.model.game_state import GameState
from src.domain.strategy.defend_army_policy import DefendArmyPolicy
from src.domain.strategy.strategy import Strategy

logger = logging.getLogger(__name__)


def choose_strategy(logic_config: LogicConfig, hero_config: HeroConfig) -> Strategy:
    match logic_config.strategy:
        case StrategyType.DEFEND_ARMY:
            return DefendArmyPolicy(logic_config, hero_config)
        case _:
            raise ValueError(f"Unknown strategy: {logic_config.strategy}")


class LogicEngine:
    # TODO: if game_state is not provided at construction, it must be passed to planning methods
    def __init__(self, logic_config: LogicConfig, hero_config: HeroConfig, game_state: GameState | None = None):
        # game_state may be provided at construction or passed later to planning methods
        self.game_state: GameState | None = game_state
        speed = logic_config.speed
        self.calculator = TravianCalculator(speed=speed)
        self.strategy = choose_strategy(logic_config, hero_config)

    def plan(self, game_state: GameState):
        return self.strategy.plan_jobs(game_state, self.calculator)

