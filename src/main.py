#!/usr/bin/env python3
"""
palera1n-gui — Main entry point
Waveshare 1.3inch LCD HAT (ST7789, 240x240) + joystick/buttons on RPi Zero 2W
"""

import sys
import os
import signal
import logging
import time

# Allow running from project root
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from display import Display
from input_handler import InputHandler
from app import App

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    handlers=[
        logging.FileHandler("/var/log/palera1n-gui.log"),
        logging.StreamHandler(sys.stdout),
    ],
)
log = logging.getLogger("main")


def _ensure_root():
    """Re-exec the script under sudo if not already running as root."""
    if os.getuid() != 0:
        print("[palera1n-gui] Not running as root — re-launching with sudo...", flush=True)
        os.execvp("sudo", ["sudo", sys.executable] + sys.argv)
        # execvp replaces this process; the line below is only reached on failure
        sys.exit("sudo not available — please run as root")


def main():
    _ensure_root()
    log.info("palera1n-gui starting up (uid=0)")

    display = Display()
    input_handler = InputHandler()
    app = App(display, input_handler)

    def shutdown(signum, frame):
        log.info("Shutdown signal received")
        app.stop()
        display.clear()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        app.run()
    except Exception as e:
        log.exception(f"Fatal error: {e}")
        display.show_error(str(e))
        time.sleep(5)
        sys.exit(1)


if __name__ == "__main__":
    main()
