from datetime import datetime, timedelta

from src.config.config import Config, Strategy
from src.core.bot import Bot
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.job.job import Job, JobStatus
from src.core.model.model import (
    Village,
    SourcePit,
    ResourceType,
    BuildingType,
    Tribe,
    GameState,
    Account,
    HeroInfo,
    Building,
    Resources,
)
from src.core.job import BuildJob
from src.scan_adapter.scanner_adapter import Scanner


class FakeDriver(DriverProtocol):
    def __init__(self) -> None:
        self.config = type("C", (), {"server_url": "http://example"})

    def navigate(self, path: str) -> None:
        # No-op: tests don't need real navigation.
        return None

    def get_village_inner_html(self, village_id: int) -> tuple[str, str]:
        # No-op: tests don't need real HTML.
        return "", ""

    def stop(self) -> None:
        return None

    def get_html(self, dorf: str) -> str:
        return ""

    def click(self, selector: str) -> bool:
        return False

    def click_first(self, selectors) -> bool:
        return False

    def click_all(self, selectors) -> int:
        return 0

    def click_nth(self, selector: str, index: int) -> bool:
        return False

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        return None

    def wait_for_selector_and_click(self, selector: str, timeout: int = 3000) -> None:
        return None

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        return False

    def current_url(self) -> str:
        return ""

    def transfer_resources_from_hero(self, support: Resources) -> None:
        return None

    def catch_full_classes_by_selector(self, selector: str) -> str:
        return ""

    def sleep(self, seconds: int) -> None:
        return None


def make_village(**overrides: object) -> Village:
    defaults: dict[str, object] = {
        "id": 2002,
        "name": "BotTestVillage",
        "tribe": Tribe.ROMANS,
        "resources": Resources(lumber=0, clay=0, iron=0, crop=0),
        "free_crop": 0,
        "source_pits": [SourcePit(id=1, type=ResourceType.LUMBER, level=1)],
        "buildings": [Building(id=10, level=1, type=BuildingType.WAREHOUSE)],
        "warehouse_capacity": 50000,
        "granary_capacity": 50000,
        "building_queue": [],
        "lumber_hourly_production": 10,
        "clay_hourly_production": 10,
        "iron_hourly_production": 10,
        "free_crop_hourly_production": 10,
    }
    defaults.update(overrides)
    return Village(**defaults)


def test_unfreeze_on_expired_job_cleanup() -> None:
    driver = FakeDriver()
    config = Config(
        strategy=Strategy.BALANCED_ECONOMIC_GROWTH,
        server_url="",
        speed=1,
        user_login="",
        user_password="",
        headless=True,
    )
    bot = Bot(driver, scanner=Scanner(), config=config)

    village = make_village()
    account = Account(server_speed=1.0)
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})
    game_state = GameState(account=account, villages=[village], hero_info=hero)

    bot.logic_engine.game_state = game_state

    now = datetime.now()
    expired_job = BuildJob(
        success_message="build started",
        failure_message="build failed",
        village_name=village.name,
        village_id=village.id,
        building_id=1,
        building_gid=1,
        target_name="",
        target_level=1,
        scheduled_time=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        status=JobStatus.PENDING,
    )

    village.is_queue_building_freeze = True

    bot.jobs.append(expired_job)

    bot._execute_pending_jobs()

    assert village.is_queue_building_freeze is False
