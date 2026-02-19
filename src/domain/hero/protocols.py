from typing import Protocol

from src.domain.shared.protocols import VideoWatcher


class AdventureContext(VideoWatcher, Protocol):
    def navigate_to_adventures(self): ...
    def start_exploration(self) -> bool: ...