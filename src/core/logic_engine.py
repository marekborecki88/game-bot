from datetime import datetime, timedelta

from src.core.job import Job
from src.core.model.Village import Village, BuildingType


class LogicEngine:
    def create_plan_for_village(self, villages: list[Village]) -> list[Job]:
        return [job for v in villages if (job := self._plan_village(v)) is not None]

    def _plan_village(self, village: Village) -> Job | None:
        if not village.building_queue_is_empty():
            return None

        return self._plan_storage_upgrade(village) or self._plan_source_pit_upgrade(village)

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

    def _plan_source_pit_upgrade(self, village: Village) -> Job | None:
        upgradable = village.upgradable_source_pits()
        if not upgradable:
            return None

        lowest_source = village.lowest_source()
        pits_of_type = [p for p in upgradable if p.type == lowest_source]
        
        if not pits_of_type:
            return None

        pit = min(pits_of_type, key=lambda p: p.level)
        return self._create_build_job(village, pit.id, pit.type.gid, pit.type.name, pit.level + 1)

    def _create_build_job(self, village: Village, building_id: int, building_gid: int, target_name: str, target_level: int) -> Job:
        now = datetime.now()
        return Job(
            task=lambda: {
                "action": "upgrade",
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

