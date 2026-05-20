#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Reels Poster
# Creates animated text reels with music and posts to @_thethoughtswithin

import os
import csv
import glob
import json
import random
import base64
import time
import subprocess
import requests
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from io import StringIO, BytesIO

# ============================================================
# CONFIGURATION
# ============================================================
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "17841426948301170")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME", "")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY", "")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET", "")

SHEET_ID = "1Rh_LmGQ9khrYX-9vBh9SkK9ygS-j0LcjQig65TS7DLI"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"
MUSIC_FOLDER = "music"
REEL_HISTORY_FILE = "reel_history.json"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #hindiwriters #reels #poetryreels"

# Unsplash photo themes (same approach as post_promo.py)
PHOTO_THEMES = [
    "misty mountains sunrise",
    "rain window bokeh",
    "autumn forest path",
    "calm lake reflection",
    "tea candle notebook",
    "golden hour field",
    "old library books",
    "flower petals minimal",
    "night sky stars",
    "river stones zen",
    "foggy forest morning",
    "desert dunes sunset",
]

# Panel color options: (fill_rgba, title_color, text_color, divider_color, brand_color)
PANEL_THEMES = [
    ((255, 252, 245, 230), (60, 40, 20),   (40, 30, 15),  (160, 140, 110), (120, 100, 70)),   # warm cream
    ((245, 248, 255, 225), (20, 40, 80),   (25, 35, 70),  (100, 130, 180), (80, 110, 160)),    # cool blue-white
    ((245, 255, 248, 225), (20, 70, 40),   (20, 60, 35),  (100, 170, 120), (70, 140, 90)),     # sage green
    ((255, 248, 248, 225), (90, 25, 25),   (80, 20, 20),  (190, 120, 120), (160, 90, 90)),     # rose blush
    ((252, 252, 252, 235), (30, 30, 30),   (20, 20, 20),  (150, 150, 150), (110, 110, 110)),   # clean white
    ((255, 250, 235, 228), (80, 55, 10),   (70, 50, 10),  (180, 150, 80),  (140, 110, 50)),    # golden parchment
]


# ============================================================
# HISTORY TRACKING
# ============================================================
def load_reel_history():
    if os.path.exists(REEL_HISTORY_FILE):
        with open(REEL_HISTORY_FILE, "r") as f:
            return json.load(f)
    return []


def save_reel_history(history, new_item):
    history.append(new_item)
    history = history[-5:]
    with open(REEL_HISTORY_FILE, "w") as f:
        json.dump(history, f)


# ============================================================
# FETCH STANZAS
# ============================================================
def fetch_all_stanzas():
    print("Fetching stanzas from Google Sheet...")
    response = requests.get(SHEET_CSV_URL)
    response.encoding = "utf-8"
    if response.status_code != 200:
        raise Exception(f"Could not fetch sheet: {response.status_code}")
    reader = csv.DictReader(StringIO(response.text))
    all_stanzas = []
    for row in reader:
        title = row.get("poem_title", "").strip()
        if not title:
            continue
        for key, value in row.items():
            if key.startswith("stanza_") and value.strip():
                all_stanzas.append((title, value.strip()))
    print(f"Found {len(all_stanzas)} stanzas")
    return all_stanzas


def pick_random_stanza(all_stanzas):
    history = load_reel_history()
    available = [(t, s) for t, s in all_stanzas if s not in history]
    if not available:
        available = all_stanzas
    title, stanza = random.choice(available)
    save_reel_history(history, stanza)
    print(f"Selected from '{title}': {stanza[:60]}...")
    return title, stanza


# ============================================================
# FONT HELPERS
# ============================================================
def find_hindi_font(bold=False):
    try:
        result = subprocess.run(
            ["fc-list", ":lang=hi", "--format=%{file}\n"],
            capture_output=True, text=True
        )
        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        if bold:
            bold_paths = [p for p in paths if "Bold" in p and "Devanagari" in p and "Condensed" not in p]
            if bold_paths:
                return bold_paths[0]
        regular = [p for p in paths if "Regular" in p and "Devanagari" in p and "Condensed" not in p]
        if regular:
            return regular[0]
        if paths:
            return paths[0]
    except Exception as e:
        print(f"fc-list error: {e}")
    fallback = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf" if bold else "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    return fallback if os.path.exists(fallback) else None


def find_latin_font(bold=False):
    paths_bold = [
        "/usr/share/fonts/truetype/lato/Lato-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    paths_regular = [
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in (paths_bold if bold else paths_regular):
        if os.path.exists(p):
            return p
    return None


# ============================================================
# FETCH BACKGROUND PHOTO FROM UNSPLASH
# ============================================================
def fetch_background_photo():
    theme = random.choice(PHOTO_THEMES)
    print(f"Fetching Unsplash photo: '{theme}'")
    try:
        url = f"https://source.unsplash.com/1080x1920/?{theme.replace(' ', ',')}"
        response = requests.get(url, timeout=20, allow_redirects=True)
        if response.status_code == 200 and len(response.content) > 10000:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
            print(f"Background photo loaded ({img.size})")
            return img
    except Exception as e:
        print(f"Unsplash fetch failed: {e}")
    # Fallback: dark gradient
    print("Using fallback gradient background")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    pixels = img.load()
    top, bottom = (20, 20, 40), (50, 30, 80)
    for y in range(VIDEO_HEIGHT):
        t = y / VIDEO_HEIGHT
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        for x in range(VIDEO_WIDTH):
            pixels[x, y] = (r, g, b)
    return img


# ============================================================
# DRAW A SINGLE FRAME
# ============================================================
def draw_frame(lines_visible, all_lines, poem_title, show_brand,
               hindi_font_path, latin_font_path, bg_photo, panel_theme):

    # --- Background: slightly darkened + blurred photo ---
    img = bg_photo.copy()
    # Darken the photo a bit so the panel pops
    overlay = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    img = Image.blend(img, overlay, alpha=0.35)
    # Light blur so text on panel is crisp against a soft bg
    img = img.filter(ImageFilter.GaussianBlur(radius=3))

    draw = ImageDraw.Draw(img, "RGBA")

    panel_fill, title_color, text_color, divider_color, brand_color = panel_theme

    # --- Fonts ---
    font_poem   = ImageFont.truetype(hindi_font_path, 72) if hindi_font_path else ImageFont.load_default()
    font_title  = ImageFont.truetype(hindi_font_path, 50) if hindi_font_path else ImageFont.load_default()
    font_brand_h = ImageFont.truetype(hindi_font_path, 36) if hindi_font_path else ImageFont.load_default()
    font_brand_l = ImageFont.truetype(latin_font_path, 36) if latin_font_path else font_brand_h

    cx = VIDEO_WIDTH // 2

    # --- Measure content to size the panel ---
    SIDE_MARGIN = 80          # panel left/right margin from frame edge
    PANEL_INNER_PAD_X = 60   # text margin inside panel (each side)
    PANEL_INNER_PAD_TOP = 60
    PANEL_INNER_PAD_BOTTOM = 60
    LINE_SPACING = 30         # extra gap between stanza lines

    # Title height
    title_bbox = draw.textbbox((0, 0), poem_title, font=font_title)
    title_h = title_bbox[3] - title_bbox[1]

    # Each stanza line height
    sample_bbox = draw.textbbox((0, 0), "क", font=font_poem)
    line_h = sample_bbox[3] - sample_bbox[1]

    divider_gap = 30
    stanza_block_h = len(all_lines) * (line_h + LINE_SPACING) - LINE_SPACING

    brand_h = 0
    if show_brand:
        b_bbox = draw.textbbox((0, 0), "द Thoughts Within", font=font_brand_h)
        brand_h = b_bbox[3] - b_bbox[1] + divider_gap + 20

    total_content_h = (
        title_h + divider_gap +
        10 +                   # divider line height area
        divider_gap +
        stanza_block_h +
        (divider_gap + 10 + divider_gap + brand_h if show_brand else 0)
    )

    panel_w = VIDEO_WIDTH - 2 * SIDE_MARGIN
    panel_h = total_content_h + PANEL_INNER_PAD_TOP + PANEL_INNER_PAD_BOTTOM

    panel_x0 = SIDE_MARGIN
    panel_y0 = (VIDEO_HEIGHT - panel_h) // 2
    panel_x1 = panel_x0 + panel_w
    panel_y1 = panel_y0 + panel_h

    # --- Draw panel with rounded corners ---
    RADIUS = 28
    draw.rounded_rectangle(
        [(panel_x0, panel_y0), (panel_x1, panel_y1)],
        radius=RADIUS,
        fill=panel_fill
    )

    # Thin border on the panel for definition
    border_color = (*divider_color, 120)
    draw.rounded_rectangle(
        [(panel_x0, panel_y0), (panel_x1, panel_y1)],
        radius=RADIUS,
        outline=border_color,
        width=2
    )

    # --- Content layout (top-down inside panel) ---
    y = panel_y0 + PANEL_INNER_PAD_TOP

    # Poem title (centered)
    title_bbox = draw.textbbox((0, 0), poem_title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    draw.text(((VIDEO_WIDTH - title_w) // 2, y), poem_title,
              font=font_title, fill=(*title_color, 255))
    y += title_h + divider_gap

    # Decorative divider under title
    div_x0 = cx - 100
    div_x1 = cx + 100
    draw.line([(div_x0, y), (div_x1, y)], fill=(*divider_color, 180), width=2)
    draw.ellipse([(cx - 4, y - 4), (cx + 4, y + 4)], fill=(*divider_color, 220))
    y += divider_gap + 10

    # --- Stanza lines (only up to lines_visible) ---
    for i, line in enumerate(all_lines):
        if i >= lines_visible:
            break
        line_bbox = draw.textbbox((0, 0), line, font=font_poem)
        lw = line_bbox[2] - line_bbox[0]
        lx = (VIDEO_WIDTH - lw) // 2
        # Current (just-revealed) line slightly bolder looking via color
        is_current = (i == lines_visible - 1)
        color = (*text_color, 255) if is_current else (*text_color, 200)
        draw.text((lx, y), line, font=font_poem, fill=color)
        y += line_h + LINE_SPACING

    # --- Brand at bottom of panel ---
    if show_brand:
        y = panel_y1 - PANEL_INNER_PAD_BOTTOM - brand_h
        draw.line([(cx - 100, y), (cx + 100, y)], fill=(*divider_color, 150), width=1)
        draw.ellipse([(cx - 3, y - 3), (cx + 3, y + 3)], fill=(*divider_color, 180))
        y += divider_gap + 10

        hindi_part = "द "
        latin_part = "Thoughts Within"
        h_bbox = draw.textbbox((0, 0), hindi_part, font=font_brand_h)
        l_bbox = draw.textbbox((0, 0), latin_part, font=font_brand_l)
        total_brand_w = (h_bbox[2] - h_bbox[0]) + (l_bbox[2] - l_bbox[0])
        brand_x = (VIDEO_WIDTH - total_brand_w) // 2
        draw.text((brand_x, y), hindi_part, font=font_brand_h, fill=(*brand_color, 220))
        draw.text((brand_x + (h_bbox[2] - h_bbox[0]), y),
                  latin_part, font=font_brand_l, fill=(*brand_color, 220))

    return img


# ============================================================
# CREATE REEL VIDEO
# ============================================================
def create_reel_video(stanza_text, poem_title, music_path, output_path, tmpdir):
    print("Creating reel video...")

    hindi_font = find_hindi_font(bold=True)
    latin_font = find_latin_font(bold=False)
    bg_photo = fetch_background_photo()
    panel_theme = random.choice(PANEL_THEMES)

    lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]
    print(f"Animating {len(lines)} lines")

    HOLD_BEFORE = 1.5
    SECS_PER_LINE = 2.5
    HOLD_AFTER = 3.0
    BRAND_DURATION = 2.5

    frames_dir = os.path.join(tmpdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    frame_idx = 0

    def save_frames(img, count):
        nonlocal frame_idx
        for _ in range(count):
            img.save(os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg"),
                     "JPEG", quality=85)
            frame_idx += 1

    # Phase 1: Title only, no lines
    frame = draw_frame(0, lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme)
    save_frames(frame, int(HOLD_BEFORE * FPS))

    # Phase 2: Reveal lines one by one
    for i in range(1, len(lines) + 1):
        frame = draw_frame(i, lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme)
        save_frames(frame, int(SECS_PER_LINE * FPS))

    # Phase 3: Hold all lines
    frame = draw_frame(len(lines), lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme)
    save_frames(frame, int(HOLD_AFTER * FPS))

    # Phase 4: Show brand
    frame = draw_frame(len(lines), lines, poem_title, True, hindi_font, latin_font, bg_photo, panel_theme)
    save_frames(frame, int(BRAND_DURATION * FPS))

    total_duration = HOLD_BEFORE + (len(lines) * SECS_PER_LINE) + HOLD_AFTER + BRAND_DURATION
    print(f"Total duration: {total_duration:.1f}s | Frames: {frame_idx}")

    frames_pattern = os.path.join(frames_dir, "frame_%06d.jpg")

    if music_path and os.path.exists(music_path):
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", frames_pattern,
            "-i", music_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-t", str(total_duration),
            "-movflags", "+faststart",
            output_path
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", frames_pattern,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "-t", str(total_duration),
            "-movflags", "+faststart",
            output_path
        ]

    print("Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr[-1000:]}")
        raise Exception("FFmpeg failed to create video")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Video created: {size_mb:.1f} MB")
    return output_path


# ============================================================
# UPLOAD TO CLOUDINARY
# ============================================================
def upload_video_to_cloudinary(video_path):
    print("Uploading video to Cloudinary...")
    import hashlib
    import time as time_mod

    timestamp = str(int(time_mod.time()))
    public_id = f"thoughtswithin_reel_{timestamp}"

    params_to_sign = f"public_id={public_id}&timestamp={timestamp}"
    signature = hashlib.sha1(
        f"{params_to_sign}{CLOUDINARY_API_SECRET}".encode()
    ).hexdigest()

    url = f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/video/upload"

    with open(video_path, "rb") as f:
        response = requests.post(url, data={
            "api_key": CLOUDINARY_API_KEY,
            "timestamp": timestamp,
            "public_id": public_id,
            "signature": signature,
        }, files={"file": f}, timeout=180)

    result = response.json()
    if "secure_url" not in result:
        raise Exception(f"Cloudinary upload failed: {result}")

    video_url = result["secure_url"]
    print(f"Video URL: {video_url}")
    return video_url


# ============================================================
# POST REEL TO INSTAGRAM
# ============================================================
def post_reel_to_instagram(video_url, caption):
    print("Posting Reel to Instagram...")

    create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    response = requests.post(create_url, data={
        "media_type": "REELS",
        "video_url": video_url,
        "caption": caption,
        "share_to_feed": "true",
        "access_token": PAGE_ACCESS_TOKEN
    })
    result = response.json()

    if "id" not in result:
        raise Exception(f"Failed to create reel container: {result}")

    container_id = result["id"]
    print(f"Container created: {container_id}")
    print("Polling for Instagram video processing...")

    for attempt in range(18):
        time.sleep(10)
        status_url = (
            f"https://graph.facebook.com/v18.0/{container_id}"
            f"?fields=status_code,status&access_token={PAGE_ACCESS_TOKEN}"
        )
        status = requests.get(status_url).json()
        code = status.get("status_code", "")
        print(f"Attempt {attempt + 1}: {code}")
        if code == "FINISHED":
            break
        elif code == "ERROR":
            raise Exception(f"Instagram processing failed: {status}")

    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    response = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": PAGE_ACCESS_TOKEN
    })
    result = response.json()

    if "id" not in result:
        raise Exception(f"Failed to publish reel: {result}")

    print(f"Reel posted! ID: {result['id']}")
    return result["id"]


# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting The Thoughts Within Reel poster...\n")

    all_stanzas = fetch_all_stanzas()
    if not all_stanzas:
        raise Exception("No stanzas found in Google Sheet.")

    title, stanza = pick_random_stanza(all_stanzas)

    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    music_path = random.choice(music_files) if music_files else None
    if music_path:
        print(f"Music: {os.path.basename(music_path)}")

    caption = (
        f"𝘼 𝙫𝙚𝙧𝙨𝙚 𝙛𝙧𝙤𝙢 '{title}'\n\n"
        f"𝘙𝘦𝘢𝘥 𝘵𝘩𝘦 𝘧𝘶𝘭𝘭 𝘱𝘰𝘦𝘮 — 𝘭𝘪𝘯𝘬 𝘪𝘯 𝘣𝘪𝘰 🔗\n\n"
        f"{HASHTAGS}"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "reel.mp4")
        create_reel_video(stanza, title, music_path, video_path, tmpdir)
        video_url = upload_video_to_cloudinary(video_path)
        post_reel_to_instagram(video_url, caption)

    print("\nDone! Reel posted to @_thethoughtswithin")


if __name__ == "__main__":
    main()
