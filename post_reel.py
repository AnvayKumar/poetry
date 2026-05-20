#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Reels Poster
# Creates animated text reels with music and posts to @_thethoughtswithin

import os
import csv
import glob
import json
import random
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
UNSPLASH_ACCESS_KEY = os.environ.get("UNSPLASH_ACCESS_KEY", "")

SHEET_ID = "1Rh_LmGQ9khrYX-9vBh9SkK9ygS-j0LcjQig65TS7DLI"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
MEANINGS_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1"
MUSIC_FOLDER = "music"
REEL_HISTORY_FILE = "reel_history.json"

VIDEO_WIDTH = 1080
VIDEO_HEIGHT = 1920
FPS = 30

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #hindiwriters #reels #poetryreels"

PHOTO_QUERIES = [
    "misty mountains fog",
    "rain window drops",
    "autumn forest leaves",
    "calm lake reflection",
    "golden hour field",
    "old books candle",
    "flower petals morning",
    "foggy forest path",
    "desert dunes sunset",
    "river stones peaceful",
    "cherry blossom pink",
    "winter snow trees",
]

# Panel themes: (fill_rgba, title_color, stanza_color, divider_color, brand_color)
PANEL_THEMES = [
    ((255, 252, 245, 235), (120, 60,  20),  (60,  35, 10),  (180, 140, 100), (140, 100, 60)),   # warm cream
    ((245, 248, 255, 230), (30,  55, 110),  (20,  40, 80),  (110, 140, 190), (80,  110, 160)),   # cool blue
    ((245, 255, 248, 230), (25,  80,  45),  (18,  60, 35),  (100, 170, 120), (70,  140, 90)),    # sage green
    ((255, 248, 248, 230), (110, 25,  25),  (80,  18, 18),  (200, 120, 120), (160, 80,  80)),    # rose blush
    ((252, 252, 252, 235), (50,  50,  50),  (25,  25, 25),  (160, 160, 160), (110, 110, 110)),   # clean white
    ((255, 250, 235, 232), (100, 65,  10),  (70,  45, 8),   (190, 155, 80),  (150, 110, 45)),    # golden parchment
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
# FETCH STANZAS + MEANINGS
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
                stanza_num = key.replace("stanza_", "")
                all_stanzas.append((title, stanza_num, value.strip()))
    print(f"Found {len(all_stanzas)} stanzas")
    return all_stanzas


def fetch_meanings():
    print("Fetching meanings from Google Sheet...")
    # Try gid=1 first, then fall back to sheet name param
    for url in [MEANINGS_CSV_URL, f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=meanings"]:
        try:
            response = requests.get(url)
            response.encoding = "utf-8"
            if response.status_code != 200:
                continue
            reader = csv.DictReader(StringIO(response.text))
            meanings = {}
            for row in reader:
                title = row.get("poem_title", "").strip()
                num = str(row.get("stanza_number", "")).strip()
                meaning = row.get("meaning", "").strip()
                if title and num and meaning:
                    meanings[(title, num)] = meaning
            if meanings:
                print(f"Found {len(meanings)} meanings")
                return meanings
        except Exception as e:
            print(f"Meanings fetch attempt failed: {e}")
    print("No meanings found, captions will omit meaning")
    return {}


def pick_random_stanza(all_stanzas):
    history = load_reel_history()
    available = [(t, n, s) for t, n, s in all_stanzas if s not in history]
    if not available:
        available = all_stanzas
    title, stanza_num, stanza = random.choice(available)
    save_reel_history(history, stanza)
    print(f"Selected stanza {stanza_num} from '{title}': {stanza[:60]}...")
    return title, stanza_num, stanza


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


def find_latin_font():
    for p in [
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(p):
            return p
    return None


# ============================================================
# FETCH BACKGROUND PHOTO FROM UNSPLASH API
# ============================================================
def fetch_background_photo():
    query = random.choice(PHOTO_QUERIES)
    print(f"Fetching Unsplash photo: '{query}'")

    # Method 1: Unsplash API with key
    if UNSPLASH_ACCESS_KEY:
        try:
            api_url = (
                f"https://api.unsplash.com/photos/random"
                f"?query={requests.utils.quote(query)}"
                f"&orientation=portrait&content_filter=high"
            )
            headers = {"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"}
            resp = requests.get(api_url, headers=headers, timeout=15)
            if resp.status_code == 200:
                data = resp.json()
                photo_url = data["urls"].get("regular") or data["urls"].get("full")
                img_resp = requests.get(photo_url, timeout=20)
                if img_resp.status_code == 200:
                    img = Image.open(BytesIO(img_resp.content)).convert("RGB")
                    img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
                    print(f"Photo loaded via Unsplash API ({query})")
                    return img
        except Exception as e:
            print(f"Unsplash API error: {e}")

    # Method 2: Picsum (reliable fallback, beautiful nature photos)
    try:
        seed = random.randint(1, 500)
        url = f"https://picsum.photos/seed/{seed}/1080/1920"
        resp = requests.get(url, timeout=20, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
            print(f"Photo loaded via Picsum (seed {seed})")
            return img
    except Exception as e:
        print(f"Picsum error: {e}")

    # Method 3: Plain gradient fallback
    print("Using gradient fallback")
    img = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT))
    pixels = img.load()
    top, bottom = (28, 18, 45), (65, 38, 90)
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

    # Background: darken + blur so the panel pops
    img = bg_photo.copy()
    dark_overlay = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    img = Image.blend(img, dark_overlay, alpha=0.40)
    img = img.filter(ImageFilter.GaussianBlur(radius=4))

    draw = ImageDraw.Draw(img, "RGBA")
    panel_fill, title_color, stanza_color, divider_color, brand_color = panel_theme

    # --- Fonts (smaller, more breathable) ---
    font_stanza = ImageFont.truetype(hindi_font_path, 54) if hindi_font_path else ImageFont.load_default()
    font_title  = ImageFont.truetype(hindi_font_path, 46) if hindi_font_path else ImageFont.load_default()
    font_brand  = ImageFont.truetype(latin_font_path, 32) if latin_font_path else font_title
    font_brand_h = ImageFont.truetype(hindi_font_path, 32) if hindi_font_path else font_title

    cx = VIDEO_WIDTH // 2
    SIDE_MARGIN      = 90    # panel edges from frame
    PAD_X            = 60    # text padding inside panel (each side)
    PAD_TOP          = 70
    PAD_BOTTOM       = 70
    LINE_GAP         = 22    # extra breathing room between stanza lines

    # --- Measure heights ---
    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    title_bbox = dummy.textbbox((0, 0), poem_title, font=font_title)
    title_h = title_bbox[3] - title_bbox[1]

    sample_bbox = dummy.textbbox((0, 0), "क", font=font_stanza)
    line_h = sample_bbox[3] - sample_bbox[1]

    divider_area = 48   # space for divider line + gap above/below
    stanza_block_h = len(all_lines) * line_h + (len(all_lines) - 1) * LINE_GAP

    brand_block_h = 0
    if show_brand:
        b_bbox = dummy.textbbox((0, 0), "Thoughts Within", font=font_brand)
        brand_block_h = divider_area + (b_bbox[3] - b_bbox[1]) + 10

    total_content_h = title_h + divider_area + stanza_block_h + brand_block_h
    panel_w = VIDEO_WIDTH - 2 * SIDE_MARGIN
    panel_h = total_content_h + PAD_TOP + PAD_BOTTOM

    panel_x0 = SIDE_MARGIN
    panel_y0 = (VIDEO_HEIGHT - panel_h) // 2
    panel_x1 = panel_x0 + panel_w
    panel_y1 = panel_y0 + panel_h

    # --- Panel rectangle ---
    draw.rounded_rectangle(
        [(panel_x0, panel_y0), (panel_x1, panel_y1)],
        radius=32,
        fill=panel_fill
    )
    draw.rounded_rectangle(
        [(panel_x0, panel_y0), (panel_x1, panel_y1)],
        radius=32,
        outline=(*divider_color, 100),
        width=2
    )

    # --- Title ---
    y = panel_y0 + PAD_TOP
    tb = draw.textbbox((0, 0), poem_title, font=font_title)
    draw.text(((VIDEO_WIDTH - (tb[2] - tb[0])) // 2, y),
              poem_title, font=font_title, fill=(*title_color, 255))
    y += title_h

    # --- Divider ---
    y += 18
    draw.line([(cx - 90, y), (cx + 90, y)], fill=(*divider_color, 160), width=1)
    draw.ellipse([(cx - 4, y - 3), (cx + 4, y + 3)], fill=(*divider_color, 200))
    y += 30

    # --- Stanza lines ---
    for i, line in enumerate(all_lines):
        if i >= lines_visible:
            break
        lb = draw.textbbox((0, 0), line, font=font_stanza)
        lw = lb[2] - lb[0]
        lx = (VIDEO_WIDTH - lw) // 2
        # Revealed lines: full opacity. Current line: slightly more vivid (just use title color)
        is_current = (i == lines_visible - 1)
        color = (*title_color, 255) if is_current else (*stanza_color, 220)
        draw.text((lx, y), line, font=font_stanza, fill=color)
        y += line_h + LINE_GAP

    # --- Brand ---
    if show_brand:
        y += 4
        draw.line([(cx - 80, y), (cx + 80, y)], fill=(*divider_color, 120), width=1)
        draw.ellipse([(cx - 3, y - 3), (cx + 3, y + 3)], fill=(*divider_color, 160))
        y += 22

        hindi_part = "द "
        latin_part = "Thoughts Within"
        hb = draw.textbbox((0, 0), hindi_part, font=font_brand_h)
        lb2 = draw.textbbox((0, 0), latin_part, font=font_brand)
        total_w = (hb[2] - hb[0]) + (lb2[2] - lb2[0])
        bx = (VIDEO_WIDTH - total_w) // 2
        draw.text((bx, y), hindi_part, font=font_brand_h, fill=(*brand_color, 210))
        draw.text((bx + (hb[2] - hb[0]), y), latin_part, font=font_brand, fill=(*brand_color, 210))

    return img


# ============================================================
# CREATE REEL VIDEO
# ============================================================
def create_reel_video(stanza_text, poem_title, music_path, output_path, tmpdir):
    print("Creating reel video...")

    hindi_font = find_hindi_font(bold=True)
    latin_font = find_latin_font()
    bg_photo   = fetch_background_photo()
    panel_theme = random.choice(PANEL_THEMES)

    lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]
    print(f"Animating {len(lines)} lines with panel theme index {PANEL_THEMES.index(panel_theme)}")

    HOLD_BEFORE    = 1.5
    SECS_PER_LINE  = 2.5
    HOLD_AFTER     = 3.0
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

    save_frames(draw_frame(0, lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme),
                int(HOLD_BEFORE * FPS))

    for i in range(1, len(lines) + 1):
        save_frames(draw_frame(i, lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme),
                    int(SECS_PER_LINE * FPS))

    save_frames(draw_frame(len(lines), lines, poem_title, False, hindi_font, latin_font, bg_photo, panel_theme),
                int(HOLD_AFTER * FPS))

    save_frames(draw_frame(len(lines), lines, poem_title, True, hindi_font, latin_font, bg_photo, panel_theme),
                int(BRAND_DURATION * FPS))

    total_duration = HOLD_BEFORE + (len(lines) * SECS_PER_LINE) + HOLD_AFTER + BRAND_DURATION
    print(f"Total duration: {total_duration:.1f}s | Frames: {frame_idx}")

    frames_pattern = os.path.join(frames_dir, "frame_%06d.jpg")

    # Instagram Reels requirements:
    # - H.264 video, AAC audio (required even if silent)
    # - min video bitrate ~3500kbps for 1080x1920
    # - audio: stereo AAC 128kbps+
    # - must be at least 3 seconds, under 90 seconds

    if music_path and os.path.exists(music_path):
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", frames_pattern,
            "-stream_loop", "-1",       # loop music if shorter than video
            "-i", music_path,
            "-t", str(total_duration),  # duration BEFORE output flags
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level", "4.0",
            "-preset", "fast",
            "-b:v", "3500k",            # explicit bitrate Instagram needs
            "-maxrate", "4000k",
            "-bufsize", "8000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",                 # stereo
            "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]
    else:
        # No music: generate a silent AAC audio track (Instagram requires audio)
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS),
            "-i", frames_pattern,
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-t", str(total_duration),
            "-c:v", "libx264",
            "-profile:v", "high",
            "-level", "4.0",
            "-preset", "fast",
            "-b:v", "3500k",
            "-maxrate", "4000k",
            "-bufsize", "8000k",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac",
            "-b:a", "128k",
            "-ac", "2",
            "-ar", "44100",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ]

    print("Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr[-2000:]}")
        raise Exception("FFmpeg failed")

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
    print(f"Video URL: {result['secure_url']}")
    return result["secure_url"]


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
    print(f"Container created: {container_id} — polling for processing...")
    for attempt in range(18):
        time.sleep(10)
        status = requests.get(
            f"https://graph.facebook.com/v18.0/{container_id}"
            f"?fields=status_code,status&access_token={PAGE_ACCESS_TOKEN}"
        ).json()
        code = status.get("status_code", "")
        print(f"Attempt {attempt + 1}: {code}")
        if code == "FINISHED":
            break
        elif code == "ERROR":
            raise Exception(f"Instagram processing failed: {status}")

    response = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish",
        data={"creation_id": container_id, "access_token": PAGE_ACCESS_TOKEN}
    ).json()
    if "id" not in response:
        raise Exception(f"Failed to publish reel: {response}")
    print(f"Reel posted! ID: {response['id']}")
    return response["id"]


# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting The Thoughts Within Reel poster...\n")

    all_stanzas = fetch_all_stanzas()
    if not all_stanzas:
        raise Exception("No stanzas found in Google Sheet.")

    meanings = fetch_meanings()
    title, stanza_num, stanza = pick_random_stanza(all_stanzas)
    meaning = meanings.get((title, stanza_num), "")

    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    music_path = random.choice(music_files) if music_files else None
    if music_path:
        print(f"Music: {os.path.basename(music_path)}")

    # Build caption with meaning if available
    if meaning:
        caption = (
            f"𝘼 𝙫𝙚𝙧𝙨𝙚 𝙛𝙧𝙤𝙢 '{title}'\n\n"
            f"✦ {meaning}\n\n"
            f"𝘙𝘦𝘢𝘥 𝘵𝘩𝘦 𝘧𝘶𝘭𝘭 𝘱𝘰𝘦𝘮 — 𝘭𝘪𝘯𝘬 𝘪𝘯 𝘣𝘪𝘰 🔗\n\n"
            f"{HASHTAGS}"
        )
    else:
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
