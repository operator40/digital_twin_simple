from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class AssetPredictIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    workorder_id: int = Field(gt=0)
    cmms_asset_id: int = Field(alias="asset_id", gt=0)
    failure_cause_id: Optional[int] = Field(default=None, gt=0)
    failure_date: datetime | None = None
    ended: datetime
    type: Literal["PREVENTIVE", "CORRECTIVE"]
    operation_ids: list[int] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_asset_predict(self):
        if self.type == "CORRECTIVE":
            if self.failure_date is None:
                raise ValueError("failure_date is required for a corrective work order")

            if self.failure_cause_id is None:
                raise ValueError("failure_cause_id is required for a corrective work order")

        return self


class AssetPredictAccepted(BaseModel):
    job_id: int


class AssetPredictionPayload(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    prediction_id: int = Field(gt=0)
    cmms_asset_id: int = Field(serialization_alias="asset_id", gt=0)
    predicted_reliability: float = Field(ge=0.0, le=1.0)


class FailureCausePredictionItem(BaseModel):
    asset_failurecause_id: int = Field(gt=0)
    predicted_occurrence_probability: float = Field(ge=0.0, le=0.99)


class AssetFailureCausePredictionPayload(BaseModel):
    prediction_id: int = Field(gt=0)
    failure_causes: list[FailureCausePredictionItem] = Field(min_length=1)


class AssetMappingIn(BaseModel):
    cmms_asset_id: int | None = Field(default=None, gt=0)
    dc_asset_id: str | None = Field(default=None, min_length=1)

    @field_validator("dc_asset_id")
    @classmethod
    def normalize_dc_asset_id(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("dc_asset_id cannot be empty")
        return normalized

    @model_validator(mode="after")
    def require_external_identifier(self):
        if self.cmms_asset_id is None and self.dc_asset_id is None:
            raise ValueError(
                "At least one of cmms_asset_id or dc_asset_id is required"
            )
        return self


class AssetMappingBatchIn(BaseModel):
    mappings: list[AssetMappingIn] = Field(min_length=1)


class AssetMappingItemResult(BaseModel):
    cmms_asset_id: int | None = None
    dc_asset_id: str | None = None
    status: Literal["created", "updated", "unchanged", "conflict"]
    asset_id: int | None = None
    reason: str | None = None


class AssetMappingBatchResult(BaseModel):
    created: int
    updated: int
    unchanged: int
    conflicts: int
    results: list[AssetMappingItemResult]
