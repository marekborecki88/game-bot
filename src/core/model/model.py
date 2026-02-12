import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum

from playwright.sync_api import Page

from src.config.config import DriverConfig

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Tile:
    """Base class for all map tiles."""
    x: int
    y: int


@dataclass(frozen=True)
class TileVillage(Tile):
    """Represents an occupied village tile."""
    village_id: int
    user_id: int
    alliance_id: int
    tribe: str = ""
    population: int = 0
    player_name: str = ""
    alliance_name: str = ""


@dataclass(frozen=True)
class TileOasisFree(Tile):
    """Represents a free (unoccupied) oasis that can be annexed."""
    bonus_resources: str = ""  # e.g., "{a.r1}" for resource bonus
    animals: dict[str, int] = field(default_factory=dict)  # Animals defending the oasis


@dataclass(frozen=True)
class TileOasisOccupied(Tile):
    """Represents an occupied oasis (already annexed by someone)."""
    field_type: str = ""  # Translated: "4-4-4-6"


@dataclass(frozen=True)
class TileAbandonedValley(Tile):
    """Represents an abandoned valley where you can settle (found new village)."""
    field_type: str = ""  # Translated: "5-4-3-6"


@dataclass(frozen=True)
class Resources:
    lumber: int | float = 0
    clay: int | float = 0
    iron: int | float = 0
    crop: int | float = 0

    def total(self) -> int | float:
        """Calculate the total of all resource types."""
        return self.lumber + self.clay + self.iron + self.crop

    def __sub__(self, other):
        return Resources(
            lumber=self.lumber - other.lumber,
            clay=self.clay - other.clay,
            iron=self.iron - other.iron,
            crop=self.crop - other.crop,
        )

    def __add__(self, other):
        return Resources(
            lumber=self.lumber + other.lumber,
            clay=self.clay + other.clay,
            iron=self.iron + other.iron,
            crop=self.crop + other.crop,
        )

    def __gt__(self, other):
        return (self.lumber > other.lumber and
                self.clay > other.clay and
                self.iron > other.iron and
                self.crop > other.crop)

    def __truediv__(self, other: "Resources"):
        return Resources(
            lumber=self.lumber / other.lumber,
            clay=self.clay / other.clay,
            iron=self.iron / other.iron,
            crop=self.crop / other.crop
        )

    def __floordiv__(self, other: "Resources") -> "Resources":
        """
        Divide resources by another Resources object (floor division).
        Used for calculating how many items can be made from available resources.
        If cost is 0 for a resource, it's unlimited (returns max int).
        
        :param other: Resource cost per item
        :return: Resources with floor division results
        """
        return Resources(
            lumber=self.lumber // other.lumber if other.lumber > 0 else float('inf'),
            clay=self.clay // other.clay if other.clay > 0 else float('inf'),
            iron=self.iron // other.iron if other.iron > 0 else float('inf'),
            crop=self.crop // other.crop if other.crop > 0 else float('inf')
        )

    def count_how_many_can_be_made(self, cost: "Resources") -> int:
        """
        Calculate how many items (with given cost in Resources) can be made from available resources.
        Returns the minimum count limited by any resource type.

        :param cost: Resource cost per one item
        :return: Maximum count of items that can be made
        """
        division_result = self // cost
        values = [division_result.lumber, division_result.clay, division_result.iron, division_result.crop]
        # Filter out inf values (unlimited resources from zero cost) to find actual limiting factor
        finite_values = [v for v in values if v != float('inf')]
        if not finite_values:
            return 0  # All resources are unlimited but no finite cost found
        return int(min(finite_values))



    def min(self):
        return min(self.lumber, self.clay, self.iron, self.crop)

    def max(self):
        return max(self.lumber, self.clay, self.iron, self.crop)

    def min_type(self) -> ResourceType:
        resource_dict = {
            ResourceType.LUMBER: self.lumber,
            ResourceType.CLAY: self.clay,
            ResourceType.IRON: self.iron,
            ResourceType.CROP: self.crop,
        }
        return min(resource_dict, key=resource_dict.get)

    def is_disjoint(self, other: "Resources") -> bool:
        """Return True if there is no overlap in positive resources between self and other."""
        for source_type, value in vars(self).items():
            if value > 0 and getattr(other, source_type) > 0:
                return False
        return True

    def calculate_how_much_can_provide(self, request: "Resources") -> "Resources":
        """Calculate how much of each requested resource can be provided.
        
        Returns a new Resources object with the minimum of available or requested for each resource type.
        """
        return Resources(
            lumber=min(self.lumber, request.lumber),
            clay=min(self.clay, request.clay),
            iron=min(self.iron, request.iron),
            crop=min(self.crop, request.crop),
        )

    def is_empty(self):
        return self.lumber == 0 and self.clay == 0 and self.iron == 0 and self.crop == 0

@dataclass
class BuildingCost:
    target_level: int
    resources: Resources
    total: int
    time_seconds: int
    time_formatted: str

@dataclass
class BuildingContract:
    resources: Resources
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
        resources=Resources(lumber=lumber, clay=clay, iron=iron, crop=crop),
        crop_consumption=crop_consumption
    )


@dataclass
class Account:
    when_beginners_protection_expires: int = 0


class ReservationStatus(Enum):
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    PARTIALLY_ACCEPTED = "partially_accepted"


@dataclass
class ReservationRequest:
    resources: Resources


# Response object describing how the hero answered a reservation request.
@dataclass
class ReservationResponse:
    status: ReservationStatus
    provided_resources: Resources


@dataclass(frozen=True)
class HeroAttributes:
    fighting_strength: int = 0
    off_bonus: int = 0
    def_bonus: int = 0
    production_points: int = 0


@dataclass
class HeroInfo:
    health: int
    experience: int
    adventures: int
    is_available: bool
    hero_attributes: HeroAttributes = field(default_factory=HeroAttributes)
    points_available: int = 0
    inventory: dict[str, int] = field(default_factory=dict)
    # Whether the daily quests UI shows a new-quest indicator (!) — belongs to UI/hero context
    has_daily_quest_indicator: bool = False
    reserved_resources: Resources = field(default_factory=Resources)

    def hero_inventory_resource(self) -> Resources:
        return Resources(
            lumber=self.inventory.get('lumber', 0),
            clay=self.inventory.get('clay', 0),
            iron=self.inventory.get('iron', 0),
            crop=self.inventory.get('crop', 0),
        )

    def send_request(self, request: Resources) -> ReservationResponse:
        zero = Resources(0, 0, 0, 0)

        if request == zero:
            return ReservationResponse(status=ReservationStatus.REJECTED, provided_resources=zero)

        hero_available_resources = self.hero_inventory_resource() - self.reserved_resources

        if hero_available_resources > request:
            # Hero has enough resources to fulfill the entire request
            self.reserved_resources += request
            return ReservationResponse(status=ReservationStatus.ACCEPTED, provided_resources=request)

        if hero_available_resources.is_disjoint(request):
            # Hero has some resources but not enough to fulfill the entire request
            return ReservationResponse(status=ReservationStatus.REJECTED, provided_resources=zero)

        to_provide = hero_available_resources.calculate_how_much_can_provide(request)
        self.reserved_resources += to_provide
        return ReservationResponse(status=ReservationStatus.PARTIALLY_ACCEPTED, provided_resources=to_provide)
    
    def has_any_adventure(self):
        return self.adventures > 0

    def can_go_on_adventure(self):
        return self.is_available and self.has_any_adventure() and self.health > 20

@dataclass
class BuildingQueue:
    parallel_building_allowed: bool
    in_jobs: list[BuildingJob] = field(default_factory=list)
    out_jobs: list[BuildingJob] = field(default_factory=list)

    @property
    def is_empty(self):
        return len(self.in_jobs) == 0 and len(self.out_jobs) == 0

    @property
    def duration(self) -> int:
        """Calculate total time remaining for all jobs in the queue."""
        # min from in_jobs and out_jobs
        in_duration = sum(job.time_remaining for job in self.in_jobs)
        out_duration = sum(job.time_remaining for job in self.out_jobs)
        if self.parallel_building_allowed:
            # If only one queue is active, re-plan no later than one hour
            if in_duration == 0 and out_duration > 0:
                return max(0, min(out_duration, 3600))
            if out_duration == 0 and in_duration > 0:
                return max(0, min(in_duration, 3600))
            return max(0, min(in_duration, out_duration))
        # parallel building not allowed, sum both queue blocks together
        return max(0, max(in_duration, out_duration))

    def add_job(self, job: "BuildingJob") -> None:
        self.in_jobs.append(job) if self._building_in_center(job.building_name) else self.out_jobs.append(job)

    def queue_key_for_building_name(self, building_name: str) -> str:
        return "in_jobs" if self._building_in_center(building_name) else "out_jobs"

    def _building_in_center(self, building_name: str) -> bool:
        return building_name not in ["Woodcutter", "Clay Pit", "Iron Mine", "Cropland"]

    def can_build_inside(self) -> bool:
        """Check if a building can be started in the center (inside)."""
        if self.parallel_building_allowed:
            return len(self.in_jobs) == 0
        return len(self.in_jobs) + len(self.out_jobs) == 0

    def can_build_outside(self) -> bool:
        """Check if a building can be started outside (source pits)."""
        if self.parallel_building_allowed:
            return len(self.out_jobs) == 0
        return len(self.in_jobs) + len(self.out_jobs) == 0

    def freeze_until(self, until: datetime, queue_key: str, job_id: str | None) -> None:
        queue = self.in_jobs if queue_key == "in_jobs" else self.out_jobs
        # freeze by adding a dummy job that lasts until the given time
        queue.append(BuildingJob(
            building_name="Freeze queue",
            target_level=0,
            time_remaining=int((until - datetime.now()).total_seconds()),
            job_id=job_id,
        ))

    def remove_jobs_by_id(self, job_id: str) -> None:
        self.in_jobs = [job for job in self.in_jobs if job.job_id != job_id]
        self.out_jobs = [job for job in self.out_jobs if job.job_id != job_id]

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

economy_building_types = {
    BuildingType.WOODCUTTER,
    BuildingType.CLAY_PIT,
    BuildingType.IRON_MINE,
    BuildingType.CROPLAND,
    BuildingType.SAWMILL,
    BuildingType.BRICKYARD,
    BuildingType.IRON_FOUNDRY,
    BuildingType.GRAIN_MILL,
    BuildingType.BAKERY,
}


class ResourceType(Enum):
    # (gid, max_level)
    LUMBER = (1, 10)
    CLAY = (2, 10)
    IRON = (3, 10)
    CROP = (4, 10)

    def __init__(self, gid: int, max_level: int):
        self.gid = gid
        self.max_level = max_level


@dataclass
class Building:
    id: int | None # None for future buildings not yet built
    level: int
    type: BuildingType

    @property
    def has_max_level(self) -> bool:
        return self.level == self.type.max_level


@dataclass
class ResourcePit:
    id: int
    type: ResourceType
    level: int


class Tribe(Enum):
    ROMANS = 1
    TEUTONS = 2
    GAULS = 3
    HUNS = 4
    SPARTANS = 5
    NORS = 6
    EGYPTIANS = 7


@dataclass
class BuildingJob:
    building_name: str
    target_level: int
    time_remaining: int
    job_id: str | None = None

@dataclass(frozen=True)
class VillageBasicInfo:
    id: int
    name: str
    coordinate_x: int
    coordinate_y: int
    is_under_attack: bool = False

@dataclass(frozen=True)
class IncomingAttackInfo:
    attack_count: int = 0
    next_attack_seconds: int | None = None


@dataclass
class GameState:
    account: "Account"
    villages: list[Village]
    hero_info: "HeroInfo"

    @property
    def calculate_global_resources(self) -> Resources:
        total_resources = Resources()
        for village in self.villages:
            total_resources += village.resources
        total_resources += self.hero_info.hero_inventory_resource()
        return total_resources


class AttributePointType(Enum):
    POWER = 1
    OFF_BONUS = 2
    DEF_BONUS = 3
    PRODUCTION_POINTS = 4


# default attribute type to allocate when not specified
DEFAULT_ATTRIBUTE_POINT_TYPE = AttributePointType.PRODUCTION_POINTS
