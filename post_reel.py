#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Reels Poster
# Creates animated text reels with music and posts to @_thethoughtswithin

import os
import csv
import glob
import json
import math
import random
import time
import subprocess
import requests
import tempfile
import base64
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
GCP_TTS_API_KEY = os.environ.get("GCP_TTS_API_KEY", "")

SHEET_ID = "1Rh_LmGQ9khrYX-9vBh9SkK9ygS-j0LcjQig65TS7DLI"
SHEET_CSV_URL   = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=0"
MUSIC_FOLDER    = "music"
REEL_HISTORY_FILE = "reel_history.json"

VIDEO_WIDTH  = 1080
VIDEO_HEIGHT = 1920
FPS          = 30

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

PANEL_THEMES = [
    ((255, 252, 245, 235), (120, 60,  20),  (60,  35, 10),  (180, 140, 100), (140, 100, 60)),
    ((245, 248, 255, 230), (30,  55, 110),  (20,  40, 80),  (110, 140, 190), (80,  110, 160)),
    ((245, 255, 248, 230), (25,  80,  45),  (18,  60, 35),  (100, 170, 120), (70,  140, 90)),
    ((255, 248, 248, 230), (110, 25,  25),  (80,  18, 18),  (200, 120, 120), (160, 80,  80)),
    ((252, 252, 252, 235), (50,  50,  50),  (25,  25, 25),  (160, 160, 160), (110, 110, 110)),
    ((255, 250, 235, 232), (100, 65,  10),  (70,  45, 8),   (190, 155, 80),  (150, 110, 45)),
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
    urls_to_try = [
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=meanings",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=meanings",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1",
    ]
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=15)
            response.encoding = "utf-8"
            print(f"  status: {response.status_code} | size: {len(response.text)}")
            if response.status_code != 200 or len(response.text) < 20:
                continue
            print(f"  Headers: {response.text.split(chr(10))[0][:150]}")
            reader = csv.DictReader(StringIO(response.text))
            meanings = {}
            for row in reader:
                title   = row.get("poem_title", "").strip()
                num     = str(row.get("stanza_number", "")).strip()
                meaning = row.get("meaning", "").strip()
                if title and num and meaning:
                    meanings[(title, num)] = meaning
            print(f"  Parsed {len(meanings)} meanings")
            if meanings:
                return meanings
        except Exception as e:
            print(f"  Error: {e}")
    print("WARNING: No meanings found")
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
def find_hindi_font():
    for p in [
        os.path.expanduser("~/.local/share/fonts/NotoSansDevanagari.ttf"),
        "/usr/share/fonts/NotoSansDevanagari.ttf",
    ]:
        if os.path.exists(p):
            print(f"Using font: {p}")
            return p
    try:
        result = subprocess.run(["fc-list", ":lang=hi", "--format=%{file}\n"],
                                capture_output=True, text=True)
        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        print(f"fc-list found {len(paths)} Hindi fonts")
        regular = [p for p in paths if "Regular" in p and "Condensed" not in p]
        if regular:
            return regular[0]
        if paths:
            return paths[0]
    except Exception as e:
        print(f"fc-list error: {e}")
    for p in ["/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"]:
        if os.path.exists(p):
            return p
    return None

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
# FETCH BACKGROUND PHOTO
# ============================================================
def fetch_background_photo():
    query = random.choice(PHOTO_QUERIES)
    print(f"Fetching photo: '{query}'")
    if UNSPLASH_ACCESS_KEY:
        try:
            resp = requests.get(
                "https://api.unsplash.com/photos/random",
                params={"query": query, "orientation": "portrait", "content_filter": "high"},
                headers={"Authorization": f"Client-ID {UNSPLASH_ACCESS_KEY}"},
                timeout=15
            )
            if resp.status_code == 200:
                photo_url = resp.json()["urls"].get("regular")
                img_resp = requests.get(photo_url, timeout=20)
                if img_resp.status_code == 200:
                    img = Image.open(BytesIO(img_resp.content)).convert("RGB")
                    img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
                    print(f"Photo: Unsplash ({query})")
                    return img
        except Exception as e:
            print(f"Unsplash error: {e}")
    try:
        seed = random.randint(1, 500)
        resp = requests.get(f"https://picsum.photos/seed/{seed}/1080/1920",
                            timeout=20, allow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 10000:
            img = Image.open(BytesIO(resp.content)).convert("RGB")
            img = img.resize((VIDEO_WIDTH, VIDEO_HEIGHT), Image.LANCZOS)
            print(f"Photo: Picsum seed {seed}")
            return img
    except Exception as e:
        print(f"Picsum error: {e}")
    print("Photo: gradient fallback")
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
# EASE CURVE
# ============================================================
def ease_out(t):
    return 1 - (1 - t) ** 3


# ============================================================
# MEASURE LAYOUT
# ============================================================
def measure_layout(lines, poem_title, hindi_font, latin_font):
    SIDE_MARGIN    = 100
    INNER_PAD_X    = 65
    LINE_GAP       = 46
    DIVIDER_AREA   = 58
    BRAND_DIV_AREA = 52
    PAD_TOP        = 90
    PAD_BOTTOM     = 90

    panel_w      = VIDEO_WIDTH - 2 * SIDE_MARGIN
    max_text_w   = panel_w - 2 * INNER_PAD_X

    dummy = ImageDraw.Draw(Image.new("RGB", (10, 10)))

    stanza_size = 48
    while stanza_size >= 26:
        font_test = ImageFont.truetype(hindi_font, stanza_size)
        widths = [dummy.textbbox((0,0), l, font=font_test)[2]
                  - dummy.textbbox((0,0), l, font=font_test)[0]
                  for l in lines]
        if max(widths) <= max_text_w:
            break
        stanza_size -= 2

    font_stanza  = ImageFont.truetype(hindi_font, stanza_size)
    title_size   = max(30, stanza_size - 6)
    font_title   = ImageFont.truetype(hindi_font, title_size)
    font_brand   = ImageFont.truetype(latin_font, 28) if latin_font else font_title
    font_brand_h = ImageFont.truetype(hindi_font, 28)

    title_bbox  = dummy.textbbox((0,0), poem_title, font=font_title)
    title_h     = title_bbox[3] - title_bbox[1]
    title_w     = title_bbox[2] - title_bbox[0]

    sample_bbox = dummy.textbbox((0,0), "क", font=font_stanza)
    line_h      = sample_bbox[3] - sample_bbox[1]

    line_widths = [dummy.textbbox((0,0), l, font=font_stanza)[2]
                   - dummy.textbbox((0,0), l, font=font_stanza)[0]
                   for l in lines]

    b_bbox  = dummy.textbbox((0,0), "Thoughts Within", font=font_brand)
    brand_h = b_bbox[3] - b_bbox[1]

    stanza_block_h  = len(lines) * line_h + (len(lines) - 1) * LINE_GAP
    total_content_h = title_h + DIVIDER_AREA + stanza_block_h + BRAND_DIV_AREA + brand_h + 10
    panel_h         = total_content_h + PAD_TOP + PAD_BOTTOM
    panel_x0        = SIDE_MARGIN
    panel_y0        = (VIDEO_HEIGHT - panel_h) // 2
    panel_x1        = panel_x0 + panel_w
    panel_y1        = panel_y0 + panel_h
    cx              = VIDEO_WIDTH // 2

    print(f"Layout: font={stanza_size}px, max_line={max(line_widths)}px / {max_text_w}px, panel_h={panel_h}px")

    return {
        "font_stanza": font_stanza, "font_title": font_title,
        "font_brand": font_brand,   "font_brand_h": font_brand_h,
        "title_h": title_h, "title_w": title_w,
        "line_h": line_h,   "line_widths": line_widths,
        "brand_h": brand_h,
        "LINE_GAP": LINE_GAP, "DIVIDER_AREA": DIVIDER_AREA,
        "BRAND_DIV_AREA": BRAND_DIV_AREA,
        "PAD_TOP": PAD_TOP, "PAD_BOTTOM": PAD_BOTTOM,
        "panel_x0": panel_x0, "panel_y0": panel_y0,
        "panel_x1": panel_x1, "panel_y1": panel_y1,
        "cx": cx,
    }


# ============================================================
# DRAW FRAME
# ============================================================
def draw_frame(bg_photo, panel_theme, layout, lines, poem_title,
               title_alpha, stanza_alpha, stanza_offset, brand_alpha):

    img  = bg_photo.copy()
    dark = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    img  = Image.blend(img, dark, alpha=0.42)
    img  = img.filter(ImageFilter.GaussianBlur(radius=4))
    draw = ImageDraw.Draw(img, "RGBA")

    panel_fill, title_color, stanza_color, divider_color, brand_color = panel_theme
    L  = layout
    ta = title_alpha / 255
    cx = L["cx"]

    draw.rounded_rectangle(
        [(L["panel_x0"], L["panel_y0"]), (L["panel_x1"], L["panel_y1"])],
        radius=32,
        fill=(*panel_fill[:3], int(panel_fill[3] * ta))
    )
    draw.rounded_rectangle(
        [(L["panel_x0"], L["panel_y0"]), (L["panel_x1"], L["panel_y1"])],
        radius=32,
        outline=(*divider_color, int(110 * ta)),
        width=2
    )

    y = L["panel_y0"] + L["PAD_TOP"]

    tx = (VIDEO_WIDTH - L["title_w"]) // 2
    draw.text((tx, y), poem_title,
              font=L["font_title"], fill=(*title_color, title_alpha))
    y += L["title_h"] + 18

    draw.line([(cx - 85, y), (cx + 85, y)],
              fill=(*divider_color, int(160 * ta)), width=1)
    draw.ellipse([(cx - 4, y - 3), (cx + 4, y + 3)],
                 fill=(*divider_color, int(200 * ta)))
    y += L["DIVIDER_AREA"] - 18

    stanza_y = y + stanza_offset
    for i, line in enumerate(lines):
        if stanza_alpha > 0:
            lx = (VIDEO_WIDTH - L["line_widths"][i]) // 2
            draw.text((lx, int(stanza_y)), line,
                      font=L["font_stanza"], fill=(*stanza_color, stanza_alpha))
        stanza_y += L["line_h"] + L["LINE_GAP"]

    y += len(lines) * L["line_h"] + (len(lines) - 1) * L["LINE_GAP"] + L["BRAND_DIV_AREA"]

    if brand_alpha > 0:
        ba = brand_alpha / 255
        draw.line([(cx - 75, y), (cx + 75, y)],
                  fill=(*divider_color, int(120 * ba)), width=1)
        draw.ellipse([(cx - 3, y - 3), (cx + 3, y + 3)],
                     fill=(*divider_color, int(160 * ba)))
        y += 24
        hindi_part = "द "
        latin_part = "Thoughts Within"
        hb  = draw.textbbox((0,0), hindi_part, font=L["font_brand_h"])
        lb2 = draw.textbbox((0,0), latin_part, font=L["font_brand"])
        total_w = (hb[2]-hb[0]) + (lb2[2]-lb2[0])
        bx = (VIDEO_WIDTH - total_w) // 2
        draw.text((bx, y), hindi_part,
                  font=L["font_brand_h"], fill=(*brand_color, brand_alpha))
        draw.text((bx + (hb[2]-hb[0]), y), latin_part,
                  font=L["font_brand"], fill=(*brand_color, brand_alpha))

    return img


# ============================================================
# GENERATE VOICEOVER via Google Cloud TTS
# ============================================================
def generate_voiceover(stanza_text, output_path):
    """
    Calls the Google Cloud TTS REST API with hi-IN-Wavenet-D (male, neural).
    Writes an MP3 to output_path and returns the audio duration in seconds.
    Falls back gracefully if the API key is missing or the call fails.
    """
    if not GCP_TTS_API_KEY:
        print("GCP_TTS_API_KEY not set — skipping voiceover")
        return None

    print("Generating voiceover via Google Cloud TTS...")

    # Clean up the stanza: join lines with a short pause (comma works well in TTS)
    lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]
    tts_text = ", ".join(lines)

    payload = {
        "input": {"text": tts_text},
        "voice": {
            "languageCode": "hi-IN",
            "name": "hi-IN-Wavenet-D",   # male, neural
            "ssmlGender": "MALE"
        },
        "audioConfig": {
            "audioEncoding": "MP3",
            "speakingRate": 0.85,         # slightly slower — suits poetry
            "pitch": -1.0,               # slightly lower — warmer, more considered
            "effectsProfileId": ["headphone-class-device"]
        }
    }

    try:
        resp = requests.post(
            f"https://texttospeech.googleapis.com/v1/text:synthesize?key={GCP_TTS_API_KEY}",
            json=payload,
            timeout=30
        )
        if resp.status_code != 200:
            print(f"TTS API error {resp.status_code}: {resp.text[:300]}")
            return None

        audio_content = resp.json().get("audioContent")
        if not audio_content:
            print("TTS response missing audioContent")
            return None

        audio_bytes = base64.b64decode(audio_content)
        with open(output_path, "wb") as f:
            f.write(audio_bytes)
        print(f"Voiceover saved: {output_path} ({len(audio_bytes) / 1024:.1f} KB)")

        # Get duration via ffprobe
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", output_path],
            capture_output=True, text=True
        )
        duration = float(probe.stdout.strip())
        print(f"Voiceover duration: {duration:.2f}s")
        return duration

    except Exception as e:
        print(f"Voiceover generation failed: {e}")
        return None


# ============================================================
# CREATE REEL VIDEO
# ============================================================
def create_reel_video(stanza_text, poem_title, music_path, output_path, tmpdir):
    print("Creating reel video...")

    hindi_font  = find_hindi_font()
    latin_font  = find_latin_font()
    bg_photo    = fetch_background_photo()
    panel_theme = random.choice(PANEL_THEMES)

    lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]
    print(f"Lines: {len(lines)}")

    layout = measure_layout(lines, poem_title, hindi_font, latin_font)

    # --- Voiceover ---
    vo_path = os.path.join(tmpdir, "voiceover.mp3")
    vo_duration = generate_voiceover(stanza_text, vo_path)
    has_voiceover = vo_duration is not None and os.path.exists(vo_path)

    # --- Timing ---
    TITLE_FADE   = 15   # panel + title + brand fade in together  (~0.5s)
    TITLE_HOLD   = 60   # title + brand alone                     (~2.0s)
    STANZA_TRANS = 40   # poem fades in                           (~1.3s)

    # Voiceover starts at the moment the poem begins fading in.
    # STANZA_HOLD = voiceover duration in frames + 1s tail, or fixed 240 if no voiceover.
    if has_voiceover:
        STANZA_HOLD = math.ceil(vo_duration * FPS) + 30   # +1s tail after voice ends
        print(f"STANZA_HOLD set to {STANZA_HOLD} frames ({STANZA_HOLD/FPS:.1f}s) from voiceover")
    else:
        STANZA_HOLD = 240
        print("STANZA_HOLD set to 240 frames (fallback, no voiceover)")

    frames_dir = os.path.join(tmpdir, "frames")
    os.makedirs(frames_dir, exist_ok=True)
    frame_idx = 0

    def emit(img):
        nonlocal frame_idx
        img.save(os.path.join(frames_dir, f"frame_{frame_idx:06d}.jpg"), "JPEG", quality=85)
        frame_idx += 1

    def frame(ta, sa, so, ba):
        return draw_frame(bg_photo, panel_theme, layout, lines, poem_title, ta, sa, so, ba)

    # Phase 1: Panel + title + brand fade in
    for f in range(TITLE_FADE):
        t = ease_out((f + 1) / TITLE_FADE)
        emit(frame(int(255 * t), 0, 0, int(255 * t)))

    # Phase 2: Title + brand hold alone
    f_title = frame(255, 0, 0, 255)
    for _ in range(TITLE_HOLD):
        emit(f_title)

    # Phase 3: Poem fades in slowly
    for f in range(STANZA_TRANS):
        t = ease_out((f + 1) / STANZA_TRANS)
        emit(frame(255, int(255 * t), 0, 255))

    # Phase 4: Everything holds (voiceover plays during this phase)
    f_hold = frame(255, 255, 0, 255)
    for _ in range(STANZA_HOLD):
        emit(f_hold)

    total_frames   = frame_idx
    total_duration = round(total_frames / FPS, 3)
    print(f"Total: {total_duration}s | {total_frames} frames")

    frames_pattern = os.path.join(frames_dir, "frame_%06d.jpg")
    has_music = music_path and os.path.exists(music_path)

    # --- FFmpeg command ---
    #
    # Inputs:
    #   0: frames (video)
    #   1: music (looped, optional)
    #   2: voiceover (optional)
    #
    # Audio filter:
    #   music at 15% volume, voice at 100%, mixed together.
    #   amix duration=longest so neither cuts the other short,
    #   but the whole thing is capped by -t total_duration.

    if has_voiceover and has_music:
        # Voiceover starts when poem fades in (after TITLE_FADE + TITLE_HOLD frames)
        vo_delay_s = (TITLE_FADE + TITLE_HOLD) / FPS
        audio_filter = (
            f"[1:a]volume=0.15[music];"
            f"[2:a]volume=1.0,adelay={int(vo_delay_s * 1000)}|{int(vo_delay_s * 1000)}[voice];"
            f"[music][voice]amix=inputs=2:duration=longest[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS), "-i", frames_pattern,
            "-stream_loop", "-1", "-i", music_path,
            "-i", vo_path,
            "-filter_complex", audio_filter,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-preset", "fast", "-b:v", "3500k", "-maxrate", "4000k",
            "-bufsize", "8000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "44100",
            "-t", str(total_duration), "-movflags", "+faststart", output_path
        ]

    elif has_voiceover and not has_music:
        # Voiceover only — pad silence before it starts
        vo_delay_s = (TITLE_FADE + TITLE_HOLD) / FPS
        audio_filter = (
            f"[1:a]volume=1.0,adelay={int(vo_delay_s * 1000)}|{int(vo_delay_s * 1000)}[aout]"
        )
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS), "-i", frames_pattern,
            "-i", vo_path,
            "-filter_complex", audio_filter,
            "-map", "0:v:0", "-map", "[aout]",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-preset", "fast", "-b:v", "3500k", "-maxrate", "4000k",
            "-bufsize", "8000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "44100",
            "-t", str(total_duration), "-movflags", "+faststart", output_path
        ]

    elif has_music and not has_voiceover:
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS), "-i", frames_pattern,
            "-stream_loop", "-1", "-i", music_path,
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-preset", "fast", "-b:v", "3500k", "-maxrate", "4000k",
            "-bufsize", "8000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "44100",
            "-t", str(total_duration), "-movflags", "+faststart", output_path
        ]

    else:
        # No audio at all
        cmd = [
            "ffmpeg", "-y",
            "-framerate", str(FPS), "-i", frames_pattern,
            "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100",
            "-map", "0:v:0", "-map", "1:a:0",
            "-c:v", "libx264", "-profile:v", "high", "-level", "4.0",
            "-preset", "fast", "-b:v", "3500k", "-maxrate", "4000k",
            "-bufsize", "8000k", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-ac", "2", "-ar", "44100",
            "-t", str(total_duration), "-movflags", "+faststart", output_path
        ]

    print("Running FFmpeg...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"FFmpeg stderr: {result.stderr[-2000:]}")
        raise Exception("FFmpeg failed")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"Video: {size_mb:.1f} MB")
    return output_path


# ============================================================
# UPLOAD TO CLOUDINARY
# ============================================================
def upload_video_to_cloudinary(video_path):
    print("Uploading to Cloudinary...")
    import hashlib, time as time_mod

    timestamp = str(int(time_mod.time()))
    public_id = f"thoughtswithin_reel_{timestamp}"
    signature = hashlib.sha1(
        f"public_id={public_id}&timestamp={timestamp}{CLOUDINARY_API_SECRET}".encode()
    ).hexdigest()

    with open(video_path, "rb") as f:
        result = requests.post(
            f"https://api.cloudinary.com/v1_1/{CLOUDINARY_CLOUD_NAME}/video/upload",
            data={"api_key": CLOUDINARY_API_KEY, "timestamp": timestamp,
                  "public_id": public_id, "signature": signature},
            files={"file": f}, timeout=180
        ).json()

    if "secure_url" not in result:
        raise Exception(f"Cloudinary failed: {result}")
    print(f"Uploaded: {result['secure_url']}")
    return result["secure_url"]


# ============================================================
# POST REEL TO INSTAGRAM
# ============================================================
def post_reel_to_instagram(video_url, caption):
    print("Posting to Instagram...")
    result = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media",
        data={"media_type": "REELS", "video_url": video_url,
              "caption": caption, "share_to_feed": "true",
              "access_token": PAGE_ACCESS_TOKEN}
    ).json()

    if "id" not in result:
        raise Exception(f"Container creation failed: {result}")

    container_id = result["id"]
    print(f"Container: {container_id} — polling...")

    for attempt in range(24):
        time.sleep(10)
        status = requests.get(
            f"https://graph.facebook.com/v18.0/{container_id}"
            f"?fields=status_code,status&access_token={PAGE_ACCESS_TOKEN}"
        ).json()
        code = status.get("status_code", "")
        print(f"  [{attempt+1}] {code}")
        if code == "FINISHED":
            break
        elif code == "ERROR":
            raise Exception(f"Instagram processing error: {status}")

    pub = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish",
        data={"creation_id": container_id, "access_token": PAGE_ACCESS_TOKEN}
    ).json()

    if "id" not in pub:
        raise Exception(f"Publish failed: {pub}")

    media_id = pub["id"]
    print(f"Reel posted! ID: {media_id}")

    comment = requests.post(
        f"https://graph.facebook.com/v18.0/{media_id}/comments",
        data={"message": HASHTAGS, "access_token": PAGE_ACCESS_TOKEN}
    ).json()
    if "id" in comment:
        print("Hashtags posted as first comment")
    else:
        print(f"First comment failed (non-critical): {comment}")

    return media_id


# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting The Thoughts Within Reel poster...\n")

    all_stanzas = fetch_all_stanzas()
    if not all_stanzas:
        raise Exception("No stanzas found.")

    meanings = fetch_meanings()
    title, stanza_num, stanza = pick_random_stanza(all_stanzas)

    meaning = ""
    if stanza_num.isdigit():
        meaning = (meanings.get((title, stanza_num), "")
                   or meanings.get((title, str(int(stanza_num))), ""))
    else:
        meaning = meanings.get((title, stanza_num), "")

    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    music_path  = random.choice(music_files) if music_files else None
    if music_path:
        print(f"Music: {os.path.basename(music_path)}")

    caption = f"𝘼 𝙫𝙚𝙧𝙨𝙚 𝙛𝙧𝙤𝙢 '{title}'\n\n"
    if meaning:
        caption += f"✦ {meaning}\n\n"
    caption += "𝘙𝘦𝘢𝘥 𝘵𝘩𝘦 𝘧𝘶𝘭𝘭 𝘱𝘰𝘦𝘮 — 𝘭𝘪𝘯𝘬 𝘪𝘯 𝘣𝘪𝘰 🔗"

    with tempfile.TemporaryDirectory() as tmpdir:
        video_path = os.path.join(tmpdir, "reel.mp4")
        create_reel_video(stanza, title, music_path, video_path, tmpdir)
        video_url = upload_video_to_cloudinary(video_path)
        post_reel_to_instagram(video_url, caption)

    print("\nDone! Reel posted to @_thethoughtswithin")


if __name__ == "__main__":
    main()
