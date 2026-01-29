from src.core.tasks import CollectDailyQuestsTask


def test_collect_daily_quests_flow(fake_driver_factory) -> None:
    driver = fake_driver_factory()
    task = CollectDailyQuestsTask(success_message='ok', failure_message='err')

    assert task.execute(driver) is True
    assert any('#navigation a.dailyQuests' == call[0] for call in driver.selector_waits)
    assert driver.clicked_first
    assert driver.clicked_all
