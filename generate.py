#!/usr/bin/env python3
"""Year progress Instagram Reel generator — GitHub commit graph style."""

import math
import subprocess
import sys
from datetime import date, timedelta
from PIL import Image, ImageDraw, ImageFont

# ── Video constants ────────────────────────────────────────────────────────────
WIDTH        = 1080
HEIGHT       = 1920
FPS          = 30
DURATION     = 5
TOTAL_FRAMES = FPS * DURATION   # 150

# ── Colours (GitHub dark theme) ────────────────────────────────────────────────
BG_COLOR    = (13,  17,  23)
CELL_EMPTY  = (22,  27,  34)
CELL_FILLED = (57, 211,  83)
TEXT_COLOR  = (230, 237, 243)
MUTED_COLOR = (110, 118, 129)
BAR_BG      = (33,  38,  45)

# ── Grid geometry ──────────────────────────────────────────────────────────────
PADDING_H = 60
CELL_GAP  = 4

# ── Font candidates (tried in order; falls back to PIL default) ────────────────
FONT_PATHS = [
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
]


def load_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_PATHS:
        try:
            return ImageFont.truetype(path, size)
        except (IOError, OSError):
            continue
    return ImageFont.load_default()


def get_year_info():
    today       = date.today()
    year        = today.year
    jan1        = date(year, 1, 1)
    dec31       = date(year, 12, 31)
    days_in_year = (dec31 - jan1).days + 1
    days_passed  = (today - jan1).days + 1   # today counts
    percentage   = days_passed / days_in_year * 100
    return today, year, days_in_year, days_passed, percentage


def build_day_grid(year: int):
    """Return (grid, num_cols).
    grid = list of (col, row, day_num, date_obj) in week-column order.
    row 0 = Monday … row 6 = Sunday.
    """
    jan1         = date(year, 1, 1)
    dec31        = date(year, 12, 31)
    days_in_year = (dec31 - jan1).days + 1
    # weekday(): 0=Mon … 6=Sun → use as row offset for the first partial week
    start_offset = jan1.weekday()

    grid = []
    for i in range(days_in_year):
        pos = i + start_offset
        col = pos // 7
        row = pos % 7
        grid.append((col, row, i + 1, jan1 + timedelta(days=i)))

    num_cols = grid[-1][0] + 1
    return grid, num_cols


def get_month_label_x(year: int, grid, cell_size: int, grid_x: int) -> dict:
    """Return {month_number: x_pixel} for the first column each month starts."""
    first_col: dict[int, int] = {}
    for col, _row, _day_num, d in grid:
        if d.month not in first_col:
            first_col[d.month] = col
    return {m: grid_x + c * (cell_size + CELL_GAP) for m, c in first_col.items()}


def draw_centered_text(draw, text, font, y, color, x_center=WIDTH // 2):
    bbox = draw.textbbox((0, 0), text, font=font)
    w    = bbox[2] - bbox[0]
    draw.text((x_center - w // 2, y), text, font=font, fill=color)


def draw_frame(
    frame_num: int,
    today: date,
    year: int,
    days_in_year: int,
    days_passed: int,
    grid,
    num_cols: int,
    cell_size: int,
    grid_x: int,
    grid_y: int,
    month_xs: dict,
) -> Image.Image:
    days_to_show = round(days_passed * frame_num / (TOTAL_FRAMES - 1))
    current_pct  = days_to_show / days_in_year * 100

    img  = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    # ── "YEAR PROGRESS" label ──────────────────────────────────────────────────
    lbl_font = load_font(36)
    draw_centered_text(draw, "YEAR PROGRESS", lbl_font, 160, MUTED_COLOR)

    # ── Year number ────────────────────────────────────────────────────────────
    year_font = load_font(200)
    draw_centered_text(draw, str(year), year_font, 220, TEXT_COLOR)

    # ── Date string ────────────────────────────────────────────────────────────
    date_font = load_font(60)
    date_str  = today.strftime("%B %-d")
    draw_centered_text(draw, date_str, date_font, 480, MUTED_COLOR)

    # ── Month labels ───────────────────────────────────────────────────────────
    month_abbr = ["Jan","Feb","Mar","Apr","May","Jun",
                  "Jul","Aug","Sep","Oct","Nov","Dec"]
    mlbl_font  = load_font(22)
    for m, x in month_xs.items():
        draw.text((x, 618), month_abbr[m - 1], font=mlbl_font, fill=MUTED_COLOR)

    # ── Commit graph grid ──────────────────────────────────────────────────────
    corner_r = max(2, cell_size // 5)
    for col, row, day_num, _d in grid:
        x     = grid_x + col * (cell_size + CELL_GAP)
        y     = grid_y + row * (cell_size + CELL_GAP)
        color = CELL_FILLED if day_num <= days_to_show else CELL_EMPTY
        draw.rounded_rectangle(
            [x, y, x + cell_size, y + cell_size],
            radius=corner_r,
            fill=color,
        )

    # ── Day-of-week labels ─────────────────────────────────────────────────────
    dow_labels = ["M", "T", "W", "T", "F", "S", "S"]
    dlbl_font  = load_font(22)
    grid_h     = 7 * cell_size + 6 * CELL_GAP
    for i, lbl in enumerate(dow_labels):
        y = grid_y + i * (cell_size + CELL_GAP) + (cell_size - 22) // 2
        draw.text((grid_x - 28, y), lbl, font=dlbl_font, fill=MUTED_COLOR)

    # ── Animated percentage ────────────────────────────────────────────────────
    pct_font = load_font(210)
    pct_str  = f"{current_pct:.1f}%"
    draw_centered_text(draw, pct_str, pct_font, 960, CELL_FILLED)

    # ── "X of Y days" ─────────────────────────────────────────────────────────
    stat_font = load_font(55)
    stat_str  = f"{days_to_show} of {days_in_year} days"
    draw_centered_text(draw, stat_str, stat_font, 1240, TEXT_COLOR)

    # ── Progress bar ───────────────────────────────────────────────────────────
    bar_x      = PADDING_H
    bar_y      = 1370
    bar_w      = WIDTH - 2 * PADDING_H
    bar_h      = 28
    bar_radius = bar_h // 2
    fill_w     = max(bar_radius * 2, int(bar_w * days_to_show / days_in_year))

    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + bar_w, bar_y + bar_h],
        radius=bar_radius,
        fill=BAR_BG,
    )
    draw.rounded_rectangle(
        [bar_x, bar_y, bar_x + fill_w, bar_y + bar_h],
        radius=bar_radius,
        fill=CELL_FILLED,
    )

    # ── Hashtag caption ────────────────────────────────────────────────────────
    cap_font = load_font(34)
    draw_centered_text(draw, "#YearProgress", cap_font, 1470, MUTED_COLOR)

    return img


def main():
    today, year, days_in_year, days_passed, percentage = get_year_info()

    print(f"Generating year progress for {year}: "
          f"day {days_passed}/{days_in_year} ({percentage:.1f}%)")

    grid, num_cols = build_day_grid(year)

    # Cell size: fit all columns inside the available width
    available_w = WIDTH - 2 * PADDING_H
    cell_size   = (available_w - (num_cols - 1) * CELL_GAP) // num_cols
    grid_w      = num_cols * cell_size + (num_cols - 1) * CELL_GAP
    grid_h      = 7 * cell_size + 6 * CELL_GAP

    # Centre grid horizontally; place it at fixed vertical position
    grid_x = PADDING_H + (available_w - grid_w) // 2
    grid_y = 650   # top of the 7-row grid

    month_xs = get_month_label_x(year, grid, cell_size, grid_x)

    output = f"year_progress_{year}.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-s", f"{WIDTH}x{HEIGHT}",
        "-pix_fmt", "rgb24",
        "-r", str(FPS),
        "-i", "-",
        "-c:v", "libx264", "-preset", "fast",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output,
    ]

    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    try:
        for f in range(TOTAL_FRAMES):
            if f % 30 == 0:
                print(f"  frame {f}/{TOTAL_FRAMES} …")
            frame_img = draw_frame(
                f, today, year, days_in_year, days_passed,
                grid, num_cols, cell_size, grid_x, grid_y, month_xs,
            )
            proc.stdin.write(frame_img.tobytes())
    finally:
        proc.stdin.close()

    ret = proc.wait()
    if ret != 0:
        print(f"ffmpeg exited with code {ret}", file=sys.stderr)
        sys.exit(ret)

    print(f"Done → {output}  ({WIDTH}×{HEIGHT}, {FPS}fps, {DURATION}s)")


if __name__ == "__main__":
    main()
