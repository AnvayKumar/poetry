#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster
# Uses Wix Blog API to get actual Hindi poem content

import os
import re
import glob
import random
import base64
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

# Your Wix site ID (from your blog URL)
WIX_SITE_ID = "dfc21335-d43c-4f38-9c2b-b6fc23da80cb"
WIX_API_URL = f"https://www.wixapis.com/blog/v3/posts?fieldsets=CONTENT_TEXT&paging.limit=100"

BLOG_RSS_URL = "https://anvaykumar.wixsite.com/thethoughtswithin/blog-feed.xml"
MUSIC_FOLDER = "music"

IMG_WIDTH = 1080
IMG_HEIGHT = 1080
BACKGROUND_COLORS = [
    "#1a1a2e", "#16213e", "#0f3460", "#1b1b2f", "#2c2c54", "#191919",
]

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #poetrylovers #hindiwriters #dil"


# ============================================================
# DETECT HINDI TEXT
# ============================================================
def is_hindi(text):
    """Check if text contains Hindi (Devanagari) characters."""
    return bool(re.search(r'[\u0900-\u097F]', text))


def extract_hindi_lines(text):
    """Extract only lines that contain Hindi characters."""
    lines = text.split("\n")
    hindi_lines = []
    for line in lines:
        line = line.strip()
        if line and is_hindi(line):
            hindi_lines.append(line)
    return hindi_lines


# ============================================================
# STEP 1: Fetch poems — try Wix API first, then RSS
# ============================================================
def fetch_posts_from_rss():
    """Fetch post list and content from RSS."""
    print("Fetching from RSS feed...")
    feed = feedparser.parse(BLOG_RSS_URL)
    if feed.entries:
        print(f"Found {len(feed.entries)} posts in RSS")
        return feed.entries
    return []


def get_post_content_from_rss(entry):
    """Get all text from RSS entry and extract Hindi lines."""
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

    if not hindi_lines:
        return None

    return "\n".join(hindi_lines)


# ============================================================
# STEP 2: Pick a random stanza from Hindi lines
# ============================================================
def pick_random_stanza(hindi_text, poem_title):
    print("Picking a random stanza from Hindi content...")

    # Group consecutive Hindi lines into stanzas
    lines = hindi_text.split("\n")
    stanzas = []
    current = []

    for line in lines:
        if line.strip():
            current.append(line.strip())
        else:
            if current:
                stanzas.append("\n".join(current))
                current = []
    if current:
        stanzas.append("\n".join(current))

    # Filter: at least 2 lines, not too long
    good_stanzas = [s for s in stanzas if len(s.split("\n")) >= 2 and len(s) < 400]

    if not good_stanzas:
        good_stanzas = stanzas if stanzas else [hindi_text[:300]]

    stanza = random.choice(good_stanzas)
    print(f"Selected stanza: {stanza[:80]}...")

    caption = f"'{poem_title}'\n\nRead the full poem at the link in bio.\n\n{HASHTAGS}"
    return {"stanza": stanza, "caption": caption}


# ============================================================
# STEP 3: Create beautiful image with larger font
# ============================================================
def create_poem_image(stanza_text, poem_title, output_path):
    print("Creating poem image...")

    bg_color = random.choice(BACKGROUND_COLORS)
    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), color=bg_color)
    draw = ImageDraw.Draw(img)

    border = 40
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border], outline="#ffffff22", width=1)
    draw.rectangle([border + 8, border + 8, IMG_WIDTH - border - 8, IMG_HEIGHT - border - 8], outline="#ffffff11", width=1)

    # Font size increased significantly — Hindi needs a Unicode-capable font
    POEM_FONT_SIZE = 58
    TITLE_FONT_SIZE = 32
    BRAND_FONT_SIZE = 26

    font_poem = None
    font_title = None
    font_brand = None

    # Try fonts that support Devanagari (Hindi)
    hindi_font_paths = [
        # Linux (GitHub Actions) — install via workflow
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/lohit-devanagari/Lohit-Devanagari.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerif-Regular.ttf",
        # Windows
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
        print("Warning: No Hindi font found, using default")
        font_poem = ImageFont.load_default()
        font_title = font_poem
        font_brand = font_poem

    # Wrap lines — shorter width for bigger font
    lines = []
    for line in stanza_text.split("\n"):
        if line.strip():
            # For Hindi, wrap at fewer characters since chars are wider
            wrapped = textwrap.wrap(line.strip(), width=18)
            lines.extend(wrapped if wrapped else [line.strip()])
        else:
            lines.append("")

    lines = [l for l in lines if l][:8]  # Max 8 lines

    line_height = 80
    total_text_height = len(lines) * line_height
    start_y = max(border + 100, (IMG_HEIGHT - total_text_height) // 2 - 40)

    # Opening quote
    draw.text((border + 30, start_y - 70), "\u201c", font=font_poem, fill="#ffffff33")

    # Draw poem lines
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        if line:
            bbox = draw.textbbox((0, 0), line, font=font_poem)
            text_width = bbox[2] - bbox[0]
            x = (IMG_WIDTH - text_width) // 2
            draw.text((x + 2, y + 2), line, font=font_poem, fill="#00000066")  # shadow
            draw.text((x, y), line, font=font_poem, fill="#ffffff")

    # Closing quote
    end_y = start_y + total_text_height
    draw.text((IMG_WIDTH - border - 70, end_y - 20), "\u201d", font=font_poem, fill="#ffffff33")

    # Poem title
    title_display = f"— {poem_title[:30]}"
    try:
        bbox = draw.textbbox((0, 0), title_display, font=font_title)
        title_w = bbox[2] - bbox[0]
        draw.text(((IMG_WIDTH - title_w) // 2, end_y + 25), title_display, font=font_title, fill="#ffffff88")
    except:
        pass

    # Brand at bottom
    brand = "@the.thoughtswithin"
    try:
        bbox = draw.textbbox((0, 0), brand, font=font_brand)
        brand_w = bbox[2] - bbox[0]
        draw.text(((IMG_WIDTH - brand_w) // 2, IMG_HEIGHT - border - 45), brand, font=font_brand, fill="#ffffff55")
    except:
        pass

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
    if not posts:
        raise Exception("Could not fetch any posts")

    # Shuffle and try posts until we find one with Hindi content
    random.shuffle(posts)
    hindi_text = None
    selected_post = None

    for post in posts[:10]:
        title = post.get("title", "Unknown")
        print(f"Trying: {title}")
        content = get_post_content_from_rss(post)
        if content and len(content) > 30:
            hindi_text = content
            selected_post = post
            print(f"Found Hindi content ({len(hindi_text)} chars)")
            break
        else:
            print("No Hindi content found, trying next...")

    if not hindi_text:
        raise Exception("Could not find Hindi content in any post. Check your RSS feed.")

    poem_title = selected_post.get("title", "The Thoughts Within")

    # Pick stanza and create image
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
