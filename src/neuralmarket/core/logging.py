"""Structured, consistently formatted logging for NeuralMarket utilities."""

from __future__ import annotations

import logging

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S%z"


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once with a consistent single-line format.

    Args:
        level: Logging level name (for example ``"INFO"`` or ``"DEBUG"``).

    Raises:
        ValueError: If ``level`` is not a recognized logging level name.
    """
    numeric_level = logging.getLevelName(level.upper())
    if not isinstance(numeric_level, int):
        raise ValueError(f"Unknown log level: {level!r}")

    logging.basicConfig(level=numeric_level, format=_LOG_FORMAT, datefmt=_DATE_FORMAT)


def get_logger(name: str) -> logging.Logger:
    """Return a named logger for a module.

    Args:
        name: Logger name, conventionally ``__name__`` of the caller.

    Returns:
        A standard library :class:`logging.Logger` instance.
    """
    return logging.getLogger(name)
