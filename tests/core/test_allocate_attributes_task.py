from datetime import datetime
from src.config.config import HeroConfig, HeroAdventuresConfig, HeroResourcesConfig
from src.core.job import AllocateAttributesJob
from src.core.model.model import HeroInfo, HeroAttributes


def test_allocate_attributes_clicks_n_times(fake_driver_factory, hero_config: HeroConfig) -> None:
    driver = fake_driver_factory()
    now = datetime.now()
    hero_info = HeroInfo(health=100, experience=0, adventures=0, is_available=True)
    task = AllocateAttributesJob(
        success_message='ok',
        failure_message='err',
        points=2,
        scheduled_time=now,
        hero_config=hero_config,
        hero_info=hero_info,
    )

    assert task.execute(driver) is True
    assert any('/hero/attributes' in p for p in driver.navigate_calls)
    assert len(driver.clicked_nth) == 2


def test_allocate_attributes_plans_ratio_based_points(hero_config: HeroConfig) -> None:
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=0,
            production_points=0,
        ),
    )
    task = AllocateAttributesJob(
        success_message='ok',
        failure_message='err',
        points=4,
        scheduled_time=datetime.now(),
        hero_config=hero_config,
        hero_info=hero_info,
    )

    allocations = task._plan_attribute_allocations()

    assert allocations == {
        "fighting_strength": 3,
        "production_points": 1,
    }

def test_allocate_attributes_applies_steps_before_ratio() -> None:
    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=False),
        resources=HeroResourcesConfig(
            support_villages=False,
            attributes_steps={"fight": 10},
            attributes_ratio={"resources": 100},
        ),
    )
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=0,
            off_bonus=0,
            def_bonus=0,
            production_points=0,
        ),
    )
    task = AllocateAttributesJob(
        success_message='ok',
        failure_message='err',
        points=12,
        scheduled_time=datetime.now(),
        hero_config=hero_config,
        hero_info=hero_info,
    )

    allocations = task._plan_attribute_allocations()

    assert allocations == {
        "fighting_strength": 10,
        "production_points": 2,
    }

def test_allocate_attributes_respects_step_order_and_skips_completed_steps() -> None:
    hero_config = HeroConfig(
        adventures=HeroAdventuresConfig(minimal_health=50, increase_difficulty=False),
        resources=HeroResourcesConfig(
            support_villages=False,
            attributes_steps={"fight": 10, "resources": 5},
            attributes_ratio={"resources": 100},
        ),
    )
    hero_info = HeroInfo(
        health=100,
        experience=0,
        adventures=0,
        is_available=True,
        hero_attributes=HeroAttributes(
            fighting_strength=10,
            off_bonus=0,
            def_bonus=0,
            production_points=2,
        ),
    )
    task = AllocateAttributesJob(
        success_message='ok',
        failure_message='err',
        points=5,
        scheduled_time=datetime.now(),
        hero_config=hero_config,
        hero_info=hero_info,
    )

    allocations = task._plan_attribute_allocations()

    assert allocations == {
        "production_points": 5,
    }
