from typing import Dict, Optional, Tuple


class HtmlCache:
    """Simple per-scan HTML cache keyed by (village_name, index).

    Public API is intentionally minimal: set/get/clear.
    """

    def __init__(self) -> None:
        self._cache: Dict[Tuple[str, int], str] = {}

    def clear(self) -> None:
        self._cache.clear()

    def get(self, village_identity: str, idx: int) -> Optional[str]:
        return self._cache.get((village_identity, idx))

    def set(self, village_identity: str, idx: int, html: str) -> None:
        self._cache[(village_identity, idx)] = html
