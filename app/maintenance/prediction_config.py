import tomllib
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from ..settings import settings


@dataclass(frozen=True, slots=True)
class PredictionConfig:
    delta_sampling: pd.Timedelta
    delta_horizon: pd.Timedelta


def load_prediction_config(config_path: str | Path | None = None) -> PredictionConfig:

    if config_path is None:
        config_path = settings.PREDICTION_CONFIG_PATH

    path = Path(config_path)

    with path.open("rb") as config_file:
        config_data = tomllib.load(config_file)

    prediction_data = config_data["prediction"]

    return PredictionConfig(delta_sampling=pd.Timedelta(prediction_data["delta_sampling"]), delta_horizon=pd.Timedelta(prediction_data["delta_horizon"]))


prediction_config = load_prediction_config()
