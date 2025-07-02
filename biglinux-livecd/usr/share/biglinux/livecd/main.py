import sys
import argparse
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
    args, remaining_argv = parser.parse_known_args()

    # Initialize the service layer with the test mode state
    system_service = SystemService(test_mode=args.test_mode)

    app = Application(system_service=system_service)
    return app.run([sys.argv[0]] + remaining_argv)

if __name__ == "__main__":
    sys.exit(main())
