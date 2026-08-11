# dummy prediction test without using dt and db
# A dummy database created inside the run_prediction function if session is None, so we don't need to initialize it here.

import pandas as pd
from prediction_module.core import run_prediction

current_job = "job-5"  # check predictions.csv for the job_id, it should be unique for each prediction run
target_asset = "asset-1"  # asset-1 or asset-2

if target_asset == "asset-1":
    operation_template = [
        {
            "asset_failurecause_id": "AFT-1",
            "operation_ids": ["operation-1", "operation-2", "operation-3"]
        },
        {
            "asset_failurecause_id": "AFT-2",
            "operation_ids": ["operation-2", "operation-4"]
        }
    ]
    failure_start_time = None  # It was a preventive maintenance
    maintenance_end_time = pd.Timestamp("2026-01-10 08:00:00")

elif target_asset == "asset-2":
    operation_template = [
        {
            "asset_failurecause_id": "AFT-3",
            "operation_ids": ["operation-2", "operation-3"]
        },
        {
            "asset_failurecause_id": "AFT-4",
            "operation_ids": ["operation-3", "operation-4", "operation-5"]
        }
    ]
    failure_start_time = pd.Timestamp("2026-01-10 09:10:00")
    maintenance_end_time = pd.Timestamp("2026-01-10 10:00:00")

else:
    raise ValueError(f"Unknown asset_id: {target_asset}")

delta_horizon = pd.Timedelta(days=5)  # freely adjustable
delta_sample = pd.Timedelta(hours=1)  # freely adjustable

# 3. Execute the prediction function
prediction_result = run_prediction(
    asset_id=target_asset,
    job_id=current_job,
    operation_template_dict=operation_template,
    failure_start_time=failure_start_time,
    maintenance_end_time=maintenance_end_time,
    delta_horizon=delta_horizon,
    delta_sampling=delta_sample,
    session=None
)
