"""
app.py — Application state machine for palera1n-gui

States:
  SPLASH → MENU → DEVICE_WAIT → DFU_GUIDE → CONFIRM → JAILBREAK → DONE
                ↘ OPTIONS
                ↘ SYSINFO
                ↘ POWER
"""

import logging
import time
import threading
from enum import Enum, auto
from typing import List

from display import Display
from input_handler import InputHandler, Button
from jailbreak import JailbreakRunner, JailbreakOptions, InstallRunner
from device import detect_device
import sysinfo
import ui

log = logging.getLogger("app")

RENDER_FPS = 15
RENDER_INTERVAL = 1.0 / RENDER_FPS


class State(Enum):
    SPLASH       = auto()
    MENU         = auto()
    DEVICE_WAIT  = auto()
    DFU_GUIDE    = auto()
    CONFIRM      = auto()
    JAILBREAK    = auto()
    DONE         = auto()
    OPTIONS      = auto()
    MORE_OPTIONS = auto()
    SYSINFO      = auto()
    POWER        = auto()
    INSTALL      = auto()


MAIN_MENU_ITEMS = [
    "Start Jailbreak",
    "Install palera1n",
    "Options",
    "System Info",
    "Power",
]

POWER_MENU_ITEMS = [
    "Reboot",
    "Shutdown",
    "Back",
]

# Keys on JailbreakOptions toggled by the More Options screen (in display order)
MORE_OPTIONS_KEYS = [
    "demote",
    "dfuhelper",
    "enter_recovery",
    "exit_recovery",
    "jbinit_log",
    "pongo_shell",
    "pongo_full",
    "reboot_device",
    "telnetd",
    "setup_partial_fakefs",
    "setup_fakefs",
    "clean_fakefs",
    "force_revert",
]


class App:
    def __init__(self, display: Display, input_handler: InputHandler):
        self._display = display
        self._input = input_handler
        self._state = State.SPLASH
        self._running = False

        # Menu state
        self._menu_selected = 0
        self._power_selected = 0
        self._options_selected = 0
        self._more_options_selected = 0

        # Jailbreak state
        self._options = JailbreakOptions()
        self._runner = JailbreakRunner()
        self._jb_log_lines: List[str] = []
        self._jb_progress: float = 0.0
        self._jb_result: int = 0
        self._jb_result_msg: str = ""
        self._jb_done = False

        # Install state
        self._install_runner = InstallRunner()
        self._install_log_lines: List[str] = []
        self._install_result: int = 0
        self._install_done = False

        # DFU guide
        self._dfu_step = 0
        self._dfu_timer = 0.0

        # Device state
        self._device = None
        self._device_poll_thread = None

        # UI state
        self._dark_mode = True
        ui.set_theme(not self._dark_mode)  # explicitly apply dark theme on startup

        # Render lock
        self._render_lock = threading.Lock()

        self._register_inputs()

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    def run(self):
        self._running = True
        self._input.start()
        self._display.show_splash()
        time.sleep(2)
        self._transition(State.MENU)

        last_render = 0.0
        while self._running:
            now = time.time()
            if now - last_render >= RENDER_INTERVAL:
                self._render()
                last_render = now
            time.sleep(0.01)

    def stop(self):
        self._running = False
        self._runner.cancel()
        self._input.stop()

    # ------------------------------------------------------------------
    # Input bindings
    # ------------------------------------------------------------------

    def _register_inputs(self):
        self._input.on(Button.UP,    self._on_up)
        self._input.on(Button.DOWN,  self._on_down)
        self._input.on(Button.LEFT,  self._on_left)
        self._input.on(Button.RIGHT, self._on_right)
        self._input.on(Button.PRESS, self._on_press)
        self._input.on(Button.KEY1,  self._on_key1)
        self._input.on(Button.KEY2,  self._on_key2)
        self._input.on(Button.KEY3,  self._on_key3)

    def _on_up(self):
        if self._state == State.MENU:
            self._menu_selected = (self._menu_selected - 1) % len(MAIN_MENU_ITEMS)
        elif self._state == State.OPTIONS:
            self._options_selected = (self._options_selected - 1) % 7
        elif self._state == State.MORE_OPTIONS:
            self._more_options_selected = (self._more_options_selected - 1) % (len(MORE_OPTIONS_KEYS) + 1)
        elif self._state == State.POWER:
            self._power_selected = (self._power_selected - 1) % len(POWER_MENU_ITEMS)

    def _on_down(self):
        if self._state == State.MENU:
            self._menu_selected = (self._menu_selected + 1) % len(MAIN_MENU_ITEMS)
        elif self._state == State.OPTIONS:
            self._options_selected = (self._options_selected + 1) % 7
        elif self._state == State.MORE_OPTIONS:
            self._more_options_selected = (self._more_options_selected + 1) % (len(MORE_OPTIONS_KEYS) + 1)
        elif self._state == State.POWER:
            self._power_selected = (self._power_selected + 1) % len(POWER_MENU_ITEMS)

    def _on_left(self):
        self._go_back()

    def _on_right(self):
        self._on_press()

    def _on_press(self):
        """Joystick click = SELECT / CONFIRM."""
        if self._state == State.MENU:
            self._handle_menu_select()
        elif self._state == State.OPTIONS:
            self._handle_options_select()
        elif self._state == State.MORE_OPTIONS:
            self._handle_more_options_select()
        elif self._state == State.POWER:
            self._handle_power_select()
        elif self._state == State.DEVICE_WAIT:
            if self._device:
                self._transition(State.DFU_GUIDE)
        elif self._state == State.DFU_GUIDE:
            self._dfu_advance()
        elif self._state == State.CONFIRM:
            self._start_jailbreak()
        elif self._state == State.DONE:
            self._transition(State.MENU)
        elif self._state == State.INSTALL and self._install_done:
            self._transition(State.MENU)

    def _on_key1(self):
        """KEY1 = context action / skip."""
        if self._state == State.DFU_GUIDE:
            # Skip DFU guide, go straight to confirm
            self._transition(State.CONFIRM)

    def _on_key2(self):
        """KEY2 = cancel current operation."""
        if self._state == State.JAILBREAK:
            self._runner.cancel()
        elif self._state == State.INSTALL:
            self._install_runner.cancel()

    def _on_key3(self):
        """KEY3 = back / cancel / exit."""
        if self._state == State.INSTALL:
            if self._install_done:
                self._transition(State.MENU)
            else:
                self._install_runner.cancel()
        else:
            self._go_back()

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _transition(self, new_state: State):
        log.info(f"State: {self._state.name} → {new_state.name}")
        self._state = new_state

        if new_state == State.DEVICE_WAIT:
            self._start_device_poll()
        elif new_state == State.DFU_GUIDE:
            self._dfu_step = 0
            self._dfu_timer = time.time()
        elif new_state == State.JAILBREAK:
            self._jb_log_lines = ["~ Starting palera1n..."]
            self._jb_progress = 0.0
            self._jb_done = False
        elif new_state == State.INSTALL:
            self._install_log_lines = ["~ Starting palera1n installation..."]
            self._install_done = False
            self._install_result = 0
            self._start_install()

    def _go_back(self):
        back_map = {
            State.DEVICE_WAIT:  State.MENU,
            State.DFU_GUIDE:    State.DEVICE_WAIT,
            State.CONFIRM:      State.MENU,
            State.OPTIONS:      State.MENU,
            State.MORE_OPTIONS: State.OPTIONS,
            State.SYSINFO:      State.MENU,
            State.POWER:        State.MENU,
            State.DONE:         State.MENU,
        }
        target = back_map.get(self._state)
        if target:
            if self._state == State.DEVICE_WAIT:
                self._stop_device_poll()
            self._transition(target)

    # ------------------------------------------------------------------
    # Menu handlers
    # ------------------------------------------------------------------

    def _handle_menu_select(self):
        item = MAIN_MENU_ITEMS[self._menu_selected]
        if item == "Start Jailbreak":
            self._transition(State.DEVICE_WAIT)
        elif item == "Install palera1n":
            self._transition(State.INSTALL)
        elif item == "Options":
            self._transition(State.OPTIONS)
        elif item == "System Info":
            self._transition(State.SYSINFO)
        elif item == "Power":
            self._transition(State.POWER)

    def _handle_options_select(self):
        opts_keys = ["rootless", "safe_mode", "verbose", "verbose_boot"]
        if self._options_selected < len(opts_keys):        # 0-3: jailbreak options
            key = opts_keys[self._options_selected]
            current = getattr(self._options, key)
            setattr(self._options, key, not current)
            log.info(f"Option {key} = {not current}")
        elif self._options_selected == 4:                  # Dark Mode toggle
            self._dark_mode = not self._dark_mode
            ui.set_theme(not self._dark_mode)
            log.info(f"Dark mode = {self._dark_mode}")
        elif self._options_selected == 5:                  # More Options
            self._more_options_selected = 0
            self._transition(State.MORE_OPTIONS)
        else:                                              # Back
            self._transition(State.MENU)

    def _handle_more_options_select(self):
        if self._more_options_selected < len(MORE_OPTIONS_KEYS):
            key = MORE_OPTIONS_KEYS[self._more_options_selected]
            current = getattr(self._options, key)
            setattr(self._options, key, not current)
            log.info(f"Option {key} = {not current}")
        else:                                              # Back
            self._transition(State.OPTIONS)

    def _handle_power_select(self):
        item = POWER_MENU_ITEMS[self._power_selected]
        if item == "Reboot":
            self._display.clear((10, 10, 10))
            import subprocess
            subprocess.run(["sudo", "reboot"])
        elif item == "Shutdown":
            self._display.clear((0, 0, 0))
            import subprocess
            subprocess.run(["sudo", "shutdown", "-h", "now"])
        elif item == "Back":
            self._transition(State.MENU)

    # ------------------------------------------------------------------
    # DFU guide
    # ------------------------------------------------------------------

    def _dfu_advance(self):
        self._dfu_step += 1
        self._dfu_timer = time.time()
        if self._dfu_step >= 3:
            self._transition(State.CONFIRM)

    # ------------------------------------------------------------------
    # Device polling
    # ------------------------------------------------------------------

    def _start_device_poll(self):
        self._device = None
        self._device_poll_thread = threading.Thread(
            target=self._device_poll_loop, daemon=True
        )
        self._device_poll_thread.start()

    def _stop_device_poll(self):
        # Thread is daemonized, will stop on its own
        self._device = None

    def _device_poll_loop(self):
        while self._state == State.DEVICE_WAIT and self._running:
            self._device = detect_device()
            time.sleep(1.5)

    # ------------------------------------------------------------------
    # Install execution
    # ------------------------------------------------------------------

    def _start_install(self):
        def on_line(line: str):
            with self._render_lock:
                self._install_log_lines.append(line)
                if len(self._install_log_lines) > 40:
                    self._install_log_lines = self._install_log_lines[-40:]

        def on_done(code: int, msg: str):
            with self._render_lock:
                self._install_result = code
                self._install_done = True
                self._install_log_lines.append(msg)
            if code == 0:
                # Invalidate cached binary path so next search picks up the new install
                self._runner._binary_path = None
            log.info(f"Install finished: code={code} msg={msg}")

        self._install_runner.start(on_line=on_line, on_done=on_done)

    # ------------------------------------------------------------------
    # Jailbreak execution
    # ------------------------------------------------------------------

    def _start_jailbreak(self):
        self._transition(State.JAILBREAK)

        def on_line(line: str):
            # Track progress heuristically from known palera1n log markers
            progress_markers = {
                "Waiting for": 0.05,
                "Setting up": 0.10,
                "Exploiting": 0.20,
                "Uploading": 0.35,
                "Booting": 0.50,
                "Installing": 0.65,
                "Bootstrapping": 0.75,
                "Setting up environment": 0.85,
                "Done": 1.0,
            }
            for marker, pct in progress_markers.items():
                if marker.lower() in line.lower():
                    self._jb_progress = max(self._jb_progress, pct)

            with self._render_lock:
                self._jb_log_lines.append(line)
                if len(self._jb_log_lines) > 40:
                    self._jb_log_lines = self._jb_log_lines[-40:]

        def on_done(code: int, msg: str):
            with self._render_lock:
                self._jb_result = code
                self._jb_result_msg = msg
                self._jb_done = True
                if code == 0:
                    self._jb_progress = 1.0
            log.info(f"Jailbreak finished: code={code} msg={msg}")
            time.sleep(1.5)
            self._transition(State.DONE)

        self._runner.start(self._options, on_line=on_line, on_done=on_done)

    # ------------------------------------------------------------------
    # Render
    # ------------------------------------------------------------------

    def _render(self):
        with self._render_lock:
            img = self._build_frame()
        if img:
            self._display.show(img)

    def _build_frame(self):
        s = self._state

        if s == State.MENU:
            return ui.draw_menu(MAIN_MENU_ITEMS, self._menu_selected, "Main Menu")

        elif s == State.DEVICE_WAIT:
            name = self._device.name if self._device else ""
            return ui.draw_device_wait(self._device is not None, name)

        elif s == State.DFU_GUIDE:
            return ui.draw_dfu_instructions(self._dfu_step)

        elif s == State.CONFIRM:
            mode = "rootless" if self._options.rootless else "rootful"
            return ui.draw_confirm(
                "Start jailbreak?",
                f"Mode: {mode}  Safe: {'on' if self._options.safe_mode else 'off'}"
            )

        elif s == State.JAILBREAK:
            tail = self._jb_log_lines[-7:]
            return ui.draw_status(
                "Jailbreaking...",
                tail,
                progress=self._jb_progress,
                hint="KEY2: Cancel",
            )

        elif s == State.DONE:
            success = self._jb_result == 0
            return ui.draw_done(success, self._jb_result_msg)

        elif s == State.OPTIONS:
            opts = {
                "rootless":     self._options.rootless,
                "safe_mode":    self._options.safe_mode,
                "verbose":      self._options.verbose,
                "verbose_boot": self._options.verbose_boot,
                "dark_mode":    self._dark_mode,
            }
            return ui.draw_options(opts, self._options_selected)

        elif s == State.MORE_OPTIONS:
            opts = {k: getattr(self._options, k) for k in MORE_OPTIONS_KEYS}
            return ui.draw_more_options(opts, self._more_options_selected)

        elif s == State.SYSINFO:
            info = sysinfo.gather_all()
            return ui.draw_sysinfo(info)

        elif s == State.POWER:
            return ui.draw_menu(POWER_MENU_ITEMS, self._power_selected, "Power")

        elif s == State.INSTALL:
            if self._install_done:
                title = "Install Complete" if self._install_result == 0 else "Install Failed"
                hint = "● / KEY3: Back to menu"
            else:
                title = "Installing palera1n"
                hint = "KEY2 / KEY3: Cancel"
            return ui.draw_status(
                title,
                self._install_log_lines[-7:],
                hint=hint,
            )

        return None
