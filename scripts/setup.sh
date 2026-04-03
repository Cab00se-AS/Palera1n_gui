#!/usr/bin/env bash
# =============================================================================
# setup.sh — palera1n-gui setup script for Raspberry Pi Zero 2W
#
# Run as root:  sudo bash scripts/setup.sh
# =============================================================================

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
LOG="/var/log/palera1n-gui-setup.log"

info()  { echo -e "\e[32m[+]\e[0m $*" | tee -a "$LOG"; }
warn()  { echo -e "\e[33m[!]\e[0m $*" | tee -a "$LOG"; }
error() { echo -e "\e[31m[✗]\e[0m $*" | tee -a "$LOG"; exit 1; }

[[ $EUID -ne 0 ]] && error "Run as root: sudo bash scripts/setup.sh"

info "=== palera1n-gui setup starting ==="
info "Project root: $SCRIPT_DIR"

# -----------------------------------------------------------------------
# 1. System packages
# -----------------------------------------------------------------------
info "Updating package list..."
apt-get update -qq

info "Installing system dependencies..."
apt-get install -y \
    python3 python3-pip python3-pil \
    python3-rpi.gpio python3-spidev \
    usbutils \
    usbmuxd \
    libopenjp2-7 \
    libtiff-dev \
    fonts-dejavu-core \
    git \
    2>&1 | tee -a "$LOG"

# -----------------------------------------------------------------------
# 2. Python packages
# -----------------------------------------------------------------------
info "Installing Python packages..."
pip3 install --break-system-packages -r "$SCRIPT_DIR/requirements.txt" 2>&1 | tee -a "$LOG"

# -----------------------------------------------------------------------
# 3. Enable SPI interface
# -----------------------------------------------------------------------
info "Enabling SPI..."
if ! grep -q "^dtparam=spi=on" /boot/firmware/config.txt; then
    echo "dtparam=spi=on" >> /boot/firmware/config.txt
    info "SPI enabled in /boot/firmware/config.txt"
else
    info "SPI already enabled"
fi

# Add spi-dev to modules
if ! grep -q "^spi-dev" /etc/modules; then
    echo "spi-dev" >> /etc/modules
fi

# -----------------------------------------------------------------------
# 4. Enable USB OTG Host Mode
# -----------------------------------------------------------------------
info "Configuring USB OTG host mode..."

# dwc2 overlay
if ! grep -q "^dtoverlay=dwc2" /boot/firmware/config.txt; then
    echo "dtoverlay=dwc2,dr_mode=host" >> /boot/firmware/config.txt
    info "dwc2 overlay added to /boot/firmware/config.txt"
fi

# dwc2 module
if ! grep -q "^dwc2" /etc/modules; then
    echo "dwc2" >> /etc/modules
fi

# -----------------------------------------------------------------------
# 5. Display config (1.3inch LCD HAT 240x240)
# -----------------------------------------------------------------------
info "Configuring display..."
CONFIG_BLOCK="
# palera1n-gui: Waveshare 1.3inch LCD HAT
hdmi_force_hotplug=1
hdmi_cvt=240 240 60 1 0 0 0
hdmi_group=2
hdmi_mode=87
display_rotate=0
gpu_mem=16
"

if ! grep -q "palera1n-gui: Waveshare" /boot/firmware/config.txt; then
    echo "$CONFIG_BLOCK" >> /boot/firmware/config.txt
    info "Display config appended to /boot/firmware/config.txt"
fi

# -----------------------------------------------------------------------
# 6. palera1n binary
# -----------------------------------------------------------------------
BINDIR="$SCRIPT_DIR/bin"
mkdir -p "$BINDIR"

if [[ ! -f "$BINDIR/palera1n" ]]; then
    warn "palera1n binary not found at $BINDIR/palera1n"
    warn "Download the ARM64 Linux binary from https://github.com/palera1n/palera1n/releases"
    warn "and place it at: $BINDIR/palera1n"
    warn "Then run: sudo chmod +x $BINDIR/palera1n"
else
    chmod +x "$BINDIR/palera1n"
    info "palera1n binary found and marked executable"
fi

# -----------------------------------------------------------------------
# 7. Systemd service
# -----------------------------------------------------------------------
info "Installing systemd service..."
SERVICE_SRC="$SCRIPT_DIR/systemd/palera1n-gui.service"
SERVICE_DEST="/etc/systemd/system/palera1n-gui.service"

# Inject real path into service file
sed "s|/opt/palera1n-gui|$SCRIPT_DIR|g" "$SERVICE_SRC" > "$SERVICE_DEST"

systemctl daemon-reload
systemctl enable palera1n-gui.service
info "Service enabled (will start on next boot)"

# -----------------------------------------------------------------------
# 8. Log directory
# -----------------------------------------------------------------------
touch /var/log/palera1n-gui.log
chmod 644 /var/log/palera1n-gui.log

# -----------------------------------------------------------------------
# Done
# -----------------------------------------------------------------------
echo ""
info "=== Setup complete! ==="
echo ""
echo "  Next steps:"
echo "  1. Download palera1n ARM64 Linux binary:"
echo "     https://github.com/palera1n/palera1n/releases"
echo "     → place it at: $BINDIR/palera1n"
echo "     → sudo chmod +x $BINDIR/palera1n"
echo ""
echo "  2. Reboot:"
echo "     sudo reboot"
echo ""
echo "  3. The GUI will auto-start on boot."
echo "     To start manually: sudo systemctl start palera1n-gui"
echo "     To view logs:      sudo journalctl -u palera1n-gui -f"
echo ""
