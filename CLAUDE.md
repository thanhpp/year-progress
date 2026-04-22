# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the generator

```bash
python3 -m venv .venv             # one-time: create venv in project folder
source .venv/bin/activate         # activate venv
pip install -r requirements.txt   # one-time: installs Pillow
python generate.py                 # produces year_progress_<year>.mp4
```

FFmpeg must be available on PATH (`apt-get install ffmpeg` on Debian/Ubuntu).

## Architecture

The entire implementation lives in `generate.py` as a single script with no CLI arguments — it always operates on `date.today()`.

**Data flow:**

1. `get_year_info()` — derives `days_passed` and `days_in_year` from the local clock.
2. `build_day_grid(year)` — maps every day of the year to `(col, row)` in the GitHub commit-graph layout: columns = weeks (left→right), rows = days-of-week Mon–Sun (top→bottom). Jan 1's weekday determines the row offset of the first column.
3. `main()` computes `total_frames = clamp(days_passed, 90, 288)` — the video runs between 3.0 s and 9.6 s at 30 fps, auto-adjusted so the fill rate stays near 1 box/frame.
4. Frames are drawn one-by-one with `draw_frame()` and piped as raw RGB24 bytes directly into an `ffmpeg` subprocess, which encodes to H.264 MP4.

**Frame rendering (`draw_frame`):**

`days_to_show = round(days_passed × frame_num / (total_frames − 1))` — always an integer, 0 on frame 0, `days_passed` on the last frame. Every element (grid, percentage, day counter, progress bar) reflects this same value so they stay in sync.

**Output:** `year_progress_<year>.mp4`, 1080×1920 (9:16), H.264, `yuv420p`, `+faststart`.

## Key constants to adjust

| Constant                           | Location             | Effect                               |
| ---------------------------------- | -------------------- | ------------------------------------ |
| `MIN_SECONDS` / `MAX_SECONDS`      | top of `generate.py` | Video duration range                 |
| `CELL_FILLED`                      | top of `generate.py` | Box colour (GitHub green by default) |
| `PADDING_H` / `CELL_GAP`           | top of `generate.py` | Grid geometry                        |
| `grid_y = 650`                     | `main()`             | Vertical position of the commit grid |
| Font sizes passed to `load_font()` | `draw_frame()`       | Text sizes for each element          |
