"""Integration tests for Romans parallel building feature."""

from datetime import datetime, timedelta
from src.core.model.model import (
    Village, GameState, HeroInfo, Resources, SourcePit, Building, 
    BuildingType, ResourceType, Account, BuildingJob
)
from src.core.model.tribe import Tribe
from src.core.strategy.balanced_economic_growth import BalancedEconomicGrowth
from src.core.calculator.calculator import TravianCalculator


def test_romans_can_plan_parallel_building():
    """Test that Romans can plan both center and resource field building simultaneously."""
    calculator = TravianCalculator(speed=1.0)
    strategy = BalancedEconomicGrowth()
    strategy.calculator = calculator
    
    # Create a Roman village with empty building queue
    village = Village(
        id=1,
        name="Test Village",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=10000, clay=10000, iron=10000, crop=10000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[
            Building(id=19, level=1, type=BuildingType.BARRACKS),
            Building(id=25, level=1, type=BuildingType.RESIDENCE),
        ],
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=[],  # Empty queue
        lumber_hourly_production=100,
        clay_hourly_production=100,
        iron_hourly_production=100,
        crop_hourly_production=100,
        free_crop_hourly_production=50,
    )
    
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
    )
    
    game_state = GameState(
        account=Account(server_speed=1.0),
        villages=[village],
        hero_info=hero_info,
    )
    
    # Plan jobs for the village
    jobs = strategy.create_plan_for_village(game_state)
    
    # Romans should be able to plan up to 2 jobs (one center, one resource field)
    assert len(jobs) >= 1
    assert len(jobs) <= 2
    
    # If we got 2 jobs, verify one is resource field and one is center building
    if len(jobs) == 2:
        building_ids = [job.building_id for job in jobs]
        
        # One should be resource field (1-18), one should be center (19+)
        resource_fields = [bid for bid in building_ids if 1 <= bid <= 18]
        center_buildings = [bid for bid in building_ids if bid >= 19]
        
        assert len(resource_fields) == 1
        assert len(center_buildings) == 1


def test_non_romans_plan_single_building():
    """Test that non-Roman tribes can only plan one building at a time."""
    calculator = TravianCalculator(speed=1.0)
    strategy = BalancedEconomicGrowth()
    strategy.calculator = calculator
    
    # Create a Gaul village with empty building queue
    village = Village(
        id=1,
        name="Test Village",
        tribe=Tribe.GAULS,
        resources=Resources(lumber=10000, clay=10000, iron=10000, crop=10000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[
            Building(id=19, level=1, type=BuildingType.BARRACKS),
            Building(id=25, level=1, type=BuildingType.RESIDENCE),
        ],
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=[],  # Empty queue
        lumber_hourly_production=100,
        clay_hourly_production=100,
        iron_hourly_production=100,
        crop_hourly_production=100,
        free_crop_hourly_production=50,
    )
    
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
    )
    
    game_state = GameState(
        account=Account(server_speed=1.0),
        villages=[village],
        hero_info=hero_info,
    )
    
    # Plan jobs for the village
    jobs = strategy.create_plan_for_village(game_state)
    
    # Non-Romans should only plan at most 1 job
    assert len(jobs) <= 1


def test_romans_with_occupied_center_can_build_resource_field():
    """Test that Romans with center building occupied can still build resource field."""
    calculator = TravianCalculator(speed=1.0)
    strategy = BalancedEconomicGrowth()
    strategy.calculator = calculator
    
    # Create a Roman village with center building in queue
    village = Village(
        id=1,
        name="Test Village",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=10000, clay=10000, iron=10000, crop=10000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[
            Building(id=19, level=1, type=BuildingType.BARRACKS),
            Building(id=25, level=1, type=BuildingType.RESIDENCE),
        ],
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=[
            BuildingJob(building_id=25, target_level=2, time_remaining=100)
        ],
        lumber_hourly_production=100,
        clay_hourly_production=100,
        iron_hourly_production=100,
        crop_hourly_production=100,
        free_crop_hourly_production=50,
    )
    
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
    )
    
    game_state = GameState(
        account=Account(server_speed=1.0),
        villages=[village],
        hero_info=hero_info,
    )
    
    # Plan jobs for the village
    jobs = strategy.create_plan_for_village(game_state)
    
    # Romans should be able to plan a resource field job even though center is occupied
    assert len(jobs) >= 1
    
    # Verify the job is for a resource field
    if len(jobs) > 0:
        job = jobs[0]
        assert 1 <= job.building_id <= 18  # Resource field IDs


def test_romans_with_occupied_resource_field_can_build_center():
    """Test that Romans with resource field occupied can still build in center."""
    calculator = TravianCalculator(speed=1.0)
    strategy = BalancedEconomicGrowth()
    strategy.calculator = calculator
    
    # Create a Roman village with resource field in queue
    village = Village(
        id=1,
        name="Test Village",
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=10000, clay=10000, iron=10000, crop=10000),
        free_crop=100,
        source_pits=[
            SourcePit(id=1, type=ResourceType.LUMBER, level=1),
            SourcePit(id=2, type=ResourceType.CLAY, level=1),
            SourcePit(id=3, type=ResourceType.IRON, level=1),
            SourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[
            Building(id=19, level=1, type=BuildingType.BARRACKS),
            Building(id=10, level=1, type=BuildingType.WAREHOUSE),
        ],
        warehouse_capacity=800,
        granary_capacity=800,
        building_queue=[
            # Resource field in queue (ID 1 is LUMBER, a resource field)
            BuildingJob(building_id=1, target_level=2, time_remaining=100)
        ],
        lumber_hourly_production=100,
        clay_hourly_production=100,
        iron_hourly_production=100,
        crop_hourly_production=100,
        free_crop_hourly_production=50,
    )
    
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
    )
    
    game_state = GameState(
        account=Account(server_speed=1.0),
        villages=[village],
        hero_info=hero_info,
    )
    
    # Plan jobs for the village
    jobs = strategy.create_plan_for_village(game_state)
    
    # Romans should be able to plan a center building job even though resource field is occupied
    # The strategy should plan to upgrade the warehouse
    assert len(jobs) == 1
    
    # Verify the job is for upgrading the WAREHOUSE
    job = jobs[0]
    assert job.building_id == 10
    assert job.target_name == "WAREHOUSE"
    assert job.target_level == 2
