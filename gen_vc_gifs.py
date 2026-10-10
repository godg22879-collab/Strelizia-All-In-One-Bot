"""
Generate 4 animated GIF music emojis for Discord VC status:
1. vc_note1.gif  - Cyan single note, pulsing glow
2. vc_note2.gif  - Purple double note, pulsing glow
3. vc_vinyl.gif  - Pink vinyl disc, spinning rings
4. vc_phones.gif - Gold headphones, pulsing glow
"""
import math, os
from PIL import Image, ImageDraw, ImageFilter
from pathlib import Path

OUT = Path(r"C:\Users\Administrator\.gemini\antigravity-ide\brain\920b6c02-b8fd-4736-b8dc-305dd36e05b7\vc_emojis")
OUT.mkdir(parents=True, exist_ok=True)

SIZE = 128
FRAMES = 16
DURATION = 60  # ms per frame

# ── helper: dark navy circle background ────────────────────────────────────────
def base_frame():
    img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([(0, 0), (SIZE - 1, SIZE - 1)], fill=(18, 22, 46, 255))
    return img, draw

# ── helper: draw a glow "bloom" by blurring a bright layer ─────────────────────
def add_glow(img, glow_img, radius=8):
    blurred = glow_img.filter(ImageFilter.GaussianBlur(radius))
    out = Image.alpha_composite(img, blurred)
    return out

# ── helper: single music note shape (♪) ────────────────────────────────────────
def draw_note(draw, cx, cy, scale=1.0, color=(0, 255, 220)):
    """Draw a simple ♪ note centred at (cx,cy)."""
    r, g, b = color
    s = scale
    # Stem
    stem_x = int(cx + 12 * s)
    draw.rectangle([stem_x, int(cy - 26*s), stem_x + int(6*s), int(cy + 4*s)], fill=(*color, 255))
    # Head (filled ellipse)
    hx, hy = cx - int(4*s), cy + int(4*s)
    draw.ellipse([hx - int(12*s), hy - int(8*s), hx + int(12*s), hy + int(8*s)], fill=(*color, 255))
    # Flag
    flag_pts = [
        (stem_x + int(6*s), int(cy - 26*s)),
        (stem_x + int(22*s), int(cy - 12*s)),
        (stem_x + int(6*s), int(cy - 8*s)),
    ]
    draw.polygon(flag_pts, fill=(*color, 255))

# ── helper: double music note shape (♫) ─────────────────────────────────────────
def draw_double_note(draw, cx, cy, scale=1.0, color=(180, 100, 255)):
    s = scale
    # Left note head
    lx, ly = cx - int(12*s), cy + int(6*s)
    draw.ellipse([lx - int(10*s), ly - int(7*s), lx + int(10*s), ly + int(7*s)], fill=(*color, 255))
    # Right note head
    rx, ry = cx + int(12*s), cy + int(4*s)
    draw.ellipse([rx - int(10*s), ry - int(7*s), rx + int(10*s), ry + int(7*s)], fill=(*color, 255))
    # Left stem
    draw.rectangle([lx + int(10*s), int(cy - 22*s), lx + int(14*s), ly], fill=(*color, 255))
    # Right stem
    draw.rectangle([rx + int(10*s), int(cy - 24*s), rx + int(14*s), ry], fill=(*color, 255))
    # Beam connecting them
    draw.polygon([
        (lx + int(10*s), int(cy - 22*s)),
        (rx + int(14*s), int(cy - 24*s)),
        (rx + int(14*s), int(cy - 16*s)),
        (lx + int(10*s), int(cy - 14*s)),
    ], fill=(*color, 255))

# ─────────────────────────────────────────────────────────────────────────────────
# 1. Cyan note — pulsing glow
# ─────────────────────────────────────────────────────────────────────────────────
def make_note1():
    frames = []
    for i in range(FRAMES):
        t = i / FRAMES
        glow_r = 10 + int(8 * math.sin(2 * math.pi * t))
        alpha_glow = 160 + int(80 * math.sin(2 * math.pi * t))
        base, draw = base_frame()

        # Glow layer
        glow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        draw_note(gd, SIZE//2 - 4, SIZE//2, scale=1.0, color=(0, 220, 210))
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(glow_r))
        # Tint glow
        r_ch, g_ch, b_ch, a_ch = glow_img.split()
        a_ch = a_ch.point(lambda x: min(255, int(x * alpha_glow / 200)))
        glow_img = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

        combined = Image.alpha_composite(base, glow_img)
        # Sharp layer on top
        sharp_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sharp_img)
        draw_note(sd, SIZE//2 - 4, SIZE//2, scale=1.0, color=(0, 255, 225))
        combined = Image.alpha_composite(combined, sharp_img)
        frames.append(combined.convert("RGBA"))

    # Save as GIF
    rgb_frames = [f.convert("RGB") for f in frames]
    rgb_frames[0].save(
        OUT / "vc_note1.gif",
        save_all=True, append_images=rgb_frames[1:],
        duration=DURATION, loop=0, optimize=False
    )
    print("OK: vc_note1.gif saved")

# ─────────────────────────────────────────────────────────────────────────────────
# 2. Purple double note — pulsing glow
# ─────────────────────────────────────────────────────────────────────────────────
def make_note2():
    frames = []
    for i in range(FRAMES):
        t = i / FRAMES
        glow_r = 10 + int(8 * math.sin(2 * math.pi * t))
        alpha_glow = 150 + int(90 * math.sin(2 * math.pi * t))
        base, draw = base_frame()

        glow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        draw_double_note(gd, SIZE//2 - 8, SIZE//2 - 4, scale=0.85, color=(160, 80, 255))
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(glow_r))
        r_ch, g_ch, b_ch, a_ch = glow_img.split()
        a_ch = a_ch.point(lambda x: min(255, int(x * alpha_glow / 200)))
        glow_img = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

        combined = Image.alpha_composite(base, glow_img)
        sharp_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sharp_img)
        draw_double_note(sd, SIZE//2 - 8, SIZE//2 - 4, scale=0.85, color=(195, 130, 255))
        combined = Image.alpha_composite(combined, sharp_img)
        frames.append(combined.convert("RGBA"))

    rgb_frames = [f.convert("RGB") for f in frames]
    rgb_frames[0].save(
        OUT / "vc_note2.gif",
        save_all=True, append_images=rgb_frames[1:],
        duration=DURATION, loop=0, optimize=False
    )
    print("OK: vc_note2.gif saved")

# ─────────────────────────────────────────────────────────────────────────────────
# 3. Pink vinyl — spinning rings
# ─────────────────────────────────────────────────────────────────────────────────
def make_vinyl():
    frames = []
    cx, cy = SIZE // 2, SIZE // 2
    for i in range(FRAMES):
        t = i / FRAMES
        angle_offset = 360 * t
        base, draw = base_frame()

        glow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        for ring in range(5, 50, 8):
            alpha = int(220 - ring * 2)
            pulse = int(12 * math.sin(2 * math.pi * t + ring * 0.3))
            gd.ellipse([cx - ring, cy - ring, cx + ring, cy + ring],
                       outline=(255, 40, 130, alpha), width=2)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(4))
        combined = Image.alpha_composite(base, glow_img)

        sharp_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sharp_img)
        for ring in range(6, 50, 9):
            sd.ellipse([cx - ring, cy - ring, cx + ring, cy + ring],
                       outline=(255, 60, 160, 255), width=2)
        sd.ellipse([cx - 6, cy - 6, cx + 6, cy + 6], fill=(255, 100, 180, 255))
        sd.ellipse([cx - 2, cy - 2, cx + 2, cy + 2], fill=(18, 22, 46, 255))

        spark_angle = math.radians(angle_offset)
        sx = int(cx + 40 * math.cos(spark_angle))
        sy = int(cy + 40 * math.sin(spark_angle))
        sd.ellipse([sx - 4, sy - 4, sx + 4, sy + 4], fill=(255, 255, 255, 200))

        combined = Image.alpha_composite(combined, sharp_img)
        frames.append(combined.convert("RGBA"))

    rgb_frames = [f.convert("RGB") for f in frames]
    rgb_frames[0].save(
        OUT / "vc_vinyl.gif",
        save_all=True, append_images=rgb_frames[1:],
        duration=DURATION, loop=0, optimize=False
    )
    print("OK: vc_vinyl.gif saved")

# ─────────────────────────────────────────────────────────────────────────────────
# 4. Gold headphones — pulsing glow
# ─────────────────────────────────────────────────────────────────────────────────
def make_phones():
    frames = []
    for i in range(FRAMES):
        t = i / FRAMES
        glow_r = 10 + int(8 * math.sin(2 * math.pi * t))
        alpha_glow = 140 + int(100 * math.sin(2 * math.pi * t))
        base, _ = base_frame()
        cx, cy = SIZE // 2, SIZE // 2

        def draw_phones(d, color, lw=4):
            d.arc([cx - 38, cy - 44, cx + 38, cy + 10], start=180, end=0,
                  fill=(*color, 255), width=lw)
            d.rectangle([cx - 46, cy - 10, cx - 30, cy + 22], fill=(*color, 255))
            d.ellipse([cx - 46, cy + 10, cx - 30, cy + 30], fill=(*color, 255))
            d.rectangle([cx + 30, cy - 10, cx + 46, cy + 22], fill=(*color, 255))
            d.ellipse([cx + 30, cy + 10, cx + 46, cy + 30], fill=(*color, 255))

        glow_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        gd = ImageDraw.Draw(glow_img)
        draw_phones(gd, (200, 150, 0), lw=6)
        glow_img = glow_img.filter(ImageFilter.GaussianBlur(glow_r))
        r_ch, g_ch, b_ch, a_ch = glow_img.split()
        a_ch = a_ch.point(lambda x: min(255, int(x * alpha_glow / 200)))
        glow_img = Image.merge("RGBA", (r_ch, g_ch, b_ch, a_ch))

        combined = Image.alpha_composite(base, glow_img)
        sharp_img = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
        sd = ImageDraw.Draw(sharp_img)
        draw_phones(sd, (255, 200, 40), lw=4)
        combined = Image.alpha_composite(combined, sharp_img)
        frames.append(combined.convert("RGBA"))

    rgb_frames = [f.convert("RGB") for f in frames]
    rgb_frames[0].save(
        OUT / "vc_phones.gif",
        save_all=True, append_images=rgb_frames[1:],
        duration=DURATION, loop=0, optimize=False
    )
    print("OK: vc_phones.gif saved")

if __name__ == "__main__":
    make_note1()
    make_note2()
    make_vinyl()
    make_phones()
    print("All GIFs saved to:", OUT)
