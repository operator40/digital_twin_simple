import logging
import time

from app.datacollector.client import DataCollectorClient
from app.datacollector.config import load_config
from app.datacollector.logging import configure_rejected_logger
from app.datacollector.repository import DataCollectorRepository
from app.datacollector.service import DataCollectorService
from app.db import SyncSessionLocal
from app.settings import settings


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s - %(message)s",
)
logger = logging.getLogger(__name__)


def main() -> None:
    config = load_config(settings.DATACOLLECTOR_CONFIG_PATH)
    if not settings.DC_BASE_URL:
        raise ValueError("DC_BASE_URL is required for the data collector")
    if settings.DC_API_KEY is None:
        raise ValueError("DC_API_KEY is required for the data collector")

    rejected_logger = configure_rejected_logger(
        settings.DATACOLLECTOR_REJECTED_LOG_PATH,
        config.rejected_log_max_bytes,
        config.rejected_log_backup_count,
    )
    client = DataCollectorClient(
        settings.DC_BASE_URL,
        settings.DC_API_KEY.get_secret_value(),
        config.request_timeout_seconds,
    )

    logger.info("DC data collector started")
    try:
        while True:
            with SyncSessionLocal() as session:
                service = DataCollectorService(
                    client=client,
                    repository=DataCollectorRepository(session),
                    config=config,
                    rejected_logger=rejected_logger,
                )
                try:
                    service.run_cycle()
                except Exception:
                    session.rollback()
                    logger.exception("DC synchronization cycle failed")
            time.sleep(config.poll_interval_minutes * 60)
    finally:
        client.close()


if __name__ == "__main__":
    main()
