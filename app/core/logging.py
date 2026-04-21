import logging


def configure_logging() -> logging.Logger:
    logger = logging.getLogger("homu.backend")
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s %(name)s %(message)s",
        )
    return logger


logger = configure_logging()
