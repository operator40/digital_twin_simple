import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_rejected_logger(
    path: str, max_bytes: int, backup_count: int
) -> logging.Logger:
    log_path = Path(path)
    log_path.parent.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("datacollector.rejected")
    logger.setLevel(logging.WARNING)
    logger.propagate = False

    if not logger.handlers:
        handler = RotatingFileHandler(
            log_path,
            maxBytes=max_bytes,
            backupCount=backup_count,
            encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    return logger
