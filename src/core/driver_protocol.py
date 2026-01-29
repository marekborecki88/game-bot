from __future__ import annotations

from typing import Protocol, Iterable, Tuple


class DriverProtocol(Protocol):
    """Lightweight driver interface used by core Task implementations.

    The protocol intentionally exposes a very small surface so the core
    package does not depend on Playwright. Concrete drivers (for example
    the Playwright-based driver in `src/driver_adapter/driver_protocol.py`) should
    implement these methods.
    """

    def navigate(self, path: str) -> None:
        """Navigate to the given server-relative path.

        The path may start with a leading slash or be a relative path.
        Implementations are expected to wait for the page to reach a stable
        load state before returning.
        """

    def get_village_inner_html(self, village_id: int) -> Tuple[str, str]:
        """
        Return the inner HTML's of dorf1 and dorf2 for the given village ID.
        :param village_id:
        :return: A tuple of (dorf1_html, dorf2_html)
        """

    def stop(self) -> None:
        """Stop the driver and close any associated browser/window."""

    def get_html(self, dorf: str) -> str:
        """Return the HTML content for a given page identifier (e.g. 'dorf1')."""

    def click(self, selector: str) -> bool:
        """Click the first element matching `selector` if visible.

        Returns True if a visible element was clicked, False otherwise.
        """

    def click_first(self, selectors: Iterable[str]) -> bool:
        """Try selectors in order and click the first visible element found.

        Returns True if an element was found (even if the click raised), False otherwise.
        """

    def click_all(self, selectors: Iterable[str]) -> int:
        """Click all visible elements matching any of provided selectors.

        Returns an estimate of number of click attempts made.
        """

    def click_nth(self, selector: str, index: int) -> bool:
        """Click the N-th element matching selector (0-based index); return True if clicked."""

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        """Wait for the page to reach a stable load state or timeout (milliseconds).

        Implementations should swallow non-fatal exceptions and return.
        """

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        """Wait for a selector to appear on the page and return True if present."""

    def current_url(self) -> str:
        """Return the driver's current URL as a string."""
