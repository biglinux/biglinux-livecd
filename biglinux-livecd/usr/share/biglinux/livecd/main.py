import sys
import argparse
import logging
from logging_config import setup_logging
from application import Application
from services import SystemService

def main():
    """Initializes and runs the GTK application."""
    parser = argparse.ArgumentParser(description="BigLinux Setup Utility")
    parser.add_argument(
        "--test-mode",
        action="store_true",
        help="Run in test mode without applying any system changes.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging.",
    )
    args, remaining_argv = parser.parse_known_args()

    # Setup logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    setup_logging(level=log_level)

    # Initialize the service layer with the test mode state
    system_service = SystemService(test_mode=args.test_mode)

    app = Application(system_service=system_service)
    return app.run([sys.argv[0]] + remaining_argv)

if __name__ == "__main__":
    sys.exit(main())
