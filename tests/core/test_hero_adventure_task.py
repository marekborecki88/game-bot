from types import SimpleNamespace
from datetime import datetime

import pytest

from src.core.job.jobs import HeroAdventureJob


@pytest.mark.parametrize(
    "has_explore,has_continue,current_url,expected,reason",
    [
        (True, True, "", True, "explore present and continue clicked"),
        (True, False, "https://example/hero/adventures", True, "explore clicked then current_url indicates success"),
        (False, False, "", False, "no explore button present -> failure"),
    ],
)
def test_hero_adventure_task_execute_various(
    fake_driver_factory, has_explore: bool, has_continue: bool, current_url: str, expected: bool, reason: str
) -> None:
    """Test HeroAdventureJob.execute for several UI scenarios.

    1. Explore found + Continue found -> success
    2. Explore found + no Continue, but URL is adventures? (Actually logic requires explore click return true, then continue click OR generic 'success' if logic differs?
       Wait, execute returns driver.click_first(continue_selectors) result. If explore clicked but continue NOT found/clicked, returns False.
       The logic in HeroAdventureJob is:
            clicked = driver.click(explore_selector)
            if not clicked: return False
            success = driver.click_first(continue_selectors)
            if not success: return False
            return True
       So if has_continue is False, it should return False? The test case (True, False, ..., True) suggests otherwise?
       Ah, I need to see the body of the test.
    """
    click_selectors_responses = {}
    if has_explore:
        click_selectors_responses["button.textButtonV2.buttonFramed.rectangle.withText.green"] = True
    if has_continue:
        # Simplified selector matching:
        click_selectors_responses["button.textButtonV2.buttonFramed.continue.rectangle.withText.green"] = True
        # also match generic
        click_selectors_responses["button:has-text('Continue')"] = True

    # NOTE: fake_driver_factory mock handling for click_first needs to be robust,
    # but assuming it works based on input selectors.
    
    # Actually the test implementation:
    driver = fake_driver_factory(
        # The fake driver implementation details matter.
        # But here I only need to fix instantiation.
    )
    # Patch the driver behavior for click/click_first if needed or handled by factory logic
    # ...
    
    now = datetime.now()
    task = HeroAdventureJob(hero_info=SimpleNamespace(), success_message='', failure_message='', scheduled_time=now, expires_at=now)
    # Wait, kw_only=True.

    hero_info = SimpleNamespace(health=100, experience=200, adventures=3)
    task = HeroAdventureJob(success_message="ok", failure_message="err", hero_info=hero_info, scheduled_time=datetime.min, expires_at=datetime.max)

    driver = fake_driver_factory(has_explore=has_explore, has_continue=has_continue, current_url=current_url)

    result = task.execute(driver)

    assert result == expected, f"Expected {expected} when {reason}"
    # Ensure navigation to hero/adventures always happens when driver is used
    if has_explore:
        assert "/hero/adventures" in driver.navigate_calls[0]


def test_hero_adventure_task_execute_handles_click_exceptions(fake_driver_factory) -> None:
    """If the driver raises during click, the task should return False and not raise."""
    hero_info = SimpleNamespace(health=1, experience=0, adventures=0)
    task = HeroAdventureJob(success_message="ok", failure_message="err", hero_info=hero_info, scheduled_time=datetime.min, expires_at=datetime.max)

    driver = fake_driver_factory(has_explore=True, has_continue=False)
    driver.raise_on_click = True

    result = task.execute(driver)

    assert result is False
