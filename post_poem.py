#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster

import os
import re
import glob
import random
import base64
import time
import requests
import textwrap
import tempfile
import feedparser
from PIL import Image, ImageDraw, ImageFont
from bs4 import BeautifulSoup

# ============================================================
# CONFIGURATION
# ============================================================
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "17841426948301170")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")

BLOG_RSS_URL = "https://anvaykumar.wixsite.com/thethoughtswithin/blog-feed.xml"
MUSIC_FOLDER = "music"

IMG_WIDTH = 1080
IMG_HEIGHT = 1080
BACKGROUND_COLORS = [
    "#1a1a2e", "#16213e", "#0f3460", "#1b1b2f", "#2c2c54", "#191919",
]

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #poetrylovers #hindiwriters #dil"


# ============================================================
# HINDI DETECTION
# ============================================================
def is_predominantly_hindi(text):
    """Returns True only if the majority of characters are Devanagari."""
    total_alpha = sum(1 for c in text if c.isalpha())
    if total_alpha == 0:
        return False
    hindi_chars = sum(1 for c in text if '\u0900' <= c <= '\u097F')
    # Must be at least 60% Hindi characters
    return (hindi_chars / total_alpha) > 0.6


def extract_hindi_lines(text):
    """Extract only lines that are predominantly Hindi."""
    lines = text.split("\n")
    hindi_lines = []
    for line in lines:
        line = line.strip()
        if line and is_predominantly_hindi(line):
            hindi_lines.append(line)
    return hindi_lines


# ============================================================
# STEP 1: Fetch poems from RSS
# ============================================================
def fetch_posts_from_rss():
    print("Fetching from RSS feed...")
    feed = feedparser.parse(BLOG_RSS_URL)
    if feed.entries:
        print(f"Found {len(feed.entries)} posts in RSS")
        return feed.entries
    raise Exception("Could not fetch RSS feed")


def get_hindi_content_from_rss(entry):
    """Extract only predominantly Hindi lines from RSS entry."""
    content_html = ""
    if hasattr(entry, "content") and entry.content:
        content_html = entry.content[0].value
    elif hasattr(entry, "summary"):
        content_html = entry.summary

    if not content_html:
        return None

    soup = BeautifulSoup(content_html, "html.parser")
    for tag in soup(["script", "style"]):
        tag.decompose()

    raw_text = soup.get_text(separator="\n")
    hindi_lines = extract_hindi_lines(raw_text)

    if len(hindi_lines) < 4:  # Need at least 4 Hindi lines to be a real poem
        return None

    return "\n".join(hindi_lines)


# ============================================================
# STEP 2: Pick a random stanza
# ============================================================
def pick_random_stanza(hindi_text, poem_title):
    print("Picking a random stanza...")

    lines = [l.strip() for l in hindi_text.split("\n") if l.strip()]

    # Group into stanzas of 4 lines each (common for Hindi poetry)
    stanzas = []
    for i in range(0, len(lines), 4):
        chunk = lines[i:i+4]
        if len(chunk) >= 2:
            stanzas.append("\n".join(chunk))

    if not stanzas:
        stanzas = ["\n".join(lines[:4])]

    stanza = random.choice(stanzas)
    print(f"Selected stanza: {stanza[:80]}...")

    caption = f"'{poem_title}'\n\nRead the full poem at the link in bio.\n\n{HASHTAGS}"
    return {"stanza": stanza, "caption": caption}


# ============================================================
# STEP 3: Create image
# ============================================================
def create_poem_image(stanza_text, poem_title, output_path):
    print("Creating poem image...")

    bg_color = random.choice(BACKGROUND_COLORS)
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    border = 40
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border], outline="#ffffff22", width=1)
    draw.rectangle([border + 8, border + 8, IMG_WIDTH - border - 8, IMG_HEIGHT - border - 8], outline="#ffffff11", width=1)

    POEM_FONT_SIZE = 62
    TITLE_FONT_SIZE = 32
    BRAND_FONT_SIZE = 26

    font_poem = font_title = font_brand = None

    hindi_font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        "C:/Windows/Fonts/mangal.ttf",
        "C:/Windows/Fonts/aparajita.ttf",
    ]

    for font_path in hindi_font_paths:
        try:
            font_poem = ImageFont.truetype(font_path, POEM_FONT_SIZE)
            font_title = ImageFont.truetype(font_path, TITLE_FONT_SIZE)
            font_brand = ImageFont.truetype(font_path, BRAND_FONT_SIZE)
            print(f"Using font: {font_path}")
            break
        except:
            continue

    if not font_poem:
        font_poem = font_title = font_brand = ImageFont.load_default()
        print("Warning: Using default font — Hindi may not render correctly")

    # Split stanza into lines and wrap
    lines = []
    for line in stanza_text.split("\n"):
        if line.strip():
            wrapped = textwrap.wrap(line.strip(), width=16)
            lines.extend(wrapped if wrapped else [line.strip()])

    lines = [l for l in lines if l][:8]

    line_height = 88
    total_text_height = len(lines) * line_height
    start_y = max(border + 100, (IMG_HEIGHT - total_text_height) // 2 - 50)

    draw.text((border + 30, start_y - 80), "\u201c", font=font_poem, fill="#ffffff33")

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_poem)
        text_width = bbox[2] - bbox[0]
        x = (IMG_WIDTH - text_width) // 2
        draw.text((x + 2, y + 2), line, font=font_poem, fill="#00000066")
        draw.text((x, y), line, font=font_poem, fill="#ffffff")

    end_y = start_y + total_text_height
    draw.text((IMG_WIDTH - border - 70, end_y - 20), "\u201d", font=font_poem, fill="#ffffff33")

    title_display = f"— {poem_title[:28]}"
    bbox = draw.textbbox((0, 0), title_display, font=font_title)
    title_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - title_w) // 2, end_y + 28), title_display, font=font_title, fill="#ffffff88")

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

    # Wait for Instagram to process the image before publishing
    print("Waiting 15 seconds for Instagram to process image...")
    time.sleep(15)

    # Check container status before publishing
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

    posts = fetch_posts_from_rss()
    random.shuffle(posts)

    hindi_text = None
    selected_post = None

    for post in posts:
        title = post.get("title", "Unknown")
        print(f"Trying: {title}")
        content = get_hindi_content_from_rss(post)
        if content:
            hindi_text = content
            selected_post = post
            print(f"Found Hindi content ({len(hindi_text)} chars)")
            break
        else:
            print("No Hindi content, trying next...")

    if not hindi_text:
        raise Exception("Could not find Hindi poem content in RSS feed.")

    poem_title = selected_post.get("title", "The Thoughts Within")
    stanza_data = pick_random_stanza(hindi_text, poem_title)

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "poem.jpg")
        create_poem_image(stanza_data["stanza"], poem_title, image_path)
        pick_random_music()
        image_url = upload_image(image_path)
        post_to_instagram(image_url, stanza_data["caption"])

    print("\nDone! Your poem has been posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
