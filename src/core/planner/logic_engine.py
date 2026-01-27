from src.core.job import Job
from src.core.model.model import Village, BuildingType, SourceType, GameState, HeroInfo
from src.core.calculator.calculator import TravianCalculator
from datetime import datetime, timedelta
import math


class LogicEngine:
    def __init__(self, game_state: GameState):
        self.game_state: GameState = game_state
        speed = game_state.account.server_speed
        self.calculator = TravianCalculator(speed=speed)


    def create_plan_for_village(self) -> list[Job]:
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
        if building_cost is None:
            # Fallback to immediate job if we cannot calculate cost
            scheduled = now
            expires = now + timedelta(hours=1)
            return Job(
                task=lambda: {
                    "action": "build",
                    "village_name": village.name,
                    "village_id": village.id,
                    "building_id": building_id,
                    "building_gid": building_gid,
                    "target_name": target_name,
                    "target_level": target_level
                },
                scheduled_time=scheduled,
                expires_at=expires
            )

        # Available resources = village resources + hero inventory
        inv = (self.game_state.hero_info.inventory if self.game_state and self.game_state.hero_info else {})
        avail = {
            'lumber': village.lumber + inv.get('lumber', 0),
            'clay': village.clay + inv.get('clay', 0),
            'iron': village.iron + inv.get('iron', 0),
            'crop': village.crop + inv.get('crop', 0),
        }

        req = {'lumber': building_cost.lumber, 'clay': building_cost.clay, 'iron': building_cost.iron, 'crop': building_cost.crop}

        # Compute shortage in seconds per resource (ceil hours -> seconds)
        shortages = {}
        max_delay_seconds = 0
        for key in ('lumber', 'clay', 'iron', 'crop'):
            short = max(0, req[key] - avail.get(key, 0))
            shortages[key] = short
            if short > 0:
                # hourly production mapping
                prod = 0
                if key == 'lumber':
                    prod = village.lumber_hourly_production
                elif key == 'clay':
                    prod = village.clay_hourly_production
                elif key == 'iron':
                    prod = village.iron_hourly_production
                elif key == 'crop':
                    prod = village.free_crop_hourly_production

                if prod > 0:
                    hours = math.ceil(short / prod)
                    delay = hours * 3600
                else:
                    # If production is zero, we cannot compute a reasonable delay; fallback to immediate
                    delay = 0

                if delay > max_delay_seconds:
                    max_delay_seconds = delay

        if max_delay_seconds > 0:
            scheduled = now + timedelta(seconds=max_delay_seconds)
            # set an expiry reasonably after scheduled time
            expires = scheduled + timedelta(hours=1)

            # Mark village queue frozen to avoid duplicate scheduling
            village.is_queue_building_freeze = True

            return Job(
                task=lambda: {
                    "action": "build",
                    "village_name": village.name,
                    "village_id": village.id,
                    "building_id": building_id,
                    "building_gid": building_gid,
                    "target_name": target_name,
                    "target_level": target_level
                },
                scheduled_time=scheduled,
                expires_at=expires
            )

        # No shortages -> immediate job
        scheduled = now
        expires = now + timedelta(hours=1)
        return Job(
            task=lambda: {
                "action": "build",
                "village_name": village.name,
                "village_id": village.id,
                "building_id": building_id,
                "building_gid": building_gid,
                "target_name": target_name,
                "target_level": target_level
            },
            scheduled_time=scheduled,
            expires_at=expires
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
                task=(lambda h=hero_info: {
                    "action": "hero_adventure",
                    "health": h.health,
                    "experience": h.experience,
                    "adventures": h.adventures
                }),
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

        points = hero_info.points_available
        if points > 0:
            jobs.append(Job(
                task=(lambda p=points: {"action": "allocate_attributes", "points": points}),
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

        # If hero-level daily quest indicator is present, schedule collect_daily_quests (no navigation required)
        if hero_info.has_daily_quest_indicator:
            jobs.append(self._create_collect_daily_quests_job())

        return jobs

    def determine_next_resoure_to_develop(self, game_state: GameState) -> SourceType | None:

        # Sum resources from villages and hero inventory
        totals = {
            SourceType.LUMBER: 0,
            SourceType.CLAY: 0,
            SourceType.IRON: 0,
            SourceType.CROP: 0,
        }
        for v in game_state.villages:
            totals[SourceType.LUMBER] += v.lumber
            totals[SourceType.CLAY] += v.clay
            totals[SourceType.IRON] += v.iron
            totals[SourceType.CROP] += v.crop
        # Add resources from hero inventory
        inv = game_state.hero_info.inventory
        totals[SourceType.LUMBER] += inv.get('lumber', 0)
        totals[SourceType.CLAY] += inv.get('clay', 0)
        totals[SourceType.IRON] += inv.get('iron', 0)
        totals[SourceType.CROP] += inv.get('crop', 0)

        min_val = min(totals.values())
        max_val = max(totals.values())
        if max_val != 0:
            diff = (max_val - min_val) / max_val
            if diff < 0.1:
                return None
        return min(totals, key=totals.get)

    def _create_new_build_job(self, village, gid, name) -> Job | None:
        for id in range(19, 39):
            if not any(b for b in village.buildings if b.id == id):
                now = datetime.now()
                return Job(
                    task=lambda: {
                        "action": "build_new",
                        "village_name": village.name,
                        "village_id": village.id,
                        "building_id": id,
                        "building_gid": gid,
                        "target_name": name,
                        "target_level": 1
                    },
                    scheduled_time=now,
                    expires_at=now + timedelta(hours=1)
                )
        return None

    def _create_collect_daily_quests_job(self) -> Job:
        now = datetime.now()
        return Job(
            task=lambda: {
                "action": "collect_daily_quests",
            },
            scheduled_time=now,
            expires_at=now + timedelta(hours=1)
        )

    def _create_collect_questmaster_job(self, village: Village) -> Job:
        now = datetime.now()
        return Job(
            task=lambda v=village: {
                "action": "collect_questmaster_rewards",
                "village_name": v.name,
                "village_id": v.id,
            },
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
