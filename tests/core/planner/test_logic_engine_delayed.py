from datetime import datetime, timedelta

import pytest

from src.config.config import AttributeAllocation, LogicConfig, Strategy, HeroConfig, HeroAdventuresConfig, HeroResourcesConfig
from src.core.job import BuildJob
from src.core.model.model import Account, GameState, HeroInfo, Resources, ResourceType, ResourcePit, Tribe, Village, \
    BuildingQueue
from src.core.planner.logic_engine import LogicEngine


def make_village(**overrides: object) -> Village:
    defaults: dict[str, object] = {
        "id": 42,
        "name": "DelayedVillage",
        "tribe": Tribe.ROMANS,
        "resources": Resources(lumber=0, clay=0, iron=0, crop=0),
        "coordinates": (0, 0),
        "free_crop": 0,
        "resource_pits": [ResourcePit(id=1, type=ResourceType.LUMBER, level=1)],
        "buildings": [],
        "warehouse_capacity": 1000,
        "granary_capacity": 1000,
        "building_queue": BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
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
    return Account(when_beginners_protection_expires=0)


@pytest.fixture
def hero_info() -> HeroInfo:
    return HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})


@pytest.fixture
def config() -> LogicConfig:
    return LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )


@pytest.fixture
def hero_config() -> HeroConfig:
    return HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=False),
        resources=HeroResourcesConfig(
            support_villages=False,
            attributes_ratio=AttributeAllocation(fighting_strength=3, production_points=1),
            attributes_steps=AttributeAllocation(),
        ),
    )


def test_create_build_job_schedules_future_when_insufficient_resources(
        account_info: Account,
        hero_info: HeroInfo,
        config: LogicConfig,
        hero_config: HeroConfig,
) -> None:
    village = make_village(
        resources=Resources(lumber=200, clay=200, iron=200, crop=200),
        lumber_hourly_production=5,
        clay_hourly_production=5,
        iron_hourly_production=5,
        crop_hourly_production=5,
        source_pits=[ResourcePit(id=2, type=ResourceType.LUMBER, level=1)],
    )

    game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(config, hero_config)

    now = datetime.now()
    jobs = engine.plan(game_state)
    assert len(jobs) == 1
    job = jobs[0]

    assert job.scheduled_time > now
    assert village.building_queue.can_build_outside() is False
    assert isinstance(job, BuildJob)
    assert job.success_message == f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started"
    assert job.failure_message == f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed"
    assert job.village_name == village.name
    assert job.village_id == village.id
    assert job.building_id == 2
    assert job.building_gid == ResourceType.LUMBER.gid
    assert job.target_name == ResourceType.LUMBER.name
    assert job.target_level == 2
    assert job.support is None
    assert job.duration == 616
    assert job.freeze_until is None
    assert job.freeze_queue_key is None


def test_create_build_job_uses_hero_inventory_to_build_immediately(
        account_info: Account,
        hero_info: HeroInfo,
        config: LogicConfig,
        hero_config: HeroConfig,
) -> None:
    village = make_village(
        resources=Resources(lumber=0, clay=0, iron=0, crop=0),
        lumber_hourly_production=1,
        clay_hourly_production=1,
        iron_hourly_production=1,
        crop_hourly_production=1,
        source_pits=[ResourcePit(id=3, type=ResourceType.LUMBER, level=1)],
    )

    hero_info.inventory.update({"lumber": 10000, "clay": 10000, "iron": 10000, "crop": 10000})

    game_state = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(config, hero_config)

    now = datetime.now()
    jobs = engine.plan(game_state)
    assert len(jobs) == 1
    job = jobs[0]

    assert now - timedelta(seconds=1) <= job.scheduled_time <= now + timedelta(seconds=1)
    assert village.building_queue.can_build_outside() is False
    assert isinstance(job, BuildJob)
    assert job.success_message == f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started"
    assert job.failure_message == f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed"
    assert job.village_name == village.name
    assert job.village_id == village.id
    assert job.building_id == 3
    assert job.building_gid == ResourceType.LUMBER.gid
    assert job.target_name == ResourceType.LUMBER.name
    assert job.target_level == 2
    assert job.support == Resources(lumber=65, clay=165, iron=85, crop=100)
    assert job.duration == 616
    assert job.freeze_until is None
    assert job.freeze_queue_key is None
