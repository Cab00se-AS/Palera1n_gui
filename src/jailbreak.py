"""
jailbreak.py — palera1n binary wrapper

Finds and executes the palera1n binary, streaming stdout/stderr line by line.
Manages process lifecycle (start, cancel, cleanup).
"""

import os
import re
import subprocess
import logging
import threading
import time
import stat
from typing import Callable, Optional, List

# Strips ANSI escape sequences (colours, cursor moves, etc.)
_ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]|\x1b[@-_]')

# Matches leading timestamps in common formats:
#   [HH:MM:SS]  [HH:MM:SS.mmm]  HH:MM:SS  YYYY-MM-DD HH:MM:SS  [MM/DD/YYYY]
#   -[MM/DD/YY HH:MM:SS]  (palera1n native format, e.g. -[03/30/26 22:29:14])
_TS_RE = re.compile(
    r'^\[?\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2}(?:\.\d+)?Z?\]?\s*'  # ISO / date+time
    r'|^\[?\d{2}:\d{2}:\d{2}(?:\.\d+)?\]?\s*'                          # HH:MM:SS
    r'|^\[?\d{2}/\d{2}/\d{4}\]?\s*'                                     # MM/DD/YYYY
    r'|^-\s*\[\d{2}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2}\]\s*'             # -[MM/DD/YY HH:MM:SS] or - [MM/DD/YY HH:MM:SS]
)

# Matches level tags in [square] or <angle> brackets, maps to UI colour prefix
_LEVEL_TAG_RE = re.compile(r'^[\[<]([A-Za-z*!+~]{1,10})[\]>]\s*')
_LEVEL_MAP = {
    'error': '!', 'err': '!', 'fatal': '!',
    'warn': '~', 'warning': '~',
    'info': '+', 'verbose': '+', 'debug': '+', 'v': '+', '*': '+',
    '!': '!', '+': '+', '~': '~',
}


def _clean_line(raw: str) -> str:
    """Strip ANSI codes and timestamps; map log-level tags to UI colour prefixes."""
    line = _ANSI_RE.sub('', raw).strip()
    line = _TS_RE.sub('', line).strip()

    prefix = ''
    m = _LEVEL_TAG_RE.match(line)
    if m:
        prefix = _LEVEL_MAP.get(m.group(1).lower(), '')
        line = line[m.end():].strip()

    if not line:
        return ''
    if prefix and line[0] not in '!+~':
        return f'{prefix} {line}'
    return line

log = logging.getLogger("jailbreak")

# Paths to search for palera1n binary
BINARY_SEARCH_PATHS = [
    os.path.join(os.path.dirname(__file__), "../bin/palera1n"),
    "/usr/local/bin/palera1n",
    "/usr/bin/palera1n",
    os.path.expanduser("~/palera1n"),
    "./palera1n",
]

# Exit codes
EXIT_SUCCESS = 0
EXIT_CANCELLED = -1
EXIT_NOT_FOUND = -2
EXIT_PERMISSION = -3


class JailbreakOptions:
    def __init__(self):
        self.rootless: bool = True               # -l / --rootless (default); False = -f
        self.safe_mode: bool = False             # -s / --safe-mode
        self.verbose: bool = False               # -v / --debug-logging
        self.verbose_boot: bool = False          # -V / --verbose-boot
        # Extended options (More Options menu)
        self.demote: bool = False                # -d / --demote
        self.dfuhelper: bool = False             # -D / --dfuhelper
        self.enter_recovery: bool = False        # -E / --enter-recovery
        self.exit_recovery: bool = False         # -n / --exit-recovery
        self.jbinit_log: bool = False            # -L / --jbinit-log-to-file
        self.pongo_shell: bool = False           # -p / --pongo-shell
        self.pongo_full: bool = False            # -P / --pongo-full
        self.reboot_device: bool = False         # -R / --reboot-device
        self.telnetd: bool = False               # -T / --telnetd
        self.setup_partial_fakefs: bool = False  # -B / --setup-partial-fakefs
        self.setup_fakefs: bool = False          # -c / --setup-fakefs
        self.clean_fakefs: bool = False          # -C / --clean-fakefs
        self.force_revert: bool = False          # --force-revert

    def to_args(self) -> List[str]:
        args = []
        if self.rootless:
            args.append("-l")
        else:
            args.append("-f")
        if self.safe_mode:
            args.append("-s")
        if self.verbose:
            args.append("-v")
        if self.verbose_boot:
            args.append("-V")
        if self.demote:
            args.append("-d")
        if self.dfuhelper:
            args.append("-D")
        if self.enter_recovery:
            args.append("-E")
        if self.exit_recovery:
            args.append("-n")
        if self.jbinit_log:
            args.append("-L")
        if self.pongo_shell:
            args.append("-p")
        if self.pongo_full:
            args.append("-P")
        if self.reboot_device:
            args.append("-R")
        if self.telnetd:
            args.append("-T")
        if self.setup_partial_fakefs:
            args.append("-B")
        if self.setup_fakefs:
            args.append("-c")
        if self.clean_fakefs:
            args.append("-C")
        if self.force_revert:
            args.append("--force-revert")
        return args


class JailbreakRunner:
    """
    Manages a single palera1n execution.

    Usage:
        runner = JailbreakRunner()
        runner.start(options, on_line=print, on_done=callback)
        ...
        runner.cancel()
    """

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False
        self._binary_path: Optional[str] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def find_binary(self) -> Optional[str]:
        """Locate the palera1n binary."""
        if self._binary_path:
            return self._binary_path
        for path in BINARY_SEARCH_PATHS:
            if os.path.isfile(path):
                self._binary_path = path
                log.info(f"Found palera1n at: {path}")
                return path
        log.error("palera1n binary not found in any search path")
        return None

    def get_version(self) -> str:
        """Return palera1n version string."""
        binary = self.find_binary()
        if not binary:
            return "not found"
        try:
            result = subprocess.run(
                [binary, "--version"],
                capture_output=True, text=True, timeout=5
            )
            return result.stdout.strip() or result.stderr.strip() or "unknown"
        except OSError as e:
            if e.errno == 8:
                log.warning(f"palera1n binary is wrong architecture: {binary}")
                return "wrong arch"
            return f"error: {e}"
        except Exception as e:
            return f"error: {e}"

    def start(
        self,
        options: JailbreakOptions,
        on_line: Callable[[str], None],
        on_done: Callable[[int, str], None],
    ):
        """
        Start palera1n in a background thread.

        Args:
            options: JailbreakOptions instance
            on_line: called for each line of palera1n output
            on_done: called with (exit_code, message) when finished
        """
        if self.is_running:
            log.warning("palera1n already running")
            return

        binary = self.find_binary()
        if not binary:
            on_done(EXIT_NOT_FOUND, "palera1n binary not found.\nSee docs/INSTALL.md")
            return

        # Ensure executable bit
        if not os.access(binary, os.X_OK):
            try:
                os.chmod(binary, os.stat(binary).st_mode | stat.S_IEXEC)
            except Exception as e:
                on_done(EXIT_PERMISSION, f"Cannot execute palera1n: {e}")
                return

        self._cancelled = False
        args = [binary] + options.to_args()

        # Ensure palera1n runs as root
        if os.getuid() != 0:
            log.warning("Not root — prepending sudo to palera1n invocation")
            args = ["sudo", "-n"] + args

        log.info(f"Launching: {' '.join(args)}")

        self._thread = threading.Thread(
            target=self._run,
            args=(args, on_line, on_done),
            daemon=True,
        )
        self._thread.start()

    def cancel(self):
        """Send SIGTERM to palera1n process."""
        self._cancelled = True
        if self._proc and self._proc.poll() is None:
            log.info("Cancelling palera1n")
            try:
                self._proc.terminate()
                time.sleep(1)
                if self._proc.poll() is None:
                    self._proc.kill()
            except Exception as e:
                log.error(f"Cancel error: {e}")

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _run(
        self,
        args: List[str],
        on_line: Callable[[str], None],
        on_done: Callable[[int, str], None],
    ):
        try:
            self._proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            log.error(f"Failed to launch: {e}")
            on_done(EXIT_PERMISSION, str(e))
            return

        try:
            for raw in self._proc.stdout:
                raw = raw.rstrip()
                if raw:
                    log.info(f"[palera1n] {raw}")
                    cleaned = _clean_line(raw)
                    if cleaned:
                        log.info(f"[display] {cleaned}")
                        on_line(cleaned)
            self._proc.wait()
        except Exception as e:
            log.error(f"Process read error: {e}")

        code = self._proc.returncode if self._proc else -99
        if self._cancelled:
            on_done(EXIT_CANCELLED, "Cancelled by user")
        elif code == 0:
            on_done(EXIT_SUCCESS, "Jailbreak completed successfully!")
        else:
            on_done(code, f"palera1n exited with code {code}")


class InstallRunner:
    """
    Downloads and runs the official palera1n install script:
      sudo /bin/sh -c "$(curl -fsSL https://static.palera.in/scripts/install.sh)"
    Streams output line-by-line to the UI.
    """

    INSTALL_CMD = [
        "sudo", "/bin/sh", "-c",
        "curl -fsSL https://static.palera.in/scripts/install.sh | /bin/sh",
    ]

    def __init__(self):
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None
        self._cancelled = False

    @property
    def is_running(self) -> bool:
        return self._proc is not None and self._proc.poll() is None

    def start(
        self,
        on_line: Callable[[str], None],
        on_done: Callable[[int, str], None],
    ):
        if self.is_running:
            return
        self._cancelled = False
        log.info(f"Running install: {' '.join(self.INSTALL_CMD)}")
        self._thread = threading.Thread(
            target=self._run,
            args=(on_line, on_done),
            daemon=True,
        )
        self._thread.start()

    def cancel(self):
        self._cancelled = True
        if self._proc and self._proc.poll() is None:
            log.info("Cancelling install")
            try:
                self._proc.terminate()
                time.sleep(1)
                if self._proc.poll() is None:
                    self._proc.kill()
            except Exception as e:
                log.error(f"Cancel error: {e}")

    def _run(
        self,
        on_line: Callable[[str], None],
        on_done: Callable[[int, str], None],
    ):
        try:
            self._proc = subprocess.Popen(
                self.INSTALL_CMD,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            log.error(f"Failed to launch install: {e}")
            on_done(-1, str(e))
            return

        try:
            for raw in self._proc.stdout:
                raw = raw.rstrip()
                if raw:
                    log.info(f"[install] {raw}")
                    cleaned = _clean_line(raw)
                    if cleaned:
                        log.info(f"[display] {cleaned}")
                        on_line(cleaned)
            self._proc.wait()
        except Exception as e:
            log.error(f"Install read error: {e}")

        code = self._proc.returncode if self._proc else -99
        if self._cancelled:
            on_done(-1, "Cancelled by user")
        elif code == 0:
            link = self._link_binary(on_line)
            msg = f"+ palera1n installed successfully!"
            if link:
                msg += f"\n+ Linked: {link}"
            on_done(0, msg)
        else:
            on_done(code, f"! Install failed (exit code {code})")

    # Known locations the install script places the binary
    _INSTALL_LOCATIONS = [
        "/usr/local/bin/palera1n",
        "/usr/bin/palera1n",
    ]

    def _link_binary(self, on_line: Callable[[str], None]) -> str:
        """Symlink the installed palera1n binary into the project bin/ directory."""
        installed = next(
            (p for p in self._INSTALL_LOCATIONS if os.path.isfile(p)), None
        )
        if not installed:
            log.warning("Could not locate installed palera1n binary to symlink")
            on_line("~ Warning: could not find installed binary to symlink")
            return ""

        bin_dir = os.path.realpath(
            os.path.join(os.path.dirname(__file__), "../bin")
        )
        link_path = os.path.join(bin_dir, "palera1n")

        try:
            if os.path.lexists(link_path):
                os.remove(link_path)
            os.symlink(installed, link_path)
            log.info(f"Symlinked {link_path} → {installed}")
            on_line(f"+ Linked bin/palera1n → {installed}")
            return link_path
        except Exception as e:
            log.error(f"Failed to create symlink: {e}")
            on_line(f"! Symlink failed: {e}")
            return ""
