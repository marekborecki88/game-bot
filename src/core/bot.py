import logging
import signal
import sys
import time
from types import FrameType

import schedule

from src.core.job import Job, JobStatus
from src.core.planner.logic_engine import LogicEngine
from src.core.model.model import Village, SourceType, VillageIdentity, GameState
from src.driver_adapter.driver import Driver
from src.scan_adapter.scanner import scan_village, scan_village_list, scan_account_info, scan_hero_info
from tests.core.test_logic_engine import hero_info

logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])


class Bot:
    """Game bot with scheduled planning and job execution."""
    
    PLANNING_INTERVAL: int = 3600  # seconds (60 minutes)
    JOB_CHECK_INTERVAL: int = 1  # seconds

    def __init__(self, driver: Driver) -> None:
        self.driver: Driver = driver
        self.logic_engine: LogicEngine = LogicEngine()
        self.jobs: list[Job] = []
        self._running: bool = False
        
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup graceful shutdown handlers for SIGINT and SIGTERM."""
        signal.signal(signal.SIGINT, self._shutdown_handler)
        signal.signal(signal.SIGTERM, self._shutdown_handler)

    def _shutdown_handler(self, signum: int, frame: FrameType | None) -> None:
        """Handle shutdown signals gracefully."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self._running = False

    def run(self) -> None:
        self.driver.login()
        """Start the bot's main loop with scheduled tasks."""
        logger.info("Starting bot...")
        self._running = True
        
        # Schedule planning task
        schedule.every(self.PLANNING_INTERVAL).seconds.do(self._run_planning)
        
        # Schedule job execution check
        schedule.every(self.JOB_CHECK_INTERVAL).seconds.do(self._execute_pending_jobs)
        
        # Run initial planning immediately
        self._run_planning()
        
        logger.info(f"Scheduler configured: planning every {self.PLANNING_INTERVAL}s, "
                    f"job check every {self.JOB_CHECK_INTERVAL}s")
        
        while self._running:
            schedule.run_pending()
            time.sleep(0.1)  # Small sleep to prevent CPU spinning
        
        self._cleanup()

    def _cleanup(self) -> None:
        """Cleanup resources on shutdown."""
        logger.info("Cleaning up...")
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

        # Cleanup completed/expired/terminated jobs
        before_count = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.status == JobStatus.PENDING]
        cleaned = before_count - len(self.jobs)
        if cleaned > 0:
            logger.debug(f"Cleaned up {cleaned} completed jobs")

    def _execute_job(self, job: Job) -> str:
        """Execute a job and return a summary message."""
        if job.is_expired():
            job.status = JobStatus.EXPIRED
            return f"Job expired (scheduled for {job.scheduled_time})"

        job.status = JobStatus.RUNNING
        try:
            payload = job.task()

            action = payload.get("action")
            village_name = payload.get("village_name")
            village_id = payload.get("village_id")
            building_id = payload.get("building_id")
            building_gid = payload.get("building_gid")
            target_name = payload.get("target_name")
            target_level = payload.get("target_level")

            self.driver.navigate_to_village(village_id)

            if action == "upgrade":
                self.build(village_name, building_id, building_gid)

            job.status = JobStatus.COMPLETED

            return f"In the village {village_name} with id {village_id} was done {action} of {target_name} to level {target_level}"
        except Exception as e:
            job.status = JobStatus.TERMINATED
            raise e

    def _run_planning(self) -> None:
        """Run the planning phase and add new jobs to the queue."""
        logger.info("Running planning phase...")
        try:
            new_jobs = self.planning()
            self.jobs.extend(new_jobs)
            logger.info(f"Planning complete: added {len(new_jobs)} new jobs. "
                       f"Total pending: {len(self.jobs)}")
        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)


    def planning(self) -> list[Job]:
        """Create a plan for all villages and return new jobs."""
        game_state = self.create_game_state()
        interval_seconds = 3600  # 60 minutes
        jobs = self.logic_engine.create_plan_for_village(game_state, interval_seconds)

        return jobs

    def fetch_account_info(self):
        html: str = self.driver.get_html("dorf1")
        return scan_account_info(html)

    def village_list(self) -> list[VillageIdentity]:
        """Get the list of all villages."""
        html: str = self.driver.get_html("dorf1")
        return scan_village_list(html)

    def build(self, village_name: str, id: int, gid: int) -> None:
        """Build/upgrade a building in a village."""
        source_type = next((st for st in SourceType if st.value == gid), None)
        logger.info(f"Building in village: {village_name}, id: {id}, "
                    f"type: {source_type.name if source_type else 'unknown'}")

        # I don't like this code
        self.driver.page.goto(f"{self.driver.config.server_url}/build.php?id={id}&gid={gid}")
        self.driver.page.wait_for_selector("#contract ")

        # Contract should be checked by scanner and building should be queued only if enough resources

        upgrade_button = self.driver.page.locator("button.textButtonV1.green.build").first
        upgrade_button.click()
        logger.info("Clicked upgrade button")

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
        return scan_village(village_identity, dorf1, dorf2)


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
