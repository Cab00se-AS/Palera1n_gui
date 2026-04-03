"""
ui.py — Screen rendering helpers for palera1n-gui

All draw_* functions return a PIL Image (240x240) ready to pass to Display.show().
Test 2042
"""

import os
import time
from PIL import Image, ImageDraw, ImageFont
from typing import List, Optional, Tuple

WIDTH = 240
HEIGHT = 240

# --- Themes ---

_DARK_THEME = {
    "BG":         (5, 5, 15),          # deep black-blue
    "ACCENT":     (120, 40, 255),      # vivid purple
    "ACCENT2":    (70, 10, 200),       # deeper purple
    "TEXT":       (200, 210, 240),     # cool blue-white
    "DIM":        (80, 85, 120),       # muted blue-grey
    "SELECTED":   (100, 180, 255),     # bright blue
    "SUCCESS":    (0, 200, 80),        # green (success text only)
    "ERROR":      (220, 40, 40),       # red
    "WARNING":    (255, 165, 0),       # orange
    "EMPH":       (220, 225, 255),     # bright blue-white
    "HINT_BAR":   (12, 8, 32),         # near-black purple
    "SEL_BG":     (20, 15, 65),        # dark blue-purple
    "SUCCESS_BG": (10, 8, 35),         # dark purple (not green)
    "ERROR_BG":   (30, 5, 5),          # dark red
}

_LIGHT_THEME = {
    "BG":         (245, 245, 252),
    "ACCENT":     (100, 30, 210),
    "ACCENT2":    (70, 0, 175),
    "TEXT":       (20, 20, 40),
    "DIM":        (110, 110, 130),
    "SELECTED":   (140, 80, 0),
    "SUCCESS":    (0, 145, 55),
    "ERROR":      (185, 25, 25),
    "WARNING":    (170, 95, 0),
    "EMPH":       (10, 10, 30),
    "HINT_BAR":   (215, 208, 238),
    "SEL_BG":     (215, 200, 250),
    "SUCCESS_BG": (225, 248, 232),
    "ERROR_BG":   (252, 228, 228),
}

_theme = _DARK_THEME


def set_theme(light: bool):
    """Switch between dark (default) and light themes."""
    global _theme
    _theme = _LIGHT_THEME if light else _DARK_THEME


def _c(key: str) -> tuple:
    return _theme[key]


def _get_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    paths = [
        os.path.join(os.path.dirname(__file__), "../assets/font.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf" if bold else
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _base_image() -> Tuple[Image.Image, ImageDraw.Draw]:
    img = Image.new("RGB", (WIDTH, HEIGHT), _c("BG"))
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, 0, WIDTH, 3], fill=_c("ACCENT"))
    return img, draw


def _header(draw: ImageDraw.Draw, title: str):
    font = _get_font(14, bold=True)
    draw.text((10, 8), "palera1n-gui", font=_get_font(11), fill=_c("ACCENT"))
    draw.text((10, 22), title, font=font, fill=_c("TEXT"))
    draw.line([0, 40, WIDTH, 40], fill=_c("ACCENT2"), width=1)


def _hint_bar(draw: ImageDraw.Draw, text: str):
    draw.rectangle([0, HEIGHT - 18, WIDTH, HEIGHT], fill=_c("HINT_BAR"))
    draw.text((4, HEIGHT - 16), text, font=_get_font(9), fill=_c("DIM"))


def draw_menu(items: List[str], selected: int, title: str = "Main Menu") -> Image.Image:
    img, draw = _base_image()
    _header(draw, title)

    item_font = _get_font(16)
    arrow_font = _get_font(14)
    row_h = 30
    start_y = 50

    for i, item in enumerate(items):
        y = start_y + i * row_h
        if i == selected:
            draw.rectangle([4, y - 2, WIDTH - 4, y + row_h - 6], fill=_c("SEL_BG"), outline=_c("ACCENT"))
            draw.text((20, y + 3), "›", font=arrow_font, fill=_c("ACCENT"))
            draw.text((32, y + 3), item, font=item_font, fill=_c("SELECTED"))
        else:
            draw.text((32, y + 3), item, font=item_font, fill=_c("TEXT"))

    _hint_bar(draw, "↕ Navigate  ● Select  KEY3 Exit")
    return img


def draw_status(title: str, lines: List[str], color=None,
                progress: Optional[float] = None, hint: str = "") -> Image.Image:
    """General status/log screen."""
    if color is None:
        color = _c("TEXT")
    img, draw = _base_image()
    _header(draw, title)

    font = _get_font(13)
    y = 48
    max_lines = 7
    for line in lines[-max_lines:]:
        if line.startswith("!"):
            fc = _c("ERROR")
        elif line.startswith("+"):
            fc = _c("SELECTED")   # blue for informational/progress lines
        elif line.startswith("~"):
            fc = _c("WARNING")
        else:
            fc = color
        draw.text((8, y), line[:32], font=font, fill=fc)
        y += 18

    if progress is not None:
        bar_y = HEIGHT - 30
        bar_w = WIDTH - 20
        draw.rectangle([10, bar_y, 10 + bar_w, bar_y + 10], outline=_c("DIM"))
        fill_w = int(bar_w * max(0.0, min(1.0, progress)))
        if fill_w > 0:
            draw.rectangle([10, bar_y, 10 + fill_w, bar_y + 10], fill=_c("ACCENT"))
        pct = int(progress * 100)
        draw.text((WIDTH // 2 - 12, bar_y - 14), f"{pct}%", font=_get_font(11), fill=_c("DIM"))

    if hint:
        _hint_bar(draw, hint[:38])

    return img


def draw_dfu_instructions(step: int) -> Image.Image:
    img, draw = _base_image()
    _header(draw, "Enter DFU Mode")

    steps = [
        ("Step 1/3", "Hold  SIDE + VOL DOWN", "for 3 seconds"),
        ("Step 2/3", "Release SIDE button", "keep VOL DOWN held"),
        ("Step 3/3", "Keep VOL DOWN held", "for 3 more seconds"),
    ]

    s_title, s_line1, s_line2 = steps[min(step, 2)]
    draw.text((10, 50), s_title, font=_get_font(13), fill=_c("ACCENT"))
    draw.text((10, 72), s_line1, font=_get_font(16, bold=True), fill=_c("EMPH"))
    draw.text((10, 96), s_line2, font=_get_font(14), fill=_c("DIM"))

    for i in range(3):
        cx = 40 + i * 80
        color = _c("ACCENT") if i == step else _c("DIM")
        draw.ellipse([cx - 8, 130, cx + 8, 146], fill=color)

    _hint_bar(draw, "KEY1: Skip  KEY3: Cancel")
    return img


def draw_device_wait(detected: bool, device_name: str = "") -> Image.Image:
    img, draw = _base_image()
    _header(draw, "Device Detection")

    if detected:
        draw.text((WIDTH // 2 - 50, 70), "✓ Connected", font=_get_font(20, bold=True), fill=_c("SELECTED"))
        draw.text((10, 105), device_name[:30], font=_get_font(13), fill=_c("TEXT"))
        draw.text((10, 130), "Ready to jailbreak", font=_get_font(14), fill=_c("DIM"))
    else:
        dots = "." * ((int(time.time() * 2) % 4))
        draw.text((10, 70), f"Waiting for device{dots}", font=_get_font(14), fill=_c("WARNING"))
        draw.text((10, 96), "Connect iPhone / iPad via", font=_get_font(13), fill=_c("DIM"))
        draw.text((10, 112), "USB OTG cable", font=_get_font(13), fill=_c("DIM"))
        draw.text((10, 140), "Supports:", font=_get_font(12), fill=_c("DIM"))
        draw.text((10, 158), "A8–A11 (iPhone 6–X, iPad 5–7)", font=_get_font(12), fill=_c("TEXT"))

    _hint_bar(draw, "KEY3: Back to menu")
    return img


def draw_confirm(question: str, detail: str = "") -> Image.Image:
    img, draw = _base_image()
    _header(draw, "Confirm")
    draw.text((10, 55), question, font=_get_font(16, bold=True), fill=_c("EMPH"))
    if detail:
        draw.text((10, 82), detail[:32], font=_get_font(12), fill=_c("DIM"))
        if len(detail) > 32:
            draw.text((10, 98), detail[32:64], font=_get_font(12), fill=_c("DIM"))

    draw.rectangle([14, 150, 104, 180], fill=_c("ACCENT2"), outline=_c("ACCENT"))
    draw.text((32, 157), "YES (●)", font=_get_font(13, bold=True), fill=(255, 255, 255))
    draw.rectangle([134, 150, 224, 180], fill=(140, 0, 0), outline=_c("ERROR"))
    draw.text((150, 157), "NO (KEY3)", font=_get_font(13), fill=(255, 255, 255))
    return img


def draw_sysinfo(info: dict) -> Image.Image:
    img, draw = _base_image()
    _header(draw, "System Info")
    font = _get_font(13)
    items = [
        ("IP Address", info.get("ip", "N/A")),
        ("CPU Temp",   info.get("cpu_temp", "N/A")),
        ("Memory",     info.get("memory", "N/A")),
        ("Disk",       info.get("disk", "N/A")),
        ("Uptime",     info.get("uptime", "N/A")),
        ("palera1n",   info.get("palera1n_ver", "N/A")),
    ]
    y = 50
    for label, val in items:
        draw.text((8, y), f"{label}:", font=font, fill=_c("DIM"))
        draw.text((100, y), str(val)[:16], font=font, fill=_c("TEXT"))
        y += 20

    _hint_bar(draw, "KEY3: Back")
    return img


_CHECKM8_LOGO_PATH = os.path.join(os.path.dirname(__file__), "../assets/checkm8.png")
_checkm8_logo: Optional[Image.Image] = None


def _get_checkm8_logo(size: int) -> Optional[Image.Image]:
    global _checkm8_logo
    if _checkm8_logo is None:
        try:
            _checkm8_logo = Image.open(_CHECKM8_LOGO_PATH).convert("RGBA")
        except Exception:
            return None
    return _checkm8_logo.resize((size, size), Image.LANCZOS)


def draw_done(success: bool, msg: str = "") -> Image.Image:
    img, draw = _base_image()
    if success:
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=_c("SUCCESS_BG"))
        draw.rectangle([0, 0, WIDTH, 3], fill=_c("SUCCESS"))

        # checkm8 logo centred near top
        logo = _get_checkm8_logo(80)
        if logo:
            lx = (WIDTH - 80) // 2
            img.paste(logo, (lx, 18), logo)

        draw.text((28, 108), "✓ SUCCESS", font=_get_font(26, bold=True), fill=_c("SUCCESS"))
        draw.text((10, 148), "Jailbreak complete!", font=_get_font(15), fill=_c("TEXT"))
    else:
        draw.rectangle([0, 0, WIDTH, HEIGHT], fill=_c("ERROR_BG"))
        draw.rectangle([0, 0, WIDTH, 3], fill=_c("ERROR"))
        draw.text((40, 70), "✗ FAILED", font=_get_font(26, bold=True), fill=_c("ERROR"))
        draw.text((10, 115), "Check log for details", font=_get_font(14), fill=_c("DIM"))

    if msg:
        draw.text((10, 170), msg[:30], font=_get_font(12), fill=_c("DIM"))

    _hint_bar(draw, "● or KEY3: Return to menu")
    return img


def draw_options(options: dict, selected: int) -> Image.Image:
    """Options screen with toggles."""
    img, draw = _base_image()
    _header(draw, "Options")
    font = _get_font(14)

    rows = [
        ("Mode",         "rootless" if options.get("rootless") else "fakefs"),
        ("Safe Mode",    "ON" if options.get("safe_mode") else "OFF"),
        ("Debug Log",    "ON" if options.get("verbose") else "OFF"),
        ("Verbose Boot", "ON" if options.get("verbose_boot") else "OFF"),
        ("Dark Mode",    "ON" if options.get("dark_mode") else "OFF"),
        ("More Options", "›"),
        ("Back", ""),
    ]
    y = 48
    for i, (label, val) in enumerate(rows):
        is_sel = i == selected
        if is_sel:
            draw.rectangle([4, y - 1, WIDTH - 4, y + 20], fill=_c("SEL_BG"), outline=_c("ACCENT"))
        draw.text((12, y + 2), label, font=font, fill=_c("SELECTED") if is_sel else _c("TEXT"))
        if val:
            if val in ("ON", "rootless"):
                vc = _c("SELECTED")
            elif val in ("OFF", "fakefs"):
                vc = _c("DIM")
            elif val == "›":
                vc = _c("ACCENT")
            else:
                vc = _c("DIM")
            draw.text((160, y + 2), val, font=font, fill=vc)
        y += 25

    _hint_bar(draw, "↕ Select  ● Toggle  KEY3 Back")
    return img


_MORE_OPT_ROWS: List[Tuple[str, str]] = [
    ("demote",               "Demote"),
    ("dfuhelper",            "DFU Helper"),
    ("enter_recovery",       "Enter Recovery"),
    ("exit_recovery",        "Exit Recovery"),
    ("jbinit_log",           "jbinit Log"),
    ("pongo_shell",          "Pongo Shell"),
    ("pongo_full",           "Pongo Full"),
    ("reboot_device",        "Reboot Device"),
    ("telnetd",              "Telnetd"),
    ("setup_partial_fakefs", "Partial Fakefs"),
    ("setup_fakefs",         "Setup Fakefs"),
    ("clean_fakefs",         "Clean Fakefs"),
    ("force_revert",         "Force Revert"),
]
_MORE_OPT_MAX_VIS = 6


def draw_more_options(options: dict, selected: int) -> Image.Image:
    """Scrollable More Options screen with all remaining palera1n boolean flags."""
    img, draw = _base_image()
    _header(draw, "More Options")
    font = _get_font(13)

    rows = [(key, label, options.get(key)) for key, label in _MORE_OPT_ROWS]
    total = len(rows) + 1  # +1 for Back

    scroll = max(0, min(selected - 2, total - _MORE_OPT_MAX_VIS))

    y = 48
    for i in range(_MORE_OPT_MAX_VIS):
        idx = scroll + i
        if idx >= total:
            break
        is_back = idx == total - 1
        label = "Back" if is_back else rows[idx][1]
        val   = None   if is_back else rows[idx][2]
        is_sel = idx == selected

        if is_sel:
            draw.rectangle([4, y - 1, WIDTH - 8, y + 20], fill=_c("SEL_BG"), outline=_c("ACCENT"))
        draw.text((12, y + 2), label, font=font, fill=_c("SELECTED") if is_sel else _c("TEXT"))
        if val is not None:
            val_str = "ON" if val else "OFF"
            vc = _c("SELECTED") if val else _c("DIM")
            draw.text((178, y + 2), val_str, font=font, fill=vc)
        y += 26

    # Scroll bar
    bar_top, bar_bot = 48, HEIGHT - 20
    bar_h = bar_bot - bar_top
    thumb_h = max(8, bar_h * _MORE_OPT_MAX_VIS // total)
    thumb_y = bar_top + (bar_h - thumb_h) * scroll // max(1, total - _MORE_OPT_MAX_VIS)
    draw.rectangle([WIDTH - 5, bar_top, WIDTH - 3, bar_bot], fill=_c("DIM"))
    draw.rectangle([WIDTH - 5, thumb_y, WIDTH - 3, thumb_y + thumb_h], fill=_c("ACCENT"))

    _hint_bar(draw, "↕ Navigate  ● Toggle  KEY3 Back")
    return img
