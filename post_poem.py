#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster
# Reads stanzas directly from Google Sheets

import os
import csv
import glob
import json
import random
import base64
import time
import subprocess
import requests
import textwrap
import tempfile
from PIL import Image, ImageDraw, ImageFont
from io import StringIO

# ============================================================
# CONFIGURATION
# ============================================================
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "17841426948301170")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")

SHEET_ID = "1Rh_LmGQ9khrYX-9vBh9SkK9ygS-j0LcjQig65TS7DLI"
SHEET_CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv"

MUSIC_FOLDER = "music"
IMG_WIDTH = 1080
IMG_HEIGHT = 1080
BACKGROUND_COLORS = [
    "#1a1a2e", "#16213e", "#0f3460", "#1b1b2f", "#2c2c54", "#191919",
]
HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #poetrylovers #hindiwriters #dil"


# ============================================================
# STEP 1: Fetch stanzas from Google Sheet
# ============================================================
def fetch_all_stanzas():
    print("Fetching stanzas from Google Sheet...")
    response = requests.get(SHEET_CSV_URL)
    response.encoding = "utf-8"
    if response.status_code != 200:
        raise Exception(f"Could not fetch Google Sheet: {response.status_code}")

    reader = csv.DictReader(StringIO(response.text))
    all_stanzas = []

    for row in reader:
        title = row.get("poem_title", "").strip()
        if not title:
            continue
        for key, value in row.items():
            if key.startswith("stanza_") and value.strip():
                stanza_text = value.strip()
                all_stanzas.append((title, stanza_text))

    print(f"Found {len(all_stanzas)} stanzas across all poems")
    return all_stanzas


# ============================================================
# STEP 2: Pick a random stanza
# ============================================================
def pick_random_stanza(all_stanzas):
    print("Picking a random stanza...")
    title, stanza = random.choice(all_stanzas)
    print(f"Selected from '{title}': {stanza[:60]}...")
    caption = f"𝘼 𝙫𝙚𝙧𝙨𝙚 𝙛𝙧𝙤𝙢 '{title}'\n\n𝘙𝘦𝘢𝘥 𝘵𝘩𝘦 𝘧𝘶𝘭𝘭 𝘱𝘰𝘦𝘮 — 𝘭𝘪𝘯𝘬 𝘪𝘯 𝘣𝘪𝘰 🔗\n\n{HASHTAGS}"
    return {"title": title, "stanza": stanza, "caption": caption}


# ============================================================
# STEP 3: Find Hindi font
# ============================================================
def find_hindi_font():
    # Try fc-list to find installed Hindi fonts
    try:
        result = subprocess.run(
            ["fc-list", ":lang=hi", "--format=%{file}\n"],
            capture_output=True,
            text=True
        )
        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        if paths:
            print(f"fc-list found Hindi font: {paths[0]}")
            return paths[0]
    except Exception as e:
        print(f"fc-list failed: {e}")

    # Fallback hardcoded paths
    fallback_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "C:/Windows/Fonts/mangal.ttf",
        "C:/Windows/Fonts/aparajita.ttf",
    ]

    # Also search recursively for any Noto Devanagari font
    noto_hits = glob.glob("/usr/share/fonts/**/Noto*Devanagari*.ttf", recursive=True)
    all_paths = noto_hits + fallback_paths

    for p in all_paths:
        if os.path.exists(p):
            print(f"Found font at: {p}")
            return p

    print("No Hindi font found!")
    return None


# ============================================================
# STEP 4: Create beautiful image
# ============================================================

# Multi-stop gradient themes (3-4 color stops each)
GRADIENT_THEMES = [
    # (color_stop_1, color_stop_2, color_stop_3, color_stop_4)
    ((255,245,235), (255,225,200), (255,200,170), (240,180,150)),  # Warm peach sunset
    ((235,245,255), (200,225,255), (170,205,255), (150,185,240)),  # Ocean blue
    ((240,255,245), (200,245,220), (170,230,200), (150,210,180)),  # Mint forest
    ((250,238,255), (230,205,255), (210,175,255), (190,155,240)),  # Purple dream
    ((255,252,230), (255,240,185), (255,225,150), (240,205,130)),  # Golden hour
    ((235,252,255), (190,238,255), (160,220,250), (140,200,235)),  # Sky
    ((255,235,242), (255,205,220), (255,180,205), (240,160,185)),  # Rose petal
    ((242,255,235), (215,255,200), (190,245,175), (170,225,155)),  # Spring green
]

def draw_gradient_background(img):
    """Draw a smooth 4-stop gradient background."""
    stops = random.choice(GRADIENT_THEMES)
    pixels = img.load()
    n = len(stops) - 1
    for y in range(IMG_HEIGHT):
        t = y / IMG_HEIGHT * n
        idx = min(int(t), n - 1)
        local_t = t - idx
        c1, c2 = stops[idx], stops[idx + 1]
        r = int(c1[0] + (c2[0] - c1[0]) * local_t)
        g = int(c1[1] + (c2[1] - c1[1]) * local_t)
        b = int(c1[2] + (c2[2] - c1[2]) * local_t)
        for x in range(IMG_WIDTH):
            pixels[x, y] = (r, g, b)
    return stops[0], stops[-1]


def create_poem_image(stanza_text, poem_title, output_path):
    print("Creating poem image...")

    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
    top_color, bottom_color = draw_gradient_background(img)
    accent = (100, 80, 60)
    draw = ImageDraw.Draw(img)

    # Dark text colors based on background
    TEXT_DARK = (40, 30, 20)
    TEXT_MED = (80, 60, 50)
    TEXT_LIGHT = (130, 110, 100)
    DIVIDER_COLOR = (180, 160, 140, 100)

    border = 55

    # Subtle border rectangle
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border],
                   outline=(*TEXT_LIGHT, 80), width=1)

    hindi_font_path = find_hindi_font()

    # Find modern Latin font (Lato preferred for modern look)
    latin_font_paths = [
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Light.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    latin_font_path = None
    for p in latin_font_paths:
        if os.path.exists(p):
            latin_font_path = p
            print(f"Latin font: {p}")
            break

    if not hindi_font_path:
        hindi_font_path = latin_font_path

    # Layout zones
    TITLE_ZONE_TOP = border + 25
    TITLE_ZONE_BOTTOM = border + 130
    BRAND_ZONE_TOP = IMG_HEIGHT - border - 95
    STANZA_ZONE_TOP = TITLE_ZONE_BOTTOM + 25
    STANZA_ZONE_BOTTOM = BRAND_ZONE_TOP - 25
    STANZA_ZONE_HEIGHT = STANZA_ZONE_BOTTOM - STANZA_ZONE_TOP

    # Split stanza into lines
    raw_lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]

    # Auto-size font to fit all lines in stanza zone
    def get_font_size(lines, zone_height, font_path=None, max_size=44, min_size=24):
        fp = font_path or hindi_font_path
        for size in range(max_size, min_size - 1, -2):
            font = ImageFont.truetype(fp, size)
            line_h = int(size * 2.0)  # More breathing room between lines
            total_h = len(lines) * line_h
            if total_h <= zone_height:
                return size, font, line_h
        font = ImageFont.truetype(fp, min_size)
        return min_size, font, int(min_size * 2.0)

    # For stanza: use a lighter/thinner variant of the Hindi font if available
    stanza_font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Light.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
    ]
    stanza_font_path = hindi_font_path  # fallback
    for sfp in stanza_font_paths:
        if os.path.exists(sfp):
            stanza_font_path = sfp
            print(f"Stanza font: {sfp}")
            break

    poem_size, font_poem, line_height = get_font_size(raw_lines, STANZA_ZONE_HEIGHT, stanza_font_path)
    print(f"Auto font size: {poem_size}px for {len(raw_lines)} lines")

    font_title = ImageFont.truetype(hindi_font_path, 38)
    font_brand_hindi = ImageFont.truetype(hindi_font_path, 28)
    font_brand_latin = ImageFont.truetype(latin_font_path, 28) if latin_font_path else font_brand_hindi

    # --- TITLE ---
    title_bbox = draw.textbbox((0, 0), poem_title, font=font_title)
    title_w = title_bbox[2] - title_bbox[0]
    title_h = title_bbox[3] - title_bbox[1]
    title_x = (IMG_WIDTH - title_w) // 2
    title_y = TITLE_ZONE_TOP + (TITLE_ZONE_BOTTOM - TITLE_ZONE_TOP - title_h) // 2
    draw.text((title_x, title_y), poem_title, font=font_title, fill=TEXT_DARK)

    # Elegant thin divider under title
    div_y = TITLE_ZONE_BOTTOM + 5
    div_cx = IMG_WIDTH // 2
    draw.line([(div_cx - 180, div_y), (div_cx + 180, div_y)], fill=TEXT_LIGHT, width=1)
    draw.ellipse([(div_cx - 4, div_y - 3), (div_cx + 4, div_y + 3)], fill=TEXT_MED)

    # --- STANZA ---
    total_stanza_height = len(raw_lines) * line_height
    start_y = STANZA_ZONE_TOP + (STANZA_ZONE_HEIGHT - total_stanza_height) // 2

    for i, line in enumerate(raw_lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_poem)
        text_width = bbox[2] - bbox[0]
        x = (IMG_WIDTH - text_width) // 2
        draw.text((x, y), line, font=font_poem, fill=TEXT_DARK)

    # Elegant thin divider above brand
    div2_y = BRAND_ZONE_TOP - 5
    draw.line([(div_cx - 180, div2_y), (div_cx + 180, div2_y)], fill=TEXT_LIGHT, width=1)
    draw.ellipse([(div_cx - 4, div2_y - 3), (div_cx + 4, div2_y + 3)], fill=TEXT_MED)

    # --- BRAND: "द Thoughts Within" ---
    # "द" in Hindi font + " Thoughts Within" in Latin font, joined together
    hindi_part = "द "
    latin_part = "Thoughts Within"

    hindi_bbox = draw.textbbox((0, 0), hindi_part, font=font_brand_hindi)
    latin_bbox = draw.textbbox((0, 0), latin_part, font=font_brand_latin)
    hindi_w = hindi_bbox[2] - hindi_bbox[0]
    latin_w = latin_bbox[2] - latin_bbox[0]
    total_brand_w = hindi_w + latin_w
    brand_x = (IMG_WIDTH - total_brand_w) // 2
    brand_y = BRAND_ZONE_TOP + 18

    draw.text((brand_x, brand_y), hindi_part, font=font_brand_hindi, fill=TEXT_MED)
    draw.text((brand_x + hindi_w, brand_y), latin_part, font=font_brand_latin, fill=TEXT_MED)

    img.save(output_path, "JPEG", quality=95)
    print(f"Image saved: {output_path}")
    return output_path


# ============================================================
# STEP 5: Pick random music
# ============================================================
def pick_random_music():
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    if not music_files:
        return None
    chosen = random.choice(music_files)
    print(f"Selected music: {os.path.basename(chosen)}")
    return chosen


# ============================================================
# STEP 6: Upload and post to Instagram
# ============================================================
def upload_image(image_path):
    print("Uploading image...")
    if not IMGBB_API_KEY:
        raise ValueError("IMGBB_API_KEY not set.")

    with open(image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode("utf-8")

    response = requests.post(
        "https://api.imgbb.com/1/upload",
        data={"key": IMGBB_API_KEY, "image": image_data, "expiration": 3600}
    )
    result = response.json()
    if result.get("success"):
        url = result["data"]["url"]
        print(f"Image uploaded: {url}")
        return url
    else:
        raise Exception(f"Image upload failed: {result}")


def post_to_instagram(image_url, caption):
    print("Posting to Instagram...")

    create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    response = requests.post(create_url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": PAGE_ACCESS_TOKEN
    })
    result = response.json()
    if "id" not in result:
        raise Exception(f"Failed to create media container: {result}")

    container_id = result["id"]
    print(f"Media container created: {container_id}")
    print("Waiting 20 seconds for Instagram to process image...")
    time.sleep(20)

    status_url = f"https://graph.facebook.com/v18.0/{container_id}?fields=status_code&access_token={PAGE_ACCESS_TOKEN}"
    status = requests.get(status_url).json()
    print(f"Container status: {status.get('status_code', 'unknown')}")

    publish_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish"
    response = requests.post(publish_url, data={
        "creation_id": container_id,
        "access_token": PAGE_ACCESS_TOKEN
    })
    result = response.json()
    if "id" not in result:
        raise Exception(f"Failed to publish: {result}")

    print(f"Successfully posted! Post ID: {result['id']}")
    return result["id"]


# ============================================================
# HISTORY TRACKING
# ============================================================
import json

HISTORY_FILE = "posted_history.json"

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_history(history, new_item):
    history.append(new_item)
    history = history[-5:]  # Keep only last 5
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f)


# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting The Thoughts Within auto-poster...\n")

    all_stanzas = fetch_all_stanzas()
    if not all_stanzas:
        raise Exception("No stanzas found in Google Sheet.")

    stanza_data = pick_random_stanza(all_stanzas)

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "poem.jpg")
        create_poem_image(stanza_data["stanza"], stanza_data["title"], image_path)
        pick_random_music()
        image_url = upload_image(image_path)
        post_to_instagram(image_url, stanza_data["caption"])

    print("\nDone! Your poem has been posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
