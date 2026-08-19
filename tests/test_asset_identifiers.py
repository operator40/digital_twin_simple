import pytest
from pydantic import ValidationError

from app.datacollector.service import parse_external_identifier
from app.maintenance.schemas import AssetMappingBatchIn, AssetPredictIn


def test_external_identifier_preserves_dc_text() -> None:
    assert parse_external_identifier("  TECH-0007  ", "dc_id") == "TECH-0007"


def test_asset_predict_keeps_external_api_alias() -> None:
    request = AssetPredictIn.model_validate(
        {
            "workorder_id": 1,
            "asset_id": 1875,
            "failure_cause_id": None,
            "failure_date": None,
            "ended": "2026-08-19T12:00:00",
            "type": "PREVENTIVE",
            "operation_ids": [],
        }
    )

    assert request.cmms_asset_id == 1875
    assert request.model_dump(mode="json", by_alias=True)["asset_id"] == 1875


def test_mapping_dc_identifier_is_trimmed() -> None:
    batch = AssetMappingBatchIn.model_validate(
        {
            "mappings": [
                {
                    "cmms_asset_id": 1875,
                    "dc_asset_id": "  TECH-00981  ",
                }
            ]
        }
    )

    assert batch.mappings[0].dc_asset_id == "TECH-00981"


def test_mapping_accepts_single_source_identifiers() -> None:
    batch = AssetMappingBatchIn.model_validate(
        {
            "mappings": [
                {"cmms_asset_id": 1875},
                {"dc_asset_id": "TECH-00981"},
            ]
        }
    )

    assert batch.mappings[0].dc_asset_id is None
    assert batch.mappings[1].cmms_asset_id is None


def test_mapping_rejects_item_without_external_identifier() -> None:
    with pytest.raises(ValidationError):
        AssetMappingBatchIn.model_validate({"mappings": [{}]})
