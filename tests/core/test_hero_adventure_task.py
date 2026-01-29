from types import SimpleNamespace
from typing import Iterable

import pytest

from src.core.tasks import HeroAdventureTask


class FakeDriver:
    def __init__(self, has_explore: bool, has_continue: bool, current_url: str = ""):
        self.has_explore = has_explore
        self.has_continue = has_continue
        self._current_url = current_url
        self.navigate_calls: list[str] = []
        self.clicked_selectors: list[str] = []
        self.clicked_first_calls: list[list[str]] = []
        self.wait_called = False
        self.raise_on_click = False

    def navigate(self, path: str) -> None:
        self.navigate_calls.append(path)

    def click(self, selector: str) -> bool:
        self.clicked_selectors.append(selector)
        if self.raise_on_click:
            raise RuntimeError("click failed")
        # Simulate clicking the explore button only
        explore_selector = "button.textButtonV2.buttonFramed.rectangle.withText.green"
        return self.has_explore and selector == explore_selector

    def click_first(self, selectors: Iterable[str]) -> bool:
        s = list(selectors)
        self.clicked_first_calls.append(s)
        return self.has_continue

    def click_all(self, selectors: Iterable[str]) -> int:
        # Not used in these tests
        return 0

    def wait_for_load_state(self, timeout: int = 3000) -> None:
        self.wait_called = True

    def current_url(self) -> str:
        return self._current_url


@pytest.mark.parametrize(
    "has_explore,has_continue,current_url,expected,reason",
    [
        (True, True, "", True, "explore present and continue clicked"),
        (True, False, "https://example/hero/adventures", True, "explore clicked then current_url indicates success"),
        (False, False, "", False, "no explore button present -> failure"),
    ],
)
def test_hero_adventure_task_execute_various(
    has_explore: bool, has_continue: bool, current_url: str, expected: bool, reason: str
) -> None:
    """Test HeroAdventureTask.execute for several UI scenarios.

    The task should orchestrate navigation and clicks using the driver's
    primitive methods without depending on Playwright types.
    """
    hero_info = SimpleNamespace(health=100, experience=200, adventures=3)
    task = HeroAdventureTask(success_message="ok", failure_message="err", hero_info=hero_info)

    driver = FakeDriver(has_explore=has_explore, has_continue=has_continue, current_url=current_url)

    result = task.execute(driver)

    assert result == expected, f"Expected {expected} when {reason}"
    # Ensure navigation to hero/adventures always happens when driver is used
    if has_explore:
        assert "/hero/adventures" in driver.navigate_calls[0]


def test_hero_adventure_task_execute_handles_click_exceptions() -> None:
    """If the driver raises during click, the task should return False and not raise."""
    hero_info = SimpleNamespace(health=1, experience=0, adventures=0)
    task = HeroAdventureTask(success_message="ok", failure_message="err", hero_info=hero_info)

    driver = FakeDriver(has_explore=True, has_continue=False, current_url="")
    driver.raise_on_click = True

    result = task.execute(driver)

    assert result is False

