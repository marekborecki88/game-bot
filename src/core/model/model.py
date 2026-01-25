import logging
from dataclasses import dataclass, field

from enum import Enum
from playwright.sync_api import Page

from src.config import Config

logger = logging.getLogger(__name__)


@dataclass
class BuildingContract:
    lumber: int
    clay: int
    iron: int
    crop: int
    crop_consumption: int


def scan_contract(page: Page) -> BuildingContract:

    resource_wrapper = page.locator(".resourceWrapper")
    resource_values = resource_wrapper.locator(".inlineIcon.resource .value").all_text_contents()

    lumber = int(resource_values[0])
    clay = int(resource_values[1])
    iron = int(resource_values[2])
    crop = int(resource_values[3])
    crop_consumption = int(resource_values[4])

    return BuildingContract(
        lumber=lumber,
        clay=clay,
        iron=iron,
        crop=crop,
        crop_consumption=crop_consumption
    )

@dataclass
class Account:
    server_speed: float
    when_beginners_protection_expires: int = 0


@dataclass
class HeroInfo:
    health: int
    experience: int
    adventures: int
    is_available: bool
    points_available: int = 0
    inventory: dict = field(default_factory=dict)


@dataclass
class Village:
    id: int
    name: str
    tribe: Tribe
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
    lumber_hourly_production: int = 2000
    clay_hourly_production: int = 2000
    iron_hourly_production: int = 2000
    crop_hourly_production: int = 2000
    max_source_pit_level: int = 10

    def build(self, page: Page, config: Config, id: int):
        source_pit = next((s for s in self.source_pits if s.id == id), None)
        if not source_pit:
            return

        page.goto(f"{config.server_url}/build.php?id={id}&gid={source_pit.type.value}")
        page.wait_for_selector("#contract ")

        logger.info("Scanning building contract...")
        contract = scan_contract(page)

        logger.debug("Contract details: %s", contract)

        # Click the upgrade button (first one, not the video feature button)
        upgrade_button = page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        logger.info("Clicked upgrade button")

    def building_queue_is_empty(self):
        return len(self.building_queue) == 0

    def lowest_source(self) -> SourceType:
        source_dict = {
            SourceType.LUMBER: self.lumber,
            SourceType.CLAY: self.clay,
            SourceType.IRON: self.iron,
            SourceType.CROP: self.crop,
        }
        
        return min(source_dict, key=source_dict.get)

    def pit_with_lowest_level_building(self, lowest_source: SourceType):
        pits_with_given_type = [pit for pit in self.source_pits if pit.type == lowest_source]
        return min(pits_with_given_type, key=lambda p: p.level)

    def building_queue_duration(self):
        if not self.building_queue:
            return 0
        return max(self.building_queue, key=lambda job: job.time_remaining).time_remaining

    def lumber_24h_ratio(self) -> float:
        return self.warehouse_capacity / (self.lumber_hourly_production * 24)

    def clay_24h_ratio(self) -> float:
        return self.warehouse_capacity / (self.clay_hourly_production * 24)

    def iron_24h_ratio(self) -> float:
        return self.warehouse_capacity / (self.iron_hourly_production * 24)

    def crop_24h_ratio(self) -> float:
        return self.granary_capacity / (self.crop_hourly_production * 24)

    def warehouse_min_ratio(self) -> float:
        """Lowest ratio among warehouse resources - the bottleneck."""
        return min(self.lumber_24h_ratio(), self.clay_24h_ratio(), self.iron_24h_ratio())

    def granary_min_ratio(self) -> float:
        return self.crop_24h_ratio()

    def get_building(self, building_type: BuildingType) -> Building | None:
        return next((b for b in self.buildings if b.type == building_type), None)

    def upgradable_source_pits(self) -> list[SourcePit]:
        return [p for p in self.source_pits if p.level < self.max_source_pit_level]


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

class Tribe(Enum):
    ROMANS = 1
    TEUTONS = 2
    GAULS = 3
    HUNS = 4
    SPARTANS = 5
    NORS = 6
    EGYPTIANS = 7

class SourceType(Enum):
    # (gid, max_level)
    LUMBER = (1, 10)
    CLAY = (2, 10)
    IRON = (3, 10)
    CROP = (4, 10)

    def __init__(self, gid: int, max_level: int):
        self.gid = gid
        self.max_level = max_level


class BuildingType(Enum):
    # (gid, max_level)
    # Resources
    WOODCUTTER = (1, 10)
    CLAY_PIT = (2, 10)
    IRON_MINE = (3, 10)
    CROPLAND = (4, 10)
    SAWMILL = (5, 5)
    BRICKYARD = (6, 5)
    IRON_FOUNDRY = (7, 5)
    GRAIN_MILL = (8, 5)
    BAKERY = (9, 5)

    # Infrastructure
    WAREHOUSE = (10, 20)
    GRANARY = (11, 20)
    MAIN_BUILDING = (15, 20)
    MARKETPLACE = (17, 20)
    EMBASSY = (18, 20)
    CRANNY = (23, 10)
    TOWN_HALL = (24, 20)
    RESIDENCE = (25, 20)
    PALACE = (26, 20)
    TREASURY = (27, 20)
    TRADE_OFFICE = (28, 20)
    STONEMASONS_LODGE = (34, 20)
    BREWERY = (35, 20)
    GREAT_WAREHOUSE = (38, 20)
    GREAT_GRANARY = (39, 20)
    WONDER_OF_THE_WORLD = (40, 100)
    HORSE_DRINKING_TROUGH = (41, 20)
    COMMAND_CENTER = (44, 20)
    WATERWORKS = (45, 20)

    # Military
    SMITHY = (13, 20)
    TOURNAMENT_SQUARE = (14, 20)
    RALLY_POINT = (16, 20)
    BARRACKS = (19, 20)
    STABLE = (20, 20)
    WORKSHOP = (21, 20)
    ACADEMY = (22, 20)
    GREAT_BARRACKS = (29, 20)
    GREAT_STABLE = (30, 20)
    CITY_WALL = (31, 20)
    EARTH_WALL = (32, 20)
    PALISADE = (33, 20)
    TRAPPER = (36, 20)
    HEROS_MANSION = (37, 20)
    STONE_WALL = (42, 20)
    MAKESHIFT_WALL = (43, 20)
    HOSPITAL = (46, 20)
    DEFENSIVE_WALL = (47, 20)
    ASCLEPEION = (48, 20)

    def __init__(self, gid: int, max_level: int):
        self.gid = gid
        self.max_level = max_level

    @classmethod
    def from_gid(cls, gid: int):
        for member in cls:
            if member.gid == gid:
                return member
        raise ValueError(f"No {cls.__name__} with gid {gid}")


@dataclass
class BuildingJob:
    building_id: int
    target_level: int
    time_remaining: int

@dataclass
class VillageIdentity:
    id: int
    name: str
    coordinate_x: int
    coordinate_y: int

@dataclass
class GameState:
    account: Account
    villages: list[Village]
    hero_info: HeroInfo


class AttributePointType(Enum):
    POWER = "power"
    OFF_BONUS = "offBonus"
    DEF_BONUS = "defBonus"
    PRODUCTION_POINTS = "productionPoints"

# default attribute type to allocate when not specified
DEFAULT_ATTRIBUTE_POINT_TYPE = AttributePointType.PRODUCTION_POINTS

