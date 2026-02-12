import pytest

from src.core.model.units import (
    LEGIONNAIRE,
    PHALANX,
    get_units_for_tribe,
    get_unit_by_name,
)
from src.core.model.model import Tribe, Resources
from src.core.calculator.calculator import TravianCalculator


class TestUnitDefinitions:
    """Tests for unit data definitions."""

    def test_legionnaire_stats(self) -> None:
        """Verify Legionnaire unit has correct stats."""
        assert LEGIONNAIRE.name == "Legionnaire"
        assert LEGIONNAIRE.tribe == Tribe.ROMANS
        assert LEGIONNAIRE.attack == 40
        assert LEGIONNAIRE.defense_vs_infantry == 35
        assert LEGIONNAIRE.defense_vs_cavalry == 50
        assert LEGIONNAIRE.training_time_seconds == 2000

    def test_legionnaire_costs(self) -> None:
        """Verify Legionnaire resource costs."""
        assert LEGIONNAIRE.costs.lumber == 120
        assert LEGIONNAIRE.costs.clay == 100
        assert LEGIONNAIRE.costs.iron == 150
        assert LEGIONNAIRE.costs.crop == 30
        assert LEGIONNAIRE.costs.total() == 400

    def test_legionnaire_training_building(self) -> None:
        """Verify Legionnaire is trained in barracks."""
        from src.core.model.model import BuildingType
        assert LEGIONNAIRE.training_building == BuildingType.BARRACKS

    def test_phalanx_stats(self) -> None:
        """Verify Phalanx unit has correct stats."""
        assert PHALANX.name == "Phalanx"
        assert PHALANX.tribe == Tribe.GAULS
        assert PHALANX.attack == 15
        assert PHALANX.defense_vs_infantry == 40
        assert PHALANX.defense_vs_cavalry == 50
        assert PHALANX.training_time_seconds == 1040

    def test_phalanx_costs(self) -> None:
        """Verify Phalanx resource costs."""
        assert PHALANX.costs.lumber == 100
        assert PHALANX.costs.clay == 130
        assert PHALANX.costs.iron == 55
        assert PHALANX.costs.crop == 30
        assert PHALANX.costs.total() == 315

    def test_phalanx_training_building(self) -> None:
        """Verify Phalanx is trained in barracks."""
        from src.core.model.model import BuildingType
        assert PHALANX.training_building == BuildingType.BARRACKS

    def test_unit_is_frozen(self) -> None:
        """Verify Unit dataclass is immutable."""
        with pytest.raises(AttributeError):
            LEGIONNAIRE.attack = 50

    def test_resources_is_frozen(self) -> None:
        """Verify Resources dataclass is immutable."""
        with pytest.raises(AttributeError):
            LEGIONNAIRE.costs.lumber = 999


class TestUnitRegistry:
    """Tests for unit retrieval functions."""

    def test_get_units_for_romans(self) -> None:
        """Verify Romans can train Legionnaire."""
        units = get_units_for_tribe(Tribe.ROMANS)
        assert len(units) == 1
        assert units[0] == LEGIONNAIRE

    def test_get_units_for_gauls(self) -> None:
        """Verify Gauls can train Phalanx."""
        units = get_units_for_tribe(Tribe.GAULS)
        assert len(units) == 1
        assert units[0] == PHALANX

    def test_get_units_for_unsupported_tribe(self) -> None:
        """Verify unsupported tribes return empty list."""
        units = get_units_for_tribe(Tribe.TEUTONS)
        assert units == []

    def test_get_unit_by_name_legionnaire(self) -> None:
        """Verify Legionnaire can be found by name for Romans."""
        unit = get_unit_by_name("Legionnaire", Tribe.ROMANS)
        assert unit == LEGIONNAIRE

    def test_get_unit_by_name_phalanx(self) -> None:
        """Verify Phalanx can be found by name for Gauls."""
        unit = get_unit_by_name("Phalanx", Tribe.GAULS)
        assert unit == PHALANX

    def test_get_unit_by_name_not_found(self) -> None:
        """Verify non-existent unit returns None."""
        unit = get_unit_by_name("Legionnaire", Tribe.GAULS)
        assert unit is None

    def test_get_unit_by_name_wrong_tribe(self) -> None:
        """Verify unit from different tribe returns None."""
        unit = get_unit_by_name("Phalanx", Tribe.ROMANS)
        assert unit is None


class TestResourcesCalculations:
    """Tests for Resources utility calculations."""

    @pytest.mark.parametrize(
        "lumber,clay,iron,crop,expected_total",
        [
            (120, 100, 150, 30, 400),  # Legionnaire
            (100, 130, 55, 30, 315),   # Phalanx
            (0, 0, 0, 0, 0),
            (1, 1, 1, 1, 4),
        ],
    )
    def test_resources_total_calculation(
        self, lumber: int, clay: int, iron: int, crop: int, expected_total: int
    ) -> None:
        """Verify Resources.total() returns correct sum."""
        resources = Resources(lumber=lumber, clay=clay, iron=iron, crop=crop)
        assert resources.total() == expected_total

    def test_count_how_many_can_be_made_legionnaire_full_cost(self) -> None:
        """Verify count with exact resources for one unit."""
        available = Resources(lumber=120, clay=100, iron=150, crop=30)
        cost = Resources(lumber=120, clay=100, iron=150, crop=30)
        assert available.count_how_many_can_be_made(cost) == 1

    def test_count_how_many_can_be_made_legionnaire_doubled(self) -> None:
        """Verify count with doubled resources."""
        available = Resources(lumber=240, clay=200, iron=300, crop=60)
        cost = Resources(lumber=120, clay=100, iron=150, crop=30)
        assert available.count_how_many_can_be_made(cost) == 2

    def test_count_how_many_can_be_made_bottleneck_crop(self) -> None:
        """Verify bottleneck resource limits the count."""
        available = Resources(lumber=1000, clay=1000, iron=1000, crop=30)
        cost = Resources(lumber=120, clay=100, iron=150, crop=30)
        assert available.count_how_many_can_be_made(cost) == 1

    def test_count_how_many_can_be_made_insufficient_resources(self) -> None:
        """Verify zero count when insufficient resources."""
        available = Resources(lumber=50, clay=50, iron=50, crop=50)
        cost = Resources(lumber=120, clay=100, iron=150, crop=30)
        assert available.count_how_many_can_be_made(cost) == 0

    def test_count_how_many_can_be_made_zero_resources(self) -> None:
        """Verify zero count with no resources."""
        available = Resources(lumber=0, clay=0, iron=0, crop=0)
        cost = Resources(lumber=120, clay=100, iron=150, crop=30)
        assert available.count_how_many_can_be_made(cost) == 0

    def test_count_how_many_can_be_made_partial_costs(self) -> None:
        """Verify count when some costs are zero."""
        available = Resources(lumber=100, clay=0, iron=0, crop=0)
        cost = Resources(lumber=10, clay=0, iron=0, crop=0)
        assert available.count_how_many_can_be_made(cost) == 10


class TestUnitTrainingTime:
    """Tests for unit training time calculation based on building level."""

    def test_calculate_unit_training_time_level_1(self) -> None:
        """Verify training time at level 1 building (100% speed)."""
        calculator = TravianCalculator()
        # Legionnaire base time: 2000 seconds at level 1 building (100% speed)
        training_time = calculator.calculate_unit_training_time(LEGIONNAIRE.training_time_seconds, 1)
        assert training_time == 2000

    def test_calculate_unit_training_time_level_2(self) -> None:
        """Verify training time at level 2 building (90% speed)."""
        calculator = TravianCalculator()
        # Legionnaire at level 2: 2000 * 0.9 = 1800 seconds
        training_time = calculator.calculate_unit_training_time(LEGIONNAIRE.training_time_seconds, 2)
        assert training_time == 1800

    def test_calculate_unit_training_time_level_20(self) -> None:
        """Verify training time at level 20 building (14% speed)."""
        calculator = TravianCalculator()
        # Legionnaire at level 20: 2000 * 0.14 = 280 seconds
        training_time = calculator.calculate_unit_training_time(LEGIONNAIRE.training_time_seconds, 20)
        assert training_time == 280

    def test_calculate_unit_training_time_level_0(self) -> None:
        """Verify training time with no building returns 0."""
        calculator = TravianCalculator()
        training_time = calculator.calculate_unit_training_time(LEGIONNAIRE.training_time_seconds, 0)
        assert training_time == 0

    def test_calculate_unit_training_time_phalanx_level_1(self) -> None:
        """Verify Phalanx training time at level 1 building."""
        calculator = TravianCalculator()
        # Phalanx base time: 1040 seconds at level 1 building
        training_time = calculator.calculate_unit_training_time(PHALANX.training_time_seconds, 1)
        assert training_time == 1040

    def test_calculate_unit_training_time_phalanx_level_5(self) -> None:
        """Verify Phalanx training time at level 5 building (66% speed)."""
        calculator = TravianCalculator()
        # Phalanx at level 5: 1040 * 0.66 = 686.4 ≈ 686 seconds
        training_time = calculator.calculate_unit_training_time(PHALANX.training_time_seconds, 5)
        assert training_time == 686

    @pytest.mark.parametrize(
        "building_level,expected_multiplier",
        [
            (1, 1.0),
            (2, 0.9),
            (3, 0.81),
            (5, 0.66),
            (10, 0.39),
            (20, 0.14),
        ],
    )
    def test_calculate_unit_training_time_multipliers(
        self, building_level: int, expected_multiplier: float
    ) -> None:
        """Verify training time multipliers for different building levels."""
        calculator = TravianCalculator()
        base_time = 1000
        expected_time = round(base_time * expected_multiplier)
        actual_time = calculator.calculate_unit_training_time(base_time, building_level)
        assert actual_time == expected_time

    def test_calculate_unit_training_time_with_speed_multiplier(self) -> None:
        """Verify training time calculation respects server speed multiplier."""
        calculator = TravianCalculator(speed=2)  # 2x speed server
        # With 2x speed, time should be halved
        training_time = calculator.calculate_unit_training_time(LEGIONNAIRE.training_time_seconds, 1)
        assert training_time == 1000  # 2000 * 1.0 / 2


class TestTrainableUnitsPerHour:
    """Tests for calculating trainable units based on hourly resource production."""

    def test_estimate_trainable_units_per_hour_legionnaire_full_resources(self) -> None:
        """Verify Legionnaire trainable units when all resources are produced."""
        from src.core.strategy.strategy import Strategy
        
        # Create a dummy strategy instance to access methods
        strategy = Strategy.__new__(Strategy)
        
        # Legionnaire costs: lumber=120, clay=100, iron=150, crop=30
        # With hourly production of 120, 100, 150, 30 - should train 1 per hour
        hourly_production = Resources(lumber=120, clay=100, iron=150, crop=30)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.ROMANS, hourly_production)
        
        assert trainable.get("Legionnaire", 0) == 1

    def test_estimate_trainable_units_per_hour_legionnaire_doubled_resources(self) -> None:
        """Verify Legionnaire trainable units with doubled resource production."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # With doubled resources, should train 2 per hour
        hourly_production = Resources(lumber=240, clay=200, iron=300, crop=60)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.ROMANS, hourly_production)
        
        assert trainable.get("Legionnaire", 0) == 2

    def test_estimate_trainable_units_per_hour_legionnaire_bottleneck_crop(self) -> None:
        """Verify Legionnaire trainable limited by crop production."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Legionnaire costs crop=30, so with crop=30 can only train 1
        # Even with unlimited other resources
        hourly_production = Resources(lumber=1000, clay=1000, iron=1000, crop=30)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.ROMANS, hourly_production)
        
        assert trainable.get("Legionnaire", 0) == 1

    def test_estimate_trainable_units_per_hour_legionnaire_insufficient_resources(self) -> None:
        """Verify no units trainable when resources insufficient."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # With insufficient resources, nothing can be trained
        hourly_production = Resources(lumber=50, clay=50, iron=50, crop=50)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.ROMANS, hourly_production)
        
        assert trainable.get("Legionnaire", 0) == 0

    def test_estimate_trainable_units_per_hour_gauls_phalanx(self) -> None:
        """Verify Phalanx trainable for Gauls."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Phalanx costs: lumber=100, clay=130, iron=55, crop=30
        hourly_production = Resources(lumber=100, clay=130, iron=55, crop=30)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.GAULS, hourly_production)
        
        assert trainable.get("Phalanx", 0) == 1

    def test_estimate_trainable_units_per_hour_unsupported_tribe(self) -> None:
        """Verify empty dict for tribes with no units."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        hourly_production = Resources(lumber=100, clay=100, iron=100, crop=100)
        trainable = strategy.estimate_trainable_units_per_hour(Tribe.TEUTONS, hourly_production)
        
        assert trainable == {}


class TestPotentialProductionPerHour:
    """Tests for calculating potential military strength production per hour."""

    def test_estimate_potential_attack_per_hour_legionnaire(self) -> None:
        """Verify potential attack production per hour for Legionnaire."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Can train 1 Legionnaire per hour, attack=40
        hourly_production = Resources(lumber=120, clay=100, iron=150, crop=30)
        attack = strategy.estimate_potential_attack_per_hour(Tribe.ROMANS, hourly_production)
        
        assert attack == 40

    def test_estimate_potential_defense_infantry_per_hour_legionnaire(self) -> None:
        """Verify potential defense vs infantry production per hour."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Can train 1 Legionnaire per hour, defense_vs_infantry=35
        hourly_production = Resources(lumber=120, clay=100, iron=150, crop=30)
        defense = strategy.estimate_potential_defense_infantry_per_hour(Tribe.ROMANS, hourly_production)
        
        assert defense == 35

    def test_estimate_potential_defense_cavalry_per_hour_legionnaire(self) -> None:
        """Verify potential defense vs cavalry production per hour."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Can train 1 Legionnaire per hour, defense_vs_cavalry=50
        hourly_production = Resources(lumber=120, clay=100, iron=150, crop=30)
        defense = strategy.estimate_potential_defense_cavalry_per_hour(Tribe.ROMANS, hourly_production)
        
        assert defense == 50

    def test_estimate_potential_attack_per_hour_doubled_production(self) -> None:
        """Verify potential attack with doubled resource production."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        # Can train 2 Legionnaire per hour, attack=40 each, total=80
        hourly_production = Resources(lumber=240, clay=200, iron=300, crop=60)
        attack = strategy.estimate_potential_attack_per_hour(Tribe.ROMANS, hourly_production)
        
        assert attack == 80

    def test_estimate_potential_production_zero_resources(self) -> None:
        """Verify zero production when no resources produced."""
        from src.core.strategy.strategy import Strategy
        
        strategy = Strategy.__new__(Strategy)
        
        hourly_production = Resources(lumber=0, clay=0, iron=0, crop=0)
        attack = strategy.estimate_potential_attack_per_hour(Tribe.ROMANS, hourly_production)
        
        assert attack == 0
