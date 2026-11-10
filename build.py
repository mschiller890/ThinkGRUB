#!/usr/bin/env python3
"""Generate a minimal black-and-white GRUB theme."""

import os
import subprocess
import glob
import struct

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
FONT_TTF = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

WHITE = (255, 255, 255, 255)
BLACK = (0, 0, 0, 255)

BOX_W = 600
BOX_H = 244

# Logo above the box (SVG viewBox is 72x26 -> same aspect)
LOGO_W = 216
LOGO_H = 78
LOGO_GAP = 40  # space between logo bottom and box top

# --------------------------------------------------
# Helpers
# --------------------------------------------------

def run(cmd):
    subprocess.run(cmd, check=True)


def pf2_metrics(size):
    """Return {ASCE, DESC} for a generated pf2 - the exact ascent/descent
    GRUB will use when drawing that font (big-endian section values)."""
    d = open(os.path.join(HERE, f"DejaVuSans-{size}.pf2"), "rb").read()
    i, out = 0, {}
    while i + 8 <= len(d):
        name = d[i:i + 4]
        ln = struct.unpack(">I", d[i + 4:i + 8])[0]
        if ln > len(d):
            break
        if name in (b"ASCE", b"DESC"):
            out[name.decode()] = int.from_bytes(d[i + 8:i + 8 + ln], "big")
        i += 8 + ln
    return out


def nine_slice(img, prefix):
    w, h = img.size
    cw, ch = w // 3, h // 3

    tiles = {
        "nw": (0, 0, cw, ch),
        "n":  (cw, 0, 2*cw, ch),
        "ne": (2*cw, 0, w, ch),
        "w":  (0, ch, cw, 2*ch),
        "c":  (cw, ch, 2*cw, 2*ch),
        "e":  (2*cw, ch, w, 2*ch),
        "sw": (0, 2*ch, cw, h),
        "s":  (cw, 2*ch, 2*cw, h),
        "se": (2*cw, 2*ch, w, h),
    }

    for name, box in tiles.items():
        img.crop(box).save(
            os.path.join(HERE, f"{prefix}_{name}.png")
        )


# --------------------------------------------------
# 1. Fonts
# GRUB matches fonts by EXACT internal name ("Family Style Size"),
# so generate one pf2 per size the theme references.
# --------------------------------------------------

SIZES = [12, 14, 16]

for s in SIZES:
    run([
        "grub-mkfont",
        "-s", str(s),
        "-o", os.path.join(HERE, f"DejaVuSans-{s}.pf2"),
        FONT_TTF
    ])

# drop stale fonts from previous builds
for f in glob.glob(os.path.join(HERE, "*.pf2")):
    if not any(f.endswith(f"DejaVuSans-{s}.pf2") for s in SIZES):
        os.remove(f)

FONT = "DejaVu Sans Regular"

# --------------------------------------------------
# 2. Geometry
# --------------------------------------------------
# GRUB row pitch = item_height + item_spacing; the style box (highlight)
# is drawn BORDER + item_height + BORDER tall and never scaled. Keep the
# two equal so the selected block fills exactly one row and never
# overlaps its neighbour.
ITEM_H = 30
ITEM_SPACING = 4

# Labels are drawn with the baseline at `ascent` and are clipped to
# their bounds (gui_label.c), so height must be >= ascent + descent.
LABEL_H = sum(pf2_metrics(12).values())

# --------------------------------------------------
# 2. Main panel
# --------------------------------------------------

panel = Image.new("RGBA", (BOX_W, BOX_H), BLACK)
d = ImageDraw.Draw(panel)

# Sharp white border (no horizontal separator lines)
d.rectangle(
    (0, 0, BOX_W - 1, BOX_H - 1),
    outline=WHITE,
    width=1
)

panel.save(os.path.join(HERE, "panel.png"))

# --------------------------------------------------
# 2b. Logo above the box
# --------------------------------------------------
# Rendered from logo.svg with librsvg at 12x, then LANCZOS-downscaled to
# the exact on-screen size so GRUB blits it 1:1 (no runtime scaling).

HIRES = 12


def render_logo():
    # librsvg renders the vectors at the requested size, so there is no
    # upscaling blur - only a high-quality LANCZOS downsample afterwards.
    pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
        os.path.join(HERE, "logo.svg"),
        LOGO_W * HIRES, LOGO_H * HIRES, True
    )
    tmp = os.path.join(HERE, "logo_hires.png")
    pixbuf.savev(tmp, "png", [], [])
    Image.open(tmp).convert("RGBA").resize(
        (LOGO_W, LOGO_H), Image.LANCZOS
    ).save(os.path.join(HERE, "logo.png"))
    os.remove(tmp)


render_logo()

# --------------------------------------------------
# 3. Menu item boxes (9-slice styles)
# --------------------------------------------------
# GRUB draws a style box as: top_border + item_height + bottom_border,
# and corners are never scaled (widget-box.c). Rows have a 34px pitch
# (item_height 30 + item_spacing 4), so the vertical border must stay at
# 2px or the selected block overlaps the next item.
#
# Horizontal slice width is independent: GRUB indents item text by the
# box's left pad (sviewport.x = max_leftpad), so H_PAD is the gap
# between the highlight's left edge and the text.
#
# The normal item box gets identical geometry (black = invisible on the
# black panel) so GRUB gives both row types the same padding and the
# text does not shift when a row becomes selected.

BORDER = 2
H_PAD = 10


def box_style(fill, prefix):
    img = Image.new("RGBA", (H_PAD * 3, BORDER * 3), fill)
    nine_slice(img, prefix)


box_style(WHITE, "sel")
box_style(BLACK, "item")

# --------------------------------------------------
# 4. Terminal box
# --------------------------------------------------

terminal = Image.new("RGBA", (24, 24), BLACK)
td = ImageDraw.Draw(terminal)

td.rectangle(
    (0, 0, 23, 23),
    outline=WHITE,
    width=1
)

nine_slice(terminal, "terminal_box")

# --------------------------------------------------
# 5. Cleanup
# --------------------------------------------------

for pattern in (
    "box_*.png",
    "old_panel*.png",
):
    for f in glob.glob(os.path.join(HERE, pattern)):
        os.remove(f)

# --------------------------------------------------
# 6. GRUB theme
# --------------------------------------------------

theme = f"""# Minimal monochrome GRUB theme

desktop-color: "#000000"

terminal-box: "terminal_box_*.png"
terminal-font: "{FONT} 14"

# Header
+ label {{
    left = 50%-272
    top = 50%-106
    width = 544
    height = {LABEL_H}

    text = "boot menu"
    font = "{FONT} 12"
    color = "#aaaaaa"
    align = "left"
}}

# Boot entries
+ boot_menu {{
    left = 50%-282
    top = 50%-78
    width = 564
    height = 156

    item_font = "{FONT} 16"
    item_color = "#ffffff"

    selected_item_font = "{FONT} 16"
    selected_item_color = "#000000"

    # icon_width/item_icon_space default to 32/4 and GRUB reserves that
    # space even with no icons, pushing text ~46px right of the title.
    icon_width = 0
    item_icon_space = 0

    item_height = {ITEM_H}
    item_padding = 10
    item_spacing = {ITEM_SPACING}

    # Matching geometry on both styles keeps row padding identical;
    # the black item box is invisible on the black panel.
    item_pixmap_style = "item_*.png"
    selected_item_pixmap_style = "sel_*.png"

    scrollbar = false
}}

# Footer: keyboard instructions
+ label {{
    left = 50%-272
    top = 50%+88
    width = 300
    height = {LABEL_H}

    text = "UP/DN select     E edit     ENTER boot"
    font = "{FONT} 12"
    color = "#aaaaaa"
    align = "left"
}}

# Footer: countdown
+ label {{
    id = "__timeout__"
    left = 50%+50
    top = 50%+88
    width = 222
    height = {LABEL_H}

    text = "boot in %ds"
    font = "{FONT} 12"
    color = "#aaaaaa"
    align = "right"
}}

# Logo above the box. Components are absolutely positioned, so this
# does NOT push the panel down - the box stays exactly centered.
+ image {{
    left = 50%-{LOGO_W // 2}
    top = 50%-{BOX_H // 2 + LOGO_GAP + LOGO_H}
    width = {LOGO_W}
    height = {LOGO_H}
    file = "logo.png"
}}

# Main panel - MUST be the LAST component.
# GRUB's canvas prepends components and paints head-first, so the FIRST
# component in this file ends up on top of everything else. The opaque
# panel has to be added last to land at the bottom layer.
+ image {{
    left = 50%-300
    top = 50%-122
    width = {BOX_W}
    height = {BOX_H}
    file = "panel.png"
}}
"""

with open(os.path.join(HERE, "theme.txt"), "w") as f:
    f.write(theme)

# --------------------------------------------------
# 7. Preview
# --------------------------------------------------

W, H = 1280, 720

img = Image.new("RGB", (W, H), "black")
d = ImageDraw.Draw(img)

f_title = ImageFont.truetype(
    FONT_TTF, 12
)

f_menu = ImageFont.truetype(
    FONT_TTF, 16
)

f_footer = ImageFont.truetype(
    FONT_TTF, 12
)

# Exact metrics GRUB will use (read from the generated pf2 files)
asc12 = pf2_metrics(12)["ASCE"]
desc12 = pf2_metrics(12)["DESC"]
asc16 = pf2_metrics(16)["ASCE"]
desc16 = pf2_metrics(16)["DESC"]

bx = W // 2 - BOX_W // 2
by = H // 2 - BOX_H // 2

# Panel
d.rectangle(
    (bx, by, bx + BOX_W - 1, by + BOX_H - 1),
    outline="white",
    width=1
)

# Logo above the box
logo_img = Image.open(os.path.join(HERE, "logo.png")).convert("RGBA")
img.paste(
    logo_img,
    (bx + (BOX_W - LOGO_W) // 2, by - LOGO_GAP - LOGO_H),
    logo_img
)

# Header (GRUB: baseline at ascent from label top)
d.text(
    (bx + 28, by + 16 + asc12),
    "boot menu",
    font=f_title,
    fill="#aaaaaa",
    anchor="ls"
)

# Menu
items = [
    "Ubuntu",
    "Advanced options for Ubuntu",
    "Windows Boot Manager",
    "UEFI Firmware Settings",
]

selected_index = 0

my = by + 54               # menu top (by+44) + item_padding (10)
pitch = ITEM_H + ITEM_SPACING

for i, item in enumerate(items):
    y = my + i * pitch

    if i == selected_index:
        # GRUB: BORDER + item_height + BORDER == one full row pitch
        d.rectangle(
            (bx + 28, y, bx + BOX_W - 28, y + pitch),
            fill="white"
        )
        color = "black"
    else:
        color = "white"

    # GRUB: text indented by the box's left pad (H_PAD), centered in item_height
    baseline = y + BORDER + (ITEM_H - (asc16 + desc16)) // 2 + asc16
    d.text(
        (bx + 28 + H_PAD, baseline),
        item,
        font=f_menu,
        fill=color,
        anchor="ls"
    )

# Footer separator removed (no horizontal lines)
footer_y = by + 210

# Footer left
d.text(
    (bx + 28, footer_y + asc12),
    "UP/DN select     E edit     ENTER boot",
    font=f_footer,
    fill="#aaaaaa",
    anchor="ls"
)

# Footer right
footer_right = "boot in 3s"

tb = d.textbbox((0, 0), footer_right, font=f_footer)
tw = tb[2] - tb[0]

d.text(
    (bx + BOX_W - 28 - tw, footer_y + asc12),
    footer_right,
    font=f_footer,
    fill="#aaaaaa",
    anchor="ls"
)

# Save preview
preview = os.path.join(HERE, "preview.png")

img.save(preview)

print("Theme generated successfully.")
print("Theme directory:", HERE)
print("Preview:", os.path.abspath(preview))
