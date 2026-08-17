from datetime import datetime, timedelta
import json
import logging
import math
import re
from typing import Any

from app.datacollector.client import DataCollectorClient
from app.datacollector.config import DataCollectorConfig
from app.datacollector.repository import DataCollectorRepository


logger = logging.getLogger(__name__)
INTEGER_PATTERN = re.compile(r"^[+-]?\d+$")


class DataCollectorService:
    def __init__(
        self,
        client: DataCollectorClient,
        repository: DataCollectorRepository,
        config: DataCollectorConfig,
        rejected_logger: logging.Logger,
    ):
        self.client = client
        self.repository = repository
        self.config = config
        self.rejected_logger = rejected_logger

    def run_cycle(self) -> None:
        now = datetime.now()
        state = self.repository.get_state()

        if state is None:
            state = self.repository.create_state(now)
            self.refresh_metrics()
            state.last_metrics_sync_at = now
            self.repository.save_state(state)
            logger.info(
                "DC collector initialized at %s; historical measurements were not requested",
                now.isoformat(),
            )
            return

        if self._metrics_refresh_is_due(state.last_metrics_sync_at, now):
            self.refresh_metrics()
            state.last_metrics_sync_at = now
            self.repository.save_state(state)

        if state.last_successful_time_to is None:
            state.last_successful_time_to = now
            self.repository.save_state(state)
            return

        time_from = state.last_successful_time_to - timedelta(
            minutes=self.config.overlap_minutes
        )
        time_to = now
        missing_metadata_refreshed = False

        for technical_object_id, metric_function_id in self.repository.list_metric_pairs():
            page = self.config.page
            while True:
                values = self.client.get_metric_values(
                    technical_object_id=technical_object_id,
                    metric_function_id=metric_function_id,
                    time_from=time_from,
                    time_to=time_to,
                    page=page,
                    size=self.config.page_size,
                )
                for item in values:
                    refreshed = self._store_metric_value(
                        item,
                        allow_metadata_refresh=not missing_metadata_refreshed,
                        refresh_time=now,
                    )
                    missing_metadata_refreshed = (
                        missing_metadata_refreshed or refreshed
                    )
                self.repository.commit()

                if len(values) < self.config.page_size:
                    break
                page += 1

        state.last_successful_time_to = time_to
        self.repository.save_state(state)
        logger.info(
            "DC measurement synchronization completed for %s - %s",
            time_from.isoformat(),
            time_to.isoformat(),
        )

    def refresh_metrics(self) -> None:
        metrics = self.client.get_metrics()
        stored = 0
        for item in metrics:
            try:
                parsed = self._parse_metric(item)
                self.repository.store_metric(**parsed)
                stored += 1
            except (KeyError, TypeError, ValueError) as exc:
                self._reject("invalid metric metadata", item, error=str(exc))
        self.repository.commit()
        logger.info("DC metric synchronization completed: %d stored", stored)

    def _store_metric_value(
        self,
        item: dict[str, Any],
        allow_metadata_refresh: bool,
        refresh_time: datetime,
    ) -> bool:
        if item.get("valid") is not True:
            return False

        try:
            technical_object_id = parse_identifier(
                item["technicalObjectUniqueIdentifier"],
                "technicalObjectUniqueIdentifier",
            )
            metric_function_id = parse_identifier(
                item["metricFunctionUniqueIdentifier"],
                "metricFunctionUniqueIdentifier",
            )
            created_at = self._parse_created_at(item["createdAt"])
            value = parse_measurement_value(item["value"])
        except (KeyError, TypeError, ValueError) as exc:
            self._reject(
                "invalid metric value",
                item,
                error=str(exc),
                value=item.get("value"),
                createdAt=item.get("createdAt"),
                sf_asset_id=item.get("technicalObjectUniqueIdentifier"),
                metric_function_id=item.get("metricFunctionUniqueIdentifier"),
            )
            return False

        sensor = self.repository.find_latest_sensor(
            technical_object_id, metric_function_id
        )
        metadata_refreshed = False
        if sensor is None and allow_metadata_refresh:
            logger.warning(
                "Unknown DC metric; refreshing metadata: sf_asset_id=%s, metric_function_id=%s",
                technical_object_id,
                metric_function_id,
            )
            self.refresh_metrics()
            metadata_refreshed = True
            state = self.repository.get_state()
            if state is not None:
                state.last_metrics_sync_at = refresh_time
                self.repository.save_state(state)
            sensor = self.repository.find_latest_sensor(
                technical_object_id, metric_function_id
            )

        if sensor is None:
            self._reject(
                "missing metric metadata after refresh",
                item,
                value=item.get("value"),
                createdAt=created_at.isoformat(),
                sf_asset_id=technical_object_id,
                metric_function_id=metric_function_id,
            )
            return metadata_refreshed

        if self.repository.measurement_exists(
            technical_object_id, metric_function_id, created_at
        ):
            return metadata_refreshed

        self.repository.store_measurement(sensor.sensor_id, created_at, value)
        return metadata_refreshed

    def _parse_metric(self, item: dict[str, Any]) -> dict[str, Any]:
        result = {
            "technical_object_id": parse_identifier(
                item["technicalObjectUniqueIdentifier"],
                "technicalObjectUniqueIdentifier",
            ),
            "technical_object_name": required_text(
                item["technicalObjectName"], "technicalObjectName"
            ),
            "metric_function_id": parse_identifier(
                item["metricFunctionUniqueIdentifier"],
                "metricFunctionUniqueIdentifier",
            ),
            "metric_function_name": required_text(
                item["metricFunctionName"], "metricFunctionName"
            ),
            "unit_name": required_text(item["unitName"], "unitName"),
            "unit_symbol": required_text(item["unitSymbol"], "unitSymbol"),
            "data_type": required_text(item["dataType"], "dataType"),
        }
        return result

    def _parse_created_at(self, value: Any) -> datetime:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("createdAt must be a non-empty string")
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone().replace(tzinfo=None)
        return parsed

    def _metrics_refresh_is_due(
        self, last_sync: datetime | None, now: datetime
    ) -> bool:
        return last_sync is None or now - last_sync >= timedelta(
            minutes=self.config.metrics_refresh_interval_minutes
        )

    def _reject(
        self, reason: str, item: Any, **context: Any
    ) -> None:
        logger.warning("DC item rejected: %s; context=%s", reason, context)
        self.rejected_logger.warning(
            json.dumps(
                {"reason": reason, **context, "payload": item},
                ensure_ascii=False,
                default=str,
            )
        )


def parse_identifier(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isfinite(value) and value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer: {value!r}")
    text = str(value).strip()
    if not INTEGER_PATTERN.fullmatch(text):
        raise ValueError(f"{field_name} must be numeric: {value!r}")
    return int(text)


def required_text(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field_name} must be a non-empty string")
    return value.strip()


def parse_measurement_value(value: Any) -> float:
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return 1.0
        if normalized == "false":
            return 0.0
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError(f"measurement value is not finite: {value!r}")
    return parsed
