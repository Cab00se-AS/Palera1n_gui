"""
input_handler.py — GPIO input for Waveshare 1.3inch LCD HAT

Button/joystick GPIO pin mapping (BCM):
  Joystick Up    → GPIO 6
  Joystick Down  → GPIO 19
  Joystick Left  → GPIO 5
  Joystick Right → GPIO 26
  Joystick Press → GPIO 13
  Button A (KEY1) → GPIO 21
  Button B (KEY2) → GPIO 20
  Button C (KEY3) → GPIO 16
"""

import logging
import time
import threading
from enum import Enum, auto
from typing import Callable, Dict, Optional

log = logging.getLogger("input")

# --- GPIO pin map (BCM) ---
PINS = {
    "UP":    6,
    "DOWN":  19,
    "LEFT":  5,
    "RIGHT": 26,
    "PRESS": 13,
    "KEY1":  21,
    "KEY2":  20,
    "KEY3":  16,
}

DEBOUNCE_MS = 200


class Button(Enum):
    UP = auto()
    DOWN = auto()
    LEFT = auto()
    RIGHT = auto()
    PRESS = auto()
    KEY1 = auto()
    KEY2 = auto()
    KEY3 = auto()


class InputHandler:
    """
    Polls or uses edge-detection on GPIO to detect button events.
    Falls back to keyboard (stdin) in mock/dev mode.

    Usage:
        inp = InputHandler()
        inp.on(Button.UP, my_callback)
        inp.start()
    """

    def __init__(self):
        self._callbacks: Dict[Button, Callable] = {}
        self._last_press: Dict[Button, float] = {}
        self._running = False
        self._mock = False
        self._thread: Optional[threading.Thread] = None
        self._gpio = None
        self._init_gpio()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def on(self, button: Button, callback: Callable):
        """Register a callback for a button press."""
        self._callbacks[button] = callback

    def start(self):
        """Start listening for input events (non-blocking)."""
        self._running = True
        if self._mock:
            self._thread = threading.Thread(target=self._mock_loop, daemon=True)
        else:
            self._thread = threading.Thread(target=self._gpio_loop, daemon=True)
        self._thread.start()
        log.info(f"Input handler started [{'mock' if self._mock else 'gpio'}]")

    def stop(self):
        self._running = False
        if self._gpio:
            try:
                self._gpio.cleanup()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Init
    # ------------------------------------------------------------------

    def _init_gpio(self):
        try:
            import RPi.GPIO as GPIO
            GPIO.setmode(GPIO.BCM)
            GPIO.setwarnings(False)
            for name, pin in PINS.items():
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            self._gpio = GPIO
            log.info("GPIO initialized")
        except (ImportError, RuntimeError):
            log.warning("RPi.GPIO not available — running in mock/keyboard mode")
            self._mock = True

    # ------------------------------------------------------------------
    # GPIO polling loop
    # ------------------------------------------------------------------

    _PIN_TO_BUTTON = {v: Button[k] for k, v in PINS.items()}

    def _gpio_loop(self):
        GPIO = self._gpio
        prev = {pin: GPIO.HIGH for pin in PINS.values()}
        while self._running:
            for pin, button in self._PIN_TO_BUTTON.items():
                current = GPIO.input(pin)
                if current == GPIO.LOW and prev[pin] == GPIO.HIGH:
                    self._fire(button)
                prev[pin] = current
            time.sleep(0.02)  # 50 Hz poll

    def _fire(self, button: Button):
        now = time.time()
        last = self._last_press.get(button, 0)
        if (now - last) * 1000 < DEBOUNCE_MS:
            return
        self._last_press[button] = now
        cb = self._callbacks.get(button)
        if cb:
            try:
                cb()
            except Exception as e:
                log.error(f"Input callback error [{button}]: {e}")

    # ------------------------------------------------------------------
    # Mock keyboard loop (for dev on desktop)
    # ------------------------------------------------------------------

    _KEY_MAP = {
        "w": Button.UP,
        "s": Button.DOWN,
        "a": Button.LEFT,
        "d": Button.RIGHT,
        "\r": Button.PRESS,
        "1": Button.KEY1,
        "2": Button.KEY2,
        "3": Button.KEY3,
    }

    def _mock_loop(self):
        """Reads single keypresses from stdin for testing."""
        import sys
        import tty
        import termios

        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            while self._running:
                ch = sys.stdin.read(1)
                button = self._KEY_MAP.get(ch)
                if button:
                    self._fire(button)
                if ch == "q":
                    self._running = False
        except Exception:
            pass
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)
