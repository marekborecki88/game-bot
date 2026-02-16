from typing import Dict, Optional, Tuple

from src.core.model.model import VillageBasicInfo


class HtmlCache:
    """Simple per-scan HTML cache keyed by (village_name, index).

    Public API is intentionally minimal: set/get/clear.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[VillageBasicInfo, int], str] = {}

    def clear(self) -> None:
        self._cache.clear()

    def get(self, village_basic_info: VillageBasicInfo, idx: int) -> Optional[str]:
        return self._cache.get((village_basic_info, idx))

    def set(self, village_basic_info: VillageBasicInfo, idx: int, html: str) -> None:
        self._cache[(village_basic_info, idx)] = html
