import pytest
from src.core.model.model import Village, SourceType, GameState, HeroInfo, Tribe
from src.core.planner.logic_engine import LogicEngine

class DummyBuilding:
    def __init__(self):
        self.level = 1
        self.type = None
        self.id = 1

@pytest.fixture
def empty_hero():
    return HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})

@pytest.fixture
def base_village():
    return Village(
        id=1,
        name="TestVillage",
        tribe=Tribe.ROMANS,
        lumber=100,
        clay=200,
        iron=300,
        crop=400,
        free_crop=0,
        source_pits=[],
        buildings=[],
        warehouse_capacity=1000,
        granary_capacity=1000,
        building_queue=[],
    )

def test_lowest_resource_type_basic(empty_hero, base_village):
    gs = GameState(account=None, villages=[base_village], hero_info=empty_hero)
    engine = LogicEngine()
    assert engine.find_lowest_resource_type_in_all(gs) == SourceType.LUMBER

def test_lowest_resource_type_with_hero_inventory(base_village):
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={
        'lumber': 500,
        'clay': 0,
        'iron': 0,
        'crop': 0
    })
    gs = GameState(account=None, villages=[base_village], hero_info=hero)
    engine = LogicEngine()
    # Now lumber is 100+500=600, so clay is lowest
    assert engine.find_lowest_resource_type_in_all(gs) == SourceType.CLAY

def test_lowest_resource_type_balanced(empty_hero):
    v1 = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        lumber=100,
        clay=100,
        iron=100,
        crop=100,
        free_crop=0,
        source_pits=[],
        buildings=[],
        warehouse_capacity=1000,
        granary_capacity=1000,
        building_queue=[],
    )
    gs = GameState(account=None, villages=[v1], hero_info=empty_hero)
    engine = LogicEngine()
    # All resources equal, should return None
    assert engine.find_lowest_resource_type_in_all(gs) is None

def test_lowest_resource_type_with_multiple_villages(empty_hero):
    v1 = Village(
        id=1,
        name="V1",
        tribe=Tribe.ROMANS,
        lumber=100,
        clay=200,
        iron=300,
        crop=400,
        free_crop=0,
        source_pits=[],
        buildings=[],
        warehouse_capacity=1000,
        granary_capacity=1000,
        building_queue=[],
    )
    v2 = Village(
        id=2,
        name="V2",
        tribe=Tribe.ROMANS,
        lumber=50,
        clay=50,
        iron=50,
        crop=50,
        free_crop=0,
        source_pits=[],
        buildings=[],
        warehouse_capacity=1000,
        granary_capacity=1000,
        building_queue=[],
    )
    gs = GameState(account=None, villages=[v1, v2], hero_info=empty_hero)
    engine = LogicEngine()
    # lumber: 150, clay: 250, iron: 350, crop: 450
    assert engine.find_lowest_resource_type_in_all(gs) == SourceType.LUMBER

def test_lowest_resource_type_with_hero_inventory_only():
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={
        'lumber': 10,
        'clay': 5,
        'iron': 20,
        'crop': 30
    })
    gs = GameState(account=None, villages=[], hero_info=hero)
    engine = LogicEngine()
    assert engine.find_lowest_resource_type_in_all(gs) == SourceType.CLAY

