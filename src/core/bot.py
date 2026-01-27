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
from src.scan_adapter.scanner import scan_village, scan_village_list, scan_account_info, scan_hero_info, scan_new_building_contract

logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])


class Bot:
    """Game bot with scheduled planning and job execution."""
    
    PLANNING_INTERVAL: int = 300  # seconds (fallback)
    JOB_CHECK_INTERVAL: int = 1  # seconds

    def __init__(self, driver: Driver) -> None:
        self.driver: Driver = driver
        self.logic_engine: LogicEngine = LogicEngine()
        self.jobs: list[Job] = []
        self._running: bool = False
        # handle to the scheduled planning job (so we can cancel/reschedule dynamically)
        self._planning_job = None

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

            # If the job targets a specific village, navigate there first
            if village_id is not None:
                try:
                    self.driver.navigate_to_village(village_id)
                except Exception:
                    logger.debug(f"Failed to navigate to village id {village_id}")

            #TODO: this part is unacceptable
            if action == "build":
                self.build(village_name, building_id, building_gid)
            elif action == "build_new":
                # "build_new" uses the same UI flow as an upgrade: navigate to the slot and place the building
                logger.info(f"Placing new building {target_name} (gid={building_gid}) in village {village_name} at slot {building_id}")
                self.build_new(village_id, village_name, building_id, building_gid)
            elif action == "hero_adventure":
                # Attempt to start a hero adventure via driver. This method is tolerant and
                # returns False if no adventure button exists (e.g., UI differs or already on adventure).
                started = False
                try:
                    started = self.driver.start_hero_adventure()
                except Exception as e:
                    logger.error(f"Error while starting hero adventure: {e}")

                if not started:
                    # If we couldn't start an adventure, mark the job as expired/failed
                    job.status = JobStatus.EXPIRED
                    return "Hero adventure not started (no button found or driver failed)"
            elif action == "allocate_attributes":
                try:
                    points = int(payload.get('points') or 0)
                    self.driver.allocate_hero_attributes(points_to_allocate=points)
                except Exception as e:
                    logger.error(f"Error while allocating hero attributes: {e}")

            job.status = JobStatus.COMPLETED

            # Return a concise summary depending on action
            if action == "hero_adventure":
                return f"Hero adventure started (health={payload.get('health')}, experience={payload.get('experience')}, adventures={payload.get('adventures')})"
            return f"In the village {village_name} with id {village_id} was done {action} of {target_name} to level {target_level}"
        except Exception as e:
            job.status = JobStatus.TERMINATED
            raise e

    def _run_planning(self) -> None:
        """Run the planning phase, add new jobs and schedule the next planning run dynamically.

        The next planning run will be scheduled for when the shortest building queue finishes
        across all villages. If there are no villages or the computed delay is invalid, a
        fallback interval (PLANNING_INTERVAL) will be used.
        """
        logger.info("Running planning phase...")
        try:
            # Build fresh game state so we can both plan and compute next planning time
            game_state = self.create_game_state()
            interval_seconds = 3600  # planning horizon (1 hour)
            new_jobs = self.logic_engine.create_plan_for_village(game_state, interval_seconds)
            # Also plan hero adventure (if applicable)
            hero_job = self.logic_engine.create_plan_for_hero(game_state.hero_info)
            if hero_job is not None:
                new_jobs.extend(hero_job)
            self.jobs.extend(new_jobs)
            logger.info(f"Planning complete: added {len(new_jobs)} new jobs. Total pending: {len(self.jobs)}")

            # compute when the building queues will finish
            try:
                if game_state.villages:
                    next_delay = int(shortest_building_queue(game_state.villages))
                else:
                    next_delay = self.PLANNING_INTERVAL
            except Exception:
                # in case something unexpected happens, fall back to default
                next_delay = self.PLANNING_INTERVAL

            # enforce sensible minimum delay to avoid tight recursion
            if next_delay <= 0:
                next_delay = 1

            self._schedule_planning_in(next_delay)

        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)


    def _schedule_planning_in(self, seconds: int) -> None:
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
            self._planning_job = schedule.every(seconds).seconds.do(self._run_planning)
            logger.info(f"Next planning scheduled in {seconds} seconds")
        except Exception as e:
            logger.error(f"Failed to schedule next planning run: {e}")


    def planning(self) -> list[Job]:
        """Create a plan for all villages and return new jobs."""
        game_state = self.create_game_state()
        interval_seconds = 3600  # 60 minutes
        jobs = self.logic_engine.create_plan_for_village(game_state, interval_seconds)
        # include hero adventure if available
        hero_jobs = self.logic_engine.create_plan_for_hero(game_state.hero_info) if getattr(game_state, 'hero_info', None) else []
        jobs.extend(hero_jobs)

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
        url = f"{self.driver.config.server_url}/build.php?id={id}&gid={gid}"
        self.driver.page.goto(url)
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

        # Ensure we're on the village page (dorf1) before attempting UI interactions
        try:
            self.driver.navigate_to_village(village_identity.id)
        except Exception:
            logger.debug("Failed to navigate back to village before claiming quest rewards")

        # If quest master reward available on the page HTML, attempt to click questmaster and collect rewards
        try:
            clicks = self.driver.claim_quest_rewards(dorf1)
            if clicks:
                logger.info(f"Collected {clicks} quest reward(s) in village {village_identity.name}")
        except Exception as e:
            logger.debug(f"Claiming quest rewards failed: {e}")

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

    def build_new(self, village_id, village_name, id, gid) -> str:
        building_category = 1 # infrastructure

        self.driver.navigate_to_village(village_id)

        # I don't like this code
        url = f"{self.driver.config.server_url}/build.php?id={id}"
        self.driver.page.goto(url)
        self.driver.page.wait_for_selector("#contract")

        find_id = f'contract_building{gid}'
        building_part = self.driver.page.locator(f"button.textButtonV1.green.build#{find_id}").first

        # contract = scan_new_building_contract(building_part)

        # Click the primary action button inside the contract (the button inside div.section1)
        try:
            # The contract wrapper has id like 'contract_building{slotId}', use it to scope the selector
            contract_container_selector = f"#{find_id}"
            section1_button = self.driver.page.locator(f"{contract_container_selector} .section1 button").first
            if section1_button:
                section1_button.click()
                logger.info("Clicked new building button (section1)")
            else:
                logger.error(f"Section1 button not found for contract {find_id}")
        except Exception as e:
            logger.error(f"Failed to click new building button for contract {find_id}: {e}", exc_info=True)

        return f"Placed new building contract in village {village_name} (id={village_id}) at slot {id} for building gid {gid}"
