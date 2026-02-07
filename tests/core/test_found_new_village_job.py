from datetime import datetime
from unittest.mock import Mock

from src.core.job.found_new_village_job import FoundNewVillageJob


def test_found_new_village_job_executes_successfully() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.click.return_value = True

    job = FoundNewVillageJob(
        success_message="new village founded from TestVillage",
        failure_message="founding new village from TestVillage failed",
        village_id=123,
        village_name="TestVillage",
        scheduled_time=datetime.now(),
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is True
    driver_mock.navigate.assert_called_once_with("/build.php?newdid=123&gid=16&tt=2")
    driver_mock.wait_for_load_state.assert_called()


def test_found_new_village_job_handles_exception() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.navigate.side_effect = Exception("Navigation failed")

    job = FoundNewVillageJob(
        success_message="new village founded",
        failure_message="founding new village failed",
        village_id=456,
        village_name="AnotherVillage",
        scheduled_time=datetime.now(),
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is False


def test_found_new_village_job_fails_when_button_not_found() -> None:
    # Given
    driver_mock = Mock()
    driver_mock.click.return_value = False

    job = FoundNewVillageJob(
        success_message="new village founded",
        failure_message="founding new village failed",
        village_id=789,
        village_name="ThirdVillage",
        scheduled_time=datetime.now(),
    )

    # When
    result = job.execute(driver_mock)

    # Then
    assert result is False

