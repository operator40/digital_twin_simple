from datetime import datetime
from typing import Any

import httpx


class DataCollectorClient:
    def __init__(self, base_url: str, api_key: str, timeout_seconds: float):
        self._client = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={"x-api-key": api_key},
            timeout=timeout_seconds,
        )

    def close(self) -> None:
        self._client.close()

    def get_metrics(self) -> list[dict[str, Any]]:
        response = self._client.get("/ex/api/metrics")
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("DC /metrics response must be a JSON array")
        return payload

    def get_metric_values(
        self,
        technical_object_id: int,
        metric_function_id: int,
        time_from: datetime,
        time_to: datetime,
        page: int,
        size: int,
    ) -> list[dict[str, Any]]:
        response = self._client.get(
            "/ex/api/metric-values",
            params={
                "technicalObjectUniqueIdentifier": str(technical_object_id),
                "metricFunctionUniqueIdentifier": str(metric_function_id),
                "timeFrom": time_from.isoformat(),
                "timeTo": time_to.isoformat(),
                "isValid": "true",
                "page": page,
                "size": size,
            },
        )
        response.raise_for_status()
        payload = response.json()
        if not isinstance(payload, list):
            raise ValueError("DC /metric-values response must be a JSON array")
        return payload
