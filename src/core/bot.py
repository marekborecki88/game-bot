from functools import singledispatchmethod
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
from src.scan_adapter.scanner import scan_village, scan_village_list, scan_account_info, scan_hero_info, scan_new_building_contract, is_reward_available
from src.core.tasks import BuildTask, BuildNewTask, HeroAdventureTask, AllocateAttributesTask, CollectDailyQuestsTask, CollectQuestmasterTask

logger = logging.getLogger(__name__)


def shortest_building_queue(villages: list[Village]) -> int:
    return min([v.building_queue_duration() for v in villages])


class Bot:
    """Game bot with scheduled planning and job execution."""
    
    PLANNING_INTERVAL: int = 300  # seconds (fallback)
    JOB_CHECK_INTERVAL: int = 1  # seconds

    def __init__(self, driver: Driver) -> None:
        self.driver: Driver = driver
        # Do not perform expensive scans during construction. The LogicEngine may receive
        # a fresh GameState at planning time via create_plan_for_village(game_state).
        self.logic_engine: LogicEngine = LogicEngine(game_state=None)
        self.jobs: list[Job] = []
        self._running: bool = False
        # handle to the scheduled planning job (so we can cancel/reschedule dynamically)
        self._planning_job = None

        self._setup_signal_handlers()

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

            #TODO: extract calculation of next planning time into separate method
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
        execution to the singledispatch `_handle_task` method which contains
        overloads for each Task subtype and a callable fallback.
        """
        if job.is_expired():
            job.status = JobStatus.EXPIRED
            return f"Job expired (scheduled for {job.scheduled_time})"

        job.status = JobStatus.RUNNING
        try:
            summary = self._handle_task(job.task, job)
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


    # Task-specific handlers using singledispatchmethod
    @singledispatchmethod
    def _handle_task(self, task, job: Job) -> str:
        """Fallback handler for unsupported task types.

        If `task` is a callable (legacy), run the fallback behaviour otherwise
        raise a RuntimeError to indicate unsupported Task type.
        """
        # Unknown task type — fallback to old behaviour if task is callable
        if callable(task):
            payload = task()
            action = payload.get("action")
            village_name = payload.get("village_name")
            village_id = payload.get("village_id")

            if village_id is not None:
                try:
                    self.driver.navigate_to_village(village_id)
                except Exception:
                    logger.debug(f"Failed to navigate to village id {village_id}")

            # minimal fallback actions
            if action == "build":
                self.build(village_name, payload.get('building_id'), payload.get('building_gid'))
            job.status = JobStatus.COMPLETED
            return f"Fallback executed action {action}"

        raise RuntimeError("Unsupported Task type and not callable")


    @_handle_task.register
    def _(self, task: BuildTask, job: Job) -> str:  # type: ignore[override]
        village_name = task.village_name
        village_id = task.village_id
        building_id = task.building_id
        building_gid = task.building_gid
        target_name = task.target_name
        target_level = task.target_level

        try:
            self.driver.navigate_to_village(village_id)
        except Exception:
            logger.debug(f"Failed to navigate to village id {village_id}")

        self.build(village_name, building_id, building_gid)
        job.status = JobStatus.COMPLETED
        return f"In the village {village_name} with id {village_id} was done build of {target_name} to level {target_level}"


    @_handle_task.register
    def _(self, task: BuildNewTask, job: Job) -> str:  # type: ignore[override]
        village_name = task.village_name
        village_id = task.village_id
        building_id = task.building_id
        building_gid = task.building_gid
        target_name = task.target_name

        try:
            self.driver.navigate_to_village(village_id)
        except Exception:
            logger.debug(f"Failed to navigate to village id {village_id}")

        logger.info(f"Placing new building {target_name} (gid={building_gid}) in village {village_name} at slot {building_id}")
        self.build_new(village_id, village_name, building_id, building_gid)
        job.status = JobStatus.COMPLETED
        return f"Placed new building {target_name} in village {village_name} (id={village_id})"


    @_handle_task.register
    def _(self, task: HeroAdventureTask, job: Job) -> str:  # type: ignore[override]
        started = False
        try:
            started = self.driver.start_hero_adventure()
        except Exception as e:
            logger.error(f"Error while starting hero adventure: {e}")

        if not started:
            job.status = JobStatus.EXPIRED
            return "Hero adventure not started (no button found or driver failed)"

        job.status = JobStatus.COMPLETED
        h = task.hero_info
        return f"Hero adventure started (health={h.health}, experience={h.experience}, adventures={h.adventures})"


    @_handle_task.register
    def _(self, task: AllocateAttributesTask, job: Job) -> str:  # type: ignore[override]
        try:
            points = int(task.points or 0)
            self.driver.allocate_hero_attributes(points_to_allocate=points)
        except Exception as e:
            logger.error(f"Error while allocating hero attributes: {e}")
            job.status = JobStatus.TERMINATED
            raise

        job.status = JobStatus.COMPLETED
        return f"Allocated {task.points} hero attribute points"


    @_handle_task.register
    def _(self, task: CollectDailyQuestsTask, job: Job) -> str:  # type: ignore[override]
        try:
            self.driver.claim_daily_quests()
            return "Daily quests not collected (element not found or click failed)"
        except Exception as e:
            logger.info(f"Error while collecting daily quests: {e}")
            job.status = JobStatus.TERMINATED
            return "Failed to collect daily quests"


    @_handle_task.register
    def _(self, task: CollectQuestmasterTask, job: Job) -> str:  # type: ignore[override]
        try:
            # get latest page html for detection and then call claim_quest_rewards
            page_html = self.driver.get_html("dorf1")
            clicks = self.driver.claim_quest_rewards(page_html)
            if clicks == 0:
                job.status = JobStatus.EXPIRED
                return "No questmaster rewards collected"
        except Exception as e:
            logger.error(f"Error while collecting questmaster rewards: {e}")
            job.status = JobStatus.TERMINATED
            raise

        job.status = JobStatus.COMPLETED
        return "Collected questmaster rewards"

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
