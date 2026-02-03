import pytest
from datetime import datetime, timedelta

from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, SourcePit, ResourceType, Tribe, GameState, Account, HeroInfo, Resources
from src.core.task.tasks import BuildTask


def make_village(**overrides) -> Village:
    defaults = {
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
    }
    defaults.update(overrides)
    return Village(**defaults)


@pytest.fixture
def account_info() -> Account:
    return Account(server_speed=1.0, when_beginners_protection_expires=0)


@pytest.fixture
def hero_info() -> HeroInfo:
    return HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})


def test_create_build_job_schedules_future_when_insufficient_resources(account_info, hero_info):
    """Ensure LogicEngine._create_build_job schedules a future job when village lacks resources."""
    village = make_village(
        resources=Resources(lumber=0, clay=0, iron=0, crop=0),
        lumber_hourly_production=5, clay_hourly_production=5, iron_hourly_production=5, crop_hourly_production=5,
        source_pits=[SourcePit(id=2, type=ResourceType.LUMBER, level=1)],
    )

    gs = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(game_state=gs)

    # Choose a building gid that is a basic resource pit (Woodcutter gid=1)
    job = engine._create_build_job(village, building_id=2, building_gid=1, target_name=ResourceType.LUMBER.name, target_level=2)

    assert job is not None, "Expected a Job to be returned"
    now = datetime.now()

    # Job should be scheduled in the future because no resources are available and production > 0
    assert job.scheduled_time > now - timedelta(seconds=1)
    assert job.scheduled_time > now, "Expected scheduled_time to be in the future when resources are insufficient"

    # And village queue freeze flag should be set
    assert getattr(village, 'is_queue_building_freeze', False) is True

    expected = BuildTask(
        success_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started",
        failure_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed",
        village_name=village.name,
        village_id=village.id,
        building_id=2,
        building_gid=1,
        target_name=ResourceType.LUMBER.name,
        target_level=2,
    )

    assert expected == job.task


def test_create_build_job_uses_hero_inventory_to_build_immediately(account_info, hero_info):
    """If hero inventory provides the missing resources, the build job should be scheduled immediately."""
    # Village has no resources, but hero carries enough to cover the cost
    village = make_village(
        resources=Resources(lumber=0, clay=0, iron=0, crop=0),
        lumber_hourly_production=0, clay_hourly_production=0, iron_hourly_production=0, crop_hourly_production=0,
        source_pits=[SourcePit(id=3, type=ResourceType.LUMBER, level=1)],
    )

    # Give hero enough resources (generous amounts to be sure)
    hero_info.inventory.update({'lumber': 10000, 'clay': 10000, 'iron': 10000, 'crop': 10000})

    gs = GameState(account=account_info, villages=[village], hero_info=hero_info)
    engine = LogicEngine(game_state=gs)

    now = datetime.now()
    job = engine._create_build_job(village, building_id=3, building_gid=1, target_name=ResourceType.LUMBER.name, target_level=2)

    assert job is not None

    # Job should be immediate (scheduled roughly now)
    assert job.scheduled_time <= now + timedelta(seconds=1)
    assert job.scheduled_time >= now - timedelta(seconds=1)

    # No freeze should be set because there was no delay
    assert getattr(village, 'is_queue_building_freeze', False) is False

    # action is stored in job.metadata, not on the task
    assert job.metadata is not None
    assert job.metadata.get('action') == 'build'

    expected = BuildTask(
        success_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} started",
        failure_message=f"construction of {ResourceType.LUMBER.name} level 2 in {village.name} failed",
        village_name=village.name,
        village_id=village.id,
        building_id=3,
        building_gid=1,
        target_name=ResourceType.LUMBER.name,
        target_level=2,
        support=Resources(lumber=65, clay=165, iron=85, crop=100)
    )

    assert expected == job.task
