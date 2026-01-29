import pytest
from typing import Any

from src.core.driver import DriverProtocol


class _FakeDriver(DriverProtocol):
    def __init__(
        self,
        *,
        has_explore: bool = False,
        has_continue: bool = False,
        current_url: str = "",
        html: str = "",
        raise_on_click: bool = False,
        upgrade_click_selectors: list[str] | None = None,
        contract_gid_match: int | None = None,
    ) -> None:
        self.has_explore = has_explore
        self.has_continue = has_continue
        self._current_url = current_url
        self.html = html
        self.raise_on_click = raise_on_click
        self.upgrade_click_selectors = upgrade_click_selectors or []
        self.contract_gid_match = contract_gid_match

        # recording
        self.navigate_calls: list[str] = []
        self.clicked: list[str] = []
        self.clicked_first: list[list[str]] = []
        self.clicked_all: list[list[str]] = []
        self.clicked_nth: list[tuple[str, int]] = []
        self.selector_waits: list[tuple[str, int]] = []
        self.wait_for_load_calls: list[int] = []

    # DriverProtocol
    def navigate(self, path: str) -> None:
        self.navigate_calls.append(path)

    def stop(self) -> None:
        return None

    def get_html(self, dorf: str) -> str:
        return self.html

    def click(self, selector: str) -> bool:
        self.clicked.append(selector)
        if self.raise_on_click:
            raise RuntimeError("click failed")
        # simulate explore button
        if selector == "button.textButtonV2.buttonFramed.rectangle.withText.green":
            return self.has_explore
        # upgrade simulation
        if selector in self.upgrade_click_selectors:
            return True
        # other clicks: assume present
        return True

    def click_first(self, selectors: Any) -> bool:
        s = list(selectors)
        self.clicked_first.append(s)
        # simulate contract_gid matching
        if self.contract_gid_match is not None:
            if any(str(self.contract_gid_match) in sel for sel in s):
                return True
        return True

    def click_all(self, selectors: Any) -> int:
        s = list(selectors)
        self.clicked_all.append(s)
        return len(s)

    def click_nth(self, selector: str, index: int) -> bool:
        self.clicked_nth.append((selector, index))
        return True

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        self.wait_for_load_calls.append(timeout)

    def wait_for_selector(self, selector: str, timeout: int = 3000) -> bool:
        self.selector_waits.append((selector, timeout))
        return True

    def current_url(self) -> str:
        return self._current_url


@pytest.fixture
def fake_driver_factory():
    """Return a factory that constructs a configured FakeDriver.

    Usage:
        driver = fake_driver_factory(has_explore=True, current_url='/hero/adventures')
    """

    def _factory(**kwargs):
        return _FakeDriver(**kwargs)

    return _factory

