from datetime import datetime
from src.core.job import AllocateAttributesJob


def test_allocate_attributes_clicks_n_times(fake_driver_factory) -> None:
    driver = fake_driver_factory()
    now = datetime.now()
    task = AllocateAttributesJob(success_message='ok', failure_message='err', points=2, scheduled_time=now)

    assert task.execute(driver) is True
    assert any('/hero/attributes' in p for p in driver.navigate_calls)
    assert len(driver.clicked_nth) == 2
