"""
Logging configuration
"""

import logging
import sys
from pathlib import Path
from .config import Config

# Ensure logs directory exists
logs_dir = Config.PROJECT_ROOT / "logs"
logs_dir.mkdir(exist_ok=True)


def setup_logger(name: str) -> logging.Logger:
    """
    Setup logger with file and console handlers
    
    Args:
        name: Logger name (usually __name__)
    
    Returns:
        Configured logger
    """
    logger = logging.getLogger(name)
    
    if logger.hasHandlers():
        return logger
    
    # Log level
    log_level = getattr(logging, Config.LOG_LEVEL, logging.INFO)
    logger.setLevel(log_level)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    
    # File handler
    file_handler = logging.FileHandler(logs_dir / "app.log")
    file_handler.setLevel(log_level)
    
    # Formatter
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    # Add handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    
    return logger