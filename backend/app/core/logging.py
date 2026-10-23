"""Logging setup for the backend."""

import logging

# HTTP client libraries log every request URL at INFO. URLs can carry keys and personal search
# terms, so they only log warnings.
QUIET_LOGGERS = ("httpx", "httpcore", "httpx2", "httpcore2")


def configure_logging(level: int = logging.INFO) -> None:
    """Send log records to stderr in a short, readable format."""
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    for name in QUIET_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)
