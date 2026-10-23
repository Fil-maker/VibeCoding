"""Logging setup; modules log through `get_logger`."""

import logging

LOG_FORMAT = "%(asctime)s %(levelname)s %(name)s %(message)s"


def configure_logging(level: int = logging.INFO) -> None:
    """Configure the root logger; a no-op once the root logger has handlers (`basicConfig`)."""
    logging.basicConfig(level=level, format=LOG_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Return the logger of a module."""
    return logging.getLogger(name)
