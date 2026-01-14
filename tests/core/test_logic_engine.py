from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, Building, SourcePit, SourceType, BuildingType, BuildingJob, Tribe


def make_village(**overrides) -> Village:
    """Test helper to create a Village with sensible defaults; override fields as needed."""
    defaults = {
        "id": 999,
        "name": "Test Village",
        "tribe": Tribe.ROMANS,
        "lumber": 1000,
        "clay": 1000,
        "iron": 1000,
        "crop": 1000,
        "free_crop": 500,
        "source_pits": [SourcePit(id=1, type=SourceType.LUMBER, level=1)],
        "buildings": [],
        "warehouse_capacity": 50000,
        "granary_capacity": 50000,
        "building_queue": [],
    }
    defaults.update(overrides)
    return Village(**defaults)


class TestLogicEngine:

    def test_skip_village_with_non_empty_building_queue(self):
        # Given: village with building in queue
        village = make_village(
            name="Test Village",
            buildings=[Building(id=19, level=1, type=BuildingType.WAREHOUSE)],
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[BuildingJob(building_id=1, target_level=2, time_remaining=3600)],
        )
        engine = LogicEngine()

        # When: create_plan_for_village is called
        jobs = engine.create_plan_for_village([village])

        # Then: no job is created for this village
        assert jobs == []

    def test_upgrade_warehouse_when_capacity_insufficient_for_24h_production(self):
        # Given: village with warehouse capacity < 24h lumber production (2000 * 24 = 48000)
        village = make_village(
            name="WarehouseTest",
            buildings=[Building(id=10, level=1, type=BuildingType.WAREHOUSE)],
            warehouse_capacity=1000,  # << 48000
            granary_capacity=50000,
            building_queue=[],
        )

        engine = LogicEngine()

        # When
        jobs = engine.create_plan_for_village([village])

        # Then: should schedule exactly one job to upgrade the warehouse
        assert len(jobs) == 1
        job = jobs[0]

        # Task payload should target the warehouse gid and the correct building id
        payload = job.task()
        assert payload["action"] == "build"
        assert payload["village_name"] == "WarehouseTest"
        assert payload["building_id"] == 10
        assert payload["building_gid"] == BuildingType.WAREHOUSE.gid

    def test_upgrade_granary_when_capacity_insufficient_for_24h_crop_production(self):
        # Given: village with granary capacity < 24h crop production (2000 * 24 = 48000)
        village = make_village(
            name="GranaryTest",
            buildings=[Building(id=11, level=1, type=BuildingType.GRANARY)],
            warehouse_capacity=50000,
            granary_capacity=1000,  # << 48000
            building_queue=[],
        )

        engine = LogicEngine()

        # When
        jobs = engine.create_plan_for_village([village])

        # Then: should schedule exactly one job to upgrade the granary
        assert len(jobs) == 1
        job = jobs[0]
        payload = job.task()
        assert payload["action"] == "build"
        assert payload["village_name"] == "GranaryTest"
        assert payload["building_id"] == 11
        assert payload["building_gid"] == BuildingType.GRANARY.gid

    def test_prioritize_storage_with_lower_ratio(self):
        # Given: village where both warehouse and granary are insufficient
        #        warehouse ratio = 0.5 (24000 / 48000), granary ratio = 0.3 (14400 / 48000)
        village = make_village(
            name="PriorityTest",
            buildings=[
                Building(id=10, level=1, type=BuildingType.WAREHOUSE),
                Building(id=11, level=1, type=BuildingType.GRANARY),
            ],
            warehouse_capacity=24000,  # ratio = 24000 / 48000 = 0.5
            granary_capacity=14400,    # ratio = 14400 / 48000 = 0.3 (lower = more urgent)
            building_queue=[],
        )

        engine = LogicEngine()

        # When
        jobs = engine.create_plan_for_village([village])

        # Then: job to upgrade granary is created (lower ratio = more urgent)
        assert len(jobs) == 1
        payload = jobs[0].task()
        assert payload["action"] == "build"
        assert payload["building_id"] == 11
        assert payload["building_gid"] == BuildingType.GRANARY.gid

    def test_upgrade_source_pit_when_storage_is_sufficient(self):
        # Given: village with sufficient warehouse and granary capacity
        #        lumber stock is lowest among resources
        village = make_village(
            name="SourcePitTest",
            lumber=100,   # lowest
            clay=500,
            iron=500,
            crop=500,
            source_pits=[
                SourcePit(id=1, type=SourceType.LUMBER, level=3),
                SourcePit(id=2, type=SourceType.LUMBER, level=1),  # lowest level lumber
                SourcePit(id=3, type=SourceType.CLAY, level=2),
            ],
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[],
        )

        engine = LogicEngine()

        # When
        jobs = engine.create_plan_for_village([village])

        # Then: job to upgrade lumber pit with lowest level is created
        assert len(jobs) == 1
        payload = jobs[0].task()
        assert payload["action"] == "build"
        assert payload["building_id"] == 2  # pit id with lowest level lumber
        assert payload["building_gid"] == SourceType.LUMBER.gid

    def test_skip_village_when_all_source_pits_at_max_level(self):
        # Given: village with sufficient storage and all source pits at max level (10)
        village = make_village(
            name="MaxedPitsTest",
            source_pits=[
                SourcePit(id=1, type=SourceType.LUMBER, level=10),
                SourcePit(id=2, type=SourceType.CLAY, level=10),
                SourcePit(id=3, type=SourceType.IRON, level=10),
                SourcePit(id=4, type=SourceType.CROP, level=10),
            ],
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[],
        )
        engine = LogicEngine()

        # When
        jobs = engine.create_plan_for_village([village])

        # Then: no job is created
        assert jobs == []

    def test_skip_storage_upgrade_when_at_max_level(self):
        # Given: village with both warehouse and granary at max level (20),
        # but even that is not enough for 24h production (bardzo wysoka produkcja),
        # a wszystkie source_pits są na max level
        village = make_village(
            name="MaxedStorageTest",
            buildings=[
                Building(id=10, level=20, type=BuildingType.WAREHOUSE),
                Building(id=11, level=20, type=BuildingType.GRANARY),
            ],
            warehouse_capacity=80000,
            granary_capacity=80000,
            lumber_hourly_production=10000,
            clay_hourly_production=10000,
            iron_hourly_production=10000,
            crop_hourly_production=10000,
            source_pits=[
                SourcePit(id=1, type=SourceType.LUMBER, level=10),
                SourcePit(id=2, type=SourceType.CLAY, level=10),
                SourcePit(id=3, type=SourceType.IRON, level=10),
                SourcePit(id=4, type=SourceType.CROP, level=10),
            ],
            building_queue=[],
        )
        engine = LogicEngine()
        # When
        jobs = engine.create_plan_for_village([village])
        # Then: no job is created (storage i source_pits maxed)
        assert jobs == []
