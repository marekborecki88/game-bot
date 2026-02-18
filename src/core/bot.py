import logging
import signal
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from types import FrameType

from src.config.config import LogicConfig, HeroConfig
from src.core.model.game_state import GameState
from src.core.model.model import HeroInfo
from src.core.model.village import Village
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.html_cache import HtmlCache
from src.core.job.job import Job
from src.core.job.scheduler import ScheduledJobQueue
from src.core.job.planning_job import PlanningJob
from src.core.job.build_job import BuildJob
from src.core.job.build_new_job import BuildNewJob
from src.core.planner.logic_engine import LogicEngine
from src.core.protocols.scanner_protocol import ScannerProtocol

CLOSE_CONTENT_BUTTON_SELECTOR = "#closeContentButton"
ATTRIBUTES = "/hero/attributes"
HERO_INVENTORY = "/hero/inventory"
PLANNING_SUCCESS_MESSAGE = "planning completed"
PLANNING_FAILURE_MESSAGE = "planning failed"

RESOURCE_TO_CLASS_MAP = {
    "lumber": "item145",
    "clay": "item146",
    "iron": "item147",
    "crop": "item148"
}


logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    if not villages:
        return 0
    return min([v.building_queue_duration() for v in villages])


@dataclass(frozen=True)
class QueueFreeze:
    village_name: str
    queue_key: str
    frozen_until: datetime
    job_id: str


class Bot:
    """Game bot with scheduled planning and job execution."""

    def __init__(self, driver: DriverProtocol, scanner: ScannerProtocol, logic_config: LogicConfig, hero_config: HeroConfig) -> None:
        self.driver: DriverProtocol = driver
        self.scanner: ScannerProtocol = scanner
        # Do not perform expensive scans during construction. The LogicEngine may receive
        # a fresh GameState at planning time via create_plan_for_village(game_state).
        self.logic_engine: LogicEngine = LogicEngine(game_state=None, logic_config=logic_config, hero_config=hero_config)
        self._running: bool = False

        # HTML cache keyed by (village_name, index) where index is 1 or 2
        self.html_cache = HtmlCache()
        # Remember active village name after create_game_state builds cache
        self._setup_signal_handlers()
        self._job_queue = ScheduledJobQueue()
        self._queue_freezes: dict[tuple[str, str], QueueFreeze] = {}
        self._job_freeze_index: dict[str, tuple[str, str]] = {}
        self._shutdown_event = threading.Event()

    def run(self) -> None:
        logger.info("Starting bot...")
        self._running = True
        # Execute first planning immediately
        initial_planning_job = PlanningJob(
            scheduled_time=datetime.now(),
            success_message=PLANNING_SUCCESS_MESSAGE,
            failure_message=PLANNING_FAILURE_MESSAGE,
            planning_context=self,
        )
        self._job_queue.push(initial_planning_job)

        while self._running:
            now = datetime.now()
            job = self._job_queue.pop_due(now)
            if job:
                self._execute_job(job)
                continue

            next_time = self._job_queue.peek_next_time()
            if next_time is None:
                # Should not happen if planning always schedules next planning
                self._shutdown_event.wait(timeout=1)
                continue

            sleep_seconds = max(1, int((next_time - now).total_seconds()))
            self._shutdown_event.wait(timeout=sleep_seconds)

        logger.info("Bot has been stopped.")

    def run_planning(self) -> None:
        logger.debug("Running planning phase...")

        try:
            game_state = self.create_game_state()
            self._apply_queue_freezes(game_state)
            jobs = self.logic_engine.plan(game_state)
            for job in jobs:
                self._register_queue_freeze(job)
                self._job_queue.push(job)

            # Schedule next planning based on building queue duration
            delay = int(self._calculate_next_delay(game_state))
            scheduled_time = datetime.now() + timedelta(seconds=delay)
            planning_job = PlanningJob(
                scheduled_time=scheduled_time,
                success_message=PLANNING_SUCCESS_MESSAGE,
                failure_message=PLANNING_FAILURE_MESSAGE,
                planning_context=self,
            )
            self._job_queue.push(planning_job)
            logger.info(f"Next planning scheduled in {delay} seconds")
        except Exception as e:
            logger.error(f"Planning failed: {e}")


    def _calculate_next_delay(self, game_state: GameState | None) -> int:
        if game_state is None:
            return 15
        return max(0, int(shortest_building_queue(game_state.villages))) + 15

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers for SIGINT and SIGTERM."""
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._running = False
        self._shutdown_event.set()

    def _register_queue_freeze(self, job: Job) -> None:
        if isinstance(job, BuildJob) and job.freeze_until and job.freeze_queue_key:
            freeze = QueueFreeze(
                village_name=job.village_name,
                queue_key=job.freeze_queue_key,
                frozen_until=job.freeze_until,
                job_id=job.job_id,
            )
            freeze_key = (freeze.village_name, freeze.queue_key)
            self._queue_freezes[freeze_key] = freeze
            self._job_freeze_index[job.job_id] = freeze_key

        if isinstance(job, BuildNewJob) and job.freeze_until and job.freeze_queue_key:
            freeze = QueueFreeze(
                village_name=job.village_name,
                queue_key=job.freeze_queue_key,
                frozen_until=job.freeze_until,
                job_id=job.job_id,
            )
            freeze_key = (freeze.village_name, freeze.queue_key)
            self._queue_freezes[freeze_key] = freeze
            self._job_freeze_index[job.job_id] = freeze_key

    def _apply_queue_freezes(self, game_state: GameState) -> None:
        now = datetime.now()
        for village in game_state.villages:
            for queue_key in ("in_jobs", "out_jobs"):
                freeze_key = (village.name, queue_key)
                freeze = self._queue_freezes.get(freeze_key)
                if freeze and freeze.frozen_until > now:
                    village.building_queue.freeze_until(
                        until=freeze.frozen_until,
                        queue_key=queue_key,
                        job_id=freeze.job_id,
                    )

    def _execute_job(self, job: Job) -> None:
        try:
            job.status = job.status.RUNNING
            result = job.execute(self.driver)
            job.status = job.status.COMPLETED if result else job.status.TERMINATED
            self._release_queue_freeze(job.job_id)
            logger.info(f"Job executed: {job.success_message}")
        except Exception as e:
            job.status = job.status.TERMINATED
            self._release_queue_freeze(job.job_id)
            logger.error(f"Job execution failed: {job.failure_message}, error: {e}")

    def _release_queue_freeze(self, job_id: str) -> None:
        freeze_key = self._job_freeze_index.pop(job_id, None)
        if freeze_key:
            self._queue_freezes.pop(freeze_key, None)

    def create_game_state(self):
        # Clear previous run cache
        self.html_cache.clear()

        # Fetch initial dorf1 and dorf2 (active village)
        dorf1_html = self.driver.get_html("/dorf1.php")
        dorf2_html = self.driver.get_html("/dorf2.php")

        # Parse village list and active village name
        villages_identities = self.scanner.scan_village_list(dorf1_html)
        current_village = self.scanner.scan_village_basic_info(dorf1_html)

        # Put active village pages into cache and remember active name
        self.html_cache.set(current_village, 1, dorf1_html)
        self.html_cache.set(current_village, 2, dorf2_html)

        # Prefetch other villages and fill cache
        for village in villages_identities:
            if village == current_village:
                continue
            d1, d2 = self.driver.get_village_inner_html(village.id)
            self.html_cache.set(village, 1, d1)
            self.html_cache.set(village, 2, d2)

        # Build game state from cache
        account_info = self.scanner.scan_account_info(dorf1_html)

        villages = []
        for village in villages_identities:
            d1 = self.html_cache.get(village, 1)
            d2 = self.html_cache.get(village, 2)
            if d1 is None or d2 is None:
                d1, d2 = self.driver.get_village_inner_html(village.id)
            village = self.scanner.scan_village(village, d1, d2)
            village.has_quest_master_reward = self.scanner.is_reward_available(d1)
            villages.append(village)

        hero_info = self.fetch_hero_info()

        return GameState(hero_info=hero_info, account=account_info, villages=villages)

    def fetch_hero_info(self) -> HeroInfo:
        """Scan hero attributes and inventory and return HeroInfo."""
        logger.debug("Scanning hero info")

        # Fetch attributes and inventory pages separately, in sequence
        hero_attrs_html = self.driver.get_html(ATTRIBUTES)
        hero_inventory_html = self.driver.get_html(HERO_INVENTORY)
        # close inventory popup if present
        self.driver.click(CLOSE_CONTENT_BUTTON_SELECTOR)

        return self.scanner.scan_hero_info(hero_attrs_html, hero_inventory_html)
