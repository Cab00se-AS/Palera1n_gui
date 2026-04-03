"""
sysinfo.py — Gathers Raspberry Pi system information for the info screen.
"""

import subprocess
import os
import logging

log = logging.getLogger("sysinfo")


def get_ip() -> str:
    try:
        result = subprocess.run(
            ["hostname", "-I"], capture_output=True, text=True, timeout=3
        )
        ips = result.stdout.strip().split()
        return ips[0] if ips else "N/A"
    except Exception:
        return "N/A"


def get_cpu_temp() -> str:
    paths = [
        "/sys/class/thermal/thermal_zone0/temp",
        "/sys/devices/virtual/thermal/thermal_zone0/temp",
    ]
    for path in paths:
        try:
            with open(path) as f:
                temp_mc = int(f.read().strip())
                return f"{temp_mc / 1000:.1f}°C"
        except Exception:
            pass
    try:
        result = subprocess.run(
            ["vcgencmd", "measure_temp"], capture_output=True, text=True, timeout=3
        )
        return result.stdout.strip().replace("temp=", "")
    except Exception:
        return "N/A"


def get_memory() -> str:
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        total = used = 0
        for line in lines:
            if line.startswith("MemTotal"):
                total = int(line.split()[1])
            elif line.startswith("MemAvailable"):
                avail = int(line.split()[1])
                used = total - avail
        if total:
            pct = (used / total) * 100
            return f"{used // 1024}M / {total // 1024}M ({pct:.0f}%)"
    except Exception:
        pass
    return "N/A"


def get_disk() -> str:
    try:
        result = subprocess.run(
            ["df", "-h", "/"], capture_output=True, text=True, timeout=3
        )
        lines = result.stdout.strip().splitlines()
        if len(lines) >= 2:
            parts = lines[1].split()
            return f"{parts[2]} / {parts[1]} ({parts[4]})"
    except Exception:
        pass
    return "N/A"


def get_uptime() -> str:
    try:
        with open("/proc/uptime") as f:
            seconds = float(f.read().split()[0])
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        return f"{h}h {m}m"
    except Exception:
        return "N/A"


def get_palera1n_version(binary_path: str = None) -> str:
    from jailbreak import JailbreakRunner
    try:
        runner = JailbreakRunner()
        v = runner.get_version()
        return v[:16] if v else "not found"
    except Exception:
        return "N/A"


def gather_all() -> dict:
    return {
        "ip":           get_ip(),
        "cpu_temp":     get_cpu_temp(),
        "memory":       get_memory(),
        "disk":         get_disk(),
        "uptime":       get_uptime(),
        "palera1n_ver": get_palera1n_version(),
    }
