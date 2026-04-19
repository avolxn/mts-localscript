from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FILENAME = "localscript.log"
_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def log_path(runtime_dir: Path) -> Path:
    directory = runtime_dir / "logs"
    directory.mkdir(parents=True, exist_ok=True)
    return directory / LOG_FILENAME


def configure_logging(runtime_dir: Path) -> Path:
    target = log_path(runtime_dir).resolve()
    logger = logging.getLogger("localscript")
    logger.setLevel(logging.INFO)
    logger.propagate = False

    for handler in list(logger.handlers):
        if isinstance(handler, RotatingFileHandler):
            current = Path(handler.baseFilename).resolve()
            if current == target:
                return target
            logger.removeHandler(handler)
            handler.close()

    handler = RotatingFileHandler(
        target,
        maxBytes=2_000_000,
        backupCount=3,
        encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(_FORMAT))
    logger.addHandler(handler)
    return target


def get_logger(name: str) -> logging.Logger:
    if name.startswith("localscript"):
        return logging.getLogger(name)
    return logging.getLogger(f"localscript.{name}")
