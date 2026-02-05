import logging
import math
from datetime import datetime, timedelta

from src.core.calculator.calculator import TravianCalculator
from src.config.config import HeroConfig
from src.core.model.model import ResourceType, Village, GameState, HeroInfo, Resources, BuildingType, ReservationStatus, \
    BuildingJob, BuildingCost
from src.core.strategy.Strategy import Strategy
from src.core.job import Job, HeroAdventureJob, AllocateAttributesJob, CollectDailyQuestsJob, CollectQuestmasterJob, BuildNewJob, BuildJob

logger = logging.getLogger(__name__)

class BalancedEconomicGrowth(Strategy):

    def __init__(self, minimum_storage_capacity_in_hours: int, hero_config: HeroConfig):
        self.minimum_storage_capacity_in_hours = minimum_storage_capacity_in_hours
        self.hero_config = hero_config
        self.calculator = None

    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        self.calculator = calculator
        new_jobs = []
        new_jobs.extend(self.create_plan_for_villages(game_state))
        # Also plan hero adventure (if applicable)
        #TODO: add information to game_state when hero will be back from adventure/traveling
        hero_jobs = self.create_plan_for_hero(game_state.hero_info)
        new_jobs.extend(hero_jobs)
        return new_jobs

    def create_plan_for_villages(self, game_state: GameState) -> list[Job]:
        global_lowest = self.determine_next_resoure_to_develop(game_state)

        jobs = []

        for village in game_state.villages:
            village_jobs = self._plan_village(village, game_state, global_lowest)
            if village_jobs:
                jobs.extend(village_jobs)

        # For questmaster rewards schedule per-village collecting jobs
        for village in game_state.villages:
            if village.has_quest_master_reward:
                qm_job = self._create_collect_questmaster_job(village)
                if qm_job:
                    jobs.append(qm_job)

        return jobs

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
                success_message="attribute points allocated ",
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
        )

    def _create_collect_questmaster_job(self, village: Village) -> Job:
        now = datetime.now()
        return CollectQuestmasterJob(
            success_message="reward from quest master collected",
            failure_message="reward from quest master collection failed",
            village=village,
            scheduled_time=now,
        )

    def _create_new_build_job(self, village, gid, name) -> Job | None:
        for pit_id in range(19, 39):
            if not any(b for b in village.buildings if b.id == pit_id):
                now = datetime.now()
                building_cost = self.calculator.get_building_details(gid, 1)
                return BuildNewJob(
                    village_name=village.name,
                    village_id=village.id,
                    building_id=pit_id,
                    building_gid=gid,
                    target_name=name,
                    success_message="construction of new building started",
                    failure_message="construction of new building failed",
                    scheduled_time=now,
                    duration=building_cost.time_seconds,
                    freeze_until=None,
                    freeze_queue_key=village.building_queue.queue_key_for_building_name(name),
                )
        return None

    def determine_next_resoure_to_develop(self, game_state: GameState) -> ResourceType | None:

        # Sum resources from villages and hero inventory
        total = Resources()
        for v in game_state.villages:
            total += v.resources
        # Add resources from hero inventory via hero_inventory_resource() (SourceType -> int)
        # game_state.hero_info exists, use its normalized resource mapping
        hero_resources = game_state.hero_info.hero_inventory_resource()

        total += hero_resources

        min_val = total.min()
        max_val = total.max()
        if max_val != 0:
            diff = (max_val - min_val) / max_val
            if diff < 0.1:
                return None
        return total.min_type()

    def _plan_village(self, village: Village, game_state: GameState, global_lowest: ResourceType | None) -> list[Job]:
        jobs = []
        if village.needs_more_free_crop():
            upgrade_crop = self._plan_source_pit_upgrade(village=village, game_state=game_state,global_lowest=ResourceType.CROP)
            if upgrade_crop and village.building_queue.can_build_outside():
                jobs.append(upgrade_crop)
        else:
            upgrade = self._plan_storage_upgrade(village=village, hero_info=game_state.hero_info)
            if upgrade and village.building_queue.can_build_inside():
                jobs.append(upgrade)

        if len(jobs) == 0 or village.building_queue.parallel_building_allowed:
            upgrade =self._plan_source_pit_upgrade(village=village, game_state=game_state, global_lowest=global_lowest)
            if upgrade and village.building_queue.can_build_outside():
                jobs.append(upgrade)

        for job in jobs:
            if isinstance(job, (BuildJob, BuildNewJob)):
                # Add job to village building queue immediately to mark it as occupied (even if scheduled in the future) and prevent duplicate planning
                building_job = BuildingJob(
                    building_name=job.target_name,
                    target_level=job.target_level,
                    time_remaining=job.duration,
                    job_id=job.job_id,
                )
                village.building_queue.add_job(building_job)
        return jobs

    def _plan_storage_upgrade(self, village: Village, hero_info: HeroInfo) -> Job | None:
        building_type = self._find_insufficient_storage(village)
        if not building_type:
            return None

        building = village.get_building(building_type)

        if building is None:
            return self._create_new_build_job(village, building_type.gid, building_type.name)

        if building and building.level < building_type.max_level:
            return self._create_build_job(village, building.id, building_type.gid, building_type.name,
                                          building.level + 1, hero_info=hero_info)

        # TODO: build next storage building if possible
        return None

    def warehouse_min_ratio(self, village: Village) -> float:
        highest_production = max(village.lumber_hourly_production, village.clay_hourly_production, village.iron_hourly_production)
        minimum_capacity = highest_production * self.minimum_storage_capacity_in_hours
        return village.warehouse_capacity / minimum_capacity

    def granary_min_ratio(self, village: Village) -> float:
        minimum_capacity = village.crop_hourly_production * self.minimum_storage_capacity_in_hours
        return village.warehouse_capacity / minimum_capacity

    def _find_insufficient_storage(self, village: Village) -> BuildingType | None:
        # check if any of the storage will full in less than minimum hours
        lumber = (village.warehouse_capacity - village.resources.lumber) / village.lumber_hourly_production
        clay = (village.warehouse_capacity - village.resources.clay) / village.clay_hourly_production
        iron = (village.warehouse_capacity - village.resources.iron) / village.iron_hourly_production
        crop = (village.granary_capacity - village.resources.crop) / village.crop_hourly_production

        full_storage_after = [
            (BuildingType.WAREHOUSE, min(lumber, clay, iron)),
            (BuildingType.GRANARY, crop)
        ]

        building_to_upgrade = [(bt, full_after) for bt, full_after in full_storage_after if full_after < self.minimum_storage_capacity_in_hours]

        if building_to_upgrade:
            result = min(building_to_upgrade, key=lambda x: x[1])
            return result[0] if result else None

        # Check warehouse and granary capacity ratios
        checks = [
            (BuildingType.WAREHOUSE, self.warehouse_min_ratio(village)),
            (BuildingType.GRANARY, self.granary_min_ratio(village)),
        ]
        result = [(bt, ratio) for bt, ratio in checks if ratio < 1.0]
        if result:
            return min(result, key=lambda x: x[1])[0]
        else:
            return None

    def _plan_source_pit_upgrade(self, village: Village, game_state: GameState, global_lowest: ResourceType | None) -> Job | None:
        upgradable = village.upgradable_source_pits()
        if not upgradable:
            return None

        # Prioritize upgrading the globally lowest resource type if applicable
        # Otherwise, upgrade the lowest level pit available
        pits_to_consider = [p for p in upgradable if p.type == global_lowest] or upgradable

        pit = min(pits_to_consider, key=lambda p: p.level)

        return self._create_build_job(village, pit.id, pit.type.gid, pit.type.name, pit.level + 1, hero_info=game_state.hero_info)

    def _create_build_job(self, village: Village, building_id: int, building_gid: int, target_name: str,
                          target_level: int, hero_info: HeroInfo) -> Job:
        """Create a build job. If resources are insufficient, compute delay based on hourly production
        (village + hero inventory) and schedule job in the future. Also set village.is_queue_building_freeze
        when scheduling a future job to prevent duplicate planning.
        """
        now = datetime.now()

        building_cost: BuildingCost = self.calculator.get_building_details(building_gid, target_level)
        duration: int = building_cost.time_seconds
        reservation_request = village.create_reservation_request(building_cost)

        if reservation_request.is_empty():
            # No shortages -> immediate job
            return BuildJob(
                success_message=f"construction of {target_name} level {target_level} in {village.name} started",
                failure_message=f"construction of {target_name} level {target_level} in {village.name} failed",
                village_name=village.name, village_id=village.id, building_id=building_id,
                building_gid=building_gid, target_name=target_name, target_level=target_level,
                support=None,
                scheduled_time=now,
                duration=duration
            )

        # send reservation request to hero
        response = hero_info.send_request(reservation_request)
        support = response.provided_resources if response.status is not ReservationStatus.REJECTED else None

        shortage = reservation_request - response.provided_resources
        max_delay_seconds = self.calculate_delay(shortage, village)

        scheduled = now
        freeze_until: datetime | None = None
        freeze_queue_key: str | None = None
        if not shortage.is_empty():
            scheduled += timedelta(seconds=max_delay_seconds)
            freeze_until = scheduled + timedelta(seconds=duration)
            # Mark village queue frozen to avoid duplicate scheduling
            freeze_queue_key = village.building_queue.queue_key_for_building_name(target_name)
            village.freeze_building_queue_until(freeze_until, freeze_queue_key, job_id=None)

        job = BuildJob(
            success_message=f"construction of {target_name} level {target_level} in {village.name} started",
            failure_message=f"construction of {target_name} level {target_level} in {village.name} failed",
            village_name=village.name, village_id=village.id, building_id=building_id,
            building_gid=building_gid, target_name=target_name, target_level=target_level,
            support=support,
            scheduled_time=scheduled,
            duration=duration,
            freeze_until=freeze_until,
            freeze_queue_key=freeze_queue_key,
        )

        if not shortage.is_empty():
            logger.info(f"Scheduling build job for {village.name} {target_name} level {target_level} in the future at {scheduled} due to resource shortage: {shortage}, max delay seconds: {max_delay_seconds}")

        return job



    def calculate_delay(self, shortage: Resources, village: Village) -> int:
        village_production = shortage / village.resources_hourly_production()

        return math.ceil(village_production.max() * 3600)
