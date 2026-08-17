from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Asset,
    DataCollectorSyncState,
    Measurement,
    MeasurementType,
    Sensor,
    SensorType,
)


SYNC_NAME = "silverfrog_dc"


class DataCollectorRepository:
    def __init__(self, session: Session):
        self.session = session

    def get_state(self) -> DataCollectorSyncState | None:
        return self.session.get(DataCollectorSyncState, SYNC_NAME)

    def create_state(self, now: datetime) -> DataCollectorSyncState:
        state = DataCollectorSyncState(
            sync_name=SYNC_NAME,
            last_successful_time_to=now,
            last_metrics_sync_at=None,
        )
        self.session.add(state)
        self.session.flush()
        return state

    def save_state(self, state: DataCollectorSyncState) -> None:
        self.session.add(state)
        self.session.commit()

    def store_metric(
        self,
        technical_object_id: int,
        technical_object_name: str,
        metric_function_id: int,
        metric_function_name: str,
        unit_name: str,
        unit_symbol: str,
        data_type: str,
    ) -> Sensor:
        asset = self.session.scalar(
            select(Asset).where(Asset.sf_asset_id == technical_object_id)
        )
        if asset is None:
            asset = Asset(
                sf_asset_id=technical_object_id,
                asset_name=technical_object_name,
            )
            self.session.add(asset)
            self.session.flush()
        elif asset.asset_name != technical_object_name:
            asset.asset_name = technical_object_name

        measurement_type = self.session.scalar(
            select(MeasurementType).where(
                MeasurementType.measurement_type_name == metric_function_name,
                MeasurementType.unit_name == unit_name,
                MeasurementType.unit_symbol == unit_symbol,
            )
        )
        if measurement_type is None:
            measurement_type = MeasurementType(
                measurement_type_name=metric_function_name,
                unit=unit_symbol or unit_name,
                unit_name=unit_name,
                unit_symbol=unit_symbol,
            )
            self.session.add(measurement_type)
            self.session.flush()

        sensor_type = self.session.scalar(
            select(SensorType).where(
                SensorType.type_name == data_type,
                SensorType.measurement_type_id
                == measurement_type.measurement_type_id,
            )
        )
        if sensor_type is None:
            sensor_type = SensorType(
                type_name=data_type,
                measurement_type_id=measurement_type.measurement_type_id,
            )
            self.session.add(sensor_type)
            self.session.flush()

        sensor = self.session.scalar(
            select(Sensor).where(
                Sensor.asset_id == asset.asset_id,
                Sensor.metric_function_id == metric_function_id,
                Sensor.sensor_name == metric_function_name,
                Sensor.type_id == sensor_type.type_id,
            )
        )
        if sensor is None:
            sensor = Sensor(
                sensor_name=metric_function_name,
                type_id=sensor_type.type_id,
                asset_id=asset.asset_id,
                metric_function_id=metric_function_id,
            )
            self.session.add(sensor)
            self.session.flush()
        return sensor

    def commit(self) -> None:
        self.session.commit()

    def rollback(self) -> None:
        self.session.rollback()

    def list_metric_pairs(self) -> list[tuple[int, int]]:
        rows = self.session.execute(
            select(Asset.sf_asset_id, Sensor.metric_function_id)
            .join(Sensor, Sensor.asset_id == Asset.asset_id)
            .where(
                Asset.sf_asset_id.is_not(None),
                Sensor.metric_function_id.is_not(None),
            )
            .distinct()
            .order_by(Asset.sf_asset_id, Sensor.metric_function_id)
        ).all()
        return [(int(asset_id), int(metric_id)) for asset_id, metric_id in rows]

    def find_latest_sensor(
        self, technical_object_id: int, metric_function_id: int
    ) -> Sensor | None:
        return self.session.scalar(
            select(Sensor)
            .join(Asset, Asset.asset_id == Sensor.asset_id)
            .where(
                Asset.sf_asset_id == technical_object_id,
                Sensor.metric_function_id == metric_function_id,
            )
            .order_by(Sensor.sensor_id.desc())
            .limit(1)
        )

    def measurement_exists(
        self,
        technical_object_id: int,
        metric_function_id: int,
        created_at: datetime,
    ) -> bool:
        return self.session.scalar(
            select(Measurement.measurement_id)
            .join(Sensor, Sensor.sensor_id == Measurement.sensor_id)
            .join(Asset, Asset.asset_id == Sensor.asset_id)
            .where(
                Asset.sf_asset_id == technical_object_id,
                Sensor.metric_function_id == metric_function_id,
                Measurement.time == created_at,
            )
            .limit(1)
        ) is not None

    def store_measurement(
        self, sensor_id: int, created_at: datetime, value: float
    ) -> None:
        self.session.add(
            Measurement(sensor_id=sensor_id, time=created_at, value=value)
        )
