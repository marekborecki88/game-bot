import pytest

from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, Building, SourcePit, ResourceType, BuildingType, BuildingJob, Tribe, GameState, Account, HeroInfo, Resources
from src.core.task.tasks import BuildTask, HeroAdventureTask, AllocateAttributesTask


def make_village(**overrides) -> Village:
    """Test helper to create a Village with sensible defaults; override fields as needed."""
    defaults = {
        "id": 999,
        "name": "Test Village",
        "tribe": Tribe.ROMANS,
        "resources": Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        "free_crop": 500,
        "source_pits": [SourcePit(id=1, type=ResourceType.LUMBER, level=1)],
        "buildings": [],
        "warehouse_capacity": 50000,
        "granary_capacity": 50000,
        "building_queue": [],
    }
    defaults.update(overrides)
    return Village(**defaults)


interval_seconds = 3600


@pytest.fixture
def account_info() -> Account:
    """Fixture to provide an Account with sensible defaults."""
    return Account(server_speed=1.0, when_beginners_protection_expires=0)


@pytest.fixture
def hero_info() -> HeroInfo:
    """Fixture to provide a HeroInfo with sensible defaults."""
    return HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True
    )


class TestLogicEngine:

    def test_skip_village_with_non_empty_building_queue(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="Test Village",
            buildings=[Building(id=19, level=1, type=BuildingType.WAREHOUSE)],
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[BuildingJob(building_id=1, target_level=2, time_remaining=3600)],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        expected = []
        assert result == expected

    def test_upgrade_warehouse_when_capacity_insufficient_for_24h_production(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="WarehouseTest",
            buildings=[Building(id=10, level=1, type=BuildingType.WAREHOUSE)],
            warehouse_capacity=1000,
            granary_capacity=50000,
            lumber_hourly_production=10000,
            clay_hourly_production=10000,
            iron_hourly_production=10000,
            crop_hourly_production=10000,
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        assert len(result) == 1
        task = result[0].task
        assert isinstance(task, BuildTask)
        assert task.village_name == "WarehouseTest"
        assert task.village_id == 999
        assert task.building_id == 10
        assert task.building_gid == BuildingType.WAREHOUSE.gid
        assert task.target_name == BuildingType.WAREHOUSE.name
        assert task.target_level == 2

    def test_upgrade_granary_when_capacity_insufficient_for_24h_crop_production(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="GranaryTest",
            buildings=[Building(id=11, level=1, type=BuildingType.GRANARY)],
            warehouse_capacity=50000,
            granary_capacity=1000,
            lumber_hourly_production=10000,
            clay_hourly_production=10000,
            iron_hourly_production=10000,
            crop_hourly_production=10000,
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        assert len(result) == 1
        task = result[0].task
        assert isinstance(task, BuildTask)
        assert task.village_name == "GranaryTest"
        assert task.village_id == 999
        assert task.building_id == 11
        assert task.building_gid == BuildingType.GRANARY.gid
        assert task.target_name == BuildingType.GRANARY.name
        assert task.target_level == 2

    def test_prioritize_storage_with_lower_ratio(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="PriorityTest",
            buildings=[
                Building(id=10, level=1, type=BuildingType.WAREHOUSE),
                Building(id=11, level=1, type=BuildingType.GRANARY),
            ],
            lumber_hourly_production=10000,
            clay_hourly_production=10000,
            iron_hourly_production=10000,
            crop_hourly_production=10000,
            warehouse_capacity=24000,
            granary_capacity=14400,
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        assert len(result) == 1
        task = result[0].task
        assert isinstance(task, BuildTask)
        assert task.village_name == "PriorityTest"
        assert task.village_id == 999
        assert task.building_id == 11
        assert task.building_gid == BuildingType.GRANARY.gid
        assert task.target_name == BuildingType.GRANARY.name
        assert task.target_level == 2

    def test_upgrade_source_pit_when_storage_is_sufficient(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="SourcePitTest",
            resources=Resources(lumber=100, clay=500, iron=500, crop=500),
            source_pits=[
                SourcePit(id=1, type=ResourceType.LUMBER, level=3),
                SourcePit(id=2, type=ResourceType.LUMBER, level=1),
                SourcePit(id=3, type=ResourceType.CLAY, level=2),
            ],
            lumber_hourly_production=1000,
            clay_hourly_production=1000,
            iron_hourly_production=1000,
            crop_hourly_production=1000,
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        assert len(result) == 1
        task = result[0].task
        assert isinstance(task, BuildTask)
        assert task.village_name == "SourcePitTest"
        assert task.village_id == 999
        assert task.building_id == 2
        assert task.building_gid == ResourceType.LUMBER.gid
        assert task.target_name == ResourceType.LUMBER.name
        assert task.target_level == 2

    def test_skip_village_when_all_source_pits_at_max_level(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="MaxedPitsTest",
            source_pits=[
                SourcePit(id=1, type=ResourceType.LUMBER, level=10),
                SourcePit(id=2, type=ResourceType.CLAY, level=10),
                SourcePit(id=3, type=ResourceType.IRON, level=10),
                SourcePit(id=4, type=ResourceType.CROP, level=10),
            ],
            lumber_hourly_production=1000,
            clay_hourly_production=1000,
            iron_hourly_production=1000,
            crop_hourly_production=1000,
            warehouse_capacity=50000,
            granary_capacity=50000,
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        expected = []
        assert result == expected

    def test_skip_storage_upgrade_when_at_max_level(self, account_info: Account, hero_info: HeroInfo):
        # Given
        village = make_village(
            name="MaxedStorageTest",
            buildings=[
                Building(id=10, level=20, type=BuildingType.WAREHOUSE),
                Building(id=11, level=20, type=BuildingType.GRANARY),
            ],
            warehouse_capacity=80000,
            granary_capacity=80000,
            lumber_hourly_production=1000,
            clay_hourly_production=1000,
            iron_hourly_production=1000,
            crop_hourly_production=1000,
            source_pits=[
                SourcePit(id=1, type=ResourceType.LUMBER, level=10),
                SourcePit(id=2, type=ResourceType.CLAY, level=10),
                SourcePit(id=3, type=ResourceType.IRON, level=10),
                SourcePit(id=4, type=ResourceType.CROP, level=10),
            ],
            building_queue=[],
        )
        game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
        engine = LogicEngine(game_state = game_state)

        # When
        result = engine.create_plan_for_village()

        # Then
        expected = []
        assert result == expected

    def test_plan_hero_adventure_when_hero_available(self, account_info: Account):
        # Given
        hero_info = HeroInfo(
            health=90,
            experience=1000,
            adventures=83,
            is_available=True
        )
        # Provide a minimal GameState for the engine
        game_state = GameState(account=account_info, villages=[], hero_info=hero_info)
        engine = LogicEngine(game_state=game_state)

        # When
        jobs = engine.create_plan_for_hero(hero_info)

        # Then
        assert len(jobs) == 1
        task = jobs[0].task
        assert isinstance(task, HeroAdventureTask)
        h = task.hero_info
        assert h.health == 90
        assert h.experience == 1000
        assert h.adventures == 83

    def test_skip_hero_adventure_when_hero_unavailable(self, account_info: Account):
        # Given
        hero_info = HeroInfo(
            health=50,
            experience=500,
            adventures=10,
            is_available=False
        )
        gs = GameState(account=account_info, villages=[], hero_info=hero_info)
        engine = LogicEngine(game_state=gs)

        # When
        jobs = engine.create_plan_for_hero(hero_info)

        # Then
        assert jobs == []

    def test_allocate_attributes_job_when_points_available(self, account_info: Account):
        # Given
        hero_info = HeroInfo(
            health=80,
            experience=5000,
            adventures=10,
            is_available=False,
            points_available=4
        )
        gs = GameState(account=account_info, villages=[], hero_info=hero_info)
        engine = LogicEngine(game_state=gs)

        # When
        jobs = engine.create_plan_for_hero(hero_info)

        # Then: should create an allocate_attributes job even if adventure not planned
        assert any(isinstance(j.task, AllocateAttributesTask) and j.task.points == 4 for j in jobs)
