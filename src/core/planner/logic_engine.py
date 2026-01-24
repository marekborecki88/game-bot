from datetime import datetime, timedelta

from src.core.job import Job
from src.core.model.model import Village, BuildingType, SourceType, GameState, HeroInfo


class LogicEngine:
    def create_plan_for_village(self, game_state: GameState, interval_in_seconds: int) -> list[Job]:
        global_lowest = self.determine_next_resoure_to_develop(game_state)
        return [job for v in game_state.villages if (job := self._plan_village(v, global_lowest)) is not None]

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

        if building and building.level < building_type.max_level:
            return self._create_build_job(village, building.id, building_type.gid, building_type.name, building.level + 1)
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
        now = datetime.now()
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
            scheduled_time=now,
            expires_at=now + timedelta(hours=1)
        )

    def create_plan_for_hero(self, hero_info: HeroInfo) -> list[Job]:
        """Create a plan for the hero, which may include an adventure and attribute allocation.

        If the hero is available (not on the way, not traveling), schedule an adventure.
        If the hero has attribute points available, schedule an allocation job.

        Returns a list of Jobs (possibly empty).
        """
        jobs: list[Job] = []

        now = datetime.now()

        # Adventure job (only if hero is available)
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

        # Attribute allocation job (if attribute points available)
        points = hero_info.points_available
        if points > 0:
            jobs.append(Job(
                task=(lambda p=points: {"action": "allocate_attributes", "points": points}),
                scheduled_time=now,
                expires_at=now + timedelta(hours=1)
            ))

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
        inv = getattr(game_state.hero_info, 'inventory', {})
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
