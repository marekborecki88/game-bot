from src.core.calculator.calculator import TravianCalculator
from src.core.job import Job
from src.core.model.game_state import GameState
from src.core.model.model import ResourceType, Building, BuildingType, BuildingCost, Resources
from src.core.model.village import Village
from src.core.strategy.strategy import Strategy
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PrioritizedJob:
    """Represents a building upgrade job with priority."""
    building_type: BuildingType
    priority: float

    def __lt__(self, other: "PrioritizedJob") -> bool:
        """Compare by priority for sorting (higher priority first)."""
        return self.priority > other.priority


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

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        """
        Plan jobs to develop defensive army considering current troop strength and resources.
        
        Analyzes multiple factors across all villages:
        - Military strength and potential troop production
        - Economy and resource production
        - Merchants mobility and capacity for multi-village trading
        - Residence/settler requirements for expanding
        - Hero adventures and attribute allocation
        - Quest rewards (daily quests and questmaster)
        
        Returns a prioritized list of jobs to execute.
        
        :param game_state: Current game state with villages and hero info
        :param calculator: Travian calculator for time and cost calculations
        :return: List of recommended jobs to execute
        """
        jobs = []
        villages = game_state.villages

        # === HERO JOBS (independent of policy) ===
        # These jobs are added regardless of the strategy chosen
        hero_jobs = self.create_plan_for_hero(game_state.hero_info)

        # === QUESTMASTER REWARDS (independent of policy) ===
        questmaster_jobs = self.plan_questmaster_rewards(villages)

        # === GLOBAL ANALYSIS ===

        # Check merchant requirements across all villages
        marketplace_requirements = self.estimate_marketplace_requirement(villages)

        # Check residence/settler requirements
        residence_requirements = self.estimate_residence_requirement(game_state)

        # === PER-VILLAGE ANALYSIS ===

        village_plans = []

        global_lowest_production = game_state.estimate_global_lowest_resource_production_in_next_hours(2)

        for village in villages:
            village_plan = self._analyze_village_plan(
                village=village,
                needs_marketplace=marketplace_requirements.get(village.id, False),
                residence_requirements=residence_requirements,
                global_lowest_production=global_lowest_production
            )
            village_plans.append(village_plan)

        # === CONSOLIDATE AND PRIORITIZE ===

        # Aggregate all building priorities from village plans
        all_building_recommendations = self._consolidate_building_recommendations(
            village_plans=village_plans,
            marketplace_needed_globally=len(villages) > 1,
            residence_requirements=residence_requirements,
        )

        # Create BuildJob objects from recommendations
        for recommendation in all_building_recommendations:
            village_id = recommendation["village_id"]
            building_type = recommendation["building_type"]
            priority = recommendation["priority"]
            reason = recommendation["reason"]

            # Find the village and building details
            village = next((v for v in villages if v.id == village_id), None)
            if not village:
                continue

            # Check if building queue allows adding this building
            if self._is_building_in_center(building_type.name):
                if not village.building_queue.can_build_inside():
                    logger.debug(f"Skipping {building_type.name} in village {village_id}: inside queue is occupied")
                    continue
            else:
                if not village.building_queue.can_build_outside():
                    logger.debug(f"Skipping {building_type.name} in village {village_id}: outside queue is occupied")
                    continue

            # Get or create the building
            building = village.get_building(building_type)
            if building is None:
                free_slot = village.find_free_building_slot()
                if not free_slot:
                    logger.debug(f"Skipping {building_type.name} in village {village_id}: no free building slot")
                    continue
                building = Building(id=free_slot, level=1, type=building_type)

            # Create BuildJob for this building using the shared method
            job = self._create_build_job(
                village=village,
                building_id=building.id,
                building_gid=building_type.gid,
                target_name=building_type.name,
                target_level=building.level + 1,
                hero_info=game_state.hero_info,
                calculator=calculator,
            )

            jobs.append({
                "job": job,
                "priority": priority,
                "reason": reason,
                "village_id": village_id,
                "building_type": building_type,
            })

        # Sort jobs by priority (descending)
        jobs.sort(key=lambda x: x["priority"], reverse=True)

        # Log job planning summary
        logger.info(f"Planned {len(jobs)} jobs across {len(villages)} villages")
        for i, job_info in enumerate(jobs[:5]):  # Log top 5 jobs
            if isinstance(job_info, dict) and "building_type" in job_info:
                logger.debug(f"  {i+1}. Village {job_info['village_id']}: {job_info['building_type'].name} "
                            f"(priority: {job_info['priority']:.1f}) - {job_info['reason']}")

        # Return Job objects: extract from dicts and keep hero/questmaster jobs
        result_jobs = []

        # Add extracted BuildJob objects from building recommendations
        for job_item in jobs:
            if isinstance(job_item, dict) and "job" in job_item:
                result_jobs.append(job_item["job"])

        # Add hero jobs and questmaster jobs
        result_jobs.extend(hero_jobs)
        result_jobs.extend(questmaster_jobs)

        return result_jobs

    def _analyze_village_plan(
        self,
        village: Village,
        needs_marketplace: bool,
        residence_requirements: dict[str, int | float],
        global_lowest_production: ResourceType
    ) -> dict:
        """
        Analyze a single village and determine optimal building/training plan.
        
        :param village: The village to analyze
        :param game_state: Current game state
        :param calculator: Travian calculator
        :param needs_marketplace: Whether village requires marketplace (multi-village account)
        :param residence_requirements: Global residence/settler requirements
        :return: Dictionary with village analysis and recommendations
        """
        # === MILITARY ANALYSIS ===

        tribe = village.tribe
        troops_statistics = self.calculate_troops_statistics(tribe, village.troops)

        barracks = village.get_building(BuildingType.BARRACKS)
        stable = village.get_building(BuildingType.STABLE)
        barracks_level = barracks.level if barracks else 0
        stable_level = stable.level if stable else 0

        hourly_production = Resources(
            lumber=village.lumber_hourly_production,
            clay=village.clay_hourly_production,
            iron=village.iron_hourly_production,
            crop=village.crop_hourly_production
        )

        trainable_units = self.estimate_trainable_units_per_hour(tribe, hourly_production)
        trainable_units_statistics = self.calculate_troops_statistics(tribe, trainable_units)

        military_building_priorities = self.estimate_military_building_priority(village, tribe)

        military_analysis = {
            "current_strength": {
                "total_attack": troops_statistics.get("attack", 0),
                "total_defense_infantry": troops_statistics.get("defense_infantry", 0),
                "total_defense_cavalry": troops_statistics.get("defense_cavalry", 0),
                "grain_consumption_per_hour": troops_statistics.get("grain_consumption", 0),
                "troop_count": sum(village.troops.values()),
            },
            "potential_production_per_hour": {
                "attack": trainable_units_statistics.get("attack", 0),
                "defense_infantry": trainable_units_statistics.get("defense_infantry", 0),
                "defense_cavalry": trainable_units_statistics.get("defense_cavalry", 0),
                "grain_consumption": trainable_units_statistics.get("grain_consumption", 0),
                "trainable_units": trainable_units
            },
            "training_buildings": {
                "barracks_level": barracks_level,
                "stable_level": stable_level,
            },
            "building_priorities": military_building_priorities,
        }

        # === ECONOMY ANALYSIS ===

        dev_stage = self.estimate_village_development_stage(village)

        economy_upgrades = self.plan_economy_upgrades(village, global_lowest_production)

        economy_analysis = {
            "development_stage": dev_stage,
            "hourly_production": Resources(
                lumber= village.lumber_hourly_production,
                clay= village.clay_hourly_production,
                iron= village.iron_hourly_production,
                crop= village.crop_hourly_production,
            ),
            "building_upgrades": economy_upgrades,
        }

        # === MERCHANT ANALYSIS ===

        merchants_needed = self.calculate_merchants_needed(village)

        merchant_analysis = {
            "merchants_needed": merchants_needed,
            "needs_marketplace": needs_marketplace,
            "marketplace_level": village.get_building(BuildingType.MARKETPLACE).level
                if village.get_building(BuildingType.MARKETPLACE) else 0,
        }

        # === RESIDENCE/SETTLER ANALYSIS ===

        residence_analysis = {
            "days_to_next_village": residence_requirements.get("days_to_next_village", 999),
            "residence_priority": residence_requirements.get("priority", 0.0),
            "culture_progress": {
                "current": residence_requirements.get("culture_points", 0),
                "needed": residence_requirements.get("culture_points_needed", 10000),
            },
            "slots": {
                "used": residence_requirements.get("village_slots_used", 1),
                "available": residence_requirements.get("village_slots_available", 0),
            },
        }

        return {
            "village_id": village.id,
            "military": military_analysis,
            "economy": economy_analysis,
            "merchants": merchant_analysis,
            "residence": residence_analysis,
        }

    def _consolidate_building_recommendations(
        self,
        village_plans: list[dict],
        marketplace_needed_globally: bool,
        residence_requirements: dict[str, int | float],
    ) -> list[dict]:
        """
        Consolidate building recommendations from all village plans into a prioritized list.
        
        Collects ALL possible recommendations and selects the one with highest priority.

        Priority order (highest to lowest):
        1. Critical military buildings (missing barracks, stable, workshop)
        2. Economy upgrades to support troop training
        3. Marketplace if multiple villages exist
        4. Residences/settlers if approaching culture threshold

        :param village_plans: List of village analysis dictionaries
        :param marketplace_needed_globally: Whether marketplace is needed (multi-village)
        :param residence_requirements: Global residence/settler requirements
        :return: List with single highest-priority building recommendation
        """
        all_recommendations: list[dict] = []

        # Collect all possible recommendations
        all_recommendations.extend(self._collect_military_recommendations(village_plans))
        all_recommendations.extend(self._collect_economy_recommendations(village_plans))

        if marketplace_needed_globally:
            all_recommendations.extend(self._collect_marketplace_recommendations(village_plans))

        days_to_village = residence_requirements.get("days_to_next_village", 999)
        residence_priority = residence_requirements.get("priority", 0.0)
        if days_to_village <= 30 and residence_priority > 0:
            all_recommendations.extend(
                self._collect_residence_recommendations(village_plans, residence_priority, days_to_village)
            )

        # Sort by priority (descending) and return top recommendation
        if not all_recommendations:
            return []

        all_recommendations.sort(key=lambda x: x["priority"], reverse=True)
        return [all_recommendations[0]]

    def _collect_military_recommendations(self, village_plans: list[dict]) -> list[dict]:
        """Collect all military building recommendations with priority 1000+."""
        recommendations: list[dict] = []

        for plan in village_plans:
            village_id = plan["village_id"]
            military_priorities = plan["military"]["building_priorities"]

            for building_type, priority_value in military_priorities.items():
                if priority_value > 0:
                    recommendations.append({
                        "village_id": village_id,
                        "building_type": building_type,
                        "priority": priority_value,
                        "reason": f"Military building critical for defense - {building_type.name}",
                        "category": "military",
                    })

        return recommendations

    def _collect_economy_recommendations(self, village_plans: list[dict]) -> list[dict]:
        """Collect all economy building recommendations with priority 500+."""
        recommendations: list[dict] = []

        for plan in village_plans:
            village_id = plan["village_id"]
            economy_upgrades: list[PrioritizedJob] = plan["economy"]["building_upgrades"]

            for prioritized_job in economy_upgrades:
                recommendations.append({
                    "village_id": village_id,
                    "building_type": prioritized_job.building_type,
                    "priority": prioritized_job.priority,
                    "reason": f"Economy upgrade to increase production - {prioritized_job.building_type.name}",
                    "category": "economy",
                })

        return recommendations

    def _collect_marketplace_recommendations(self, village_plans: list[dict]) -> list[dict]:
        """Collect all marketplace building recommendations with priority 100-300."""
        recommendations: list[dict] = []

        for plan in village_plans:
            village_id = plan["village_id"]
            marketplace_level = plan["merchants"]["marketplace_level"]

            if marketplace_level < 1:
                priority = 300.0
                reason = "Build marketplace for multi-village trade"
            elif marketplace_level < 5:
                priority = 250.0 + (10 - marketplace_level)
                reason = f"Upgrade marketplace to level {marketplace_level + 1}"
            else:
                priority = 100.0
                reason = "Marketplace upgrade (low priority)"

            recommendations.append({
                "village_id": village_id,
                "building_type": BuildingType.MARKETPLACE,
                "priority": priority,
                "reason": reason,
                "category": "marketplace",
            })

        return recommendations

    def _collect_residence_recommendations(
        self, village_plans: list[dict], residence_priority: float, days_to_village: int
    ) -> list[dict]:
        """Collect all residence building recommendations with priority 200+."""
        recommendations: list[dict] = []

        for plan in village_plans:
            village_id = plan["village_id"]
            recommendations.append({
                "village_id": village_id,
                "building_type": BuildingType.RESIDENCE,
                "priority": 200.0 + residence_priority,
                "reason": f"Residence/settlers - {days_to_village} days to next village",
                "category": "residence",
            })

        return recommendations

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
        self, village: Village, global_lowest_production: ResourceType, planned_units: dict[str, int] | None = None
    ) -> list[PrioritizedJob]:
        dev_stage = self.estimate_village_development_stage(village)

        match dev_stage:
            case 'early':
                return self.plan_economy_upgrades_early_stage(village, global_lowest_production)
            case 'mid':
                return self.plan_economy_upgrades_mid_stage(village, global_lowest_production, planned_units or {})
            case _:  # advanced
                return self.plan_economy_upgrades_advanced_stage(village, global_lowest_production, planned_units or {})

    def plan_economy_upgrades_early_stage(self, village: Village, global_lowest_production: ResourceType) -> list[PrioritizedJob]:
        """
        Plan economy upgrades for early-stage village.

        Priority order:
        1. Crop if free_crop < 5 (priority 1000)
        2. Woodcutter, Clay Pit, Iron Mine to level 2 (priority 700, ordered by lowest level)
        3. Warehouse/Granary if capacity < 12h production (priority 500)
        4. All resource pits according to global_lowest_production (priority 100)

        :param village: The village to plan for
        :param global_lowest_production: The resource type with lowest global production
        :return: List of PrioritizedJob sorted by priority (highest first)
        """
        jobs = [
            *self._calculate_critical_crop_upgrade(village),
            *self._calculate_primary_pits_to_level_2(village, global_lowest_production),
            *self._calculate_storage_upgrades_for_12h_production(village),
            *self._calculate_lowest_production_resource_upgrade(village, global_lowest_production),
        ]

        return sorted(jobs, reverse=True)

    def _calculate_critical_crop_upgrade(self, village: Village) -> list[PrioritizedJob]:
        """
        Calculate cropland upgrade if free_crop < 5 with priority 1000.

        :param village: The village to check
        :return: List with PrioritizedJob or empty list
        """
        if village.free_crop <= 5:
            cropland = village.get_building(BuildingType.CROPLAND)
            if cropland and cropland.level < village.max_source_pit_level():
                return [PrioritizedJob(building_type=BuildingType.CROPLAND, priority=1000.0)]
        return []

    def _calculate_primary_pits_to_level_2(self, village: Village, global_lowest_production: ResourceType) -> list[PrioritizedJob]:
        """
        Calculate woodcutter, clay pit, and iron mine upgrades to level 2 with priority 700.
        Only if free_crop >= 5. Ordered by lowest level first.

        :param village: The village to check
        :return: List of PrioritizedJob or empty list
        """
        if village.free_crop < 5:
            return []

        pit = village.get_resource_pit(global_lowest_production)
        if pit.level < 2:
            building_type = BuildingType.from_gid(pit.type.gid)
            return [PrioritizedJob(building_type=building_type, priority=700.0)]

        return []

    def _calculate_storage_upgrades_for_12h_production(self, village: Village) -> list[PrioritizedJob]:
        """
        Calculate warehouse/granary upgrades if capacity < 12h production with priority 500.

        In Travian, each resource (lumber, clay, iron) has separate storage in warehouse,
        so we check if ANY resource's 12h production exceeds warehouse capacity.

        :param village: The village to check
        :return: List of PrioritizedJob or empty list
        """
        jobs: list[PrioritizedJob] = []

        # Check each resource separately - each has its own limit in warehouse
        resources_12h_production = max(village.lumber_hourly_production, village.clay_hourly_production, village.iron_hourly_production) * 12

        if village.warehouse_capacity < resources_12h_production:
            jobs.append(PrioritizedJob(building_type=BuildingType.WAREHOUSE, priority=500.0))

        crop_12h_production = village.crop_hourly_production * 12

        if village.granary_capacity < crop_12h_production:
            jobs.append(PrioritizedJob(building_type=BuildingType.GRANARY, priority=500.0))

        return jobs

    def _calculate_lowest_production_resource_upgrade(
        self,
        village: Village,
        global_lowest_production: ResourceType
    ) -> list[PrioritizedJob]:
        """
        Calculate resource pit upgrade for the globally lowest production resource with priority 100.

        :param village: The village to check
        :param global_lowest_production: The resource type with lowest global production
        :return: List with PrioritizedJob or empty list
        """
        resource_to_building = {
            ResourceType.LUMBER: BuildingType.WOODCUTTER,
            ResourceType.CLAY: BuildingType.CLAY_PIT,
            ResourceType.IRON: BuildingType.IRON_MINE,
            ResourceType.CROP: BuildingType.CROPLAND,
        }

        target_building_type = resource_to_building.get(global_lowest_production)
        target_building = village.get_building(target_building_type)
        if target_building and target_building.level < village.max_source_pit_level():
            return [PrioritizedJob(building_type=target_building_type, priority=100.0)]

        return []

    def plan_economy_upgrades_mid_stage(
        self, village: Village, global_lowest_production: ResourceType, planned_units: dict[str, int]
    ) -> list[PrioritizedJob]:
        """
        Plan economy upgrades for mid-stage village.
        
        Balances between:
        - Continuing economy development (pits to higher levels)
        - Adding secondary production buildings (sawmill, brickyard, etc.)
        - Adjusting resource production to match unit training needs
        
        Proportions are based on planned units' resource costs.
        
        :param village: The village to plan for
        :param planned_units: Dict mapping unit name to quantity (e.g., {"Legionnaire": 100})
        :return: List of PrioritizedJob sorted by priority (highest first)
        """
        jobs: list[PrioritizedJob] = []

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
                priority = 500.0 + (proportion * 300.0)
                jobs.append(PrioritizedJob(building_type=pit_type, priority=priority))

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
                priority = 300.0 + (proportion * 150.0)
                jobs.append(PrioritizedJob(building_type=building_type, priority=priority))
            elif building_level < 5:
                # Upgrade existing
                proportion = resource_proportions.get(resource_type, 0.25)
                priority = 250.0 + (proportion * 100.0)
                jobs.append(PrioritizedJob(building_type=building_type, priority=priority))

        # === Crop handling - balanced approach ===
        cropland = village.get_building(BuildingType.CROPLAND)
        crop_level = cropland.level if cropland else 0

        if crop_level < max_pit_level:
            # Crop priority based on its proportion in unit costs
            crop_proportion = resource_proportions.get(ResourceType.CROP, 0.25)
            priority = 200.0 + (crop_proportion * 200.0)
            jobs.append(PrioritizedJob(building_type=BuildingType.CROPLAND, priority=priority))

        return sorted(jobs, reverse=True)

    def plan_economy_upgrades_advanced_stage(
            self, village: Village, global_lowest_production: ResourceType, planned_units: dict[str, int]
    ) -> list[PrioritizedJob]:
        """
        Plan economy upgrades for advanced-stage village.
        
        At this stage, primary economy is mature. Focus on:
        - Completing specialized resource production (based on planned units)
        - Secondary production buildings upgrades to maximum
        - Crop to comfortable level if needed
        
        Primary resource pits only upgraded if specialized production requires it.
        
        :param village: The village to plan for
        :param planned_units: Dict mapping unit name to quantity
        :return: List of PrioritizedJob sorted by priority (highest first)
        """
        jobs: list[PrioritizedJob] = []

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
                priority = 500.0 + (proportion * 300.0)
                jobs.append(PrioritizedJob(building_type=building_type, priority=priority))

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
                priority = 300.0 + (proportion * 200.0)
                jobs.append(PrioritizedJob(building_type=pit_type, priority=priority))

        # === Crop to comfortable level ===
        cropland = village.get_building(BuildingType.CROPLAND)
        crop_level = cropland.level if cropland else 0

        if crop_level < max_pit_level:
            # Lower priority at this stage, but still upgrade
            jobs.append(PrioritizedJob(building_type=BuildingType.CROPLAND, priority=100.0))

        return sorted(jobs, reverse=True)

    @staticmethod
    def _is_building_in_center(building_name: str) -> bool:
        """Check if building is in the center (inside) or outside (source pits)."""
        return building_name not in ["Woodcutter", "Clay Pit", "Iron Mine", "Cropland"]





