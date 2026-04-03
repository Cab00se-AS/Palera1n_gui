# palera1n-gui

A standalone GUI for [palera1n](https://github.com/palera1n/palera1n) running on a **Raspberry Pi Zero 2W** with the **Waveshare 1.3inch LCD HAT** (240×240 IPS, joystick + 3 buttons). No keyboard, monitor, or SSH needed. Everything is controlled from the HAT.

```
┌─────────────────────────┐
│  palera1n-gui  Main Menu│
│─────────────────────────│
│  › Start Jailbreak      │
│    Options              │
│    System Info          │
│    Power                │
│─────────────────────────│
│ ↕ Navigate  ● Select    │
└─────────────────────────┘
```

---

## Hardware

| Component | Part |
|---|---|
| SBC | Raspberry Pi Zero 2W |
| Display HAT | Waveshare 1.3inch LCD HAT (ST7789, 240×240, SPI) |
| OS | Raspberry Pi OS Lite 64-bit |
| Connection | USB OTG (Micro-USB → iPhone) |

Full wiring and hardware details: [docs/HARDWARE.md](docs/HARDWARE.md)

---

## Quick Start

### 1. Flash the Pi

Use [Raspberry Pi Imager](https://www.raspberrypi.com/software/) to flash **Raspberry Pi OS Lite (64-bit)** to a microSD card. In the advanced settings:
- Enable SSH
- Set a username/password
- Configure WiFi for initial SSH access

### 2. Clone this repo onto the Pi

```bash
git clone https://github.com/YOUR_USERNAME/palera1n-gui.git /opt/palera1n-gui
cd /opt/palera1n-gui
```

### 3. Download palera1n binary

```bash
# Download from https://github.com/palera1n/palera1n/releases/latest
# Get the Linux ARM64 binary
wget -O bin/palera1n https://github.com/palera1n/palera1n/releases/latest/download/palera1n-linux-arm64
chmod +x bin/palera1n
```

See [docs/INSTALL_PALERA1N.md](docs/INSTALL_PALERA1N.md) for details.

### 4. Run setup

```bash
sudo bash scripts/setup.sh
```

This will:
- Install all system and Python dependencies
- Enable SPI in `/boot/config.txt`
- Configure USB OTG host mode
- Configure the display resolution
- Install and enable the systemd service

### 5. Reboot

```bash
sudo reboot
```

The GUI will auto-start on boot and appear on the LCD HAT.

---

## Controls

| Input | Action |
|---|---|
| Joystick ↑ / ↓ | Navigate menu |
| Joystick ● (click) | Select / Confirm |
| Joystick ← | Back |
| KEY1 | Skip / Context action |
| KEY2 | Cancel current operation |
| KEY3 | Back / Cancel / Exit |

---

## Features

- **Menu-driven UI** rendered at 15 fps on the 240×240 IPS display
- **Device detection**: polls USB and shows connection status
- **DFU mode guide**: step-by-step on-screen instructions
- **Live log streaming**: palera1n output scrolls on screen in real time
- **Progress bar**: heuristic progress tracking from palera1n log output
- **Options screen**: toggle rootless/rootful, safe mode, verbose, tweaks
- **System info**: IP, CPU temp, RAM, disk, uptime, palera1n version
- **Power menu**: reboot / shutdown from the device
- **Auto-start via systemd**: boots straight into the GUI
- **Mock mode**: runs on a desktop (keyboard-driven) for development

---

## Project Structure

```
palera1n-gui/
├── src/
│   ├── main.py          # Entry point
│   ├── app.py           # State machine / app logic
│   ├── display.py       # ST7789 display driver (SPI / FB / mock)
│   ├── input_handler.py # GPIO joystick + button handler
│   ├── ui.py            # All screen rendering (PIL/Pillow)
│   ├── jailbreak.py     # palera1n subprocess wrapper
│   ├── device.py        # iPhone USB detection
│   └── sysinfo.py       # System info gathering
├── bin/
│   └── palera1n         # ← place binary here (not in repo)
├── assets/
│   └── font.ttf         # Optional custom font (falls back to system fonts)
├── docs/
│   ├── HARDWARE.md      # Wiring, BOM, GPIO map
│   ├── INSTALL_PALERA1N.md
│   └── TROUBLESHOOTING.md
├── scripts/
│   └── setup.sh         # Full setup script
├── systemd/
│   └── palera1n-gui.service
├── requirements.txt
└── README.md
```

---

## Supported iOS Devices

palera1n uses the [checkm8](https://checkm8.info/) bootrom exploit (A8–A11):

| Device | Chip |
|---|---|
| iPhone 6s / 6s Plus / SE 1st gen | A9 |
| iPhone 7 / 7 Plus | A10 Fusion |
| iPhone 8 / 8 Plus / X | A11 Bionic |
| iPad 5th / 6th / 7th gen | A9 / A10 |

---

## Development / Testing on Desktop

Run without a Pi. The app falls back to mock display (frames saved as PNG) and keyboard input:

```bash
pip3 install Pillow
python3 src/main.py
```

Keys: `w/s` = up/down, `Enter` = select, `1/2/3` = KEY1/2/3, `q` = quit.

---

## Logs

```bash
# Systemd journal
sudo journalctl -u palera1n-gui -f

# Log file
tail -f /var/log/palera1n-gui.log
```

---

## License

MIT. See [LICENSE](LICENSE)

---

## Disclaimer

This project is a UI wrapper. It does not include or distribute the palera1n binary. Use responsibly and only on devices you own.
