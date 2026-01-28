from src.core.job import Job
from src.core.tasks import (
    BuildTask, BuildNewTask, HeroAdventureTask, AllocateAttributesTask,
    CollectDailyQuestsTask, CollectQuestmasterTask
)
from src.core.model.model import Village, BuildingType, SourceType, GameState, HeroInfo, Resources, ReservationStatus
from src.core.calculator.calculator import TravianCalculator
from datetime import datetime, timedelta
import math
import logging

logger = logging.getLogger(__name__)


class LogicEngine:
    #TODO: if game_state is not provided at construction, it must be passed to planning methods
    def __init__(self, game_state: GameState | None = None):
        # game_state may be provided at construction or passed later to planning methods
        self.game_state: GameState | None = game_state
        speed = game_state.account.server_speed if game_state else 1.0
        self.calculator = TravianCalculator(speed=speed)


    def create_plan_for_village(self, game_state: GameState | None = None) -> list[Job]:
        # Accept a fresh game_state (preferred) and store it for subsequent calculations
        if game_state:
            self.game_state = game_state
        if not self.game_state:
            return []

        global_lowest = self.determine_next_resoure_to_develop(self.game_state)
        jobs = [job for v in self.game_state.villages if (job := self._plan_village(v, global_lowest)) is not None]

        # For questmaster rewards schedule per-village collecting jobs
        for village in self.game_state.villages:
            if village.has_quest_master_reward:
                qm_job = self._create_collect_questmaster_job(village)
                if qm_job:
                    jobs.append(qm_job)

        return jobs

    def _plan_village(self, village: Village, global_lowest: SourceType | None) -> Job | None:
        if not village.building_queue_is_empty():
            return None

        if village.needs_more_free_crop():
            return self._plan_source_pit_upgrade(village, SourceType.CROP)

        return self._plan_storage_upgrade(village) or self._plan_source_pit_upgrade(village, global_lowest)

    def _plan_storage_upgrade(self, village: Village) -> Job | None:
        storage_needs = self._find_insufficient_storage(village)
        if not storage_needs:
            return None

        building_type, _ = min(storage_needs, key=lambda x: x[1])
        building = village.get_building(building_type)

        if building is None:
            return self._create_new_build_job(village, building_type.gid, building_type.name)

        if building and building.level < building_type.max_level:
            return self._create_build_job(village, building.id, building_type.gid, building_type.name, building.level + 1)

        #TODO: build next storage building if possible
        return None

    def _find_insufficient_storage(self, village: Village) -> list[tuple[BuildingType, float]]:
        checks = [
            (BuildingType.WAREHOUSE, village.warehouse_min_ratio()),
            (BuildingType.GRANARY, village.granary_min_ratio()),
        ]
        return [(bt, ratio) for bt, ratio in checks if ratio < 1.0]

    def _plan_source_pit_upgrade(self, village: Village, global_lowest: SourceType | None) -> Job | None:
        upgradable = village.upgradable_source_pits()
        if not upgradable:
            return None

        # Prioritize upgrading the globally lowest resource type if applicable
        # Otherwise, upgrade the lowest level pit available
        pits_to_consider = [p for p in upgradable if p.type == global_lowest] or upgradable

        pit = min(pits_to_consider, key=lambda p: p.level)
        return self._create_build_job(village, pit.id, pit.type.gid, pit.type.name, pit.level + 1)

    def _create_build_job(self, village: Village, building_id: int, building_gid: int, target_name: str, target_level: int) -> Job:
        """Create a build job. If resources are insufficient, compute delay based on hourly production
        (village + hero inventory) and schedule job in the future. Also set village.is_queue_building_freeze
        when scheduling a future job to prevent duplicate planning.
        """
        now = datetime.now()

        building_cost = self.calculator.get_building_details(building_gid, target_level)
        build_task = BuildTask(success_message="build scheduled", failure_message="build failed",
                               village_name=village.name, village_id=village.id, building_id=building_id,
                               building_gid=building_gid, target_name=target_name, target_level=target_level)
        if building_cost is None:
            # Fallback to immediate job if we cannot calculate cost
            scheduled = now
            expires = now + timedelta(hours=1)
            return Job(
                task=build_task,
                scheduled_time=scheduled,
                expires_at=expires,
                metadata={"action": "build", "village_id": village.id}
            )

        # Require game_state to be present
        if not self.game_state:
            raise ValueError("LogicEngine._create_build_job requires game_state to be set")

        # Use hero inventory to cover as much of the cost as possible, transfer those
        # resources into the village (mutate hero inventory and village values), then
        # compute remaining shortages based only on village production.
        # game_state.hero_info is guaranteed to exist; use it directly
        hero_info = self.game_state.hero_info

        reservation_request = village.create_reservation_request(building_cost)

        # send reservation request to hero
        response = hero_info.send_request(reservation_request)

        if response.status is not ReservationStatus.ACCEPTED:
            shortage = reservation_request - response.provided_resources
            max_delay_seconds = self.calculate_delay(shortage, village)

            scheduled = now + timedelta(seconds=max_delay_seconds)
            # set an expiry reasonably after scheduled time
            expires = scheduled + timedelta(hours=1)

            # Mark village queue frozen to avoid duplicate scheduling
            village.is_queue_building_freeze = True
            logger.info(f"Scheduled delayed build for village {village.name} (id={village.id}) in {max_delay_seconds} seconds; freezing queue")

            return Job(
                task=build_task,
                scheduled_time=scheduled,
                expires_at=expires,
                metadata={"action": "build", "village_id": village.id}
            )

        # No shortages -> immediate job
        scheduled = now
        expires = now + timedelta(hours=1)
        return Job(
            task=build_task,
            scheduled_time=scheduled,
            expires_at=expires,
            metadata={"action": "build", "village_id": village.id}
        )

    def create_plan_for_hero(self, hero_info: HeroInfo) -> list[Job]:
        """Create a plan for the hero, which may include an adventure and attribute allocation.

        If the hero is available (not on the way, not traveling), schedule an adventure.
        If the hero has attribute points available, schedule an allocation job.

        Returns a list of Jobs (possibly empty).
        """
        jobs: list[Job] = []

        now = datetime.now()

        if hero_info.is_available:
            jobs.append(Job(
                task=HeroAdventureTask(
                    success_message="hero adventure scheduled",
                    failure_message="hero adventure failed",
                    hero_info=hero_info,
                ),
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

        points = hero_info.points_available
        if points > 0:
            jobs.append(Job(
                task=AllocateAttributesTask(
                    success_message="attribute allocation scheduled",
                    failure_message="attribute allocation failed",
                    points=points,
                ),
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

        # If hero-level daily quest indicator is present, schedule collect_daily_quests (no navigation required)
        if hero_info.has_daily_quest_indicator:
            jobs.append(self._create_collect_daily_quests_job())

        return jobs

    def determine_next_resoure_to_develop(self, game_state: GameState) -> SourceType | None:

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

    def _create_new_build_job(self, village, gid, name) -> Job | None:
        for id in range(19, 39):
            if not any(b for b in village.buildings if b.id == id):
                now = datetime.now()
                return Job(
                    task=BuildNewTask(
                        village_name=village.name,
                        village_id=village.id,
                        building_id=id,
                        building_gid=gid,
                        target_name=name,
                        success_message="new building scheduled",
                        failure_message="new building failed",
                    ),
                    scheduled_time=now,
                    expires_at=now + timedelta(hours=1),
                    metadata={"action": "build_new", "village_id": village.id}
                )
        return None

    def _create_collect_daily_quests_job(self) -> Job:
        now = datetime.now()
        return Job(
            task=CollectDailyQuestsTask(
                success_message="collect daily scheduled",
                failure_message="collect daily failed",
            ),
            scheduled_time=now,
            expires_at=now + timedelta(hours=1)
        )

    def _create_collect_questmaster_job(self, village: Village) -> Job:
        now = datetime.now()
        return Job(
            task=CollectQuestmasterTask(
                success_message="collect qm scheduled",
                failure_message="collect qm failed",
                village=village,
            ),
            scheduled_time=now,
            expires_at=now + timedelta(hours=1)
        )

    #TODO: need refactor
    def unfreeze_village_queue(self, village_id: int) -> None:
        if not self.game_state:
            return
        for v in self.game_state.villages:
            if v.id == village_id:
                v.is_queue_building_freeze = False
                return

    def calculate_delay(self, shortage: Resources, village: Village) -> int:
        village_production = shortage / village.resources_hourly_production()

        return math.ceil(village_production.max() * 3600)

