"""One-off generator for the Shoe Xpress Android app icon (adaptive icon
foreground layers + legacy square/round PNGs). Not part of the app runtime -
run manually whenever the icon needs to change."""
import os

from PIL import Image, ImageDraw, ImageFont

RES = r"D:\Inventory manager\frontend\android\app\src\main\res"
BRAND_BG = (79, 70, 229)  # indigo-600, matches the web app's primary buttons
BRAND_FG = (255, 255, 255)

DENSITIES = {
    "mdpi": (48, 108),
    "hdpi": (72, 162),
    "xhdpi": (96, 216),
    "xxhdpi": (144, 324),
    "xxxhdpi": (192, 432),
}


def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        r"C:\Windows\Fonts\segoeuib.ttf",
        r"C:\Windows\Fonts\arialbd.ttf",
        r"C:\Windows\Fonts\arial.ttf",
    ]
    for path in candidates:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _draw_glyph(draw: ImageDraw.ImageDraw, cx: int, cy: int, size: int, color):
    font = _font(size)
    text = "SX"
    bbox = draw.textbbox((0, 0), text, font=font)
    w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
    draw.text((cx - w / 2 - bbox[0], cy - h / 2 - bbox[1]), text, font=font, fill=color)


def make_foreground(canvas_px: int) -> Image.Image:
    img = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # Adaptive icon safe zone is the center 66% of the canvas - keep the
    # glyph within that so it survives circle/squircle/rounded-square masks.
    glyph_size = int(canvas_px * 0.40)
    _draw_glyph(draw, canvas_px // 2, canvas_px // 2, glyph_size, BRAND_FG)
    return img


def make_legacy(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), BRAND_BG + (255,))
    draw = ImageDraw.Draw(img)
    _draw_glyph(draw, size // 2, size // 2, int(size * 0.5), BRAND_FG)
    return img


def make_round(size: int) -> Image.Image:
    img = make_legacy(size)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size, size), fill=255)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(img, (0, 0), mask)
    return out


def main():
    for density, (legacy_px, fg_px) in DENSITIES.items():
        d = os.path.join(RES, f"mipmap-{density}")
        make_foreground(fg_px).save(os.path.join(d, "ic_launcher_foreground.png"))
        make_legacy(legacy_px).save(os.path.join(d, "ic_launcher.png"))
        make_round(legacy_px).save(os.path.join(d, "ic_launcher_round.png"))
        print(f"wrote {density}: legacy {legacy_px}px, foreground {fg_px}px")

    # Play Store / adaptive icon background color source.
    bg_xml = os.path.join(RES, "values", "ic_launcher_background.xml")
    hex_color = "#%02X%02X%02X" % BRAND_BG
    with open(bg_xml, "w", encoding="utf-8") as f:
        f.write(
            '<?xml version="1.0" encoding="utf-8"?>\n<resources>\n'
            f'    <color name="ic_launcher_background">{hex_color}</color>\n'
            "</resources>\n"
        )
    print("updated adaptive icon background color to", hex_color)


if __name__ == "__main__":
    main()
