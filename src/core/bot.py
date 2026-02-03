import logging
import signal
import time
from types import FrameType

import schedule

from src.config.config import Config
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

    PLANNING_INTERVAL: int = 300  # seconds (fallback)
    JOB_CHECK_INTERVAL: int = 1  # seconds

    def __init__(self, driver: DriverProtocol, scanner: ScannerProtocol, config: Config) -> None:
        self.driver: DriverProtocol = driver
        self.scanner: ScannerProtocol = scanner
        # Do not perform expensive scans during construction. The LogicEngine may receive
        # a fresh GameState at planning time via create_plan_for_village(game_state).
        self.logic_engine: LogicEngine = LogicEngine(game_state=None, config=config)
        self.jobs: list[Job] = []
        self._running: bool = False
        # handle to the scheduled planning job (so we can cancel/reschedule dynamically)
        self._planning_job = None

        # HTML cache keyed by (village_name, index) where index is 1 or 2
        self.html_cache = HtmlCache()
        # Remember active village name after create_game_state builds cache
        self._active_village_name: str | None = None

        self._setup_signal_handlers()

    def _schedule_planning(self, game_state: GameState) -> None:
        """Schedule the next planning run after `seconds` seconds.

        Cancels any previously scheduled planning job to ensure only one planner job exists.
        """
        # cancel previous planning job if present
        if self._planning_job is not None:
            try:
                schedule.cancel_job(self._planning_job)
            except Exception:
                pass

        # schedule the next planner job
        try:
            delay = self._calculate_next_delay(game_state)
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
            # Build fresh game state so we can both plan and compute next planning time
            game_state = self.create_game_state()
            jobs = self.logic_engine.plan(game_state)
            self.jobs.extend(jobs)
            logger.info(f"Planning complete: added {len(jobs)} new jobs. Total pending: {len(self.jobs)}")

            self._schedule_planning(game_state)

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
        schedule.every(self.JOB_CHECK_INTERVAL).seconds.do(self._execute_pending_jobs)

        # Run initial planning immediately; it will schedule the next run based on queues
        self._run_planning()

        logger.info(f"Scheduler configured: dynamic planning, job check every {self.JOB_CHECK_INTERVAL}s")

        while self._running:
            schedule.run_pending()
            time.sleep(0.1)  # Small sleep to prevent CPU spinning

        self._cleanup()

    def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up...")
        # cancel any planner job we registered
        if self._planning_job is not None:
            try:
                schedule.cancel_job(self._planning_job)
            except Exception:
                pass
        schedule.clear()
        pending_count = len([j for j in self.jobs if j.status == JobStatus.PENDING])
        logger.info(f"Shutdown complete. {pending_count} pending jobs remaining.")

    def _execute_pending_jobs(self) -> None:
        """Execute all jobs that are ready and cleanup completed ones."""
        for job in self.jobs:
            if job.should_execute():
                try:
                    logger.debug(f"Executing job scheduled for {job.scheduled_time}")
                    summary = self._execute_job(job)
                    logger.info(summary)
                except Exception as e:
                    logger.error(f"Job execution failed: {e}", exc_info=True)

        # Mark expired jobs so they are included in cleanup
        for j in self.jobs:
            try:
                if j.is_expired() and j.status == JobStatus.PENDING:
                    j.status = JobStatus.EXPIRED
            except Exception:
                pass

        # Cleanup completed/expired/terminated jobs
        before_count = len(self.jobs)
        # Identify jobs that will be removed so we can perform cleanup actions (e.g., unfreeze villages)
        remaining = [j for j in self.jobs if j.status == JobStatus.PENDING]
        removed = [j for j in self.jobs if j.status != JobStatus.PENDING]

        # For any removed build-related jobs, attempt to unfreeze the respective village
        for j in removed:
            try:
                if isinstance(j, (BuildJob, BuildNewJob)) and hasattr(j, 'village_id'):
                    try:
                        self.logic_engine.unfreeze_village_queue(j.village_id)
                        logger.debug(
                            f"Unfroze village queue for village id {j.village_id} during cleanup")
                    except Exception:
                        logger.debug(
                            f"Failed to unfreeze village queue for id {j.village_id} during cleanup")
            except Exception:
                pass

        self.jobs = remaining
        cleaned = before_count - len(self.jobs)
        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} completed jobs")

    def _execute_job(self, job: Job) -> str:
        """Execute a job and return a summary message.

        This method performs common bookkeeping (expiration check, status toggles,
        exception handling and final cleanup) and delegates the task-specific
        execution to the `_handle_task` method which runs Task instances.
        """
        if job.is_expired():
            job.status = JobStatus.EXPIRED
            return f"Job expired (scheduled for {job.scheduled_time})"

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
            raise
        finally:
            # Ensure that if we scheduled a future build and froze the queue, we unfreeze it now
            try:
                vid = None
                if isinstance(job, BuildJob) or isinstance(job, BuildNewJob):
                    vid = job.village_id
                elif hasattr(job, 'village'):
                    vid = getattr(job, 'village', None).id if getattr(job, 'village', None) else None

                if vid:
                    try:
                        self.logic_engine.unfreeze_village_queue(vid)
                    except Exception:
                        logger.debug(f"Failed to unfreeze village queue for id {vid}")
            except Exception:
                # Swallow any errors in cleanup to avoid masking job errors
                pass

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
