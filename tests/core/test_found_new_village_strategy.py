from src.config.config import LogicConfig, HeroConfig, AttributeAllocation, HeroAdventuresConfig, HeroResourcesConfig
from src.core.calculator.calculator import TravianCalculator
from src.core.job.found_new_village_job import FoundNewVillageJob
from src.core.model.model import (
    GameState, Village, Resources, Tribe, BuildingQueue, HeroInfo, HeroAttributes, Account
)
from src.core.strategy.balanced_economic_growth import BalancedEconomicGrowth


def test_strategy_creates_found_new_village_job_when_settlers_available() -> None:
    # Given
    logic_config = LogicConfig(
        speed=3,
        strategy=None,
        minimum_storage_capacity_in_hours=2,
        daily_quest_threshold=50,
    )

    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=True),
        resources=HeroResourcesConfig(
            support_villages=True,
            attributes_ratio=AttributeAllocation(production_points=100),
            attributes_steps=AttributeAllocation(production_points=5),
        ),
    )

    strategy = BalancedEconomicGrowth(logic_config, hero_config)
    calculator = TravianCalculator(speed=3)

    # Create a village with 3 settlers
    village = Village(
        id=1,
        name="MainVillage",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=100,
        source_pits=[],
        buildings=[],
        warehouse_capacity=5000,
        granary_capacity=5000,
        building_queue=BuildingQueue(parallel_building_allowed=True),
        troops={"Settlers": 3, "Legionnaire": 10},
    )

    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=0,
            production_points=0,
        ),
        points_available=0,
        inventory={},
        has_daily_quest_indicator=False,
    )

    game_state = GameState(
        villages=[village],
        hero_info=hero_info,
        account=Account(),
    )

    # When
    jobs = strategy.plan_jobs(game_state, calculator)

    # Then
    found_village_jobs = [job for job in jobs if isinstance(job, FoundNewVillageJob)]
    assert len(found_village_jobs) == 1
    assert found_village_jobs[0].village_id == 1
    assert found_village_jobs[0].village_name == "MainVillage"


def test_strategy_does_not_create_found_new_village_job_when_settlers_insufficient() -> None:
    # Given
    logic_config = LogicConfig(
        speed=3,
        strategy=None,
        minimum_storage_capacity_in_hours=2,
        daily_quest_threshold=50,
    )

    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=True),
        resources=HeroResourcesConfig(
            support_villages=True,
            attributes_ratio=AttributeAllocation(production_points=100),
            attributes_steps=AttributeAllocation(production_points=5),
        ),
    )

    strategy = BalancedEconomicGrowth(logic_config, hero_config)
    calculator = TravianCalculator(speed=3)

    # Create a village with only 2 settlers
    village = Village(
        id=1,
        name="MainVillage",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=100,
        source_pits=[],
        buildings=[],
        warehouse_capacity=5000,
        granary_capacity=5000,
        building_queue=BuildingQueue(parallel_building_allowed=True),
        troops={"Settlers": 2, "Legionnaire": 10},
    )

    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=0,
            production_points=0,
        ),
        points_available=0,
        inventory={},
        has_daily_quest_indicator=False,
    )

    game_state = GameState(
        villages=[village],
        hero_info=hero_info,
        account=Account(),
    )

    # When
    jobs = strategy.plan_jobs(game_state, calculator)

    # Then
    found_village_jobs = [job for job in jobs if isinstance(job, FoundNewVillageJob)]
    assert len(found_village_jobs) == 0


def test_strategy_does_not_create_found_new_village_job_when_no_settlers() -> None:
    # Given
    logic_config = LogicConfig(
        speed=3,
        strategy=None,
        minimum_storage_capacity_in_hours=2,
        daily_quest_threshold=50,
    )

    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=True),
        resources=HeroResourcesConfig(
            support_villages=True,
            attributes_ratio=AttributeAllocation(production_points=100),
            attributes_steps=AttributeAllocation(production_points=5),
        ),
    )

    strategy = BalancedEconomicGrowth(logic_config, hero_config)
    calculator = TravianCalculator(speed=3)

    # Create a village without settlers
    village = Village(
        id=1,
        name="MainVillage",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=100,
        source_pits=[],
        buildings=[],
        warehouse_capacity=5000,
        granary_capacity=5000,
        building_queue=BuildingQueue(parallel_building_allowed=True),
        troops={"Legionnaire": 10},
    )

    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=0,
            production_points=0,
        ),
        points_available=0,
        inventory={},
        has_daily_quest_indicator=False,
    )

    game_state = GameState(
        villages=[village],
        hero_info=hero_info,
        account=Account(),
    )

    # When
    jobs = strategy.plan_jobs(game_state, calculator)

    # Then
    found_village_jobs = [job for job in jobs if isinstance(job, FoundNewVillageJob)]
    assert len(found_village_jobs) == 0

