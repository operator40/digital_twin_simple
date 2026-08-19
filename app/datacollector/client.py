from dataclasses import dataclass
from datetime import datetime
from typing import Any

import httpx


@dataclass(frozen=True)
class MetricValuesPage:
    content: list[dict[str, Any]]
    number: int
    total_pages: int


def parse_metric_values_page(payload: Any) -> MetricValuesPage:
    if not isinstance(payload, dict):
        raise ValueError(
            "DC /metric-values response must be a paginated JSON object"
        )

    content = payload.get("content")
    page = payload.get("page")
    if not isinstance(content, list) or not all(
        isinstance(item, dict) for item in content
    ):
        raise ValueError("DC /metric-values content must be a JSON array")
    if not isinstance(page, dict):
        raise ValueError("DC /metric-values response is missing page metadata")

    number = page.get("number")
    total_pages = page.get("totalPages")
    if (
        not isinstance(number, int)
        or isinstance(number, bool)
        or number < 0
    ):
        raise ValueError("DC /metric-values page.number must be non-negative")
    if (
        not isinstance(total_pages, int)
        or isinstance(total_pages, bool)
        or total_pages < 0
    ):
        raise ValueError(
            "DC /metric-values page.totalPages must be non-negative"
        )
    if total_pages > 0 and number >= total_pages:
        raise ValueError("DC /metric-values page metadata is inconsistent")

    return MetricValuesPage(
        content=content,
        number=number,
        total_pages=total_pages,
    )


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
        technical_object_id: str,
        metric_function_id: str,
        time_from: datetime,
        time_to: datetime,
        page: int,
        size: int,
    ) -> MetricValuesPage:
        response = self._client.get(
            "/ex/api/metric-values",
            params={
                "technicalObjectUniqueIdentifier": technical_object_id,
                "metricFunctionUniqueIdentifier": metric_function_id,
                "timeFrom": time_from.isoformat(),
                "timeTo": time_to.isoformat(),
                "isValid": "true",
                "page": page,
                "size": size,
            },
        )
        response.raise_for_status()
        return parse_metric_values_page(response.json())
