from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AssetPredictIn(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    workorder_id: int = Field(gt=0)
    sf_asset_id: int = Field(alias="asset_id", gt=0)
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
    sf_asset_id: int = Field(serialization_alias="asset_id", gt=0)
    predicted_reliability: float = Field(ge=0.0, le=1.0)


class FailureCausePredictionItem(BaseModel):
    asset_failurecause_id: int = Field(gt=0)
    predicted_occurence_probability: float = Field(ge=0.0, le=0.99)


class AssetFailureCausePredictionPayload(BaseModel):
    prediction_id: int = Field(gt=0)
    failure_causes: list[FailureCausePredictionItem] = Field(min_length=1)
