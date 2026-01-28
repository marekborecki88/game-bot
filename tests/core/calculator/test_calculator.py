from src.core.calculator.calculator import TravianCalculator
from src.core.model.model import Resources, BuildingCost


def test_warehouse_level_8_speed_5_mb_3():
    # Warehouse from level 7 to 8
    # Main Building at level 3
    # Server speed x5
    calc = TravianCalculator(version="4.6", speed=5)
    details = calc.get_building_details("Warehouse", 8, main_building_level=3)

    # Expected costs (calculated based on logic):
    # 130 * 1.28^7 = 731.8... -> 730
    # 160 * 1.28^7 = 900.7... -> 900
    # 90 * 1.28^7 = 506.6... -> 505
    # 40 * 1.28^7 = 225.1... -> 225
    # Expected time:
    # TimeT3(3875).value_at(8) = 3875 * 1.16^7 - (1875 * 1.16)
    # = 3875 * 2.8262... - 2175 = 10951.58... - 2175 = 8776.58...
    # MB factor (lvl 3) = 0.964^(3-1) = 0.929296
    # Time = 8776.58... * 0.929296 / 5 = 1631.18... -> 1631
    expected = BuildingCost(
        target_level=8,
        resources=Resources(lumber=730,
                            clay=900,
                            iron=505,
                            crop=225),
        total=2360,
        time_seconds=1631,
        time_formatted="00:27:11"
    )

    assert details == expected
