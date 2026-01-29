from src.core.tasks import BuildTask


def test_build_task_attempts_upgrade_click(fake_driver_factory) -> None:
    driver = fake_driver_factory(upgrade_click_selectors=["button.textButtonV1.green.build"])
    task = BuildTask(success_message='ok', failure_message='err', village_name='V', village_id=1, building_id=42, building_gid=7, target_name='S', target_level=1)

    result = task.execute(driver)

    assert result is True
    # verify navigation included build.php with id and gid
    assert any('/build.php' in p and 'id=42' in p and 'gid=7' in p for p in driver.navigate_calls)
    # verify upgrade selector was attempted
    assert "button.textButtonV1.green.build" in driver.clicked
