from src.domain.calculator.calculator import TravianCalculator
from src.domain.model.model import Resources, BuildingCost


def test_warehouse_level_8_speed_5_mb_3():
    # Given
    calc = TravianCalculator(version="4.6", speed=10)

    # when
    details = calc.get_building_details("Cropland", 1, main_building_level=2)

    # Then
    expected = BuildingCost(
        target_level=1,
        resources=Resources(lumber=70,
                            clay=90,
                            iron=70,
                            crop=20),
        total=250,
        time_seconds=14,
        time_formatted="00:00:14"
    )
    assert details == expected
