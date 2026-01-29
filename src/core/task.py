from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from src.core.driver import DriverProtocol


@dataclass(frozen=True)
class Task:
    """Base Task data holder: only message fields are required.

    Concrete tasks should extend this class with additional properties and
    implement the behavior methods that accept a driver implementing
    ``DriverProtocol``. Keeping methods on Task small and explicit makes
    unit testing straightforward by providing a fake driver implementation.
    """

    success_message: str
    failure_message: str

    def navigate(self, driver: DriverProtocol, path: str) -> None:
        """Navigate to a server path using the provided driver.

        This method delegates to the driver and does not raise for driver
        implementation-specific errors; callers may handle exceptions as
        needed.
        """
        driver.navigate(path)

    def execute(self, driver: DriverProtocol) -> Any:
        """Perform the task using the provided driver and return a result.

        Concrete subclasses should override this method with their own
        implementation. The default implementation is a no-op that returns
        None.
        """
        return None

    def close_window(self, driver: DriverProtocol) -> None:
        """Request the driver to stop/close the browser window.

        This delegates to ``driver.stop()`` which drivers must implement.
        """
        driver.stop()
