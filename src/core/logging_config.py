from __future__ import annotations

import logging
import os
from logging import Logger
from logging.config import dictConfig
from typing import Any


def _default_logging_dict(level: int | str) -> dict[str, Any]:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)-8s %(name)s - %(message)s",
            }
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "DEBUG",
                "formatter": "default",
                "stream": "ext://sys.stdout",
            }
        },
        "root": {
            "level": level if isinstance(level, str) else logging.getLevelName(level),
            "handlers": ["console"],
        },
    }


def configure_logging(level_name: str | int | None = None) -> None:
    """Configure logging for the application.

    - If `level_name` is a string like 'INFO' it will be resolved to the numeric level.
    - If None, tries `LOG_LEVEL` env var, otherwise defaults to INFO.
    This function uses ``dictConfig`` and ensures handlers are not filtered out
    by handler-levels (handlers use DEBUG) while the root logger controls
    the effective output level.
    """
    if level_name is None:
        level_name = os.getenv("LOG_LEVEL", "INFO")

    if isinstance(level_name, str):
        level_name = level_name.upper()
        level = getattr(logging, level_name, logging.INFO)
    else:
        level = level_name

    cfg = _default_logging_dict(level_name if isinstance(level_name, str) else logging.getLevelName(level))
    dictConfig(cfg)
    # Explicitly set root level to be safe
    logging.getLogger().setLevel(level)


def get_logger(name: str) -> Logger:
    """Return a module logger by name. Use this in modules as

    `logger = get_logger(__name__)`
    """
    return logging.getLogger(name)
