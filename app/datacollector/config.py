from dataclasses import dataclass
from pathlib import Path
import tomllib


@dataclass(frozen=True)
class DataCollectorConfig:
    poll_interval_minutes: float
    overlap_minutes: float
    metrics_refresh_interval_minutes: float
    page: int
    page_size: int
    request_timeout_seconds: float
    rejected_log_max_bytes: int
    rejected_log_backup_count: int


def load_config(path: str) -> DataCollectorConfig:
    with Path(path).open("rb") as config_file:
        raw = tomllib.load(config_file)["datacollector"]

    config = DataCollectorConfig(**raw)
    if config.poll_interval_minutes <= 0:
        raise ValueError("poll_interval_minutes must be greater than zero")
    if config.overlap_minutes < 0:
        raise ValueError("overlap_minutes cannot be negative")
    if config.metrics_refresh_interval_minutes <= 0:
        raise ValueError("metrics_refresh_interval_minutes must be greater than zero")
    if config.page < 0:
        raise ValueError("page cannot be negative")
    if config.page_size <= 0:
        raise ValueError("page_size must be greater than zero")
    if config.request_timeout_seconds <= 0:
        raise ValueError("request_timeout_seconds must be greater than zero")
    return config
