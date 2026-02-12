from dataclasses import dataclass
from enum import Enum

from src.core.model.model import Resources, BuildingType, Tribe


@dataclass(frozen=True)
class Unit:
    """
    Represents a Travian unit with its stats, costs, and training requirements.
    
    Attributes:
        name: Unit name (e.g., "Legionnaire", "Phalanx")
        tribe: Tribe that can train this unit
        costs: Resource costs to train one unit
        attack: Attack value
        defense_vs_infantry: Defense value against infantry units
        defense_vs_cavalry: Defense value against cavalry units
        training_time_seconds: Time in seconds to train one unit (at level 1 barracks/stable)
        training_building: Type of building required for training (barracks, stable, or workshop)
        grain_consumption: Grain consumed per hour by one trained unit
    """
    name: str
    tribe: Tribe
    costs: Resources
    attack: int
    defense_vs_infantry: int
    defense_vs_cavalry: int
    training_time_seconds: int
    training_building: BuildingType
    grain_consumption: int = 1  # Default grain consumption, can be overridden


# Roman units
LEGIONNAIRE = Unit(
    name="Legionnaire",
    tribe=Tribe.ROMANS,
    costs=Resources(lumber=120, clay=100, iron=150, crop=30),
    attack=40,
    defense_vs_infantry=35,
    defense_vs_cavalry=50,
    training_time_seconds=2000,  # 0:33:20
    training_building=BuildingType.BARRACKS,
    grain_consumption=1,
)

# Gaul units
PHALANX = Unit(
    name="Phalanx",
    tribe=Tribe.GAULS,
    costs=Resources(lumber=100, clay=130, iron=55, crop=30),
    attack=15,
    defense_vs_infantry=40,
    defense_vs_cavalry=50,
    training_time_seconds=1040,  # 0:17:20
    training_building=BuildingType.BARRACKS,
    grain_consumption=1,
)


def get_units_for_tribe(tribe: Tribe) -> list[Unit]:
    """
    Get all units available for a specific tribe.
    
    Args:
        tribe: The tribe to get units for
        
    Returns:
        List of Unit objects available for the tribe
    """
    units_by_tribe: dict[Tribe, list[Unit]] = {
        Tribe.ROMANS: [LEGIONNAIRE],
        Tribe.GAULS: [PHALANX],
        Tribe.TEUTONS: [],
        Tribe.HUNS: [],
        Tribe.SPARTANS: [],
        Tribe.NORS: [],
        Tribe.EGYPTIANS: [],
    }
    return units_by_tribe.get(tribe, [])


def get_unit_by_name(unit_name: str, tribe: Tribe) -> Unit | None:
    """
    Get a unit by name for a specific tribe.
    
    Args:
        unit_name: The name of the unit (e.g., "Legionnaire")
        tribe: The tribe to search in
        
    Returns:
        Unit object if found, None otherwise
    """
    for unit in get_units_for_tribe(tribe):
        if unit.name == unit_name:
            return unit
    return None
