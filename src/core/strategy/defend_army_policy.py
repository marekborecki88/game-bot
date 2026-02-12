from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState, ResourceType, Building, BuildingType, BuildingCost, Resources
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

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list:
        """
        Plan jobs to develop defensive army considering current troop strength and resources.
        Analyzes military metrics across all villages and returns job recommendations.
        
        :param game_state: Current game state with villages and hero info
        :param calculator: Travian calculator for time and cost calculations
        :return: List of recommended jobs to execute
        """
        jobs = []
        
        # Analyze military strength across all villages
        for village in game_state.villages:
            # Calculate current military metrics
            total_attack = self.estimate_total_attack(village.troops)
            total_defense_infantry = self.estimate_total_defense_infantry(village.troops)
            total_defense_cavalry = self.estimate_total_defense_cavalry(village.troops)
            grain_consumption = self.estimate_grain_consumption_per_hour(village.troops)
            
            # Get training building levels
            barracks = village.get_building(BuildingType.BARRACKS)
            stable = village.get_building(BuildingType.STABLE)
            barracks_level = barracks.level if barracks else 0
            stable_level = stable.level if stable else 0
            
            # Create Resources object with hourly production
            hourly_production = Resources(
                lumber=village.lumber_hourly_production,
                clay=village.clay_hourly_production,
                iron=village.iron_hourly_production,
                crop=village.crop_hourly_production
            )
            
            # Calculate potential production per hour based on hourly resources
            potential_attack_per_hour = self.estimate_potential_attack_per_hour(
                village.tribe,
                hourly_production
            )
            potential_defense_infantry_per_hour = self.estimate_potential_defense_infantry_per_hour(
                village.tribe,
                hourly_production
            )
            potential_defense_cavalry_per_hour = self.estimate_potential_defense_cavalry_per_hour(
                village.tribe,
                hourly_production
            )
            
            # Calculate trainable units per hour
            trainable_units = self.estimate_trainable_units_per_hour(
                village.tribe,
                hourly_production
            )
            
            # Log current military status (for debugging/planning)
            military_status = {
                "village_id": village.id,
                "current_strength": {
                    "total_attack": total_attack,
                    "total_defense_infantry": total_defense_infantry,
                    "total_defense_cavalry": total_defense_cavalry,
                    "grain_consumption_per_hour": grain_consumption,
                    "troop_count": sum(village.troops.values()),
                },
                "potential_production_per_hour": {
                    "attack": potential_attack_per_hour,
                    "defense_infantry": potential_defense_infantry_per_hour,
                    "defense_cavalry": potential_defense_cavalry_per_hour,
                    "trainable_units": trainable_units,
                },
                "training_buildings": {
                    "barracks_level": barracks_level,
                    "stable_level": stable_level,
                },
            }
            
            # TODO: Based on military_status, decide on training jobs, building upgrades, etc.
            # This will be expanded with actual job creation logic
        
        return jobs



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





