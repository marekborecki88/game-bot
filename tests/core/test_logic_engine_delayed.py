import time
from datetime import datetime, timedelta

from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, Building, SourcePit, SourceType, BuildingType, BuildingJob, Tribe, GameState, Account, HeroInfo, Building


def make_village(**overrides) -> Village:
    defaults = {
        "id": 1001,
        "name": "DelayedVillage",
        "tribe": Tribe.ROMANS,
        "lumber": 0,
        "clay": 0,
        "iron": 0,
        "crop": 0,
        "free_crop": 0,
        "source_pits": [SourcePit(id=1, type=SourceType.LUMBER, level=1)],
        "buildings": [Building(id=10, level=1, type=BuildingType.WAREHOUSE)],
        "warehouse_capacity": 50000,
        "granary_capacity": 50000,
        "building_queue": [],
        "lumber_hourly_production": 10,
        "clay_hourly_production": 20,
        "iron_hourly_production": 30,
        # free_crop_hourly_production is used for crop shortages
        "free_crop_hourly_production": 40,
        # Ensure crop hourly production is non-zero so needs_more_free_crop() doesn't divide by zero
        "crop_hourly_production": 1,
    }
    defaults.update(overrides)
    return Village(**defaults)


def test_create_delayed_build_job_when_resources_insufficient():
    account = Account(server_speed=1.0)
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})

    # Village has zero resources but non-zero production -> should schedule delayed job
    village = make_village(lumber=0, clay=0, iron=0, crop=0)

    game_state = GameState(account=account, villages=[village], hero_info=hero)
    engine = LogicEngine(game_state=game_state)

    jobs = engine.create_plan_for_village(game_state)
    # At least one job should be returned for storage upgrade
    assert len(jobs) >= 1

    # find a build job for the warehouse
    build_jobs = [j for j in jobs if j.metadata and j.metadata.get('action') == 'build']
    assert build_jobs, "No build job with metadata found"

    job = build_jobs[0]
    # scheduled_time should be in the future
    assert job.scheduled_time > datetime.now()
    # village should be frozen
    assert village.is_queue_building_freeze is True




