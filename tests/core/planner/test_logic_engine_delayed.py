import pytest

from datetime import datetime, timedelta

from src.config.config import Config, Strategy
from src.core.model.model import Account, GameState, HeroInfo, Resources, ResourceType, SourcePit, Tribe, Village
from src.core.planner.logic_engine import LogicEngine
from src.core.job import BuildJob


def make_village(**overrides: object) -> Village:
    defaults: dict[str, object] = {
        "id": 42,
        "name": "DelayedVillage",
        "tribe": Tribe.ROMANS,
        "resources": Resources(lumber=0, clay=0, iron=0, crop=0),
        "free_crop": 0,
        "source_pits": [SourcePit(id=1, type=ResourceType.LUMBER, level=1)],
        "buildings": [],
        "warehouse_capacity": 1000,
        "granary_capacity": 1000,
        "building_queue": [],
        "lumber_hourly_production": 10,
        "clay_hourly_production": 10,
        "iron_hourly_production": 10,
        "crop_hourly_production": 10,
        # Ensure non-zero crop production so Village.needs_more_free_crop() can't divide by zero.
        "free_crop_hourly_production": 10,
    }
    defaults.update(overrides)
    return Village(**defaults)


@pytest.fixture
def account_info() -> Account:
    return Account(server_speed=1.0, when_beginners_protection_expires=0)


@pytest.fixture
def hero_info() -> HeroInfo:
    return HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})


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


def test_create_build_job_schedules_future_when_insufficient_resources(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
    village = make_village(
        resources=Resources(lumber=0, clay=0, iron=0, crop=0),
        lumber_hourly_production=5,
        clay_hourly_production=5,
        iron_hourly_production=5,
        crop_hourly_production=5,
        source_pits=[SourcePit(id=2, type=ResourceType.LUMBER, level=1)],
    )

    game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(config)

    jobs = engine.plan(game_state)
    assert len(jobs) == 1
    job = jobs[0]

    now = datetime.now()
    assert job.scheduled_time > now
    assert village.is_queue_building_freeze is True

    expected = BuildJob(
        scheduled_time=job.scheduled_time,  # match the dynamically assigned scheduled_time and
        expires_at=job.expires_at,      # expires_at values
        success_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started",
        failure_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed",
        village_name=village.name,
        village_id=village.id,
        building_id=2,
        building_gid=ResourceType.LUMBER.gid,
        target_name=ResourceType.LUMBER.name,
        target_level=2,
    )

    assert expected == job


def test_create_build_job_uses_hero_inventory_to_build_immediately(
    account_info: Account,
    hero_info: HeroInfo,
    config: Config,
) -> None:
    village = make_village(
        resources=Resources(lumber=0, clay=0, iron=0, crop=0),
        lumber_hourly_production=1,
        clay_hourly_production=1,
        iron_hourly_production=1,
        crop_hourly_production=1,
        source_pits=[SourcePit(id=3, type=ResourceType.LUMBER, level=1)],
    )

    hero_info.inventory.update({"lumber": 10000, "clay": 10000, "iron": 10000, "crop": 10000})

    game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(config)

    now = datetime.now()
    jobs = engine.plan(game_state)
    assert len(jobs) == 1
    job = jobs[0]

    assert now - timedelta(seconds=1) <= job.scheduled_time <= now + timedelta(seconds=1)
    assert village.is_queue_building_freeze is False


    expected = BuildJob(
        scheduled_time=job.scheduled_time,  # match the dynamically assigned scheduled_time and
        expires_at=job.expires_at,      # expires_at values
        success_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started",
        failure_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed",
        village_name=village.name,
        village_id=village.id,
        building_id=3,
        building_gid=ResourceType.LUMBER.gid,
        target_name=ResourceType.LUMBER.name,
        target_level=2,
        support=Resources(lumber=65, clay=165, iron=85, crop=100),
    )

    assert expected == job
