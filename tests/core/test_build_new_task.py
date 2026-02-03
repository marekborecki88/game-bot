from datetime import datetime
from src.core.job import BuildNewJob


def test_build_new_task_places_contract(fake_driver_factory) -> None:
    driver = fake_driver_factory(contract_gid_match=7)
    now = datetime.now()
    task = BuildNewJob(success_message='ok', failure_message='err', village_name='V', village_id=1, building_id=5, building_gid=7, target_name='S', scheduled_time=now, expires_at=now)

    result = task.execute(driver)

    assert result is True
    assert any('/build.php?id=5' in p for p in driver.navigate_calls)
    assert any('contract_building7' in ''.join(sel) for sel in driver.clicked_first)
