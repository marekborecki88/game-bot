from dataclasses import dataclass

from enum import Enum


@dataclass
class Village:
    name: str
    lumber: int
    clay: int
    iron: int
    crop: int
    free_crop: int
    source_pits: list[SourcePit]
    buildings: list[Building]
    warehouse_capacity: int
    granary_capacity: int
    building_queue: list[BuildingJob]


@dataclass
class Building:
    id: int
    level: int
    type: BuildingType


@dataclass
class SourcePit:
    id: int
    type: SourceType
    level: int


class SourceType(Enum):
    LUMBER = 1
    CLAY = 2
    IRON = 3
    CROP = 4


class BuildingType(Enum):
    MAIN_BUILDING = 15
    WAREHOUSE = 10
    GRANARY = 11
    RALLY_POINT = 16
    MARKETPLACE = 17
    EMBASSY = 18
    BARRACKS = 19
    STABLE = 20
    WORKSHOP = 21
    ACADEMY = 22
    CRANNY = 23
    TOWN_HALL = 24
    RESIDENCE = 25
    PALACE = 26
    TREASURY = 27
    TRADE_OFFICE = 28
    GREAT_BARRACKS = 29
    GREAT_STABLE = 30
    WALL = 31  # Different per tribe (31-33)
    STONEMASON = 34
    BREWERY = 35
    TRAPPER = 36
    HERO_MANSION = 37
    GREAT_WAREHOUSE = 38
    GREAT_GRANARY = 39
    WONDER_OF_THE_WORLD = 40
    HORSE_DRINKING_TROUGH = 41
    TOURNAMENT_SQUARE = 14


@dataclass
class BuildingJob:
    building_id: int
    target_level: int
    time_remaining: int