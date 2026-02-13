from typing import Protocol
from datetime import datetime

from src.config.config import HeroConfig, LogicConfig
from src.core.calculator.calculator import TravianCalculator
from src.core.model.game_state import GameState
from src.core.model.model import Resources, BuildingType, Tribe, HeroInfo
from src.core.model.village import Village
from src.core.model.units import get_unit_by_name, get_units_for_tribe
from src.core.job.job import Job
from src.core.model.model import ResourceType
from src.core.job import HeroAdventureJob, AllocateAttributesJob, CollectDailyQuestsJob, CollectQuestmasterJob


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

    def total_attack(self, village_troops: dict[str, int], tribe: Tribe) -> int:
        """
        Calculate total attack points from all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :return: Total attack value
        """
        if not village_troops:
            return 0

        attack = 0
        for unit_name, quantity in village_troops.items():
            unit = get_unit_by_name(unit_name, tribe)

            if unit:
                attack += unit.attack * quantity

        return attack

    def total_defense_infantry(self, village_troops: dict[str, int], tribe: Tribe) -> int:
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
            unit = get_unit_by_name(unit_name, tribe)
            if unit:
                total_defense += unit.defense_vs_infantry * quantity

        return total_defense

    def total_defense_cavalry(self, village_troops: dict[str, int], tribe: Tribe) -> int:
        """
        Calculate total defense against cavalry from all trained units in a village.

        :param village_troops: Dictionary mapping unit name to quantity
        :param tribe: The tribe of the village (used to find units)
        :return: Total defense against cavalry value
        """
        if not village_troops:
            return 0

        defense = 0
        for unit_name, quantity in village_troops.items():
            # Try to find the unit in all tribes
            unit = get_unit_by_name(unit_name, tribe)
            if unit:
                defense += unit.defense_vs_cavalry * quantity

        return defense

    def grain_consumption_per_hour(self, village_troops: dict[str, int], tribe: Tribe) -> int:
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
            unit = get_unit_by_name(unit_name, tribe)

            if unit:
                total_consumption += unit.grain_consumption * quantity

        return total_consumption

    def estimate_trainable_units_per_hour(self, village_tribe: Tribe, hourly_production: Resources) -> dict[str, int]:
        # This method should treat differently units trained in barracks and stable,
        # because we can train one in barrack and one in stable
        # At this moment this method calculate only one unit from barracks,
        # but in future we need to compare units and choose best option or mix option

        trainable_units: dict[str, int] = {}
        
        units = get_units_for_tribe(village_tribe)
        if not units:
            return trainable_units

        for unit in units:
            # Calculate how many units can be trained based on available resources
            units_trainable = hourly_production.count_how_many_can_be_made(unit.costs)
            if units_trainable > 0:
                trainable_units[unit.name] = units_trainable.__int__()

        return trainable_units

    def calculate_troops_statistics(self, tribe: Tribe, units: dict[str, int]) -> dict[str, int]:
        statistics = {
            'attack': 0,
            'defense_infantry': 0,
            'defense_cavalry': 0,
            'grain_consumption': 0,
        }
        for unit_name, quantity in units.items():
            unit = get_unit_by_name(unit_name, tribe)
            if not unit:
                continue
            statistics['attack'] += unit.attack * quantity
            statistics['defense_infantry'] += unit.defense_vs_infantry * quantity
            statistics['defense_cavalry'] += unit.defense_vs_cavalry * quantity
            statistics['grain_consumption'] += unit.grain_consumption * quantity
        return statistics


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

    def calculate_merchants_needed(self, village: Village) -> int:
        """
        Calculate the number of merchants needed for a village based on its development stage.
        
        Merchants are essential for transporting resources between multiple villages.
        The number of merchants scales with:
        - Development stage (early -> mid -> advanced)
        - Hourly resource production (higher production = more merchants needed)
        
        **Calculation formula:**
        - Total hourly production (sum of all resources per hour)
        - Merchant capacity ratio based on development stage (how much capacity each merchant provides):
          * early: 0.0 (no merchants needed)
          * mid: 0.5 (each merchant covers 50% of production capacity)
          * advanced: 1.0 (each merchant covers 100% of production capacity)
        - Base merchant capacity = 1000 resources per unit
        - merchants_needed = total_hourly_production / (base_capacity * capacity_ratio)
        
        :param village: The village to analyze
        :return: Number of merchants needed (minimum 0)
        """
        dev_stage = self.estimate_village_development_stage(village)
        
        # Merchant capacity ratio by development stage
        # Represents what percentage of hourly production the total merchant capacity should cover
        # Each merchant has fixed capacity of 1000 resources
        stage_merchant_capacity_ratio = {
            'early': 0.0,      # No merchants in early stage
            'mid': 0.5,        # Total merchant capacity = 50% of hourly production
            'advanced': 1.0,   # Total merchant capacity = 100% of hourly production
        }
        
        capacity_ratio = stage_merchant_capacity_ratio.get(dev_stage, 0.0)
        
        if capacity_ratio == 0.0:
            return 0
        
        # Total hourly production
        total_hourly_production = (
            village.lumber_hourly_production +
            village.clay_hourly_production +
            village.iron_hourly_production +
            village.crop_hourly_production
        )
        
        # Base merchant capacity (resources per merchant unit)
        merchant_base_capacity = 1000
        
        # Calculate merchants needed
        merchants = int(total_hourly_production / (merchant_base_capacity * capacity_ratio))
        
        return max(0, merchants)

    def estimate_marketplace_requirement(self, villages: list[Village]) -> dict[int, bool]:
        """
        Determine if each village requires a marketplace.
        
        A marketplace is needed when:
        - The account has multiple villages (more than 1)
        
        A marketplace is NOT needed when:
        - Only 1 village exists in the account
        
        :param villages: List of all villages in the account
        :return: Dictionary mapping village_id to bool (True = needs marketplace)
        """
        needs_marketplace: dict[int, bool] = {}
        
        # Single village = no marketplace needed
        if len(villages) == 1:
            needs_marketplace[villages[0].id] = False
            return needs_marketplace
        
        # Multiple villages = all villages need marketplace
        for village in villages:
            needs_marketplace[village.id] = True
        
        return needs_marketplace

    def estimate_residence_requirement(
        self, game_state: GameState
    ) -> dict[str, int | float]:
        """
        Determine the priority for building/upgrading residences and training settlers.
        
        Residences are crucial for founding new villages. Priority increases as culture points
        approach the next village threshold.
        
        Calculation:
        - Days to next village = days_to_new_village() from Account
        - The closer to threshold, the higher the priority (exponential growth)
        - Priority coefficient scales with village development stage
        
        **Returns a dictionary with:**
        - 'days_to_next_village': Days remaining until culture threshold is reached
        - 'priority': Priority coefficient (0-100 scale)
          * 0: Far from threshold, low priority
          * ~30-50: Approaching threshold, medium priority
          * ~80-100: Very close to threshold, high priority
        - 'culture_points': Current culture points
        - 'culture_points_needed': Points remaining for next village
        
        :param game_state: Current game state with account info
        :param culture_threshold: Culture points needed for a new village (default: 10000)
        :return: Dictionary with residence/settler requirement metrics
        """
        account = game_state.account
        culture_threshold = 2000
        days_to_village = account.days_to_new_village(culture_threshold)
        
        # Calculate points needed for next village
        points_needed = max(0, culture_threshold - account.culture_points)
        
        # Calculate priority based on proximity to threshold
        # Exponential curve: far away = low priority, close = high priority
        if points_needed <= 0:
            priority = 100.0
        elif days_to_village >= 30:
            priority = 10.0  # More than month away - low priority
        elif days_to_village >= 14:
            priority = 30.0  # 2 weeks away - medium priority
        elif days_to_village >= 7:
            priority = 60.0  # 1 week away - high priority
        else:
            priority = 90.0  # Less than week - very high priority
        
        # Adjust priority based on number of villages
        # More villages = higher priority for new village
        num_villages = len(game_state.villages)
        village_multiplier = 1.0 + (num_villages * 0.2)
        priority = priority * village_multiplier
        
        return {
            'days_to_next_village': days_to_village,
            'priority': min(100.0, priority),  # Cap at 100
            'culture_points': account.culture_points,
            'culture_points_needed': points_needed,
            'village_slots_used': num_villages,
            'village_slots_available': max(0, account.village_slots - num_villages),
        }

    def create_plan_for_hero(self, hero_info: HeroInfo) -> list[Job]:
        """Create a plan for the hero, which may include an adventure and attribute allocation.

        If the hero is available (not on the way, not traveling), schedule an adventure.
        If the hero has attribute points available, schedule an allocation job.

        Returns a list of Jobs (possibly empty).
        """
        jobs: list[Job] = []

        now = datetime.now()

        if hero_info.can_go_on_adventure() and hero_info.health >= self.hero_config.adventures.minimal_health:
            jobs.append(HeroAdventureJob(
                success_message="hero adventure scheduled",
                failure_message="hero adventure failed",
                hero_info=hero_info,
                hero_config=self.hero_config,
                scheduled_time=now,
            ))

        points = hero_info.points_available
        if points > 0:
            jobs.append(AllocateAttributesJob(
                success_message="attribute points allocated",
                failure_message="attribute points allocation failed",
                points=points,
                hero_info=hero_info,
                hero_config=self.hero_config,
                scheduled_time=now,
            ))

        # If hero-level daily quest indicator is present, schedule collect_daily_quests (no navigation required)
        if hero_info.has_daily_quest_indicator:
            jobs.append(self._create_collect_daily_quests_job())

        return jobs

    def _create_collect_daily_quests_job(self) -> Job:
        now = datetime.now()
        return CollectDailyQuestsJob(
            success_message="daily quests collected",
            failure_message="daily quests collection failed",
            scheduled_time=now,
            daily_quest_threshold=self.logic_config.daily_quest_threshold,
        )

    def _create_collect_questmaster_job(self, village: Village) -> Job:
        now = datetime.now()
        return CollectQuestmasterJob(
            success_message="reward from quest master collected",
            failure_message="reward from quest master collection failed",
            village=village,
            scheduled_time=now,
        )

    def plan_questmaster_rewards(self, villages: list[Village]) -> list[Job]:
        """Create jobs for collecting questmaster rewards from villages that have them available.

        :param villages: List of villages to check for questmaster rewards
        :return: List of CollectQuestmasterJob jobs
        """
        jobs: list[Job] = []
        for village in villages:
            if village.has_quest_master_reward:
                qm_job = self._create_collect_questmaster_job(village)
                if qm_job:
                    jobs.append(qm_job)
        return jobs