from dataclasses import dataclass

from src.domain.config import HeroConfig
from src.application.job.job import Job
from src.domain.protocols.driver_protocol import DriverProtocol
from src.domain.model.model import DEFAULT_ATTRIBUTE_POINT_TYPE, AttributePointType, HeroAttributes, HeroInfo


@dataclass(kw_only=True)
class AllocateAttributesJob(Job):
    points: int
    hero_info: HeroInfo
    hero_config: HeroConfig

    def execute(self, driver: DriverProtocol) -> bool:
        """Allocate hero attribute points using driver primitives.

        Returns True on success, False on failure.
        """
        try:
            # Navigate and ensure hero attributes section is present
            driver.navigate('/hero/attributes')
            present = driver.wait_for_selector('div.heroAttributes', timeout=3000)
            if not present:
                return False

            buttons_selector = "button.textButtonV2.buttonFramed.plus.rectangle.withIcon.green, [role=\"button\"].textButtonV2.buttonFramed.plus.rectangle.withIcon.green"

            allocations = self._plan_attribute_allocations()
            if not allocations:
                target_index = DEFAULT_ATTRIBUTE_POINT_TYPE.value - 1
                for _ in range(self.points):
                    driver.click_nth(buttons_selector, target_index)
            else:
                index_by_key = {
                    "fighting_strength": AttributePointType.POWER.value - 1,
                    "off_bonus": AttributePointType.OFF_BONUS.value - 1,
                    "def_bonus": AttributePointType.DEF_BONUS.value - 1,
                    "production_points": AttributePointType.PRODUCTION_POINTS.value - 1,
                }
                for key, count in allocations.items():
                    target_index = index_by_key[key]
                    for _ in range(count):
                        driver.click_nth(buttons_selector, target_index)

            saved = driver.click_first(['#savePoints', 'button#savePoints'])
            driver.click("a#closeContentButton")

            return saved
        except Exception:
            return False

    def _plan_attribute_allocations(self) -> dict[str, int]:
        """Plan which attributes to allocate points to based on steps and ratios."""
        ratios_dict = self.hero_config.resources.attributes_ratio.to_dict()
        steps_dict = self.hero_config.resources.attributes_steps.to_dict()

        current = self._current_attributes()
        step_allocations = self._plan_step_allocations(current, steps_dict)
        remaining_points = self.points - sum(step_allocations.values())
        if remaining_points < 0:
            remaining_points = 0

        ratio_allocations = self._plan_ratio_allocations(current, ratios_dict, remaining_points)
        return self._merge_allocations(step_allocations, ratio_allocations)

    def _plan_ratio_allocations(self, current: dict[str, int], ratios: dict[str, int], points: int) -> dict[str, int]:
        """Allocate points based on ratio proportions using a greedy algorithm.

        For each point to allocate, find the attribute with the largest deficit
        relative to its target proportion.
        """
        if not ratios or points <= 0:
            return {}

        total_ratio = sum(ratios.values())
        if total_ratio == 0:
            return {}

        total_current = sum(current.get(key, 0) for key in ratios.keys())
        allocations = dict.fromkeys(ratios.keys(), 0)
        total = total_current

        for _ in range(points):
            best_key: str | None = None
            best_deficit: float | None = None

            for key, ratio in ratios.items():
                target = (ratio / total_ratio) * (total + 1)
                current_value = current.get(key, 0) + allocations[key]
                deficit = target - current_value

                if best_deficit is None or deficit > best_deficit:
                    best_deficit = deficit
                    best_key = key

            if best_key is None:
                break

            allocations[best_key] += 1
            total += 1

        return {key: value for key, value in allocations.items() if value > 0}

    def _plan_step_allocations(self, current: dict[str, int], steps: dict[str, int]) -> dict[str, int]:
        if not steps:
            return {}

        allocations = dict.fromkeys(steps.keys(), 0)
        remaining_points = self.points

        for key in steps.keys():
            if remaining_points <= 0:
                break
            target = steps[key]
            current_value = current.get(key, 0) + allocations[key]
            needed = max(0, target - current_value)
            to_add = min(remaining_points, needed)
            allocations[key] += to_add
            remaining_points -= to_add

        return {key: value for key, value in allocations.items() if value > 0}

    def _current_attributes(self) -> dict[str, int]:
        hero_attributes: HeroAttributes = self.hero_info.hero_attributes
        return {
            "fighting_strength": hero_attributes.fighting_strength,
            "off_bonus": hero_attributes.off_bonus,
            "def_bonus": hero_attributes.def_bonus,
            "production_points": hero_attributes.production_points,
        }


    def _merge_allocations(self, left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
        merged = dict(left)
        for key, value in right.items():
            merged[key] = merged.get(key, 0) + value
        return merged
