#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster
# Reads stanzas directly from Google Sheets

import os
import re
import csv
import glob
import random
import base64
import time
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

# Google Sheet ID (from your URL)
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
    """Download Google Sheet as CSV and extract all stanzas."""
    print("Fetching stanzas from Google Sheet...")
    
    response = requests.get(SHEET_CSV_URL)
    if response.status_code != 200:
        raise Exception(f"Could not fetch Google Sheet: {response.status_code}")
    
    reader = csv.DictReader(StringIO(response.text))
    
    all_stanzas = []  # List of (poem_title, stanza_text)
    
    for row in reader:
        title = row.get("poem_title", "").strip()
        if not title:
            continue
        
        # Collect all stanza columns (stanza_1, stanza_2, ...)
        for key, value in row.items():
            if key.startswith("stanza_") and value.strip():
                stanza_text = value.strip()
                # Clean up the stanza — normalize newlines
                stanza_text = stanza_text.replace("\\n", "\n")
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
    caption = f"'{title}'\n\nRead the full poem at the link in bio.\n\n{HASHTAGS}"
    return {"title": title, "stanza": stanza, "caption": caption}


# ============================================================
# STEP 3: Create beautiful image
# ============================================================
def create_poem_image(stanza_text, poem_title, output_path):
    print("Creating poem image...")

    bg_color = random.choice(BACKGROUND_COLORS)
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    border = 40
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border], outline="#ffffff22", width=1)
    draw.rectangle([border + 8, border + 8, IMG_WIDTH - border - 8, IMG_HEIGHT - border - 8], outline="#ffffff11", width=1)

    POEM_FONT_SIZE = 58
    TITLE_FONT_SIZE = 30
    BRAND_FONT_SIZE = 24

    font_poem = font_title = font_brand = None

    def find_hindi_font():
        import subprocess, glob as g
        try:
            result = subprocess.run(["fc-list", ":lang=hi", "--format=%{file}\n"], capture_output=True, text=True)
            paths = [p.strip() for p in result.stdout.strip().split("
") if p.strip()]
            if paths:
                print(f"fc-list found: {paths[0]}")
                return paths[0]
        except Exception as e:
            print(f"fc-list failed: {e}")
        noto_hits = g.glob("/usr/share/fonts/**/Noto*Devanagari*.ttf", recursive=True)
        fallback = ["C:/Windows/Fonts/mangal.ttf", "C:/Windows/Fonts/aparajita.ttf"]
        for p in noto_hits + fallback:
            if os.path.exists(p):
                print(f"Found font: {p}")
                return p
        return None

    font_path = find_hindi_font()
    if font_path:
        try:
            font_poem = ImageFont.truetype(font_path, POEM_FONT_SIZE)
            font_title = ImageFont.truetype(font_path, TITLE_FONT_SIZE)
            font_brand = ImageFont.truetype(font_path, BRAND_FONT_SIZE)
            print(f"Using font: {font_path}")
        except Exception as e:
            print(f"Font load error: {e}")
    if not font_poem:
        font_poem = font_title = font_brand = ImageFont.load_default()
        print("Warning: Using default font — Hindi may render as boxes")

    # Split stanza into lines
    raw_lines = [l.strip() for l in stanza_text.split("\n") if l.strip()]
    
    # Wrap long lines
    lines = []
    for line in raw_lines:
        if len(line) > 20:
            wrapped = textwrap.wrap(line, width=20)
            lines.extend(wrapped)
        else:
            lines.append(line)

    lines = lines[:10]  # Max 10 lines

    line_height = 80
    total_text_height = len(lines) * line_height
    start_y = max(border + 100, (IMG_HEIGHT - total_text_height) // 2 - 50)

    # Opening quote
    draw.text((border + 30, start_y - 80), "\u201c", font=font_poem, fill="#ffffff33")

    # Draw each poem line
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_poem)
        text_width = bbox[2] - bbox[0]
        x = (IMG_WIDTH - text_width) // 2
        draw.text((x + 2, y + 2), line, font=font_poem, fill="#00000066")  # shadow
        draw.text((x, y), line, font=font_poem, fill="#ffffff")

    end_y = start_y + total_text_height

    # Closing quote
    draw.text((IMG_WIDTH - border - 70, end_y - 20), "\u201d", font=font_poem, fill="#ffffff33")

    # Poem title
    title_display = f"— {poem_title[:28]}"
    bbox = draw.textbbox((0, 0), title_display, font=font_title)
    title_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - title_w) // 2, end_y + 28), title_display, font=font_title, fill="#ffffff88")

    # Brand
    brand = "@the.thoughtswithin"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    brand_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - brand_w) // 2, IMG_HEIGHT - border - 45), brand, font=font_brand, fill="#ffffff55")

    img.save(output_path, "JPEG", quality=95)
    print(f"Image saved: {output_path}")
    return output_path


# ============================================================
# STEP 4: Pick random music
# ============================================================
def pick_random_music():
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    if not music_files:
        return None
    chosen = random.choice(music_files)
    print(f"Selected music: {os.path.basename(chosen)}")
    return chosen


# ============================================================
# STEP 5: Upload and post to Instagram
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

    # Create media container
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

    # Wait for Instagram to process the image
    print("Waiting 20 seconds for Instagram to process image...")
    time.sleep(20)

    # Check status
    status_url = f"https://graph.facebook.com/v18.0/{container_id}?fields=status_code&access_token={PAGE_ACCESS_TOKEN}"
    status = requests.get(status_url).json()
    print(f"Container status: {status.get('status_code', 'unknown')}")

    # Publish
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
# MAIN
# ============================================================
def main():
    print("Starting The Thoughts Within auto-poster...\n")

    # 1. Fetch all stanzas from Google Sheet
    all_stanzas = fetch_all_stanzas()
    if not all_stanzas:
        raise Exception("No stanzas found in Google Sheet. Please add poem content.")

    # 2. Pick a random stanza
    stanza_data = pick_random_stanza(all_stanzas)

    # 3. Create image
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "poem.jpg")
        create_poem_image(stanza_data["stanza"], stanza_data["title"], image_path)
        pick_random_music()
        image_url = upload_image(image_path)
        post_to_instagram(image_url, stanza_data["caption"])

    print("\nDone! Your poem has been posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
