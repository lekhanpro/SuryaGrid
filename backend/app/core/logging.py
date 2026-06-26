"""Structured logging configuration."""

import logging
import sys

from app.config import get_settings


def setup_logging() -> logging.Logger:
    settings = get_settings()
    level = logging.DEBUG if settings.DEBUG else logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    logger = logging.getLogger("suryagrid")
    logger.setLevel(level)
    logger.addHandler(handler)
    return logger


logger = setup_logging()
