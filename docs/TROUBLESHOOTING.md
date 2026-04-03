# Troubleshooting

## Display is blank / no output

1. Confirm SPI is enabled:
   ```bash
   ls /dev/spidev*
   # Should show /dev/spidev0.0
   ```
   If missing: `sudo raspi-config` → Interface Options → SPI → Enable

2. Check `/boot/config.txt` contains:
   ```
   dtparam=spi=on
   ```

3. Confirm the HAT is fully seated on the GPIO header (all 40 pins).

4. Check the display backend being used:
   ```bash
   sudo journalctl -u palera1n-gui | grep "Display initialized"
   ```

## "Exec format error" running palera1n

You downloaded the wrong binary architecture. Get the **ARM64** Linux binary, not x86_64.

```bash
file bin/palera1n
# Should say: ELF 64-bit LSB executable, ARM aarch64
```

## iPhone not detected

1. Check USB OTG is in host mode:
   ```bash
   grep dwc2 /boot/config.txt
   # Should show: dtoverlay=dwc2,dr_mode=host
   ```

2. Check lsusb works:
   ```bash
   sudo apt-get install usbutils
   lsusb
   ```

3. Make sure you're using the **OTG port** (center micro-USB) on the Pi Zero 2W, NOT the power port.

4. Try a different cable. USB OTG adapters can be finicky.

5. Put the device into DFU mode manually before connecting.

## GPIO buttons not responding

Check that `RPi.GPIO` is installed:
```bash
python3 -c "import RPi.GPIO; print('OK')"
```

If it fails:
```bash
sudo apt-get install python3-rpi.gpio
```

## Service won't start

View full logs:
```bash
sudo journalctl -u palera1n-gui -n 100 --no-pager
```

Run manually to see errors directly:
```bash
sudo python3 /opt/palera1n-gui/src/main.py
```

## palera1n crashes mid-jailbreak

- This is usually a USB timing issue. Try:
  - A powered USB hub between Pi and iPhone
  - A shorter/different cable
  - Ensure Pi has stable 5V power (not USB from a laptop)
- Check `/var/log/palera1n-gui.log` for the exact error line.

## Mock mode (running on a desktop for dev)

If `RPi.GPIO` is not installed, the app falls back to keyboard input:

| Key | Action |
|---|---|
| `w` | Joystick Up |
| `s` | Joystick Down |
| `a` | Left / Back |
| `d` | Right |
| `Enter` | Select |
| `1` | KEY1 |
| `2` | KEY2 |
| `3` | KEY3 |
| `q` | Quit |

Frames are saved to `/tmp/palera1n_frame.png` for visual debugging.
