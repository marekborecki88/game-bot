from dataclasses import dataclass

from src.config.config import HeroConfig
from src.core.job.job import Job
from src.core.protocols.driver_protocol import DriverProtocol
from src.core.model.model import DEFAULT_ATTRIBUTE_POINT_TYPE, AttributePointType, HeroAttributes, HeroInfo


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
        ratios = self._normalize_ratio(self.hero_config.resources.attributes_ratio, preserve_order=False)
        steps = self._normalize_ratio(self.hero_config.resources.attributes_steps, preserve_order=True)

        current = self._current_attributes()
        step_allocations = self._plan_step_allocations(current, steps)
        remaining_points = self.points - sum(step_allocations.values())
        if remaining_points < 0:
            remaining_points = 0

        ratio_allocations = self._plan_ratio_allocations(current, ratios, remaining_points)
        return self._merge_allocations(step_allocations, ratio_allocations)

    def _plan_ratio_allocations(self, current: dict[str, int], ratios: dict[str, int], points: int) -> dict[str, int]:
        if not ratios or points <= 0:
            return {}

        total_ratio = sum(ratios.values())
        total_current = sum(current[key] for key in ratios.keys())
        allocations = {key: 0 for key in ratios.keys()}
        total = total_current

        for _ in range(points):
            best_key = None
            best_deficit = None
            for key, ratio in ratios.items():
                target = (ratio / total_ratio) * (total + 1)
                current_value = current[key] + allocations[key]
                deficit = target - current_value
                if best_deficit is None or deficit > best_deficit:
                    best_deficit = deficit
                    best_key = key

            if best_key is None:
                break

            allocations[best_key] += 1
            total += 1

        return allocations

    def _plan_step_allocations(self, current: dict[str, int], steps: dict[str, int]) -> dict[str, int]:
        if not steps:
            return {}

        allocations = {key: 0 for key in steps.keys()}
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

    def _normalize_ratio(self, raw_ratio: dict[str, int], preserve_order: bool) -> dict[str, int]:
        key_map = {
            "fight": "fighting_strength",
            "fighting_strength": "fighting_strength",
            "power": "fighting_strength",
            "off": "off_bonus",
            "off_bonus": "off_bonus",
            "def": "def_bonus",
            "def_bonus": "def_bonus",
            "resources": "production_points",
            "production": "production_points",
            "production_points": "production_points",
        }
        ordered_keys = [
            "fighting_strength",
            "off_bonus",
            "def_bonus",
            "production_points",
        ]
        normalized: dict[str, int] = {}
        ordered_canonicals: list[str] = []
        for key, value in raw_ratio.items():
            if value <= 0:
                continue
            canonical = key_map.get(key)
            if canonical is None:
                continue
            normalized[canonical] = normalized.get(canonical, 0) + int(value)
            if preserve_order and canonical not in ordered_canonicals:
                ordered_canonicals.append(canonical)

        if preserve_order:
            return {key: normalized[key] for key in ordered_canonicals}
        return {key: normalized[key] for key in ordered_keys if key in normalized}

    def _merge_allocations(self, left: dict[str, int], right: dict[str, int]) -> dict[str, int]:
        merged = dict(left)
        for key, value in right.items():
            merged[key] = merged.get(key, 0) + value
        return merged
