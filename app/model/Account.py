from dataclasses import dataclass

from app.model.Village import Village


@dataclass
class Account:
    villages: list[Village]