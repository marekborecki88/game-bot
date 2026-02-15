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
def new_village() -> Village:
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
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=750, clay=750, iron=750, crop=750),
        free_crop=5,
        resource_pits=resource_pits,
        buildings=buildings,
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=building_queue,
        lumber_hourly_production=lumber_production,
        clay_hourly_production=clay_production,
        iron_hourly_production=iron_production,
        crop_hourly_production=crop_production,
        free_crop_hourly_production=crop_production - 2,  # -2 for base consumption
    )


def test_should_decide_to_build_iron_mine(logic_config: LogicConfig, hero_config: HeroConfig, hero_info: HeroInfo, new_village: Village):
    logic_engine = LogicEngine(logic_config, hero_config)
    game_state = GameState(
        account=Account(),
        villages=[new_village],
        hero_info=hero_info
    )

    jobs = logic_engine.plan(game_state)

    build_jobs = [job for job in jobs if isinstance(job, BuildJob)]

    assert len(build_jobs) == 1

    expected = {
        "building_gid": BuildingType.IRON_MINE.gid,
        "target_level": 1,
    }

    actual_job = build_jobs[0]
    assert {
        "building_gid": actual_job.building_gid,
        "target_level": actual_job.target_level,
    } == expected
