import logging
import logging.handlers
import sys
from pathlib import Path

from src.utils.paths import get_user_data_dir


def setup_logger() -> logging.Logger:
    """
    Initializes the root logger for the CI-Hörtrainer application.
    Sets up a rotating file handler to log to the user data directory,
    and a stream handler to log to the console.
    """
    # Create logs directory
    log_dir = get_user_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = log_dir / "ci_training.log"

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # Avoid adding handlers multiple times if setup is called again
    if not logger.handlers:
        # File handler: max 5MB, keep 3 backup files, utf-8 encoding
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8"
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)

        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_formatter = logging.Formatter(
            '%(levelname)s: %(message)s'
        )
        console_handler.setFormatter(console_formatter)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger


def get_logger(name: str) -> logging.Logger:
    """
    Returns a logger with the specified name.
    Useful for creating module-level loggers (e.g. logger = get_logger(__name__)).
    """
    return logging.getLogger(name)
