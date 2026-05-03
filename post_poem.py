#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster

import os
import glob
import random
import base64
import subprocess
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

# Navigation/UI text to filter out
JUNK_PHRASES = [
    "All Posts", "My Poems", "The Thought Circle", "Search",
    "Recent Posts", "See All", "Subscribe", "Connect with me",
    "bottom of page", "top of page", "min read", "Updated:",
    "Tags:", "Name", "Email", "Join", "Submit", "© 20"
]


# ============================================================
# STEP 1: Fetch poems from RSS (content is embedded in RSS)
# ============================================================
def fetch_blog_posts():
    print("Fetching poems from RSS feed...")
    feed = feedparser.parse(BLOG_RSS_URL)
    if not feed.entries:
        raise Exception("Could not fetch RSS feed")
    print(f"Found {len(feed.entries)} poems")
    return feed.entries


def extract_poem_from_rss(entry):
    """Extract poem text from RSS entry content — this has the actual poem."""
    # RSS entries have content/summary with HTML
    content_html = ""
    if hasattr(entry, "content") and entry.content:
        content_html = entry.content[0].value
    elif hasattr(entry, "summary"):
        content_html = entry.summary

    if not content_html:
        return None

    # Parse HTML and extract text
    soup = BeautifulSoup(content_html, "html.parser")
    
    # Remove script and style tags
    for tag in soup(["script", "style"]):
        tag.decompose()

    # Get text line by line
    raw_text = soup.get_text(separator="\n")
    
    # Clean up lines
    lines = []
    for line in raw_text.split("\n"):
        line = line.strip()
        # Skip empty lines and junk navigation text
        if not line:
            lines.append("")
            continue
        if any(junk.lower() in line.lower() for junk in JUNK_PHRASES):
            continue
        if len(line) < 3:
            continue
        lines.append(line)

    # Remove consecutive blank lines
    cleaned = []
    prev_blank = False
    for line in lines:
        if line == "":
            if not prev_blank:
                cleaned.append("")
            prev_blank = True
        else:
            cleaned.append(line)
            prev_blank = False

    poem_text = "\n".join(cleaned).strip()
    return poem_text if len(poem_text) > 30 else None


# ============================================================
# STEP 2: Pick a random stanza
# ============================================================
def pick_random_stanza(poem_text, poem_title):
    print("Picking a random stanza...")

    # Split into stanzas by blank lines
    stanzas = [s.strip() for s in poem_text.split("\n\n") if s.strip()]

    # Filter: at least 2 lines, not too long, no junk
    good_stanzas = []
    for s in stanzas:
        lines = [l for l in s.split("\n") if l.strip()]
        if len(lines) >= 2 and len(s) < 400:
            # Make sure it doesn't contain junk
            if not any(junk.lower() in s.lower() for junk in JUNK_PHRASES):
                good_stanzas.append(s)

    if not good_stanzas:
        print("Warning: No good stanzas found, using full poem text")
        good_stanzas = stanzas if stanzas else [poem_text[:300]]

    stanza = random.choice(good_stanzas)
    print(f"Selected stanza ({len(stanza)} chars): {stanza[:80]}...")

    caption = f"'{poem_title}'\n\nRead the full poem at the link in bio.\n\n{HASHTAGS}"
    return {"stanza": stanza, "caption": caption}


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

    # Load fonts — Windows first, then Linux (GitHub Actions)
    try:
        font_poem = ImageFont.truetype("C:/Windows/Fonts/georgia.ttf", 44)
        font_title = ImageFont.truetype("C:/Windows/Fonts/georgiai.ttf", 28)
        font_brand = ImageFont.truetype("C:/Windows/Fonts/arial.ttf", 22)
    except:
        try:
            font_poem = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf", 44)
            font_title = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSerif-Oblique.ttf", 28)
            font_brand = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 22)
        except:
            font_poem = ImageFont.load_default()
            font_title = font_poem
            font_brand = font_poem

    # Wrap text into lines
    lines = []
    for line in stanza_text.split("\n"):
        if line.strip():
            wrapped = textwrap.wrap(line.strip(), width=24)
            lines.extend(wrapped if wrapped else [line.strip()])
        else:
            lines.append("")

    # Limit to max 10 lines so it fits
    lines = [l for l in lines if l][:10]

    line_height = 68
    total_text_height = len(lines) * line_height
    start_y = max(border + 80, (IMG_HEIGHT - total_text_height) // 2 - 40)

    # Opening quote
    draw.text((border + 30, start_y - 70), "\u201c", font=font_poem, fill="#ffffff33")

    # Draw poem lines
    for i, line in enumerate(lines):
        y = start_y + i * line_height
        if line:
            bbox = draw.textbbox((0, 0), line, font=font_poem)
            text_width = bbox[2] - bbox[0]
            x = (IMG_WIDTH - text_width) // 2
            # Shadow
            draw.text((x + 2, y + 2), line, font=font_poem, fill="#00000066")
            # Main text
            draw.text((x, y), line, font=font_poem, fill="#ffffff")

    # Closing quote
    end_y = start_y + total_text_height
    draw.text((IMG_WIDTH - border - 60, end_y - 20), "\u201d", font=font_poem, fill="#ffffff33")

    # Poem title
    title_display = f"— {poem_title[:35]}"
    bbox = draw.textbbox((0, 0), title_display, font=font_title)
    title_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - title_w) // 2, end_y + 20), title_display, font=font_title, fill="#ffffff88")

    # Brand at bottom
    brand = "@the.thoughtswithin"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    brand_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - brand_w) // 2, IMG_HEIGHT - border - 40), brand, font=font_brand, fill="#ffffff55")

    img.save(output_path, "JPEG", quality=95)
    print(f"Image saved: {output_path}")
    return output_path


# ============================================================
# STEP 4: Pick random music
# ============================================================
def pick_random_music():
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    if not music_files:
        print("No music files found.")
        return None
    chosen = random.choice(music_files)
    print(f"Selected music: {os.path.basename(chosen)}")
    return chosen


# ============================================================
# STEP 5: Upload image and post to Instagram
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

    # 1. Fetch all poems from RSS
    posts = fetch_blog_posts()

    # 2. Pick random poems until we get one with content
    poem_text = None
    selected_post = None
    random.shuffle(posts)

    for post in posts[:8]:  # Try up to 8 posts
        title = post.get("title", "Unknown")
        print(f"Trying: {title}")
        poem_text = extract_poem_from_rss(post)
        if poem_text and len(poem_text) > 50:
            selected_post = post
            print(f"Got poem content ({len(poem_text)} chars)")
            break
        else:
            print(f"No usable content found, trying next...")

    if not poem_text or not selected_post:
        raise Exception("Could not extract poem content from any post")

    poem_title = selected_post.get("title", "The Thoughts Within")

    # 3. Pick random stanza
    stanza_data = pick_random_stanza(poem_text, poem_title)

    # 4. Create image
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "poem.jpg")
        create_poem_image(stanza_data["stanza"], poem_title, image_path)

        # Pick random music (ready for future video support)
        pick_random_music()

        # 5. Upload and post
        image_url = upload_image(image_path)
        post_to_instagram(image_url, stanza_data["caption"])

    print("\nDone! Your poem has been posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
