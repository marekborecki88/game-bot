from datetime import datetime, timedelta

from src.core.bot import Bot
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.task.job import Job, JobStatus
from src.core.model.model import Village, SourcePit, ResourceType, BuildingType, Tribe, GameState, \
    Account, HeroInfo, Building, Resources
from src.core.task.tasks import BuildTask
from src.scan_adapter.scanner_adapter import Scanner


class FakeDriver(DriverProtocol):
    def __init__(self):
        class Page:
            def goto(self, *args, **kwargs):
                pass

            def wait_for_selector(self, *args, **kwargs):
                pass

        self.page = Page()
        self.config = type('C', (), {'server_url': 'http://example'})

    # Provide DriverProtocol methods as stubs or delegations
    def navigate(self, path: str) -> None:
        # Map to page.goto for compatibility
        self.page.goto(path)

    def stop(self) -> None:
        return None

    def get_html(self, dorf: str) -> str:
        return ""

    def click(self, selector: str) -> bool:
        return False

    def click_first(self, selectors):
        return False

    def click_all(self, selectors):
        return 0

    def click_nth(self, selector: str, index: int) -> bool:
        return False

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        return None

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        return False

    def current_url(self) -> str:
        return ""

    # Legacy helpers used by this test
    def navigate_to_village(self, id):
        return

    def get_hero_attributes_html(self):
        return ""

    def get_hero_inventory_html(self):
        return ""


def make_village(**overrides) -> Village:
    defaults = {
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


def test_unfreeze_on_expired_job_cleanup():
    # Setup bot with fake driver and a frozen village
    driver = FakeDriver()
    bot = Bot(driver, scanner=Scanner())

    village = make_village()
    account = Account(server_speed=1.0)
    hero = HeroInfo(health=100, experience=0, adventures=0, is_available=True, inventory={})
    game_state = GameState(account=account, villages=[village], hero_info=hero)

    # Inject game_state into logic engine
    bot.logic_engine.game_state = game_state

    # Simulate a delayed job that then expires (status changed to EXPIRED)
    now = datetime.now()
    expired_job = Job(
        task=BuildTask(
            success_message=f"construction of  level 1 in {village.name} started",
            failure_message=f"construction of  level 1 in {village.name} failed",
            village_name=village.name,
            village_id=village.id,
            building_id=1,
            building_gid=1,
            target_name="",
            target_level=1,
        ),
        scheduled_time=now - timedelta(hours=2),
        expires_at=now - timedelta(hours=1),
        status=JobStatus.PENDING,
        metadata={"action": "build", "village_id": village.id}
    )

    # Mark village frozen as if planner scheduled a future job
    village.is_queue_building_freeze = True

    bot.jobs.append(expired_job)

    # Run executor which should perform cleanup and unfreeze villages for removed build jobs
    bot._execute_pending_jobs()

    assert village.is_queue_building_freeze is False
