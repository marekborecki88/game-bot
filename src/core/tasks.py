from dataclasses import dataclass
from typing import Any

from src.core.model.model import Village
from src.core.task import Task
from src.core.driver import DriverProtocol
from src.core.model.model import DEFAULT_ATTRIBUTE_POINT_TYPE


@dataclass(frozen=True)
class BuildTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int

    def execute(self, driver: DriverProtocol) -> bool:
        """Perform building/upgrade action using driver primitives.

        Returns True if the primary action (clicking the build/upgrade button)
        was attempted, False otherwise.
        """
        # Navigate directly to the build URL for the given slot and gid
        driver.navigate(f"/build.php?id={self.building_id}&gid={self.building_gid}")

        # Wait for contract UI to appear
        if not driver.wait_for_selector('#contract', timeout=3000):
            return False

        # Try common upgrade button selector
        upgrade_selector = "button.textButtonV1.green.build"
        return driver.click(upgrade_selector)


@dataclass(frozen=True)
class BuildNewTask(Task):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str

    def execute(self, driver: DriverProtocol) -> bool:
        """Place a new building contract using driver primitives.

        Navigates to the build page for the slot and attempts to click the
        contract action button. Returns True if a click attempt was made.
        """
        try:
            # Navigate to the build page for the slot
            driver.navigate(f"/build.php?id={self.building_id}")

            # Wait for contract area
            if not driver.wait_for_selector('#contract', timeout=3000):
                return False

            # Try to click the specific contract button for the building gid
            find_id = f'contract_building{self.building_gid}'
            contract_button_selectors = [
                f"button.textButtonV1.green.build#{find_id}",
                f"#{find_id} .section1 button",
                f"#{find_id} button",
            ]

            if driver.click_first(contract_button_selectors):
                return True

            # Fallback: generic contract button
            if driver.click_first(["#contract .section1 button", "#contract button"]):
                return True

            return False
        except Exception:
            return False


@dataclass(frozen=True)
class HeroAdventureTask(Task):
    hero_info: Any

    def execute(self, driver: DriverProtocol) -> bool:
        """Start a hero adventure using the provided driver primitives.

        The Task is responsible for orchestration: navigating to the hero
        adventures page, clicking the Explore button, waiting for UI updates,
        attempting to click any Continue control and finally inferring
        success from the current URL if needed.
        """
        try:
            # Navigate to hero adventures view
            driver.navigate("/hero/adventures")

            # Exact selector where the green Explore button typically lives
            explore_selector = "button.textButtonV2.buttonFramed.rectangle.withText.green"
            clicked = driver.click(explore_selector)
            if not clicked:
                # Explore button not found or not visible
                return False

            # Allow UI to update
            driver.wait_for_load_state()

            # Try continue selectors
            continue_selectors = [
                "button.textButtonV2.buttonFramed.continue.rectangle.withText.green",
                "text=Continue",
                "button.continue",
                "a.continue",
                "button.button.green",
                "a.button.green",
                "button:has-text('Continue')",
                "a:has-text('Continue')",
            ]

            success = driver.click_first(continue_selectors)

            if not success:
                return False

            driver.click("a#closeContentButton")
            return True
        except Exception:
            # Swallow any driver exceptions and report failure
            return False


@dataclass(frozen=True)
class AllocateAttributesTask(Task):
    points: int

    def execute(self, driver: DriverProtocol) -> bool:
        """Allocate hero attribute points using driver primitives.

        Returns True on success, False on failure.
        """
        try:
            # Navigate and ensure hero attributes section is present
            driver.navigate('/hero/attributes')
            present = driver.wait_for_selector('div.heroAttributes', timeout=3000)
            if not present:
                return False

            buttons_selector = "button.textButtonV2.buttonFramed.plus.rectangle.withIcon.green, [role=\"button\"].textButtonV2.buttonFramed.plus.rectangle.withIcon.green"

            target_index = DEFAULT_ATTRIBUTE_POINT_TYPE.value - 1

            # Click the N-th plus button points times
            for _ in range(self.points):
                driver.click_nth(buttons_selector, target_index)

            saved = driver.click_first(['#savePoints', 'button#savePoints'])
            driver.click("a#closeContentButton")

            return saved
        except Exception:
            return False


@dataclass(frozen=True)
class CollectDailyQuestsTask(Task):
    def execute(self, driver: DriverProtocol) -> bool:
        """Click the daily quests anchor and collect rewards using driver primitives.

        Returns True if the flow ran (click attempts made), False otherwise.
        """
        try:
            # Wait for daily quests anchor
            present = driver.wait_for_selector('#navigation a.dailyQuests', timeout=1000)
            if not present:
                return False

            # Try to click the anchor (may fail silently)
            try:
                driver.click('#navigation a.dailyQuests')
            except Exception:
                # continue regardless
                pass

            # Try initial Collect rewards controls
            collect_rewards_selectors = [
                'button.collectRewards',
                "button.textButtonV2.buttonFramed.collectRewards",
                "button:has-text('Collect rewards')",
                "text=Collect rewards",
            ]

            driver.click_first(collect_rewards_selectors)

            # Final collect buttons
            final_collect_selectors = [
                "button.collect",
                "button.collectable",
                "button:has-text('Collect')",
                "button.textButtonV2.buttonFramed.collect",
                "button.textButtonV2.buttonFramed.collect.collectable",
            ]

            driver.click_all(final_collect_selectors)
            driver.click("a#closeContentButton")
            return True
        except Exception:
            return False


@dataclass(frozen=True)
class CollectQuestmasterTask(Task):
    village: Village

    def execute(self, driver: DriverProtocol) -> bool:
        """Collect questmaster rewards if available.

        Returns True if any click attempts were made (rewards collected or attempted), False otherwise.
        """
        try:
            # Get the latest page HTML for detection
            page_html = driver.get_html("dorf1")
            try:
                from src.scan_adapter.scanner import is_reward_available
                if not is_reward_available(page_html):
                    return False
            except Exception:
                # If detection fails, be conservative and do nothing
                return False

            # Click the questmaster button if present
            try:
                driver.click('#questmasterButton')
                driver.wait_for_load_state(3000)
            except Exception:
                # continue even if click fails
                pass

            # Click all 'Collect' controls
            collect_selectors = [
                "button:has-text('Collect')",
                "button:has-text('collect')",
                "a:has-text('Collect')",
                "a:has-text('collect')",
                "text=Collect",
                "text=collect",
            ]

            clicks = driver.click_all(collect_selectors)
            driver.click("a#closeContentButton")
            return clicks > 0
        except Exception:
            return False
