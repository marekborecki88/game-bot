import pytest

from src.config.config import Config, Strategy
from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import (
    Village,
    Building,
    SourcePit,
    ResourceType,
    BuildingType,
    BuildingJob,
    Tribe,
    GameState,
    Account,
    HeroInfo,
    Resources,
)
from src.core.job import BuildJob, HeroAdventureJob, AllocateAttributesJob


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


@pytest.fixture
def account_info() -> Account:
    return Account(server_speed=1.0, when_beginners_protection_expires=0)


@pytest.fixture
def hero_info() -> HeroInfo:
    return HeroInfo(health=100, experience=0, adventures=0, is_available=True)


@pytest.fixture
def config() -> Config:
    return Config(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        server_url="",
        speed=1,
        user_login="",
        user_password="",
        headless=True,
    )


def test_skip_village_with_non_empty_building_queue(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
    village = make_village(
        name="Test Village",
        buildings=[Building(id=19, level=1, type=BuildingType.WAREHOUSE)],
        warehouse_capacity=50000,
        granary_capacity=50000,
        building_queue=[BuildingJob(building_id=1, target_level=2, time_remaining=3600)],
    )
    game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)

    engine = LogicEngine(config)
    jobs = engine.plan(game_state)

    build_jobs = [j for j in jobs if j.action in ("build", "build_new")]
    assert build_jobs == []


def test_upgrade_warehouse_when_capacity_insufficient_for_24h_production(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    build_jobs = engine.plan(game_state)
    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert isinstance(job, BuildJob)
    assert job.village_name == "WarehouseTest"
    assert job.village_id == 999
    assert job.building_id == 10
    assert job.building_gid == BuildingType.WAREHOUSE.gid
    assert job.target_name == BuildingType.WAREHOUSE.name
    assert job.target_level == 2


def test_upgrade_granary_when_capacity_insufficient_for_24h_crop_production(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    build_jobs = engine.plan(game_state)
    
    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert isinstance(job, BuildJob)
    assert job.village_name == "GranaryTest"
    assert job.village_id == 999
    assert job.building_id == 11
    assert job.building_gid == BuildingType.GRANARY.gid
    assert job.target_name == BuildingType.GRANARY.name
    assert job.target_level == 2


def test_prioritize_storage_with_lower_ratio(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    build_jobs = engine.plan(game_state)
    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert isinstance(job, BuildJob)
    assert job.village_name == "PriorityTest"
    assert job.village_id == 999
    assert job.building_id == 11
    assert job.building_gid == BuildingType.GRANARY.gid
    assert job.target_name == BuildingType.GRANARY.name
    assert job.target_level == 2


def test_upgrade_source_pit_when_storage_is_sufficient(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    build_jobs = engine.plan(game_state)
    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert isinstance(job, BuildJob)
    assert job.village_name == "SourcePitTest"
    assert job.village_id == 999
    assert job.building_id == 2
    assert job.building_gid == ResourceType.LUMBER.gid
    assert job.target_name == ResourceType.LUMBER.name
    assert job.target_level == 2


def test_skip_village_when_all_source_pits_at_max_level(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    jobs = engine.plan(game_state)

    build_jobs = [j for j in jobs if isinstance(j, BuildJob)]
    assert build_jobs == []


def test_skip_storage_upgrade_when_at_max_level(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
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

    engine = LogicEngine(config)
    build_jobs = engine.plan(game_state)
    assert build_jobs == []


def test_plan_hero_adventure_when_hero_available(
    account_info: Account,
    config: Config,
) -> None:
    hero_info = HeroInfo(health=90, experience=1000, adventures=83, is_available=True)
    game_state = GameState(account=account_info, villages=[], hero_info=hero_info)

    engine = LogicEngine(config)
    hero_jobs = engine.plan(game_state)

    assert len(hero_jobs) == 1

    hero_adventure_job = hero_jobs[0]
    assert isinstance(hero_adventure_job, HeroAdventureJob)


def test_skip_hero_adventure_when_hero_unavailable(
    account_info: Account,
    config: Config,
) -> None:
    hero_info = HeroInfo(health=50, experience=500, adventures=10, is_available=False)
    game_state = GameState(account=account_info, villages=[], hero_info=hero_info)

    engine = LogicEngine(config)
    jobs = engine.plan(game_state)

    hero_jobs = [j for j in jobs if isinstance(j, HeroAdventureJob)]
    assert hero_jobs == []


def test_allocate_attributes_job_when_points_available(
    account_info: Account,
    config: Config,
) -> None:
    hero_info = HeroInfo(
        health=80,
        experience=5000,
        adventures=10,
        is_available=False,
        points_available=4,
    )
    game_state = GameState(account=account_info, villages=[], hero_info=hero_info)

    engine = LogicEngine(config)
    jobs = engine.plan(game_state)

    assert any(isinstance(j, AllocateAttributesJob) and j.points == 4 for j in jobs)
