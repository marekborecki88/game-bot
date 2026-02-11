from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState, ResourceType, Building, BuildingType, BuildingCost
from src.core.model.village import Village


class DefendArmyPolicy:
    # Mapping between economy building types and their corresponding resource types
    BUILDING_TO_RESOURCE: dict[BuildingType, ResourceType] = {
        BuildingType.WOODCUTTER: ResourceType.LUMBER,
        BuildingType.SAWMILL: ResourceType.LUMBER,
        BuildingType.CLAY_PIT: ResourceType.CLAY,
        BuildingType.BRICKYARD: ResourceType.CLAY,
        BuildingType.IRON_MINE: ResourceType.IRON,
        BuildingType.IRON_FOUNDRY: ResourceType.IRON,
        BuildingType.CROPLAND: ResourceType.CROP,
        BuildingType.GRAIN_MILL: ResourceType.CROP,
        BuildingType.BAKERY: ResourceType.CROP,
    }

    def __init__(self, logic_config, hero_config):
        self.logic_config = logic_config
        self.hero_config = hero_config

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator):
        """
            This method will calculate multiple factors to determine the best plan for develop defencive army.
            it will consider such factors as:
            - training troops
            - build military objects
            - current resources balance and production
            - merchants mobility and capacity
            - warehouse and granary capacity

        :param game_state:
        :param calculator:
        :return:
        """
        # self.economy_upgrades(game_state, calculator)



    def all_possible_economy_upgrades(
        self, villages: list[Village], calculator: TravianCalculator
    ) -> dict[ResourceType, list[tuple[Village, Building, BuildingCost, int]]]:
        """
        Return all possible economy building upgrades grouped by resource type.

        Returns:
            Dictionary where keys are ResourceType and values are lists of tuples
            containing (village, building, upgrade_cost).
        """
        upgrades_by_resource: dict[ResourceType, list[tuple[Village, Building, BuildingCost, int]]] = {
            ResourceType.LUMBER: [],
            ResourceType.CLAY: [],
            ResourceType.IRON: [],
            ResourceType.CROP: [],
        }

        for village in villages:
            # Check existing buildings that can be upgraded
            for building in village.buildings:
                if not building.has_max_level and building.type in self.BUILDING_TO_RESOURCE:
                    resource_type = self.BUILDING_TO_RESOURCE[building.type]
                    upgrade_cost = calculator.get_building_details(building.type.gid, building.level + 1)
                    improvement = calculator.production_improvement_by_upgrade_level(building.level + 1)
                    upgrades_by_resource[resource_type].append((village, building, upgrade_cost, improvement))

            # Check future buildings that can be built
            future_buildings = [
                BuildingType.SAWMILL,
                BuildingType.BRICKYARD,
                BuildingType.IRON_FOUNDRY,
                BuildingType.GRAIN_MILL,
                BuildingType.BAKERY,
            ]
            for future_building in future_buildings:
                if village.can_build(future_building):
                    resource_type = self.BUILDING_TO_RESOURCE[future_building]
                    upgrade_cost = calculator.get_building_details(future_building.gid, 1)
                    improvement = village.production_per_hour(resource_type) * 0.05
                    new_building = Building(id=None, level=0, type=future_building)
                    upgrades_by_resource[resource_type].append((village, new_building, upgrade_cost, improvement.__int__()))

        return upgrades_by_resource

    def economy_upgrades(self, game_state, calculator):
        total_resources = game_state.calculate_global_resources
        villages = game_state.villages
        possible_upgrades = self.all_possible_economy_upgrades(villages, calculator)
        ...





