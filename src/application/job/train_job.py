import logging
from dataclasses import dataclass

from src.application.job.job import Job
from src.domain.protocols.driver_protocol import DriverProtocol

logger = logging.getLogger(__name__)


@dataclass(kw_only=True)
class TrainJob(Job):
    village_id: int
    military_building_id: int
    troop_type: int
    quantity: int

    def execute(self, driver: DriverProtocol) -> bool:
        """Train troops using the driver's train_troops method.

        Returns True if the training action was successfully executed,
        False otherwise.
        """
        try:
            driver.train_troops(
                village_id=self.village_id,
                military_building_id=self.military_building_id,
                troop_type=self.troop_type,
                quantity=self.quantity
            )
            return True
        except Exception as e:
            logger.error(
                f"Failed to train troops in village {self.village_id}: "
                f"building_id={self.military_building_id}, troop_type={self.troop_type}, "
                f"quantity={self.quantity}. Error: {e}",
                exc_info=True
            )
            return False


