from typing import Protocol

from src.config.config import HeroConfig, LogicConfig
from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState, Resources, BuildingType, Tribe
from src.core.model.village import Village
from src.core.model.units import get_unit_by_name, get_units_for_tribe
from src.core.job.job import Job
from src.core.model.model import ResourceType


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

    def get_missing_critical_military_buildings(self, village: Village) -> list[tuple[BuildingType, int]]:
        """
        Identify missing critical military buildings in a village.
        
        Returns military buildings that are not yet constructed, sorted by priority:
        1. BARRACKS (always highest - trains infantry)
        2. STABLE (trains cavalry)
        3. WORKSHOP (trains siege units)

        :param village: The village to analyze
        :return: List of (BuildingType, priority_index) tuples, sorted by priority
        """
        critical_buildings = [
            (BuildingType.BARRACKS, 0),
            (BuildingType.STABLE, 1),
            (BuildingType.WORKSHOP, 2),
        ]
        
        missing_buildings: list[tuple[BuildingType, int]] = []
        
        for building_type, priority in critical_buildings:
            existing = village.get_building(building_type)
            if existing is None:
                missing_buildings.append((building_type, priority))
        
        return missing_buildings

    def estimate_village_development_stage(self, village: Village) -> str:
        """
        Determine the development stage of a village based on resource pit and production building levels.
        
        Stages:
        - 'early': Any primary resource pit (woodcutter/clay_pit/iron_mine) is below level 5
        - 'mid': All primary resource pits are level 5+, but not yet advanced
        - 'advanced': At least one resource type is fully developed:
          * Lumber: all woodcutters at level 10 AND sawmill at level 5+
          * Clay: all clay pits at level 10 AND brickyard at level 5+
          * Iron: all iron mines at level 10 AND iron foundry at level 5+

        :param village: The village to analyze
        :return: Development stage as string: 'early', 'mid', or 'advanced'
        """
        # Get resource pit levels by type
        pit_levels = {
            ResourceType.LUMBER: [],
            ResourceType.CLAY: [],
            ResourceType.IRON: [],
            ResourceType.CROP: [],
        }
        
        for pit in village.resource_pits:
            pit_levels[pit.type].append(pit.level)
        
        # Check for early stage: any primary resource pit < 5
        for resource_type in [ResourceType.LUMBER, ResourceType.CLAY, ResourceType.IRON]:
            if pit_levels[resource_type]:
                min_level = min(pit_levels[resource_type])
                if min_level < 5:
                    return 'early'
        
        # Check for advanced stage - combinations of primary + secondary buildings
        # Lumber: woodcutter (primary) + sawmill (secondary)
        sawmill = village.get_building(BuildingType.SAWMILL)
        sawmill_level = sawmill.level if sawmill else 0
        if pit_levels[ResourceType.LUMBER] and min(pit_levels[ResourceType.LUMBER]) == 10 and sawmill_level >= 5:
            return 'advanced'
        
        # Clay: clay_pit (primary) + brickyard (secondary)
        brickyard = village.get_building(BuildingType.BRICKYARD)
        brickyard_level = brickyard.level if brickyard else 0
        if pit_levels[ResourceType.CLAY] and min(pit_levels[ResourceType.CLAY]) == 10 and brickyard_level >= 5:
            return 'advanced'
        
        # Iron: iron_mine (primary) + iron_foundry (secondary)
        iron_foundry = village.get_building(BuildingType.IRON_FOUNDRY)
        iron_foundry_level = iron_foundry.level if iron_foundry else 0
        if pit_levels[ResourceType.IRON] and min(pit_levels[ResourceType.IRON]) == 10 and iron_foundry_level >= 5:
            return 'advanced'
        
        # Otherwise mid stage
        return 'mid'

    def estimate_military_building_priority(
        self, village: Village, tribe: Tribe
    ) -> dict[BuildingType, float]:
        """
        Calculate priority coefficient for each military building in a village.
        
        Higher coefficient = higher priority to build/upgrade.
        Considers:
        - Missing critical buildings (barracks, stable, workshop)
        - Village development stage
        - Current building levels

        :param village: The village to analyze
        :param tribe: The tribe of the village (unused parameter, kept for interface compatibility)
        :return: Dictionary mapping BuildingType to priority coefficient (0-100 scale)
        """
        priorities: dict[BuildingType, float] = {
            BuildingType.BARRACKS: 0.0,
            BuildingType.STABLE: 0.0,
            BuildingType.WORKSHOP: 0.0,
        }
        
        # Get village development stage
        dev_stage = self.estimate_village_development_stage(village)
        
        # Determine development stage multiplier
        stage_multiplier = {
            'early': 1.2,      # Early stage: boost military building priority
            'mid': 1.0,        # Mid stage: balanced priority
            'advanced': 0.9,   # Advanced: slightly lower priority (focus on upgrades)
        }.get(dev_stage, 1.0)
        
        # === BARRACKS Priority ===
        barracks = village.get_building(BuildingType.BARRACKS)
        if barracks is None:
            # Missing barracks = highest priority
            priorities[BuildingType.BARRACKS] = 40.0 * stage_multiplier
        else:
            # Existing barracks: priority based on level upgrade potential
            upgrade_priority = max(0.0, (20 - barracks.level) / 20.0) * 10.0
            priorities[BuildingType.BARRACKS] = upgrade_priority * stage_multiplier
        
        # === STABLE Priority ===
        stable = village.get_building(BuildingType.STABLE)
        
        if stable is None:
            # Missing stable = high priority
            priorities[BuildingType.STABLE] = 30.0 * stage_multiplier
        else:
            # Existing stable: priority based on level upgrade potential
            upgrade_priority = max(0.0, (20 - stable.level) / 20.0) * 10.0
            priorities[BuildingType.STABLE] = upgrade_priority * stage_multiplier
        
        # === WORKSHOP Priority ===
        workshop = village.get_building(BuildingType.WORKSHOP)
        
        if workshop is None:
            # Missing workshop: lower priority than barracks/stable
            priorities[BuildingType.WORKSHOP] = 20.0 * stage_multiplier
        else:
            # Existing workshop: priority based on level
            upgrade_priority = max(0.0, (20 - workshop.level) / 20.0) * 8.0
            priorities[BuildingType.WORKSHOP] = upgrade_priority * stage_multiplier
        
        return priorities

    def estimate_resource_production_proportions(
        self, planned_units: dict[str, int]
    ) -> dict[ResourceType, float]:
        """
        Calculate target resource production proportions based on planned unit costs.
        
        Analyzes the costs of planned units and returns proportional production targets
        for each resource type. Used for balancing production towards unit training needs.
        
        Example: If Legionnaires cost lumber:clay:iron:crop = 120:100:150:30,
        the returned proportions would reflect these ratios.

        :param planned_units: Dictionary mapping unit name to quantity (e.g., {"Legionnaire": 100})
        :return: Dictionary mapping ResourceType to proportion (sum = 1.0)
        """
        if not planned_units:
            # Default balanced proportions
            return {
                ResourceType.LUMBER: 0.25,
                ResourceType.CLAY: 0.25,
                ResourceType.IRON: 0.25,
                ResourceType.CROP: 0.25,
            }

        # Calculate total resource requirements for planned units
        total_lumber = 0
        total_clay = 0
        total_iron = 0
        total_crop = 0
        
        for unit_name, quantity in planned_units.items():
            unit = None
            for tribe in Tribe:
                unit = get_unit_by_name(unit_name, tribe)
                if unit:
                    break
            if unit:
                total_lumber += unit.costs.lumber * quantity
                total_clay += unit.costs.clay * quantity
                total_iron += unit.costs.iron * quantity
                total_crop += unit.costs.crop * quantity
        
        total = total_lumber + total_clay + total_iron + total_crop
        if total == 0:
            # Fallback to balanced proportions
            return {
                ResourceType.LUMBER: 0.25,
                ResourceType.CLAY: 0.25,
                ResourceType.IRON: 0.25,
                ResourceType.CROP: 0.25,
            }
        
        return {
            ResourceType.LUMBER: total_lumber / total,
            ResourceType.CLAY: total_clay / total,
            ResourceType.IRON: total_iron / total,
            ResourceType.CROP: total_crop / total,
        }