import logging
import signal
import time
from types import FrameType

import schedule

from src.config.config import LogicConfig
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.html_cache import HtmlCache
from src.core.job.job import Job, JobStatus
from src.core.model.model import Village, GameState
from src.core.planner.logic_engine import LogicEngine
from src.core.job import BuildJob, BuildNewJob
from src.core.protocols.scanner_protocol import ScannerProtocol

CLOSE_CONTENT_BUTTON_SELECTOR = "#closeContentButton"
ATTRIBUTES = "/hero/attributes"
HERO_INVENTORY = "/hero/inventory"
CLASS_TO_RESOURCE_MAP = {
    "item145": "lumber",
    "item146": "clay",
    "item147": "iron",
    "item148": "crop"
}
RESOURCE_TO_CLASS_MAP = {
    "lumber": "item145",
    "clay": "item146",
    "iron": "item147",
    "crop": "item148"
}


logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])


class Bot:
    """Game bot with scheduled planning and job execution."""

    def __init__(self, driver: DriverProtocol, scanner: ScannerProtocol, logic_config: LogicConfig) -> None:
        self.driver: DriverProtocol = driver
        self.scanner: ScannerProtocol = scanner
        # Do not perform expensive scans during construction. The LogicEngine may receive
        # a fresh GameState at planning time via create_plan_for_village(game_state).
        self.logic_engine: LogicEngine = LogicEngine(game_state=None, logic_config=logic_config)
        self._running: bool = False

        # HTML cache keyed by (village_name, index) where index is 1 or 2
        self.html_cache = HtmlCache()
        # Remember active village name after create_game_state builds cache
        self._active_village_name: str | None = None

        self._setup_signal_handlers()

    def _schedule_planning(self) -> None:
        try:
            # Build fresh game state so we can both plan and compute next planning time
            game_state = self.create_game_state()
            jobs = self.logic_engine.plan(game_state)
            logger.info(f"Planning complete: added {len(jobs)} new jobs. Total pending: {len(jobs)}")

            for job in jobs:
                try:
                    logger.debug(f"Executing job scheduled for {job.scheduled_time}")
                    summary = self._execute_job(job)
                    logger.info(summary)
                except Exception as e:
                    logger.error(f"Job execution failed: {e}", exc_info=True)

            delay = int(self._calculate_next_delay(game_state))
            self._planning_job = schedule.every(delay).seconds.do(self._run_planning)
            logger.info(f"Next planning scheduled in {delay} seconds")
        except Exception as e:
            logger.error(f"Failed to schedule next planning run: {e}")

    def _run_planning(self) -> None:
        """Run the planning phase, add new jobs and schedule the next planning run dynamically.

        The next planning run will be scheduled for when the shortest building queue finishes
        across all villages. If there are no villages or the computed delay is invalid, a
        fallback interval (PLANNING_INTERVAL) will be used.
        """
        logger.debug("Running planning phase...")


        try:
            self._schedule_planning()
        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)

    def _calculate_next_delay(self, game_state: GameState) -> int:
        return int(shortest_building_queue(game_state.villages)) or 1

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers for SIGINT and SIGTERM."""
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._running = False

    def run(self) -> None:
        """Start the bot's main loop with scheduled tasks."""
        logger.info("Starting bot...")
        self._running = True

        # NOTE: planning is now scheduled dynamically by `_run_planning` itself
        # Schedule job execution check
        # schedule.every(self.JOB_CHECK_INTERVAL).seconds.do(self._execute_pending_jobs)

        # Run initial planning immediately; it will schedule the next run based on queues
        self._run_planning()


        while self._running:
            schedule.run_pending()
            time.sleep(0.1)  # Small sleep to prevent CPU spinning

    def _execute_job(self, job: Job) -> str:
        """Execute a job and return a summary message.

        This method performs common bookkeeping (expiration check, status toggles,
        exception handling and final cleanup) and delegates the task-specific
        execution to the `_handle_task` method which runs Task instances.
        """

        job.status = JobStatus.RUNNING
        try:
            summary = self._handle_task(job)
            # If handler succeeded, ensure job status is COMPLETED unless handler set it.
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.COMPLETED
            return summary
        except Exception:
            # Ensure terminated on unexpected exceptions
            job.status = JobStatus.TERMINATED
        

    def _handle_task(self, job: Job) -> str:
        """Generic task handler: run the Job and return a summary.

        Assumes `job` implements execute() and
        providing success_message/failure_message.
        """
        try:
            succeeded = job.execute(self.driver)
        except Exception:
            succeeded = False

        if not succeeded:
            job.status = JobStatus.EXPIRED
            return job.failure_message

        job.status = JobStatus.COMPLETED
        return job.success_message

    def create_game_state(self):
        # Clear previous run cache
        self.html_cache.clear()

        # Fetch initial dorf1 and dorf2 (active village)
        dorf1_html = self.driver.get_html("/dorf1.php")
        dorf2_html = self.driver.get_html("/dorf2.php")

        # Parse village list and active village name
        villages_identities = self.scanner.scan_village_list(dorf1_html)
        active_name = self.scanner.scan_village_name(dorf1_html)

        # Put active village pages into cache and remember active name
        self.html_cache.set(active_name, 1, dorf1_html)
        self.html_cache.set(active_name, 2, dorf2_html)
        self._active_village_name = active_name

        # Prefetch other villages and fill cache
        for v in villages_identities:
            if v.name == active_name:
                continue
            d1, d2 = self.driver.get_village_inner_html(v.id)
            self.html_cache.set(v.name, 1, d1)
            self.html_cache.set(v.name, 2, d2)

        # Build game state from cache
        account_info = self.scanner.scan_account_info(dorf1_html)

        villages = []
        for v in villages_identities:
            d1 = self.html_cache.get(v.name, 1)
            d2 = self.html_cache.get(v.name, 2)
            if d1 is None or d2 is None:
                d1, d2 = self.driver.get_village_inner_html(v.id)
            village = self.scanner.scan_village(v, d1, d2)
            village.has_quest_master_reward = self.scanner.is_reward_available(d1)
            villages.append(village)

        hero_info = self.fetch_hero_info()

        return GameState(hero_info=hero_info, account=account_info, villages=villages)

    def fetch_hero_info(self):
        """Scan hero attributes and inventory and return HeroInfo."""
        logger.debug("Scanning hero info")

        # Fetch attributes and inventory pages separately, in sequence
        hero_attrs_html = self.driver.get_html(ATTRIBUTES)
        hero_inventory_html = self.driver.get_html(HERO_INVENTORY)
        # close inventory popup if present
        self.driver.click(CLOSE_CONTENT_BUTTON_SELECTOR)

        return self.scanner.scan_hero_info(hero_attrs_html, hero_inventory_html)
