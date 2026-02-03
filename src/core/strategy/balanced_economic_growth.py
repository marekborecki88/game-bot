import logging
import math
from datetime import datetime, timedelta

from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import ResourceType, Village, GameState, HeroInfo, Resources, BuildingType, ReservationStatus
from src.core.strategy.Strategy import Strategy
from src.core.job import Job, HeroAdventureJob, AllocateAttributesJob, CollectDailyQuestsJob, CollectQuestmasterJob, BuildNewJob, BuildJob

logger = logging.getLogger(__name__)

class BalancedEconomicGrowth(Strategy):


    def plan_jobs(self, game_state: GameState, calculator: TravianCalculator) -> list[Job]:
        self.calculator = calculator
        new_jobs = []
        new_jobs.extend(self.create_plan_for_village(game_state))
        # Also plan hero adventure (if applicable)
        hero_jobs = self.create_plan_for_hero(game_state.hero_info)
        new_jobs.extend(hero_jobs)
        return new_jobs

    def create_plan_for_village(self, game_state: GameState | None = None) -> list[Job]:
        global_lowest = self.determine_next_resoure_to_develop(game_state)
        jobs = [job for v in game_state.villages if (job := self._plan_village(v, game_state.hero_info, global_lowest)) is not None]

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

        if hero_info.can_go_on_adventure():
            jobs.append(HeroAdventureJob(
                success_message="hero adventure scheduled",
                failure_message="hero adventure failed",
                hero_info=hero_info,
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

        points = hero_info.points_available
        if points > 0:
            jobs.append(AllocateAttributesJob(
                success_message="attribute points allocated ",
                failure_message="attribute points allocation failed",
                points=points,
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
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
            expires_at=now + timedelta(hours=1)
        )

    def _create_collect_questmaster_job(self, village: Village) -> Job:
        now = datetime.now()
        return CollectQuestmasterJob(
            success_message="reward from quest master collected",
            failure_message="reward from quest master collection failed",
            village=village,
            scheduled_time=now,
            expires_at=now + timedelta(hours=1)
        )

    def _create_new_build_job(self, village, gid, name) -> Job | None:
        for id in range(19, 39):
            if not any(b for b in village.buildings if b.id == id):
                now = datetime.now()
                return BuildNewJob(
                    village_name=village.name,
                    village_id=village.id,
                    building_id=id,
                    building_gid=gid,
                    target_name=name,
                    success_message="construction of new building started",
                    failure_message="construction of new building failed",
                    scheduled_time=now,
                    expires_at=now + timedelta(hours=1)
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

    def _plan_village(self, village: Village, hero_info: HeroInfo, global_lowest: ResourceType | None) -> Job | None:
        if not village.building_queue_is_empty():
            return None

        if village.needs_more_free_crop():
            return self._plan_source_pit_upgrade(village=village, hero_info=hero_info, global_lowest=ResourceType.CROP)

        return self._plan_storage_upgrade(village, hero_info=hero_info) or self._plan_source_pit_upgrade(village, hero_info, global_lowest)

    def _plan_storage_upgrade(self, village: Village, hero_info: HeroInfo) -> Job | None:
        storage_needs = self._find_insufficient_storage(village)
        if not storage_needs:
            return None

        building_type, _ = min(storage_needs, key=lambda x: x[1])
        building = village.get_building(building_type)

        if building is None:
            return self._create_new_build_job(village, building_type.gid, building_type.name)

        if building and building.level < building_type.max_level:
            return self._create_build_job(village, building.id, building_type.gid, building_type.name,
                                          building.level + 1, hero_info=hero_info)

        # TODO: build next storage building if possible
        return None

    def _find_insufficient_storage(self, village: Village) -> list[tuple[BuildingType, float]]:
        checks = [
            (BuildingType.WAREHOUSE, village.warehouse_min_ratio()),
            (BuildingType.GRANARY, village.granary_min_ratio()),
        ]
        return [(bt, ratio) for bt, ratio in checks if ratio < 1.0]

    def _plan_source_pit_upgrade(self, village: Village, hero_info: HeroInfo, global_lowest: ResourceType | None) -> Job | None:
        upgradable = village.upgradable_source_pits()
        if not upgradable:
            return None

        # Prioritize upgrading the globally lowest resource type if applicable
        # Otherwise, upgrade the lowest level pit available
        pits_to_consider = [p for p in upgradable if p.type == global_lowest] or upgradable

        pit = min(pits_to_consider, key=lambda p: p.level)
        return self._create_build_job(village, pit.id, pit.type.gid, pit.type.name, pit.level + 1, hero_info=hero_info)

    def _create_build_job(self, village: Village, building_id: int, building_gid: int, target_name: str,
                          target_level: int, hero_info: HeroInfo) -> Job:
        """Create a build job. If resources are insufficient, compute delay based on hourly production
        (village + hero inventory) and schedule job in the future. Also set village.is_queue_building_freeze
        when scheduling a future job to prevent duplicate planning.
        """
        now = datetime.now()

        building_cost = self.calculator.get_building_details(building_gid, target_level)

        reservation_request = village.create_reservation_request(building_cost)

        # send reservation request to hero
        response = hero_info.send_request(reservation_request)

        support = response.provided_resources if response.status is not ReservationStatus.REJECTED else None

        # TODO: FOR ACCAPETED AND PARTIALLY_ACCEPTED, there is need to create separate task because we need to transfer resources from hero to village
        if response.status is not ReservationStatus.ACCEPTED:
            shortage = reservation_request - response.provided_resources
            max_delay_seconds = self.calculate_delay(shortage, village)

            scheduled = now + timedelta(seconds=max_delay_seconds)
            # set an expiry reasonably after scheduled time
            expires = scheduled + timedelta(hours=1)

            # Mark village queue frozen to avoid duplicate scheduling
            village.is_queue_building_freeze = True
            logger.info(
                f"Scheduled delayed build for village {village.name} (id={village.id}) in {max_delay_seconds} seconds; freezing queue")

            return BuildJob(
                success_message=f"construction of {target_name} level {target_level} in {village.name} started",
                failure_message=f"construction of {target_name} level {target_level} in {village.name} failed",
                village_name=village.name, village_id=village.id, building_id=building_id,
                building_gid=building_gid, target_name=target_name, target_level=target_level,
                support=support,
                scheduled_time=scheduled,
                expires_at=expires,
            )

        # No shortages -> immediate job
        scheduled = now
        expires = now + timedelta(hours=1)
        return BuildJob(
            success_message=f"construction of {target_name} level {target_level} in {village.name} started",
            failure_message=f"construction of {target_name} level {target_level} in {village.name} failed",
            village_name=village.name, village_id=village.id, building_id=building_id,
            building_gid=building_gid, target_name=target_name, target_level=target_level,
            support=support,
            scheduled_time=scheduled,
            expires_at=expires,
        )

    def calculate_delay(self, shortage: Resources, village: Village) -> int:
        village_production = shortage / village.resources_hourly_production()

        return math.ceil(village_production.max() * 3600)
