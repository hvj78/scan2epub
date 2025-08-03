import logging
import sys
from typing import Optional


def setup_logging(debug: bool = False, level: Optional[int] = None) -> None:
    """
    Configure root logging for the application.

    Args:
        debug: If True, sets log level to DEBUG; otherwise INFO.
        level: Optional explicit level to override debug flag.
    """
    # Determine level
    log_level = level if level is not None else (logging.DEBUG if debug else logging.INFO)

    # Clear existing handlers to avoid duplicate logs if setup is called multiple times
    root = logging.getLogger()
    if root.handlers:
        for h in list(root.handlers):
            root.removeHandler(h)

    handler = logging.StreamHandler(stream=sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
        datefmt="%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root.setLevel(log_level)
    root.addHandler(handler)

    # Reduce verbosity of noisy third-party loggers if needed
    for noisy in ("azure", "urllib3", "httpx"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
