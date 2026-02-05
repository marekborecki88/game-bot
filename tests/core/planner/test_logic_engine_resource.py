from __future__ import annotations

from src.config.config import LogicConfig, Strategy, HeroConfig, HeroAdventuresConfig, HeroResourcesConfig
from src.core.model.model import Account, GameState, HeroInfo, Resources, ResourceType, SourcePit, Tribe, Village, \
    BuildingQueue
from src.core.planner.logic_engine import LogicEngine


def _create_hero_config() -> HeroConfig:
    """Helper to create HeroConfig for tests."""
    return HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=False),
        resources=HeroResourcesConfig(
            support_villages=False,
            attributes_ratio={"fight": 3, "resources": 1},
            attributes_steps={},
        ),
    )


def test_lowest_resource_type_basic() -> None:
    logic_config = LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )
    hero_config = _create_hero_config()

    # ...existing code...
    village = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=100, clay=200, iron=300, crop=400),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    # Hero inventory: empty
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})

    game_state = GameState(
        account=Account(when_beginners_protection_expires=0),
        villages=[village],
        hero_info=hero,
    )

    build_jobs = LogicEngine(logic_config, hero_config).plan(game_state)

    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert job.target_name == ResourceType.LUMBER.name


def test_lowest_resource_type_with_hero_inventory() -> None:
    logic_config = LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )
    hero_config = _create_hero_config()

    # ...existing code...
    village = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=100, clay=200, iron=300, crop=400),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    # Hero inventory adds lumber only: L=500
    # Combined totals: L=600, C=200, I=300, Cr=400 -> lowest: CLAY
    hero = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        inventory={"lumber": 500, "clay": 0, "iron": 0, "crop": 0},
    )

    game_state = GameState(
        account=Account(when_beginners_protection_expires=0),
        villages=[village],
        hero_info=hero,
    )

    build_jobs = LogicEngine(logic_config, hero_config).plan(game_state)

    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert job.target_name == ResourceType.CLAY.name


def test_lowest_resource_type_balanced() -> None:
    logic_config = LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )
    hero_config = _create_hero_config()

    # ...existing code...
    village = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})

    game_state = GameState(
        account=Account(when_beginners_protection_expires=0),
        villages=[village],
        hero_info=hero,
    )

    build_jobs = LogicEngine(logic_config, hero_config).plan(game_state)

    # In the current implementation, even when global-lowest is "None", the planner
    # still picks an upgradable pit (fallback). For this test data it becomes LUMBER.
    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert job.target_name == ResourceType.LUMBER.name


def test_lowest_resource_type_with_multiple_villages() -> None:
    logic_config = LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )
    hero_config = _create_hero_config()

    # ...existing code...
    v1 = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=2000, iron=3000, crop=4000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    # Village V2 resources: all 50
    v2 = Village(
        id=2,
        name="V2",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=500, clay=500, iron=500, crop=500),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    # Combined totals: L=150, C=250, I=350, Cr=450 -> lowest: LUMBER
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})

    game_state = GameState(
        account=Account(when_beginners_protection_expires=0),
        villages=[v1, v2],
        hero_info=hero,
    )

    build_jobs = LogicEngine(logic_config, hero_config).plan(game_state)

    assert len(build_jobs) == 2

    # Ensure at least one scheduled build targets LUMBER.
    assert any(job.target_name == ResourceType.LUMBER.name for job in build_jobs)


#TODO: add case where one resource is extremely high and we shoulnd't upgrate right this one
#TODO: add case where two resource are extremely high and and 2 others are equal lowest
def test_lowest_resource_type_with_hero_inventory_only() -> None:
    logic_config = LogicConfig(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        speed=1,
    )
    hero_config = _create_hero_config()

    # ...existing code...
    village = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[],
        warehouse_capacity=100000,
        granary_capacity=100000,
        building_queue=BuildingQueue(
            parallel_building_allowed=False,
            in_jobs=[],
            out_jobs=[],
        ),
        lumber_hourly_production=10,
        clay_hourly_production=10,
        iron_hourly_production=10,
        crop_hourly_production=10,
    )

    # Hero inventory only: L=10, C=5, I=20, Cr=30 -> lowest: CLAY
    hero = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        inventory={"lumber": 1000, "clay": 5, "iron": 2000, "crop": 3000},
    )

    game_state = GameState(
        account=Account(when_beginners_protection_expires=0),
        villages=[village],
        hero_info=hero,
    )

    build_jobs = LogicEngine(logic_config, hero_config).plan(game_state)

    assert len(build_jobs) == 1

    job = build_jobs[0]
    assert job.target_name == ResourceType.CLAY.name
