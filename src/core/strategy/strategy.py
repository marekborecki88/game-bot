from typing import Protocol

from src.config.config import HeroConfig, LogicConfig
from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState, Resources
from src.core.model.units import get_unit_by_name, get_units_for_tribe, Tribe
from src.core.job.job import Job


class Strategy(Protocol):

    def __init__(self, logic_config: LogicConfig, hero_config: HeroConfig):
        self.logic_config = logic_config
        self.hero_config = hero_config

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        """
            This method will calculate multiple factors to determine the best plan for develop defencive army.
            it will consider such factors as:
            - training troops
            - build military objects
            - current resources balance and production
            - merchants mobility and capacity
            - warehouse and granary capacity
            - residence and settlers training

        :param game_state:
        :param calculator:
        :return:
        """
        ...

    def estimate_total_attack(self, village_troops: dict[str, int]) -> int:
        """
        Calculate total attack points from all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :return: Total attack value
        """
        if not village_troops:
            return 0

        total_attack = 0
        for unit_name, quantity in village_troops.items():
            # Try to find the unit in all tribes
            unit = None
            for tribe in Tribe:
                unit = get_unit_by_name(unit_name, tribe)
                if unit:
                    break
            if unit:
                total_attack += unit.attack * quantity

        return total_attack

    def estimate_total_defense_infantry(self, village_troops: dict[str, int]) -> int:
        """
        Calculate total defense against infantry from all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :return: Total defense against infantry value
        """
        if not village_troops:
            return 0

        total_defense = 0
        for unit_name, quantity in village_troops.items():
            # Try to find the unit in all tribes
            unit = None
            for tribe in Tribe:
                unit = get_unit_by_name(unit_name, tribe)
                if unit:
                    break
            if unit:
                total_defense += unit.defense_vs_infantry * quantity

        return total_defense

    def estimate_total_defense_cavalry(self, village_troops: dict[str, int]) -> int:
        """
        Calculate total defense against cavalry from all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :return: Total defense against cavalry value
        """
        if not village_troops:
            return 0

        total_defense = 0
        for unit_name, quantity in village_troops.items():
            # Try to find the unit in all tribes
            unit = None
            for tribe in Tribe:
                unit = get_unit_by_name(unit_name, tribe)
                if unit:
                    break
            if unit:
                total_defense += unit.defense_vs_cavalry * quantity

        return total_defense

    def estimate_grain_consumption_per_hour(self, village_troops: dict[str, int]) -> int:
        """
        Calculate hourly grain consumption of all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :return: Total grain consumption per hour
        """
        if not village_troops:
            return 0

        total_consumption = 0
        for unit_name, quantity in village_troops.items():
            # Try to find the unit in all tribes
            unit = None
            for tribe in Tribe:
                unit = get_unit_by_name(unit_name, tribe)
                if unit:
                    break
            if unit:
                total_consumption += unit.grain_consumption * quantity

        return total_consumption

    def estimate_trainable_units_per_hour(self, village_tribe: Tribe, hourly_production: Resources) -> dict[str, int]:
        """
        Calculate how many units of each type can be trained per hour based on hourly resource production.
        For each unit type available for the tribe, calculate how many can be trained using only
        the hourly production rate (without consuming stored resources).

        :param village_tribe: The tribe of the village
        :param hourly_production: Hourly production of all resources
        :return: Dictionary mapping unit name to quantity trainable per hour
        """
        trainable_units: dict[str, int] = {}
        
        units = get_units_for_tribe(village_tribe)
        if not units:
            return trainable_units

        for unit in units:
            # Calculate how many units can be trained based on available resources
            units_trainable = hourly_production.count_how_many_can_be_made(unit.costs)
            if units_trainable > 0:
                trainable_units[unit.name] = units_trainable

        return trainable_units

    def estimate_potential_attack_per_hour(self, village_tribe: Tribe, hourly_production: Resources) -> int:
        """
        Calculate total attack points that could be produced per hour from hourly resource production.

        :param village_tribe: The tribe of the village
        :param hourly_production: Hourly production of all resources
        :return: Total attack value from units trainable per hour
        """
        trainable_units = self.estimate_trainable_units_per_hour(village_tribe, hourly_production)
        return self.estimate_total_attack(trainable_units)

    def estimate_potential_defense_infantry_per_hour(self, village_tribe: Tribe, hourly_production: Resources) -> int:
        """
        Calculate total defense against infantry that could be produced per hour from hourly resource production.

        :param village_tribe: The tribe of the village
        :param hourly_production: Hourly production of all resources
        :return: Total defense against infantry from units trainable per hour
        """
        trainable_units = self.estimate_trainable_units_per_hour(village_tribe, hourly_production)
        return self.estimate_total_defense_infantry(trainable_units)

    def estimate_potential_defense_cavalry_per_hour(self, village_tribe: Tribe, hourly_production: Resources) -> int:
        """
        Calculate total defense against cavalry that could be produced per hour from hourly resource production.

        :param village_tribe: The tribe of the village
        :param hourly_production: Hourly production of all resources
        :return: Total defense against cavalry from units trainable per hour
        """
        trainable_units = self.estimate_trainable_units_per_hour(village_tribe, hourly_production)
        return self.estimate_total_defense_cavalry(trainable_units)