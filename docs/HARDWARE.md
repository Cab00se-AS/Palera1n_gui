# Hardware Setup: Waveshare 1.3inch LCD HAT

## Bill of Materials

| Item | Notes |
|---|---|
| Raspberry Pi Zero 2W | Must be Zero **2** W (ARM Cortex-A53, 64-bit) |
| Waveshare 1.3inch LCD HAT | ST7789, 240×240, SPI, 1x joystick + 3x buttons |
| MicroSD card | 8GB+ recommended, Class 10 |
| USB OTG cable | Micro-USB (Pi) → USB-A female |
| USB-A to Lightning/USB-C cable | To connect iPhone |
| 5V 2.5A micro-USB power supply | For Pi |

## HAT GPIO Pin Map

The Waveshare 1.3inch LCD HAT plugs directly onto the 40-pin GPIO header.

### Display (SPI)

| Signal | GPIO (BCM) | Physical Pin |
|---|---|---|
| SPI MOSI (SDA) | GPIO 10 | Pin 19 |
| SPI CLK (SCL) | GPIO 11 | Pin 23 |
| SPI CS | GPIO 8 (CE0) | Pin 24 |
| DC (Data/Cmd) | GPIO 25 | Pin 22 |
| RST (Reset) | GPIO 27 | Pin 13 |
| BL (Backlight) | GPIO 24 | Pin 18 |

### Joystick

| Direction | GPIO (BCM) | Physical Pin |
|---|---|---|
| Up | GPIO 6 | Pin 31 |
| Down | GPIO 19 | Pin 35 |
| Left | GPIO 5 | Pin 29 |
| Right | GPIO 26 | Pin 37 |
| Press (center) | GPIO 13 | Pin 33 |

### Buttons

| Button | GPIO (BCM) | Physical Pin | Role in palera1n-gui |
|---|---|---|---|
| KEY1 | GPIO 21 | Pin 40 | Skip / Context action |
| KEY2 | GPIO 20 | Pin 38 | Cancel operation |
| KEY3 | GPIO 16 | Pin 36 | Back / Exit |

All buttons are **active LOW** (pulled up internally). A press connects the pin to GND.

## USB OTG Host Mode

The Pi Zero 2W has a single Micro-USB port (the one closer to the center). This is a USB OTG port.

To use it as a **USB host** (to plug in iPhone):
1. The `setup.sh` script adds `dtoverlay=dwc2,dr_mode=host` to `/boot/config.txt`
2. Connect your iPhone via: **OTG adapter → USB-A female → iPhone cable**

```
[Pi Zero 2W micro-USB]──[OTG adapter]──[USB-A cable]──[iPhone]
```

> ⚠️ This means the Pi must be powered via the **PWR** micro-USB port (the one on the edge), not the OTG port.

## OS Image

Use **Raspberry Pi OS Lite (64-bit)**. No desktop needed.

Download: https://www.raspberrypi.com/software/operating-systems/

Flash with Raspberry Pi Imager. In the imager's advanced settings:
- Enable SSH
- Set hostname: `palera1n`
- Set username/password
- Configure WiFi (for initial setup via SSH)
