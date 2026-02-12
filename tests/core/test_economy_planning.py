"""Tests for economy planning strategies across different village development stages."""

import pytest
from src.config.config import (
    HeroConfig, LogicConfig, HeroAdventuresConfig, HeroResourcesConfig,
    AttributeAllocation
)
from src.core.model.model import (
    Building, BuildingType, Resources, ResourceType, Tribe, ResourcePit, BuildingQueue, BuildingJob
)
from src.core.model.village import Village
from src.core.strategy.defend_army_policy import DefendArmyPolicy


@pytest.fixture
def hero_config() -> HeroConfig:
    """Create a minimal HeroConfig for testing."""
    return HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=20, increase_difficulty=False),
        resources=HeroResourcesConfig(
            support_villages=False,
            attributes_ratio=AttributeAllocation(production_points=100),
            attributes_steps=AttributeAllocation(production_points=1),
        ),
    )


@pytest.fixture
def logic_config() -> LogicConfig:
    """Create a minimal LogicConfig for testing."""
    return LogicConfig(speed=1, strategy=None)


@pytest.fixture
def strategy(logic_config: LogicConfig, hero_config: HeroConfig) -> DefendArmyPolicy:
    return DefendArmyPolicy(logic_config, hero_config)


@pytest.fixture
def early_stage_village() -> Village:
    """Village in early stage: resource pits below level 5."""
    return Village(
        id=1,
        name="Early Village",
        coordinates=(0, 0),
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=100, clay=100, iron=100, crop=100),
        free_crop=50,
        resource_pits=[
            ResourcePit(id=1, type=ResourceType.LUMBER, level=2),
            ResourcePit(id=2, type=ResourceType.CLAY, level=2),
            ResourcePit(id=3, type=ResourceType.IRON, level=2),
            ResourcePit(id=4, type=ResourceType.CROP, level=1),
        ],
        buildings=[
            Building(id=1, level=2, type=BuildingType.MAIN_BUILDING),
            Building(id=2, level=10, type=BuildingType.WAREHOUSE),
            Building(id=3, level=10, type=BuildingType.GRANARY),
        ],
        warehouse_capacity=1000,
        granary_capacity=1000,
        building_queue=BuildingQueue(parallel_building_allowed=False),
        lumber_hourly_production=30,
        clay_hourly_production=30,
        iron_hourly_production=30,
        crop_hourly_production=40,
        free_crop_hourly_production=5,
        is_upgraded_to_city=False,
        is_permanent_capital=False,
    )


@pytest.fixture
def mid_stage_village() -> Village:
    """Village in mid stage: resource pits at level 5+."""
    return Village(
        id=2,
        name="Mid Village",
        coordinates=(1, 1),
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=500, clay=500, iron=500, crop=500),
        free_crop=200,
        resource_pits=[
            ResourcePit(id=1, type=ResourceType.LUMBER, level=5),
            ResourcePit(id=2, type=ResourceType.CLAY, level=5),
            ResourcePit(id=3, type=ResourceType.IRON, level=5),
            ResourcePit(id=4, type=ResourceType.CROP, level=5),
        ],
        buildings=[
            Building(id=1, level=5, type=BuildingType.MAIN_BUILDING),
            Building(id=2, level=15, type=BuildingType.WAREHOUSE),
            Building(id=3, level=15, type=BuildingType.GRANARY),
            Building(id=4, level=2, type=BuildingType.BARRACKS),
        ],
        warehouse_capacity=2000,
        granary_capacity=2000,
        building_queue=BuildingQueue(parallel_building_allowed=False),
        lumber_hourly_production=100,
        clay_hourly_production=100,
        iron_hourly_production=100,
        crop_hourly_production=120,
        free_crop_hourly_production=15,
        is_upgraded_to_city=False,
        is_permanent_capital=False,
    )


@pytest.fixture
def advanced_stage_village() -> Village:
    """Village in advanced stage: at least one resource type fully developed."""
    return Village(
        id=3,
        name="Advanced Village",
        coordinates=(2, 2),
        tribe=Tribe.ROMANS,
        resources=Resources(lumber=1000, clay=1000, iron=1000, crop=1000),
        free_crop=500,
        resource_pits=[
            ResourcePit(id=1, type=ResourceType.LUMBER, level=10),
            ResourcePit(id=2, type=ResourceType.CLAY, level=8),
            ResourcePit(id=3, type=ResourceType.IRON, level=8),
            ResourcePit(id=4, type=ResourceType.CROP, level=8),
        ],
        buildings=[
            Building(id=1, level=10, type=BuildingType.MAIN_BUILDING),
            Building(id=2, level=20, type=BuildingType.WAREHOUSE),
            Building(id=3, level=20, type=BuildingType.GRANARY),
            Building(id=4, level=5, type=BuildingType.SAWMILL),  # Level 5 needed for advanced
            Building(id=5, level=3, type=BuildingType.BARRACKS),
            Building(id=6, level=3, type=BuildingType.STABLE),
        ],
        warehouse_capacity=5000,
        granary_capacity=5000,
        building_queue=BuildingQueue(parallel_building_allowed=False),
        lumber_hourly_production=200,
        clay_hourly_production=180,
        iron_hourly_production=180,
        crop_hourly_production=240,
        free_crop_hourly_production=30,
        is_upgraded_to_city=False,
        is_permanent_capital=False,
    )


class TestEarlyStageEconomyPlanning:
    """Test economy planning for early stage villages."""

    def test_early_stage_detection(self, strategy: DefendArmyPolicy, early_stage_village: Village) -> None:
        """Verify that early stage village is correctly identified."""
        stage = strategy.estimate_village_development_stage(early_stage_village)
        assert stage == 'early'

    def test_early_stage_planning_focuses_on_pits_level_2(
        self, strategy: DefendArmyPolicy, early_stage_village: Village
    ) -> None:
        """Early stage planning should prioritize getting pits to level 2."""
        upgrades = strategy.plan_economy_upgrades_early_stage(early_stage_village)
        
        assert len(upgrades) > 0
        # Get pit buildings that are below level 2
        pit_types = {BuildingType.WOODCUTTER, BuildingType.CLAY_PIT, BuildingType.IRON_MINE}
        pit_upgrades = [building_type for building_type, _ in upgrades if building_type in pit_types]
        
        # Should have recommendations for pit upgrades
        assert len(pit_upgrades) > 0

    def test_early_stage_main_building_upgrade(
        self, strategy: DefendArmyPolicy, early_stage_village: Village
    ) -> None:
        """Early stage should include main building upgrade to level 5."""
        upgrades = strategy.plan_economy_upgrades_early_stage(early_stage_village)
        building_types = [bt for bt, _ in upgrades]
        
        assert BuildingType.MAIN_BUILDING in building_types

    def test_early_stage_returns_sorted_by_priority(
        self, strategy: DefendArmyPolicy, early_stage_village: Village
    ) -> None:
        """Upgrades should be sorted by priority (descending)."""
        upgrades = strategy.plan_economy_upgrades_early_stage(early_stage_village)
        
        priorities = [priority for _, priority in upgrades]
        assert priorities == sorted(priorities, reverse=True)


class TestMidStageEconomyPlanning:
    """Test economy planning for mid-stage villages."""

    def test_mid_stage_detection(self, strategy: DefendArmyPolicy, mid_stage_village: Village) -> None:
        """Verify that mid stage village is correctly identified."""
        stage = strategy.estimate_village_development_stage(mid_stage_village)
        assert stage == 'mid'

    def test_mid_stage_planning_with_roman_legionnaires(
        self, strategy: DefendArmyPolicy, mid_stage_village: Village
    ) -> None:
        """Mid stage planning should consider Legionnaire costs (120 lumber, 100 clay, 150 iron, 30 crop)."""
        planned_units = {"Legionnaire": 100}
        upgrades = strategy.plan_economy_upgrades_mid_stage(mid_stage_village, planned_units)
        
        # Iron should have higher priority due to high Legionnaire iron cost (150)
        iron_pits = [p for p in upgrades if p[0] == BuildingType.IRON_MINE]
        assert len(iron_pits) > 0

    def test_mid_stage_includes_secondary_buildings(
        self, strategy: DefendArmyPolicy, mid_stage_village: Village
    ) -> None:
        """Mid stage should include secondary production buildings."""
        planned_units = {"Legionnaire": 50}
        upgrades = strategy.plan_economy_upgrades_mid_stage(mid_stage_village, planned_units)
        building_types = [bt for bt, _ in upgrades]
        
        # Should include secondary buildings
        secondary = {BuildingType.SAWMILL, BuildingType.BRICKYARD, BuildingType.IRON_FOUNDRY}
        has_secondary = any(bt in secondary for bt in building_types)
        assert has_secondary

    def test_mid_stage_returns_sorted_by_priority(
        self, strategy: DefendArmyPolicy, mid_stage_village: Village
    ) -> None:
        """Mid stage upgrades should be sorted by priority (descending)."""
        planned_units = {"Legionnaire": 50}
        upgrades = strategy.plan_economy_upgrades_mid_stage(mid_stage_village, planned_units)
        
        priorities = [priority for _, priority in upgrades]
        assert priorities == sorted(priorities, reverse=True)


class TestAdvancedStageEconomyPlanning:
    """Test economy planning for advanced-stage villages."""

    def test_advanced_stage_detection(self, strategy: DefendArmyPolicy, advanced_stage_village: Village) -> None:
        """Verify that advanced stage village is correctly identified."""
        stage = strategy.estimate_village_development_stage(advanced_stage_village)
        assert stage == 'advanced'

    def test_advanced_stage_planning_prioritizes_secondary_buildings(
        self, strategy: DefendArmyPolicy, advanced_stage_village: Village
    ) -> None:
        """Advanced stage should prioritize secondary production buildings."""
        planned_units = {"Legionnaire": 100}
        upgrades = strategy.plan_economy_upgrades_advanced_stage(advanced_stage_village, planned_units)
        building_types = [bt for bt, _ in upgrades]
        
        # Secondary buildings should be included
        secondary = {BuildingType.BRICKYARD, BuildingType.IRON_FOUNDRY}
        has_secondary = any(bt in secondary for bt in building_types)
        assert has_secondary

    def test_advanced_stage_resource_specialization(
        self, strategy: DefendArmyPolicy, advanced_stage_village: Village
    ) -> None:
        """Advanced stage should specialize based on planned units."""
        # Legionnaires cost heavily in iron (150) and lumber (120)
        planned_units = {"Legionnaire": 100}
        upgrades = strategy.plan_economy_upgrades_advanced_stage(advanced_stage_village, planned_units)
        
        # Iron and lumber related buildings should have high priority
        building_types = [bt for bt, _ in upgrades]
        iron_or_lumber = {BuildingType.IRON_MINE, BuildingType.IRON_FOUNDRY, 
                         BuildingType.WOODCUTTER, BuildingType.SAWMILL}
        
        relevant = [bt for bt in building_types if bt in iron_or_lumber]
        assert len(relevant) > 0

    def test_advanced_stage_returns_sorted_by_priority(
        self, strategy: DefendArmyPolicy, advanced_stage_village: Village
    ) -> None:
        """Advanced stage upgrades should be sorted by priority (descending)."""
        planned_units = {"Legionnaire": 50}
        upgrades = strategy.plan_economy_upgrades_advanced_stage(advanced_stage_village, planned_units)
        
        priorities = [priority for _, priority in upgrades]
        assert priorities == sorted(priorities, reverse=True)


class TestResourceProportionEstimation:
    """Test resource production proportion calculation based on unit costs."""

    def test_empty_units_returns_balanced_proportions(self, strategy: DefendArmyPolicy) -> None:
        """Empty unit list should return balanced proportions (0.25 each)."""
        proportions = strategy.estimate_resource_production_proportions({})
        
        assert proportions[ResourceType.LUMBER] == 0.25
        assert proportions[ResourceType.CLAY] == 0.25
        assert proportions[ResourceType.IRON] == 0.25
        assert proportions[ResourceType.CROP] == 0.25

    def test_legionnaire_proportions(self, strategy: DefendArmyPolicy) -> None:
        """Legionnaire costs (120:100:150:30) should reflect in proportions."""
        # Legionnaire: lumber=120, clay=100, iron=150, crop=30 (total=400)
        proportions = strategy.estimate_resource_production_proportions({"Legionnaire": 100})
        
        # Expected: 120/400=0.3, 100/400=0.25, 150/400=0.375, 30/400=0.075
        assert abs(proportions[ResourceType.LUMBER] - 0.30) < 0.01
        assert abs(proportions[ResourceType.CLAY] - 0.25) < 0.01
        assert abs(proportions[ResourceType.IRON] - 0.375) < 0.01
        assert abs(proportions[ResourceType.CROP] - 0.075) < 0.01

    def test_proportions_sum_to_one(self, strategy: DefendArmyPolicy) -> None:
        """Proportions should always sum to 1.0."""
        proportions = strategy.estimate_resource_production_proportions({"Legionnaire": 50})
        
        total = sum(proportions.values())
        assert abs(total - 1.0) < 0.01


class TestEconomyUpgradePlanning:
    """Test the main plan_economy_upgrades method routing."""

    def test_early_stage_routing(
        self, strategy: DefendArmyPolicy, early_stage_village: Village
    ) -> None:
        """plan_economy_upgrades should route to early stage method for early villages."""
        upgrades = strategy.plan_economy_upgrades(early_stage_village)
        
        assert len(upgrades) > 0
        # Early stage focuses on basic pits, so we should see pit upgrades
        building_types = {bt for bt, _ in upgrades}
        primary_pits = {BuildingType.WOODCUTTER, BuildingType.CLAY_PIT, BuildingType.IRON_MINE}
        assert len(building_types & primary_pits) > 0

    def test_mid_stage_routing(self, strategy: DefendArmyPolicy, mid_stage_village: Village) -> None:
        """plan_economy_upgrades should route to mid stage method for mid villages."""
        planned_units = {"Legionnaire": 50}
        upgrades = strategy.plan_economy_upgrades(mid_stage_village, planned_units)
        
        assert len(upgrades) > 0

    def test_advanced_stage_routing(
        self, strategy: DefendArmyPolicy, advanced_stage_village: Village
    ) -> None:
        """plan_economy_upgrades should route to advanced stage method for advanced villages."""
        planned_units = {"Legionnaire": 100}
        upgrades = strategy.plan_economy_upgrades(advanced_stage_village, planned_units)
        
        assert len(upgrades) > 0
