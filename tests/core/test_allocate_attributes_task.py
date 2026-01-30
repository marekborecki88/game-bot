from src.core.task.tasks import AllocateAttributesTask


def test_allocate_attributes_clicks_n_times(fake_driver_factory) -> None:
    driver = fake_driver_factory()
    task = AllocateAttributesTask(success_message='ok', failure_message='err', points=2)

    assert task.execute(driver) is True
    assert any('/hero/attributes' in p for p in driver.navigate_calls)
    assert len(driver.clicked_nth) == 2
