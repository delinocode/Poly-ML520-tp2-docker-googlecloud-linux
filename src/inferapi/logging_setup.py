"""Logging configuration, done once, in one place.

Every module asks for its own logger with `logging.getLogger(__name__)` and never
touches a handler: names under `inferapi.` inherit from the `inferapi` logger, so one
setting here steers the whole package. Only the entrypoints (`cli.main`, `serve`) call
`setup_logging`, because a module that configures logging on import steals the decision
from whoever imported it.

Two destinations on purpose: stdout follows the configured level, the file always keeps
DEBUG. The run you need to explain is always one that already finished, and nobody gets
to replay it with the level turned up.
"""

import logging
import sys

from inferapi.config import LoggingConfig

# Timestamp, level and logger name are what make a line sortable, filterable, and
# traceable back to the code that wrote it. Everything else belongs in the message.
LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s | %(message)s"
DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(log_settings: LoggingConfig) -> None:
    """Call once, at the entrypoint. `level` only throttles stdout."""
    formatter = logging.Formatter(LOG_FORMAT, datefmt=DATE_FORMAT)

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(formatter)
    stdout_handler.setLevel(log_settings.level.upper())

    if log_settings.debug_file is not None:
        log_settings.debug_file.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_settings.debug_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(logging.DEBUG)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(stdout_handler)
    if log_settings.debug_file is not None:
        root.addHandler(file_handler)

    # A record is dropped by its logger before any handler ever sees it, so the logger
    # has to be at least as permissive as the most permissive handler. Everything from
    # `inferapi` is let through here and each handler filters on its own; third-party
    # libraries stay at INFO on the root, which is what keeps their DEBUG out.
    root.setLevel(logging.INFO)
    logging.getLogger("inferapi").setLevel(logging.DEBUG)
