# Installing palera1n Binary

palera1n itself is **not included** in this repo. You must download it separately.

## Download

Go to the official palera1n releases page:

```
https://github.com/palera1n/palera1n/releases/latest
```

Download the **Linux ARM64** binary. It will be named something like:

```
palera1n-linux-arm64
```

## Install

```bash
# From the project root
mkdir -p bin

# Copy/move the downloaded binary
cp ~/Downloads/palera1n-linux-arm64 bin/palera1n

# Make it executable
chmod +x bin/palera1n

# Verify it runs
./bin/palera1n --version
```

## Notes

- The binary **must** be at `bin/palera1n` relative to the project root, or at `/usr/local/bin/palera1n`
- The setup script will also search `~/palera1n` and `/usr/bin/palera1n`
- Make sure you're downloading the **ARM64** build, not x86_64
- palera1n must be run as **root**. The systemd service handles this automatically

## Supported Devices

palera1n supports A8–A11 devices (checkm8 exploit):

| Device | Chip |
|---|---|
| iPhone 6s / 6s Plus | A9 |
| iPhone SE (1st gen) | A9 |
| iPhone 7 / 7 Plus | A10 |
| iPhone 8 / 8 Plus | A11 |
| iPhone X | A11 |
| iPad (5th, 6th, 7th gen) | A9/A10 |
