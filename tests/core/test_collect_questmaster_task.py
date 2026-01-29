from types import SimpleNamespace

import pytest

from src.core.tasks import CollectQuestmasterTask


@pytest.mark.parametrize('reward_available', [True, False])
def test_collect_questmaster_task(fake_driver_factory, monkeypatch, reward_available: bool) -> None:
    html = '<html></html>'
    driver = fake_driver_factory(html=html)
    task = CollectQuestmasterTask(success_message='ok', failure_message='err', village=SimpleNamespace(id=1, name='V'))

    def fake_is_reward_available(html_arg: str) -> bool:
        assert html_arg == html
        return reward_available

    monkeypatch.setattr('src.scan_adapter.scanner.is_reward_available', fake_is_reward_available)

    result = task.execute(driver)
    assert result == reward_available
    if reward_available:
        assert any('#questmasterButton' in c for c in driver.clicked)
