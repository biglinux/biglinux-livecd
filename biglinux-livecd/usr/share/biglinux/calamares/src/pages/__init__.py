"""
Pages package for BigLinux Calamares Configuration Tool
Application pages and navigation components
"""

import logging

# Import all page classes
from .main_page import MainPage
from .maintenance_page import MaintenancePage
from .minimal_page import MinimalPage
from .tips_page import TipsPage

# Package metadata
__version__ = "1.0.0"
__author__ = "BigLinux Team"

# Logger for the pages package
logger = logging.getLogger(__name__)

# Expose main page classes
__all__ = ["MainPage", "MaintenancePage", "MinimalPage", "TipsPage"]


def initialize_pages():
    """Initialize pages package - call this at application startup"""
    logger.info("Pages package initialized")


def cleanup_pages():
    """Cleanup pages package - call this at application shutdown"""
    logger.info("Pages package cleaned up")