import logging

from sqlalchemy import inspect, text

from .db import sync_engine


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("db-init")


REQUIRED_TABLES = {
    "asset_failure_types",
    "asset_worksheet_lists",
    "assets",
    "etas_betas",
    "failure_types",
    "gammas",
    "measurement_types",
    "measurements",
    "operations_done_lists",
    "prediction_asset_failure_type_levels",
    "prediction_asset_levels",
    "prediction_jobs",
    "predictions",
    "ranges",
    "sensor_failure_types",
    "sensor_statistics",
    "sensor_types",
    "sensors",
}

REQUIRED_HYPERTABLES = {
    "asset_worksheet_lists",
    "measurements",
    "prediction_asset_failure_type_levels",
    "prediction_asset_levels",
}


def main() -> None:
    """Verify the SQL-managed TimescaleDB schema before app startup."""

    log.info("Verifying database schema")

    with sync_engine.connect() as connection:
        existing_tables = set(
            inspect(connection).get_table_names(schema="public")
        )
        missing_tables = REQUIRED_TABLES - existing_tables

        if missing_tables:
            raise RuntimeError(
                "Missing database tables: "
                + ", ".join(sorted(missing_tables))
            )

        has_timescaledb = connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_extension "
                "WHERE extname = 'timescaledb'"
                ")"
            )
        ).scalar_one()

        if not has_timescaledb:
            raise RuntimeError("The timescaledb extension is not installed")

        hypertables = set(
            connection.execute(
                text(
                    "SELECT hypertable_name "
                    "FROM timescaledb_information.hypertables "
                    "WHERE hypertable_schema = 'public'"
                )
            ).scalars()
        )
        missing_hypertables = REQUIRED_HYPERTABLES - hypertables

        if missing_hypertables:
            raise RuntimeError(
                "Tables not configured as hypertables: "
                + ", ".join(sorted(missing_hypertables))
            )

        has_jobstatus = connection.execute(
            text(
                "SELECT EXISTS ("
                "SELECT 1 FROM pg_type t "
                "JOIN pg_namespace n ON n.oid = t.typnamespace "
                "WHERE n.nspname = 'public' AND t.typname = 'jobstatus'"
                ")"
            )
        ).scalar_one()

        if not has_jobstatus:
            raise RuntimeError("The public.jobstatus enum is missing")

        connection.execute(
            text(
                "ALTER TYPE public.jobstatus "
                "ADD VALUE IF NOT EXISTS 'skipped'"
            )
        )
        connection.commit()

    log.info("Database schema is valid")


if __name__ == "__main__":
    main()
