from dataclasses import dataclass


@dataclass
class Task:
    """Base Task data holder: only message fields are required.

    Concrete tasks should extend this class with additional properties.
    """
    success_message: str
    failure_message: str

