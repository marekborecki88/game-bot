import logging
from dataclasses import dataclass, field
from datetime import datetime

from playwright.sync_api import Page

from src.config.config import DriverConfig
from src.core.model.model import Resources, Tribe, BuildingQueue, scan_contract, ResourceType, BuildingCost, \
    BuildingType, Building, ResourcePit

logger = logging.getLogger(__name__)


@dataclass
class Village:
    id: int
    name: str
    coordinates: tuple[int, int]
    tribe: Tribe
    resources: Resources
    free_crop: int
    resource_pits: list[ResourcePit]
    buildings: list[Building]
    warehouse_capacity: int
    granary_capacity: int
    building_queue: BuildingQueue
    lumber_hourly_production: int = 0
    clay_hourly_production: int = 0
    iron_hourly_production: int = 0
    crop_hourly_production: int = 0
    is_upgraded_to_city: bool = False
    is_permanent_capital: bool = False
    has_quest_master_reward: bool = False
    is_under_attack: bool = False
    incoming_attack_count: int = 0
    next_attack_seconds: int | None = None
    troops: dict[str, int] = field(default_factory=dict)
    last_train_time: datetime | None = None


    def build(self, page: Page, driver_config: DriverConfig, id: int):
        source_pit = next((s for s in self.source_pits if s.id == id), None)
        if not source_pit:
            return

        page.goto(f"{driver_config.server_url}/build.php?id={id}&gid={source_pit.type.value}")
        page.wait_for_selector("#contract ")

        logger.info("Scanning building contract...")
        contract = scan_contract(page)

        logger.debug("Contract details: %s", contract)

        # Click the upgrade button (first one, not the video feature button)
        upgrade_button = page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        logger.info("Clicked upgrade button")

    def lowest_source(self) -> "ResourceType":
        source_dict = {
            ResourceType.LUMBER: self.resources.lumber,
            ResourceType.CLAY: self.resources.clay,
            ResourceType.IRON: self.resources.iron,
            ResourceType.CROP: self.resources.crop,
        }

        return min(source_dict, key=source_dict.get)

    def pit_with_lowest_level_building(self, lowest_source: "ResourceType"):
        pits_with_given_type = [pit for pit in self.source_pits if pit.type == lowest_source]
        return min(pits_with_given_type, key=lambda p: p.level)

    def building_queue_duration(self) -> int:
        return self.building_queue.duration

    def get_building(self, building_type: "BuildingType") -> "Building | ResourcePit | None":
        if building_type.gid <= 4:
            resource_type = ResourceType.find_by_gid(gid=building_type.gid)
            return self.get_resource_pit(resource_type)
        return next((b for b in self.buildings if b.type == building_type), None)

    def get_resource_pit(self, resource_type: "ResourceType") -> "ResourcePit":
        fields = [r for r in self.resource_pits if r.type == resource_type]
        return min(fields, key=lambda p: p.level)

    def upgradable_resource_pits(self) -> list["ResourcePit"]:
        return [p for p in self.resource_pits if p.level < self.max_source_pit_level()]

    def needs_more_free_crop(self) -> bool:

        crop_ratio = 0 if self.crop_hourly_production == 0 else self.free_crop / self.crop_hourly_production
        return crop_ratio < 0.1 and self.any_crop_is_upgradable()

    def max_source_pit_level(self):
        if self.is_permanent_capital:
            return 20
        if self.is_upgraded_to_city:
            return 12
        return 10

    # TODO: better would be return particular id to upgrade
    def any_crop_is_upgradable(self):
        self_source_pits = [p for p in self.resource_pits if
                            p.type == ResourceType.CROP and p.level < self.max_source_pit_level()]
        return len(self_source_pits) > 0

    def create_reservation_request(self, building_cost: BuildingCost) -> Resources:
        """Return shortages for a building cost based on current village resources.

        Result is a dict keyed by SourceType with non-negative integer shortages
        (cost - available, floored at 0). This is a pure calculation and does not
        mutate village state.
        """
        return Resources(
            lumber=max(0, building_cost.resources.lumber - self.resources.lumber),
            clay=max(0, building_cost.resources.clay - self.resources.clay),
            iron=max(0, building_cost.resources.iron - self.resources.iron),
            crop=max(0, building_cost.resources.crop - self.resources.crop),
        )

    @property
    def resources_hourly_production(self) -> Resources:
        return Resources(
            lumber=self.lumber_hourly_production,
            clay=self.clay_hourly_production,
            iron=self.iron_hourly_production,
            crop=self.crop_hourly_production,
        )

    def freeze_building_queue_until(self, until: datetime, queue_key: str, job_id: str | None) -> None:
        self.building_queue.freeze_until(until=until, queue_key=queue_key, job_id=job_id)

    def has_military_building_for_training(self):
        military_buildings = [
            BuildingType.BARRACKS,
            # BuildingType.STABLE,
            # BuildingType.WORKSHOP,
        ]
        return any(self.get_building(building_type) for building_type in military_buildings)

    def con_train(self):
        return self.building_queue.is_empty and self.has_military_building_for_training() and not self._is_train_queue_freeze()

    def _is_train_queue_freeze(self) -> bool:
        if not self.last_train_time:
            return False
        time_since_last_train = (datetime.now() - self.last_train_time).total_seconds()
        # at least 15 minutes should pass between training sessions
        return time_since_last_train < 15 * 60


    def can_build(self, building: BuildingType) -> bool:
        """
        Check if the prerequisites for building are met.
        build means build new one, not upgrade existing one.
        """
        if self.get_building(building):
            return False

        match building:
            case BuildingType.SAWMILL | BuildingType.BRICKYARD | BuildingType.IRON_FOUNDRY | BuildingType.GRAIN_MILL:
                return self._has_at_least_one_10_level_resource_pit(building)
            case BuildingType.BAKERY:
                if self.get_building(BuildingType.BAKERY):
                    return False
                grain_mill = self.get_building(BuildingType.GRAIN_MILL)
                return grain_mill and grain_mill.level == 5
            case _:
                return False

    def _has_at_least_one_10_level_resource_pit(self, building_type: BuildingType) -> bool:
        lvl_10 = [f for f in self.buildings if f.type == building_type and f.level == 10]
        return len(lvl_10) > 0

    def production_per_hour(self, resource_type: ResourceType):
        match resource_type:
            case ResourceType.LUMBER:
                return self.lumber_hourly_production
            case ResourceType.CLAY:
                return self.clay_hourly_production
            case ResourceType.IRON:
                return self.iron_hourly_production
            case ResourceType.CROP:
                return self.crop_hourly_production

    def find_free_building_slot(self) -> int | None:
        if len(self.buildings) == 20:
            return None
        ids = [i.id for i in self.buildings]
        for i in range(18, 39):
            if i not in ids:
                return i
        return None # because python wants

