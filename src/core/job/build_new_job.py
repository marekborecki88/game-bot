from dataclasses import dataclass
from datetime import datetime

from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class BuildNewJob(Job):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    freeze_until: datetime | None = None
    freeze_queue_key: str | None = None

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
