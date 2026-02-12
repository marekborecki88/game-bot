from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import GameState, ResourceType, Building, BuildingType, BuildingCost, Resources
from src.core.model.village import Village
from src.core.strategy.strategy import Strategy


class DefendArmyPolicy(Strategy):
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
            
            # Evaluate military building priorities
            military_building_priorities = self.estimate_military_building_priority(village, village.tribe)
            military_status["building_priorities"] = military_building_priorities
            
            # TODO: Based on military_status, decide on training jobs, building upgrades, etc.
            # This will be expanded with actual job creation logic
        
        return jobs

    def evaluate_military_building_requirements(
        self, villages: list[Village]
    ) -> dict[int, dict[BuildingType, float]]:
        """
        Evaluate military building priorities for all villages.
        
        Returns a dictionary mapping village ID to building priorities for that village.
        Priority coefficients range from 0-100, where higher values indicate more critical
        buildings to construct or upgrade.

        :param villages: List of villages to analyze
        :return: Dictionary mapping village_id to dict of (BuildingType -> priority_coefficient)
        """
        building_priorities: dict[int, dict[BuildingType, float]] = {}
        
        for village in villages:
            priorities = self.estimate_military_building_priority(village, village.tribe)
            building_priorities[village.id] = priorities
        
        return building_priorities



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

    def plan_economy_upgrades(
        self, village: Village, planned_units: dict[str, int] | None = None
    ) -> list[tuple[BuildingType, float]]:
        """
        Plan economy building upgrades for a village based on its development stage.
        
        Returns a list of building upgrades sorted by priority (highest first).
        Each tuple contains (BuildingType, priority_coefficient).
        
        **Economy Development Stages:**
        
        **EARLY STAGE** (any primary pit < level 5):
        - Phase 1: Build all resource pits (woodcutter, clay_pit, iron_mine) to level 2
        - Upgrade main building to level 5
        - Upgrade warehouse/granary to hold 12h production
        - Phase 2: Crop only if free_crop is too low (< 0.1 ratio to hourly production)
        - Upgrade all primary pits to level 5
        
        **MID STAGE** (all primary pits >= level 5):
        - Continue upgrading primary pits towards max village level
        - Build/upgrade secondary production buildings (sawmill, brickyard, iron_foundry)
        - Balance resource proportions based on planned unit costs
        - For Legionnaires: iron costs 150, lumber 120 (highest priorities)
        - For Phalanx: clay costs 130, lumber 100
        
        **ADVANCED STAGE** (at least one resource fully developed):
        - Primary pits only upgraded if that resource has > 30% proportion in unit costs
        - Prioritize secondary buildings to maximum level
        - Specialize production based on planned military units
        
        **Resource Proportion Calculation:**
        When units are specified, production targets are proportionally adjusted:
        - Legionnaire: 120 lumber + 100 clay + 150 iron + 30 crop = heavy on iron
        - Empty unit list: balanced 25% each
        
        :param village: The village to plan for
        :param planned_units: Optional dict mapping unit name to quantity (e.g., {"Legionnaire": 100})
        :return: List of (BuildingType, priority) tuples sorted by priority (descending)
        """
        dev_stage = self.estimate_village_development_stage(village)
        
        if dev_stage == 'early':
            return self.plan_economy_upgrades_early_stage(village)
        elif dev_stage == 'mid':
            return self.plan_economy_upgrades_mid_stage(village, planned_units or {})
        else:  # advanced
            return self.plan_economy_upgrades_advanced_stage(village, planned_units or {})

    def plan_economy_upgrades_early_stage(
        self, village: Village
    ) -> list[tuple[BuildingType, float]]:
        """
        Plan economy upgrades for early stage village.
        
        Phase 1 (levels 2):
        - Build all primary resource pits to level 2 (woodcutter, clay_pit, iron_mine)
        - Upgrade main building to level 5
        - Upgrade warehouse and granary to hold 12h production
        
        Phase 2 (levels 2->5):
        - Upgrade crop only if free_crop is too low (ratio < 0.1 to hourly production)
        - Upgrade all primary resource pits to level 5
        - Maintain warehouse/granary capacity
        
        :param village: The village to plan for
        :return: List of (BuildingType, priority) tuples sorted by priority
        """
        upgrades: dict[BuildingType, float] = {}
        priority_counter = 1000  # Start with high priority
        
        # === PHASE 1: Get pits to level 2 ===
        primary_pits = [BuildingType.WOODCUTTER, BuildingType.CLAY_PIT, BuildingType.IRON_MINE]
        
        for pit_type in primary_pits:
            pit = village.get_building(pit_type)
            pit_level = pit.level if pit else 0
            
            if pit_level < 2:
                upgrades[pit_type] = float(priority_counter)
                priority_counter -= 100
        
        # === Upgrade main building to level 5 ===
        main_building = village.get_building(BuildingType.MAIN_BUILDING)
        main_level = main_building.level if main_building else 0
        
        if main_level < 5:
            # Lower priority than pits to level 2, but still high
            upgrades[BuildingType.MAIN_BUILDING] = float(priority_counter)
            priority_counter -= 100
        
        # === Ensure warehouse/granary can hold 12h production ===
        # (This is handled separately in storage planning, keeping for now)
        
        # === PHASE 2: Upgrade pits to level 5 ===
        for pit_type in primary_pits:
            pit = village.get_building(pit_type)
            pit_level = pit.level if pit else 0
            
            if 2 <= pit_level < 5:
                upgrades[pit_type] = float(priority_counter)
                priority_counter -= 50
        
        # === PHASE 2: Crop handling - only if free_crop is too low ===
        cropland = village.get_building(BuildingType.CROPLAND)
        crop_level = cropland.level if cropland else 0
        
        if village.needs_more_free_crop() and crop_level < 5:
            upgrades[BuildingType.CROPLAND] = float(priority_counter)
            priority_counter -= 30
        
        return sorted(upgrades.items(), key=lambda x: x[1], reverse=True)

    def plan_economy_upgrades_mid_stage(
        self, village: Village, planned_units: dict[str, int]
    ) -> list[tuple[BuildingType, float]]:
        """
        Plan economy upgrades for mid-stage village.
        
        Balances between:
        - Continuing economy development (pits to higher levels)
        - Adding secondary production buildings (sawmill, brickyard, etc.)
        - Adjusting resource production to match unit training needs
        
        Proportions are based on planned units' resource costs.
        
        :param village: The village to plan for
        :param planned_units: Dict mapping unit name to quantity (e.g., {"Legionnaire": 100})
        :return: List of (BuildingType, priority) tuples sorted by priority
        """
        upgrades: dict[BuildingType, float] = {}
        priority_counter = 1000
        
        # Get target resource proportions based on planned units
        resource_proportions = self.estimate_resource_production_proportions(planned_units)
        
        # === Primary resource pits to level 10 (or village max) ===
        primary_pits = {
            BuildingType.WOODCUTTER: ResourceType.LUMBER,
            BuildingType.CLAY_PIT: ResourceType.CLAY,
            BuildingType.IRON_MINE: ResourceType.IRON,
        }
        
        max_pit_level = village.max_source_pit_level()
        
        for pit_type, resource_type in primary_pits.items():
            pit = village.get_building(pit_type)
            pit_level = pit.level if pit else 0
            
            if pit_level < max_pit_level:
                # Priority based on target proportion for this resource
                proportion = resource_proportions.get(resource_type, 0.25)
                # Higher proportion = higher priority
                priority = 500 + (proportion * 300)
                upgrades[pit_type] = priority
                priority_counter -= 50
        
        # === Secondary production buildings (sawmill, brickyard, iron_foundry) ===
        secondary_buildings = [
            (BuildingType.SAWMILL, ResourceType.LUMBER),
            (BuildingType.BRICKYARD, ResourceType.CLAY),
            (BuildingType.IRON_FOUNDRY, ResourceType.IRON),
        ]
        
        for building_type, resource_type in secondary_buildings:
            building = village.get_building(building_type)
            building_level = building.level if building else 0
            
            if building is None:
                # Not yet built
                proportion = resource_proportions.get(resource_type, 0.25)
                priority = 300 + (proportion * 150)
                upgrades[building_type] = priority
            elif building_level < 5:
                # Upgrade existing
                proportion = resource_proportions.get(resource_type, 0.25)
                priority = 250 + (proportion * 100)
                upgrades[building_type] = priority
        
        # === Crop handling - balanced approach ===
        cropland = village.get_building(BuildingType.CROPLAND)
        crop_level = cropland.level if cropland else 0
        
        if crop_level < max_pit_level:
            # Crop priority based on its proportion in unit costs
            crop_proportion = resource_proportions.get(ResourceType.CROP, 0.25)
            priority = 200 + (crop_proportion * 200)
            upgrades[BuildingType.CROPLAND] = priority
        
        return sorted(upgrades.items(), key=lambda x: x[1], reverse=True)

    def plan_economy_upgrades_advanced_stage(
        self, village: Village, planned_units: dict[str, int]
    ) -> list[tuple[BuildingType, float]]:
        """
        Plan economy upgrades for advanced-stage village.
        
        At this stage, primary economy is mature. Focus on:
        - Completing specialized resource production (based on planned units)
        - Secondary production buildings upgrades to maximum
        - Crop to comfortable level if needed
        
        Primary resource pits only upgraded if specialized production requires it.
        
        :param village: The village to plan for
        :param planned_units: Dict mapping unit name to quantity
        :return: List of (BuildingType, priority) tuples sorted by priority
        """
        upgrades: dict[BuildingType, float] = {}
        priority_counter = 1000
        
        resource_proportions = self.estimate_resource_production_proportions(planned_units)
        max_pit_level = village.max_source_pit_level()
        
        # === Secondary buildings to maximum level ===
        secondary_buildings = [
            (BuildingType.SAWMILL, ResourceType.LUMBER),
            (BuildingType.BRICKYARD, ResourceType.CLAY),
            (BuildingType.IRON_FOUNDRY, ResourceType.IRON),
        ]
        
        for building_type, resource_type in secondary_buildings:
            building = village.get_building(building_type)
            building_level = building.level if building else 0
            
            if building_level < 5:
                # Prioritize based on specialization needs
                proportion = resource_proportions.get(resource_type, 0.25)
                priority = 500 + (proportion * 300)
                upgrades[building_type] = priority
        
        # === Specialty: boost primary pits for specialized resources ===
        primary_pits = {
            BuildingType.WOODCUTTER: ResourceType.LUMBER,
            BuildingType.CLAY_PIT: ResourceType.CLAY,
            BuildingType.IRON_MINE: ResourceType.IRON,
        }
        
        # Only upgrade pits if they're below max AND the resource has high proportion
        for pit_type, resource_type in primary_pits.items():
            pit = village.get_building(pit_type)
            pit_level = pit.level if pit else 0
            
            proportion = resource_proportions.get(resource_type, 0.25)
            
            # Upgrade pits with high resource proportion to maximum
            if pit_level < max_pit_level and proportion > 0.30:
                priority = 300 + (proportion * 200)
                upgrades[pit_type] = priority
        
        # === Crop to comfortable level ===
        cropland = village.get_building(BuildingType.CROPLAND)
        crop_level = cropland.level if cropland else 0
        
        if crop_level < max_pit_level:
            # Lower priority at this stage, but still upgrade
            upgrades[BuildingType.CROPLAND] = 100.0
        
        return sorted(upgrades.items(), key=lambda x: x[1], reverse=True)





