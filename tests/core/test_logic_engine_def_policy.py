import pytest

from src.config.config import LogicConfig, HeroConfig, Strategy
from src.core.job.build_job import BuildJob
from src.core.model.game_state import GameState
from src.core.model.model import Account, HeroInfo, Resources, Tribe, BuildingQueue, ResourcePit, ResourceType, Building, BuildingType
from src.core.model.village import Village
from src.core.planner.logic_engine import LogicEngine


@pytest.fixture
def logic_config() -> LogicConfig:
    return LogicConfig(strategy=Strategy.DEFEND_ARMY, speed=1)


@pytest.fixture
def hero_config() -> HeroConfig:
    return HeroConfig()

@pytest.fixture
def hero_info() -> HeroInfo:
    return HeroInfo(health=100, experience=0, adventures=0, is_available=False)


@pytest.fixture
def village() -> Village:
    """Fixture for a new village with initial building configuration.

    Initial configuration:
    - Main building: level 1
    - Rally point: level 1
    - Resource pits:
        - 1x Woodcutter level 2 (id=1)
        - 1x Crop level 2 (id=2)
        - 1x Clay pit level 1 (id=3)
        - 3x Woodcutter level 0 (id=4,5,6) - 3/hour each
        - 3x Clay pit level 0 (id=7,8,9) - 3/hour each
        - 3x Iron mine level 0 (id=10,11,12) - 3/hour each
        - 5x Crop level 0 (id=13,14,15,16,17,18) - 3/hour each
    """

    # Resource pits (18 fields total)
    resource_pits = [
        # Level 2 fields
        ResourcePit(id=1, type=ResourceType.LUMBER, level=2),
        ResourcePit(id=2, type=ResourceType.CROP, level=2),

        # Level 1 field
        ResourcePit(id=3, type=ResourceType.CLAY, level=1),

        # Level 0 woodcutters (3 more)
        ResourcePit(id=4, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=5, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=6, type=ResourceType.LUMBER, level=0),

        # Level 0 clay pits (3 more)
        ResourcePit(id=7, type=ResourceType.CLAY, level=0),
        ResourcePit(id=8, type=ResourceType.CLAY, level=0),
        ResourcePit(id=9, type=ResourceType.CLAY, level=0),

        # Level 0 iron mines (4 total)
        ResourcePit(id=10, type=ResourceType.IRON, level=0),
        ResourcePit(id=11, type=ResourceType.IRON, level=0),
        ResourcePit(id=12, type=ResourceType.IRON, level=0),
        ResourcePit(id=13, type=ResourceType.IRON, level=0),

        # Level 0 crops (5 more, 6 total including the level 2 one)
        ResourcePit(id=14, type=ResourceType.CROP, level=0),
        ResourcePit(id=15, type=ResourceType.CROP, level=0),
        ResourcePit(id=16, type=ResourceType.CROP, level=0),
        ResourcePit(id=17, type=ResourceType.CROP, level=0),
        ResourcePit(id=18, type=ResourceType.CROP, level=0),
    ]

    # Buildings (center)
    buildings = [
        Building(id=19, level=1, type=BuildingType.MAIN_BUILDING),
        Building(id=20, level=1, type=BuildingType.RALLY_POINT),
    ]

    # Building queue (empty)
    building_queue = BuildingQueue(parallel_building_allowed=False)

    # Calculate hourly production (approximate values for level 0=3/h, level 1, level 2)
    # Level 0: 3/hour, Level 1: ~5/hour, Level 2: ~10/hour (approximation)
    lumber_production = 10 + 3 + 3 + 3  # 1x lvl2 + 3x lvl0
    clay_production = 5 + 3 + 3 + 3  # 1x lvl1 + 3x lvl0
    iron_production = 3 + 3 + 3 + 3  # 4x lvl0
    crop_production = 10 + 3 + 3 + 3 + 3 + 3  # 1x lvl2 + 5x lvl0

    return Village(
        id=1,
        name="New Village",
        coordinates=(0, 0),
        tribe=Tribe.GAULS,
        resources=Resources(lumber=750, clay=750, iron=750, crop=750),
        free_crop=crop_production - 6,  # -2 for base consumption
        resource_pits=resource_pits,
        buildings=buildings,
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=building_queue,
        lumber_hourly_production=lumber_production,
        clay_hourly_production=clay_production,
        iron_hourly_production=iron_production,
        crop_hourly_production=crop_production,
    )


def test_should_plan_1st_upgrade(logic_config: LogicConfig, hero_config: HeroConfig, hero_info: HeroInfo,
                                 village: Village):
    logic_engine = LogicEngine(logic_config, hero_config)
    game_state = GameState(
        account=Account(),
        villages=[village],
        hero_info=hero_info
    )

    jobs = logic_engine.plan(game_state)

    build_jobs = [job for job in jobs if isinstance(job, BuildJob)]

    assert len(build_jobs) == 1

    build_job = build_jobs[0]
    assert build_job.building_gid == BuildingType.WOODCUTTER.gid
    assert build_job.target_level == 1


def test_should_plan_2nd_upgrade_after_iron(logic_config: LogicConfig, hero_config: HeroConfig,
                                            hero_info: HeroInfo, village: Village):
    # Iron Mine level 1 costs: lumber=100, clay=80, iron=30, crop=60
    iron_mine_cost = Resources(lumber=100, clay=80, iron=30, crop=60)

    # After upgrading one iron mine from level 0 to level 1
    # Level 0: 3/hour, Level 1: 7/hour -> production increase: 4/hour
    updated_resource_pits = [
        ResourcePit(id=1, type=ResourceType.LUMBER, level=2),
        ResourcePit(id=2, type=ResourceType.CROP, level=2),
        ResourcePit(id=3, type=ResourceType.CLAY, level=1),
        ResourcePit(id=4, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=5, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=6, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=7, type=ResourceType.CLAY, level=0),
        ResourcePit(id=8, type=ResourceType.CLAY, level=0),
        ResourcePit(id=9, type=ResourceType.CLAY, level=0),
        ResourcePit(id=10, type=ResourceType.IRON, level=1),  # Upgraded to level 1
        ResourcePit(id=11, type=ResourceType.IRON, level=0),
        ResourcePit(id=12, type=ResourceType.IRON, level=0),
        ResourcePit(id=13, type=ResourceType.IRON, level=0),
        ResourcePit(id=14, type=ResourceType.CROP, level=0),
        ResourcePit(id=15, type=ResourceType.CROP, level=0),
        ResourcePit(id=16, type=ResourceType.CROP, level=0),
        ResourcePit(id=17, type=ResourceType.CROP, level=0),
        ResourcePit(id=18, type=ResourceType.CROP, level=0),
    ]

    village_after_upgrade = Village(
        id=village.id,
        name=village.name,
        coordinates=village.coordinates,
        tribe=village.tribe,
        resources=village.resources - iron_mine_cost,
        free_crop=village.free_crop - 3,  # Iron Mine consumes 1 crop
        resource_pits=updated_resource_pits,
        buildings=village.buildings,
        warehouse_capacity=village.warehouse_capacity,
        granary_capacity=village.granary_capacity,
        building_queue=village.building_queue,
        lumber_hourly_production=village.lumber_hourly_production,
        clay_hourly_production=village.clay_hourly_production,
        iron_hourly_production=village.iron_hourly_production + 4,  # Level 0->1: 3->7 (+4)
        crop_hourly_production=village.crop_hourly_production,
    )

    logic_engine = LogicEngine(logic_config, hero_config)
    game_state = GameState(
        account=Account(),
        villages=[village_after_upgrade],
        hero_info=hero_info
    )

    jobs = logic_engine.plan(game_state)

    build_jobs = [job for job in jobs if isinstance(job, BuildJob)]

    assert len(build_jobs) == 1

    build_job = build_jobs[0]
    assert build_job.building_gid == BuildingType.WOODCUTTER.gid
    assert build_job.target_level == 1

def test_should_plan_3rd_upgrade_after_iron_and_woodcutter(logic_config: LogicConfig, hero_config: HeroConfig,
                                                           hero_info: HeroInfo, village: Village):
    # First upgrade: Iron Mine level 1 costs: lumber=100, clay=80, iron=30, crop=60
    iron_mine_cost = Resources(lumber=100, clay=80, iron=30, crop=60)

    # Second upgrade: Woodcutter level 1 costs: lumber=40, clay=100, iron=50, crop=60
    woodcutter_cost = Resources(lumber=40, clay=100, iron=50, crop=60)

    # After upgrading both iron mine and woodcutter from level 0 to level 1
    updated_resource_pits = [
        ResourcePit(id=1, type=ResourceType.LUMBER, level=2),
        ResourcePit(id=2, type=ResourceType.CROP, level=2),
        ResourcePit(id=3, type=ResourceType.CLAY, level=1),
        ResourcePit(id=4, type=ResourceType.LUMBER, level=1),  # Upgraded to level 1
        ResourcePit(id=5, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=6, type=ResourceType.LUMBER, level=0),
        ResourcePit(id=7, type=ResourceType.CLAY, level=0),
        ResourcePit(id=8, type=ResourceType.CLAY, level=0),
        ResourcePit(id=9, type=ResourceType.CLAY, level=0),
        ResourcePit(id=10, type=ResourceType.IRON, level=1),  # Upgraded to level 1
        ResourcePit(id=11, type=ResourceType.IRON, level=0),
        ResourcePit(id=12, type=ResourceType.IRON, level=0),
        ResourcePit(id=13, type=ResourceType.IRON, level=0),
        ResourcePit(id=14, type=ResourceType.CROP, level=0),
        ResourcePit(id=15, type=ResourceType.CROP, level=0),
        ResourcePit(id=16, type=ResourceType.CROP, level=0),
        ResourcePit(id=17, type=ResourceType.CROP, level=0),
        ResourcePit(id=18, type=ResourceType.CROP, level=0),
    ]

    village_after_upgrades = Village(
        id=village.id,
        name=village.name,
        coordinates=village.coordinates,
        tribe=village.tribe,
        resources=village.resources - iron_mine_cost - woodcutter_cost,
        free_crop=village.free_crop - 5,  # Both consume 1 crop each
        resource_pits=updated_resource_pits,
        buildings=village.buildings,
        warehouse_capacity=village.warehouse_capacity,
        granary_capacity=village.granary_capacity,
        building_queue=village.building_queue,
        lumber_hourly_production=village.lumber_hourly_production + 4,  # Woodcutter 0->1: +4
        clay_hourly_production=village.clay_hourly_production,
        iron_hourly_production=village.iron_hourly_production + 4,  # Iron Mine 0->1: +4
        crop_hourly_production=village.crop_hourly_production,
    )

    logic_engine = LogicEngine(logic_config, hero_config)
    game_state = GameState(
        account=Account(),
        villages=[village_after_upgrades],
        hero_info=hero_info
    )

    jobs = logic_engine.plan(game_state)

    build_jobs = [job for job in jobs if isinstance(job, BuildJob)]

    assert len(build_jobs) == 1

    build_job = build_jobs[0]
    assert build_job.building_gid == BuildingType.CLAY_PIT.gid
    assert build_job.target_level == 1
