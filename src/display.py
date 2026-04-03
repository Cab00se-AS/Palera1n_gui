"""
display.py — Framebuffer/SPI renderer for Waveshare 1.3inch LCD HAT (ST7789, 240x240)

Renders PIL Image objects to the screen. Two backends are supported:
  - 'spidev'  : Direct SPI via spidev + RPi.GPIO (preferred on real hardware)
  - 'fb'      : Write raw RGB565 to /dev/fb0 (works with fbcp-ili9341 running)
  - 'mock'    : Headless/dev mode, saves frames to /tmp as PNG
"""

import os
import logging
import time
import struct
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger("display")

# --- Display dimensions ---
WIDTH = 240
HEIGHT = 240

# --- GPIO pins (BCM numbering) for SPI direct mode ---
PIN_RST = 27
PIN_DC = 25
PIN_BL = 24
SPI_BUS = 0
SPI_DEV = 0
SPI_SPEED = 40_000_000  # 40 MHz


class Display:
    """
    Abstracts screen output. Auto-detects backend based on environment.
    Usage:
        display = Display()
        img = Image.new('RGB', (240, 240), 'black')
        display.show(img)
    """

    def __init__(self, backend: str = "auto"):
        self.width = WIDTH
        self.height = HEIGHT
        self._backend = self._detect_backend(backend)
        self._init_backend()
        log.info(f"Display initialized [{self._backend}]")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show(self, img: Image.Image):
        """Push a 240x240 PIL Image to the screen."""
        if img.size != (WIDTH, HEIGHT):
            img = img.resize((WIDTH, HEIGHT), Image.LANCZOS)
        if img.mode != "RGB":
            img = img.convert("RGB")
        self._write_image(img)

    def clear(self, color=(0, 0, 0)):
        img = Image.new("RGB", (WIDTH, HEIGHT), color)
        self.show(img)

    def show_error(self, msg: str):
        img = Image.new("RGB", (WIDTH, HEIGHT), (180, 0, 0))
        draw = ImageDraw.Draw(img)
        font = self._get_font(14)
        draw.text((10, 90), "ERROR", font=self._get_font(22), fill="white")
        draw.text((10, 120), msg[:28], font=font, fill="white")
        if len(msg) > 28:
            draw.text((10, 140), msg[28:56], font=font, fill="white")
        self.show(img)

    def show_splash(self):
        img = Image.new("RGB", (WIDTH, HEIGHT), (10, 10, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle([0, 0, WIDTH, 4], fill=(80, 0, 200))
        draw.rectangle([0, HEIGHT - 4, WIDTH, HEIGHT], fill=(80, 0, 200))
        draw.text((30, 70), "palera1n-gui", font=self._get_font(24), fill=(180, 100, 255))
        draw.text((60, 102), "for RPi Zero 2W", font=self._get_font(14), fill=(150, 150, 200))
        draw.text((25, 130), "iPhone & iPad supported", font=self._get_font(12), fill=(100, 80, 160))
        draw.text((20, 160), "Waveshare 1.3\" HAT", font=self._get_font(13), fill=(100, 100, 150))
        draw.text((70, 200), "Loading...", font=self._get_font(14), fill=(120, 120, 120))
        self.show(img)

    # ------------------------------------------------------------------
    # Font helper
    # ------------------------------------------------------------------

    def _get_font(self, size: int = 16) -> ImageFont.FreeTypeFont:
        font_paths = [
            os.path.join(os.path.dirname(__file__), "../assets/font.ttf"),
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        for p in font_paths:
            if os.path.exists(p):
                try:
                    return ImageFont.truetype(p, size)
                except Exception:
                    pass
        return ImageFont.load_default()

    # ------------------------------------------------------------------
    # Backend detection & init
    # ------------------------------------------------------------------

    def _detect_backend(self, hint: str) -> str:
        if hint != "auto":
            return hint
        if os.path.exists("/dev/spidev0.0"):
            try:
                import spidev  # noqa
                import RPi.GPIO  # noqa
                return "spidev"
            except ImportError:
                pass
        if os.path.exists("/dev/fb1") or os.path.exists("/dev/fb0"):
            return "fb"
        return "mock"

    def _init_backend(self):
        if self._backend == "spidev":
            self._init_spi()
        elif self._backend == "fb":
            fb_dev = "/dev/fb1" if os.path.exists("/dev/fb1") else "/dev/fb0"
            self._fb_dev = fb_dev
            log.info(f"Framebuffer backend: {fb_dev}")
        else:
            log.warning("Mock display mode — frames saved to /tmp/palera1n_frame.png")

    def _init_spi(self):
        import spidev
        import RPi.GPIO as GPIO

        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(PIN_RST, GPIO.OUT)
        GPIO.setup(PIN_DC, GPIO.OUT)
        GPIO.setup(PIN_BL, GPIO.OUT)
        GPIO.output(PIN_BL, GPIO.HIGH)

        # Hardware reset
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.01)
        GPIO.output(PIN_RST, GPIO.LOW)
        time.sleep(0.01)
        GPIO.output(PIN_RST, GPIO.HIGH)
        time.sleep(0.05)

        self._gpio = GPIO
        self._spi = spidev.SpiDev()
        self._spi.open(SPI_BUS, SPI_DEV)
        self._spi.max_speed_hz = SPI_SPEED
        self._spi.mode = 0

        self._st7789_init()

    def _st7789_cmd(self, cmd: int):
        self._gpio.output(PIN_DC, self._gpio.LOW)
        self._spi.writebytes([cmd])

    def _st7789_data(self, data):
        self._gpio.output(PIN_DC, self._gpio.HIGH)
        if isinstance(data, int):
            data = [data]
        self._spi.writebytes(data)

    def _st7789_init(self):
        """ST7789 initialisation sequence for 240x240."""
        cmds = [
            (0x36, [0x70]),   # MADCTL — RGB order, 90° rotation
            (0x3A, [0x05]),   # COLMOD — RGB565
            (0xB2, [0x0C, 0x0C, 0x00, 0x33, 0x33]),
            (0xB7, [0x35]),
            (0xBB, [0x19]),
            (0xC0, [0x2C]),
            (0xC2, [0x01]),
            (0xC3, [0x12]),
            (0xC4, [0x20]),
            (0xC6, [0x0F]),
            (0xD0, [0xA4, 0xA1]),
            (0x11, None),     # SLPOUT
            (0x21, None),     # INVON — IPS panel requires inversion for correct colours
            (0x29, None),     # DISPON
        ]
        for cmd, data in cmds:
            self._st7789_cmd(cmd)
            if data:
                self._st7789_data(data)
            if cmd in (0x11, 0x29):
                time.sleep(0.12)

    def _set_window(self, x0, y0, x1, y1):
        self._st7789_cmd(0x2A)
        self._st7789_data([(x0 >> 8) & 0xFF, x0 & 0xFF, (x1 >> 8) & 0xFF, x1 & 0xFF])
        self._st7789_cmd(0x2B)
        self._st7789_data([(y0 >> 8) & 0xFF, y0 & 0xFF, (y1 >> 8) & 0xFF, y1 & 0xFF])
        self._st7789_cmd(0x2C)

    # ------------------------------------------------------------------
    # Write image to screen
    # ------------------------------------------------------------------

    def _write_image(self, img: Image.Image):
        if self._backend == "spidev":
            self._write_spi(img)
        elif self._backend == "fb":
            self._write_fb(img)
        else:
            img.save("/tmp/palera1n_frame.png")

    def _write_spi(self, img: Image.Image):
        self._set_window(0, 0, WIDTH - 1, HEIGHT - 1)
        # Convert to RGB565
        pixels = []
        for r, g, b in img.getdata():
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            pixels.append((rgb565 >> 8) & 0xFF)
            pixels.append(rgb565 & 0xFF)
        self._gpio.output(PIN_DC, self._gpio.HIGH)
        # Send in chunks to avoid SPI buffer overflow
        chunk = 4096
        for i in range(0, len(pixels), chunk):
            self._spi.writebytes(pixels[i:i + chunk])

    def _write_fb(self, img: Image.Image):
        try:
            with open(self._fb_dev, "wb") as f:
                for r, g, b in img.getdata():
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    f.write(struct.pack("H", rgb565))
        except Exception as e:
            log.error(f"Framebuffer write error: {e}")
