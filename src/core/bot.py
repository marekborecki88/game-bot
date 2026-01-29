import logging
import signal
import sys
import time
from types import FrameType

import schedule

from src.core.driver import DriverProtocol
from src.core.job import Job, JobStatus
from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, SourceType, VillageIdentity, GameState
from src.driver_adapter.driver import Driver
from src.scan_adapter.scanner import scan_village, scan_village_list, scan_account_info, scan_hero_info, is_reward_available
from src.core.tasks import BuildTask, BuildNewTask

logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])


class Bot:
    """Game bot with scheduled planning and job execution."""
    
    PLANNING_INTERVAL: int = 300  # seconds (fallback)
    JOB_CHECK_INTERVAL: int = 1  # seconds

    def __init__(self, driver: DriverProtocol) -> None:
        self.driver: DriverProtocol = driver
        # Do not perform expensive scans during construction. The LogicEngine may receive
        # a fresh GameState at planning time via create_plan_for_village(game_state).
        self.logic_engine: LogicEngine = LogicEngine(game_state=None)
        self.jobs: list[Job] = []
        self._running: bool = False
        # handle to the scheduled planning job (so we can cancel/reschedule dynamically)
        self._planning_job = None

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
        logger.info("Running planning phase...")

        new_jobs = []

        try:
            # Build fresh game state so we can both plan and compute next planning time
            game_state = self.create_game_state()
            new_jobs.extend(self.logic_engine.create_plan_for_village(game_state))
            # Also plan hero adventure (if applicable)
            hero_jobs = self.logic_engine.create_plan_for_hero(game_state.hero_info)
            new_jobs.extend(hero_jobs)
            self.jobs.extend(new_jobs)
            logger.info(f"Planning complete: added {len(new_jobs)} new jobs. Total pending: {len(self.jobs)}")

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
                if j.metadata and j.metadata.get('action') in ("build", "build_new") and j.metadata.get('village_id'):
                    try:
                        self.logic_engine.unfreeze_village_queue(j.metadata.get('village_id'))
                        logger.debug(f"Unfroze village queue for village id {j.metadata.get('village_id')} during cleanup")
                    except Exception:
                        logger.debug(f"Failed to unfreeze village queue for id {j.metadata.get('village_id')} during cleanup")
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
        except Exception as e:
            # Ensure terminated on unexpected exceptions
            job.status = JobStatus.TERMINATED
            raise
        finally:
            # Ensure that if we scheduled a future build and froze the queue, we unfreeze it now
            try:
                vid = None
                if isinstance(job.task, BuildTask) or isinstance(job.task, BuildNewTask):
                    vid = job.task.village_id
                elif hasattr(job.task, 'village'):
                    vid = getattr(job.task, 'village', None).id if getattr(job.task, 'village', None) else None

                if vid:
                    try:
                        self.logic_engine.unfreeze_village_queue(vid)
                    except Exception:
                        logger.debug(f"Failed to unfreeze village queue for id {vid}")
            except Exception:
                # Swallow any errors in cleanup to avoid masking job errors
                pass


    def _handle_task(self, job: Job) -> str:
        """Generic task handler: run the Task and return a summary.

        Assumes `job.task` is a Task instance implementing execute() and
        providing success_message/failure_message. Legacy callable jobs were
        removed from planning; if a non-Task is encountered we raise.
        """
        task = job.task

        try:
            succeeded = task.execute(self.driver)
        except Exception:
            succeeded = False

        if not succeeded:
            job.status = JobStatus.EXPIRED
            return task.failure_message

        job.status = JobStatus.COMPLETED
        return task.success_message


    def planning(self) -> list[Job]:
        """Create a plan for all villages and return new jobs."""
        game_state = self.create_game_state()
        jobs = self.logic_engine.create_plan_for_village(game_state)
        hero_jobs = self.logic_engine.create_plan_for_hero(game_state.hero_info)
        jobs.extend(hero_jobs)

        return jobs

    def fetch_account_info(self):
        html: str = self.driver.get_html("dorf1")
        return scan_account_info(html)

    def village_list(self) -> list[VillageIdentity]:
        """Get the list of all villages."""
        html: str = self.driver.get_html("dorf1")
        return scan_village_list(html)

    def wait_for_next_task(self, seconds: int) -> None:
        """Wait for a specified number of seconds before next task."""
        logger.info(f"Waiting {seconds} seconds for next task...")
        self._count_down(seconds)

    def _count_down(self, seconds: int) -> int:
        """Countdown timer with periodic page refresh."""
        if seconds == 0:
            sys.stdout.write('\rWaiting for next task: Finished\n')
            sys.stdout.flush()
            return 0
        elif seconds % 60 == 0:
            self.driver.refresh()

        sys.stdout.write(f'\rWaiting for next task: {seconds} seconds remaining')
        time.sleep(1)
        sys.stdout.flush()
        return self._count_down(seconds - 1)

    def fetch_village_info(self, village_identity: VillageIdentity) -> Village:
        """Scan a village and return its current state."""
        logger.debug(f"Scanning village: {village_identity.name}")
        dorf1, dorf2 = self.driver.get_village_inner_html(village_identity.id)

        # Ensure we're on the village page (dorf1)
        self.driver.navigate_to_village(village_identity.id)

        # Detect questmaster reward and set flag directly (allow exceptions to surface)
        reward_available = is_reward_available(dorf1)

        village = scan_village(village_identity, dorf1, dorf2)

        # Set detection flag directly on the typed dataclass
        village.has_quest_master_reward = reward_available

        return village


    def fetch_hero_info(self):
        """Scan hero attributes and inventory and return HeroInfo."""
        logger.debug("Scanning hero info")

        # Fetch attributes and inventory pages separately, in sequence
        hero_attrs_html = self.driver.get_hero_attributes_html()
        hero_inventory_html = self.driver.get_hero_inventory_html()

        return scan_hero_info(hero_attrs_html, hero_inventory_html)


    def create_game_state(self):
        account_info = self.fetch_account_info()
        villages = [self.fetch_village_info(v) for v in self.village_list()]
        hero_info = self.fetch_hero_info()
        return GameState(hero_info=hero_info, account=account_info, villages=villages)
