"""
Services package for BigLinux Calamares Configuration Tool
Business logic and external integrations
"""

import logging

# Import all service classes
from .system_service import SystemService
from .package_service import PackageService  
from .install_service import InstallService

# Package metadata
__version__ = "1.0.0"
__author__ = "BigLinux Team"

# Logger for the services package
logger = logging.getLogger(__name__)

# Service instances (singletons)
_system_service = None
_package_service = None
_install_service = None


def get_system_service() -> SystemService:
    """
    Get the system service singleton instance
    
    Returns:
        SystemService instance
    """
    global _system_service
    if _system_service is None:
        _system_service = SystemService()
        logger.debug("SystemService instance created")
    return _system_service


def get_package_service() -> PackageService:
    """
    Get the package service singleton instance
    
    Returns:
        PackageService instance
    """
    global _package_service
    if _package_service is None:
        _package_service = PackageService()
        logger.debug("PackageService instance created")
    return _package_service


def get_install_service() -> InstallService:
    """
    Get the install service singleton instance
    
    Returns:
        InstallService instance
    """
    global _install_service
    if _install_service is None:
        _install_service = InstallService()
        logger.debug("InstallService instance created")
    return _install_service


def initialize_services():
    """Initialize all services - call this at application startup"""
    logger.info("Initializing services...")
    
    # Initialize system service first (other services may depend on it)
    system_svc = get_system_service()
    system_svc.initialize()
    
    # Initialize package service
    package_svc = get_package_service()
    package_svc.initialize()
    
    # Initialize install service
    install_svc = get_install_service()
    install_svc.initialize()
    
    logger.info("All services initialized successfully")


def cleanup_services():
    """Cleanup all services - call this at application shutdown"""
    logger.info("Cleaning up services...")
    
    global _system_service, _package_service, _install_service
    
    # Cleanup in reverse order
    if _install_service:
        _install_service.cleanup()
        _install_service = None
    
    if _package_service:
        _package_service.cleanup()
        _package_service = None
        
    if _system_service:
        _system_service.cleanup()
        _system_service = None
    
    logger.info("All services cleaned up")


# Expose main classes and functions
__all__ = [
    "SystemService",
    "PackageService", 
    "InstallService",
    "get_system_service",
    "get_package_service",
    "get_install_service",
    "initialize_services",
    "cleanup_services"
]