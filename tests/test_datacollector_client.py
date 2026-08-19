import pytest

from app.datacollector.client import parse_metric_values_page


def test_parse_metric_values_page() -> None:
    result = parse_metric_values_page(
        {
            "content": [
                {
                    "value": "13.0000000000000000",
                    "createdAt": "2026-08-18 11:16:53.931",
                    "metricFunctionUniqueIdentifier": "teszt",
                    "technicalObjectUniqueIdentifier": "pe teszt",
                    "symbol": "A",
                    "tags": None,
                    "valid": True,
                }
            ],
            "page": {
                "size": 10,
                "number": 0,
                "totalElements": 1,
                "totalPages": 1,
            },
        }
    )

    assert result.number == 0
    assert result.total_pages == 1
    assert result.content[0]["value"] == "13.0000000000000000"
    assert result.content[0]["tags"] is None


@pytest.mark.parametrize(
    "payload",
    [
        [],
        {"content": [], "page": None},
        {"content": {}, "page": {"number": 0, "totalPages": 1}},
        {"content": [], "page": {"number": -1, "totalPages": 1}},
        {"content": [], "page": {"number": 0, "totalPages": "1"}},
    ],
)
def test_parse_metric_values_page_rejects_invalid_payload(payload: object) -> None:
    with pytest.raises(ValueError):
        parse_metric_values_page(payload)
