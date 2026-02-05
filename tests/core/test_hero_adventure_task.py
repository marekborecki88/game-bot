from types import SimpleNamespace
from datetime import datetime

import pytest

from src.config.config import HeroConfig
from src.core.job import HeroAdventureJob


@pytest.mark.parametrize(
    "has_explore,has_continue,current_url,expected,reason",
    [
        (True, True, "", True, "explore present and continue clicked"),
        (True, False, "https://example/hero/adventures", True, "explore clicked then current_url indicates success"),
        (False, False, "", False, "no explore button present -> failure"),
    ],
)
def test_hero_adventure_task_execute_various(
    fake_driver_factory, hero_config: HeroConfig, has_explore: bool, has_continue: bool, current_url: str, expected: bool, reason: str
) -> None:
    """Test HeroAdventureJob.execute for several UI scenarios."""
    # ...existing code...
    now = datetime.now()
    hero_info = SimpleNamespace(health=100, experience=200, adventures=3)
    task = HeroAdventureJob(success_message="ok", failure_message="err", hero_info=hero_info, scheduled_time=datetime.min, hero_config=hero_config)

    driver = fake_driver_factory(has_explore=has_explore, has_continue=has_continue, current_url=current_url)

    result = task.execute(driver)

    assert result == expected, f"Expected {expected} when {reason}"
    # Ensure navigation to hero/adventures always happens when driver is used
    if has_explore:
        assert "/hero/adventures" in driver.navigate_calls[0]


def test_hero_adventure_task_execute_handles_click_exceptions(fake_driver_factory, hero_config: HeroConfig) -> None:
    """If the driver raises during click, the task should return False and not raise."""
    hero_info = SimpleNamespace(health=1, experience=0, adventures=0)
    task = HeroAdventureJob(success_message="ok", failure_message="err", hero_info=hero_info, scheduled_time=datetime.min, hero_config=hero_config)

    driver = fake_driver_factory(has_explore=True, has_continue=False)
    driver.raise_on_click = True

    result = task.execute(driver)

    assert result is False
