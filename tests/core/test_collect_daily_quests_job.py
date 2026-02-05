from datetime import datetime
from unittest.mock import Mock

import pytest

from src.core.job.collect_daily_quests_job import CollectDailyQuestsJob


def test_collect_daily_quests_job_collects_when_threshold_met() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.get_text_content.return_value = "53"

    job = CollectDailyQuestsJob(
        success_message="daily quests collected",
        failure_message="daily quests collection failed",
        scheduled_time=datetime.now(),
        daily_quest_threshold=50,
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is True
    driver_mock.wait_for_selector_and_click.assert_any_call('#navigation a.dailyQuests')
    driver_mock.wait_for_selector_and_click.assert_any_call(".textButtonV2.buttonFramed.collectRewards.rectangle.withText.green")
    driver_mock.wait_for_selector_and_click.assert_any_call(".textButtonV2.buttonFramed.collect.collectable.rectangle.withText.green")


def test_collect_daily_quests_job_does_not_collect_when_threshold_not_met() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.get_text_content.return_value = "30"

    job = CollectDailyQuestsJob(
        success_message="daily quests collected",
        failure_message="daily quests collection failed",
        scheduled_time=datetime.now(),
        daily_quest_threshold=50,
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is False
    driver_mock.wait_for_selector_and_click.assert_any_call('#navigation a.dailyQuests')
    # Should close dialog but NOT collect rewards
    driver_mock.get_text_content.assert_called_once_with(".achievedPoints .achieved")


def test_collect_daily_quests_job_handles_invalid_points() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.get_text_content.return_value = "invalid"

    job = CollectDailyQuestsJob(
        success_message="daily quests collected",
        failure_message="daily quests collection failed",
        scheduled_time=datetime.now(),
        daily_quest_threshold=50,
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is False


@pytest.mark.parametrize("achieved_points, threshold, should_collect", [
    (50, 50, True),  # Exactly at threshold
    (51, 50, True),  # Above threshold
    (100, 50, True),  # Well above threshold
    (49, 50, False),  # Just below threshold
    (0, 50, False),  # Zero points
    (25, 50, False),  # Half threshold
])
def test_collect_daily_quests_job_threshold_scenarios(
    achieved_points: int,
    threshold: int,
    should_collect: bool
) -> None:
    # Given
    driver_mock = Mock()
    driver_mock.get_text_content.return_value = str(achieved_points)

    job = CollectDailyQuestsJob(
        success_message="daily quests collected",
        failure_message="daily quests collection failed",
        scheduled_time=datetime.now(),
        daily_quest_threshold=threshold,
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is should_collect

