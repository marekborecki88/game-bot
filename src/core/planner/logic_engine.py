import logging

from src.config.config import LogicConfig, Strategy as StrategyType
from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState
from src.core.strategy.Strategy import Strategy
from src.core.strategy.balanced_economic_growth import BalancedEconomicGrowth

logger = logging.getLogger(__name__)


def choose_strategy(logic_config: LogicConfig) -> Strategy:
    match logic_config.strategy:
        case StrategyType.BALANCED_ECONOMIC_GROWTH:
            return BalancedEconomicGrowth()
        case StrategyType.DEFEND_ARMY:
            raise ValueError("Not implemented yet: Strategy.DEFEND_ARMY")
        case _:
            raise ValueError(f"Unknown strategy: {logic_config.strategy}")


class LogicEngine:
    # TODO: if game_state is not provided at construction, it must be passed to planning methods
    def __init__(self, logic_config: LogicConfig, game_state: GameState | None = None):
        # game_state may be provided at construction or passed later to planning methods
        self.game_state: GameState | None = game_state
        speed = game_state.account.server_speed if game_state else 1.0
        self.calculator = TravianCalculator(speed=speed)
        self.strategy = choose_strategy(logic_config)

    def plan(self, game_state: GameState):
        return self.strategy.plan_jobs(game_state, self.calculator)

    # TODO: need refactor
    def unfreeze_village_queue(self, village_id: int) -> None:
        if not self.game_state:
            return
        for v in self.game_state.villages:
            if v.id == village_id:
                v.is_queue_building_freeze = False
                return
