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
    urls_to_try = [
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&sheet=meanings",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet=meanings",
        f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid=1",
    ]
    for url in urls_to_try:
        try:
            response = requests.get(url, timeout=15)
            response.encoding = "utf-8"
            print(f"  URL: {url[-60:]} | status: {response.status_code} | size: {len(response.text)}")
            if response.status_code != 200 or len(response.text) < 20:
                continue
            first_line = response.text.split("\n")[0]
            print(f"  Headers: {first_line[:150]}")
            reader = csv.DictReader(StringIO(response.text))
            meanings = {}
            for row in reader:
                title   = row.get("poem_title", "").strip()
                num     = str(row.get("stanza_number", "")).strip()
                meaning = row.get("meaning", "").strip()
                if title and num and meaning:
                    meanings[(title, num)] = meaning
            print(f"  Parsed {len(meanings)} meanings from this URL")
            if meanings:
                return meanings
        except Exception as e:
            print(f"  Error: {e}")
    print("WARNING: No meanings found in any URL")
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
# DRAW A SINGLE FRAME (UPDATED SPACING AND PERSISTENCE)
# ============================================================
def draw_frame(lines_visible, all_lines, poem_title,
               hindi_font_path, latin_font_path, bg_photo, panel_theme):

    # Background processing
    img = bg_photo.copy()
    dark_overlay = Image.new("RGB", (VIDEO_WIDTH, VIDEO_HEIGHT), (0, 0, 0))
    img = Image.blend(img, dark_overlay, alpha=0.40)
    img = img.filter(ImageFilter.GaussianBlur(radius=4))

    draw = ImageDraw.Draw(img, "RGBA")
    panel_fill, title_color, stanza_color, divider_color, brand_color = panel_theme

    # Typography sizes
    font_stanza = ImageFont.truetype(hindi_font_path, 54) if hindi_font_path else ImageFont.load_default()
    font_title  = ImageFont.truetype(hindi_font_path, 48) if hindi_font_path else ImageFont.load_default()
    font
