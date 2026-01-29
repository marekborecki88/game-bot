from __future__ import annotations

from typing import Protocol


class DriverProtocol(Protocol):
    """Lightweight driver interface used by core Task implementations.

    The protocol intentionally exposes a very small surface so the core
    package does not depend on Playwright. Concrete drivers (for example
    the Playwright-based driver in `src/driver_adapter/driver.py`) should
    implement these methods.
    """

    def navigate(self, path: str) -> None:
        """Navigate to the given server-relative path.

        The path may start with a leading slash or be a relative path.
        Implementations are expected to wait for the page to reach a stable
        load state before returning.
        """

    def stop(self) -> None:
        """Stop the driver and close any associated browser/window."""

    def get_html(self, dorf: str) -> str:
        """Return the HTML content for a given page identifier (e.g. 'dorf1')."""

