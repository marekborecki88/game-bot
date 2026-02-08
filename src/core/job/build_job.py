from dataclasses import dataclass
from datetime import datetime

from src.core.model.model import Resources
from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol


@dataclass(kw_only=True)
class BuildJob(Job):
    village_name: str
    village_id: int
    building_id: int
    building_gid: int
    target_name: str
    target_level: int
    support: Resources | None = None
    freeze_until: datetime | None = None
    freeze_queue_key: str | None = None

    def execute(self, driver: DriverProtocol) -> bool:
        """Perform building/upgrade action using driver primitives.

        Returns True if the primary action (clicking the build/upgrade button)
        was attempted, False otherwise.
        """
        # Navigate directly to the build URL for the given slot and gid
        driver.navigate(f"/build.php?newdid={self.village_id}&id={self.building_id}&gid={self.building_gid}")

        if self.support:
            # Fill in support resources if provided
            driver.transfer_resources_from_hero(self.support)

        # Wait for contract UI to appear
        if not driver.wait_for_selector('#contract', timeout=3000):
            return False

        # Try common upgrade button selector
        upgrade_selector = "button.textButtonV1.green.build"
        return driver.click(upgrade_selector)
