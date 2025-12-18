"""
Centralized logging configuration for BigLinux LiveCD.
"""

import logging
import sys

# Create logger
logger = logging.getLogger("biglinux-livecd")

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """
    Configure the application logger.
    
    Args:
        level: Logging level (default: INFO)
    
    Returns:
        Configured logger instance
    """
    logger.setLevel(level)
    
    # Avoid duplicate handlers if called multiple times
    if logger.handlers:
        return logger
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Format: timestamp - level - message
    formatter = logging.Formatter(
        fmt="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    console_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    
    return logger


def get_logger() -> logging.Logger:
    """
    Get the application logger instance.
    
    Returns:
        Logger instance
    """
    return logger
