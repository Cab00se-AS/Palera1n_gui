"""
device.py — iPhone / Apple device detection over USB

Detects iPhones in normal, recovery, or DFU mode using lsusb.
Apple USB vendor ID: 0x05ac
"""

import subprocess
import logging
import time
from dataclasses import dataclass
from typing import Optional

log = logging.getLogger("device")

APPLE_VENDOR_ID = "05ac"

# Known Apple USB product IDs
DEVICE_MODES = {
    "1227": "DFU Mode",
    "1281": "Recovery Mode (iBSS)",
    "1286": "Recovery Mode (iBEC)",
    "12a8": "Normal Mode (iPhone)",
    "12aa": "Normal Mode (iPad)",
    "12ab": "Normal Mode (iPod/iPad)",
}

# Supported checkm8 devices (A8–A11)
SUPPORTED_CHIPS = {
    "iPhone8,1": "iPhone 6s",
    "iPhone8,2": "iPhone 6s Plus",
    "iPhone8,4": "iPhone SE (1st gen)",
    "iPhone9,1": "iPhone 7",
    "iPhone9,3": "iPhone 7",
    "iPhone9,2": "iPhone 7 Plus",
    "iPhone9,4": "iPhone 7 Plus",
    "iPhone10,1": "iPhone 8",
    "iPhone10,2": "iPhone 8 Plus",
    "iPhone10,3": "iPhone X",
    "iPhone10,4": "iPhone 8",
    "iPhone10,5": "iPhone 8 Plus",
    "iPhone10,6": "iPhone X",
    "iPad6,11": "iPad (5th gen)",
    "iPad6,12": "iPad (5th gen)",
    "iPad7,5": "iPad (6th gen)",
    "iPad7,6": "iPad (6th gen)",
    "iPad7,11": "iPad (7th gen)",
    "iPad7,12": "iPad (7th gen)",
}


@dataclass
class AppleDevice:
    vendor_id: str
    product_id: str
    mode: str
    name: str
    supported: bool


def detect_device() -> Optional[AppleDevice]:
    """
    Runs lsusb and returns an AppleDevice if an Apple USB device is found,
    or None if nothing is connected.
    """
    try:
        result = subprocess.run(
            ["lsusb"], capture_output=True, text=True, timeout=5
        )
        for line in result.stdout.splitlines():
            line_lower = line.lower()
            if APPLE_VENDOR_ID in line_lower:
                parts = line.split()
                try:
                    # Format: Bus XXX Device XXX: ID vendor:product description
                    id_field = next(p for p in parts if ":" in p and APPLE_VENDOR_ID in p.lower())
                    vid, pid = id_field.split(":")
                    pid = pid.lower()
                    mode = DEVICE_MODES.get(pid, "Apple Device")
                    supported = pid in ("1227", "1281", "1286")  # DFU/recovery
                    name = mode
                    log.info(f"Apple device detected: {vid}:{pid} — {mode}")
                    return AppleDevice(
                        vendor_id=vid,
                        product_id=pid,
                        mode=mode,
                        name=name,
                        supported=supported,
                    )
                except (StopIteration, ValueError):
                    pass
    except FileNotFoundError:
        log.warning("lsusb not found — install usbutils")
    except subprocess.TimeoutExpired:
        log.warning("lsusb timed out")
    except Exception as e:
        log.error(f"Device detection error: {e}")
    return None


def wait_for_device(timeout: float = 60.0, poll_interval: float = 1.0,
                    require_dfu: bool = True) -> Optional[AppleDevice]:
    """
    Blocks until an Apple device is detected or timeout expires.
    If require_dfu=True, only returns when device is in DFU/Recovery mode.
    """
    deadline = time.time() + timeout
    log.info(f"Waiting for device (timeout={timeout}s, require_dfu={require_dfu})")
    while time.time() < deadline:
        dev = detect_device()
        if dev:
            if not require_dfu or dev.supported:
                return dev
            log.info(f"Device found but not in DFU/recovery: {dev.mode}")
        time.sleep(poll_interval)
    log.warning("Device wait timed out")
    return None


def is_device_connected() -> bool:
    return detect_device() is not None
