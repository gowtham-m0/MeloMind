"""Logging setup for the backend."""

import logging


def configure_logging(level: int = logging.INFO) -> None:
    """Send log records to stderr in a short, readable format."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
