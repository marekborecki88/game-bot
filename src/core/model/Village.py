from dataclasses import dataclass

from enum import Enum
from playwright.sync_api import Page

from src.config import Config


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
class Village:
    id: int
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

    def build(self, page: Page, config: Config, id: int):
        source_pit = next((s for s in self.source_pits if s.id == id), None)
        if not source_pit:
            return

        page.goto(f"{config.server_url}/build.php?id={id}&gid={source_pit.type.value}")
        page.wait_for_selector("#contract ")

        print("Scanning building contract...")
        contract = scan_contract(page)

        print(contract)

        # Click the upgrade button (first one, not the video feature button)
        upgrade_button = page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        print("Clicked upgrade button")

    def building_queue_is_empty(self):
        return len(self.building_queue) == 0

    def lowest_source(self):
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

@dataclass
class VillageIdentity:
    id: int
    name: str
    coordinate_x: int
    coordinate_y: int