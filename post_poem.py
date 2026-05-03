#!/usr/bin/env python3
# The Thoughts Within - Automated Instagram Poetry Poster
# Fetches a random poem from your Wix blog, picks a random stanza,
# creates a beautiful image + video with random music, posts to @the.thoughtswithin

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
BLOG_URL = "https://anvaykumar.wixsite.com/thethoughtswithin/blog"
MUSIC_FOLDER = "music"  # Folder containing your MP3 files

IMG_WIDTH = 1080
IMG_HEIGHT = 1080
BACKGROUND_COLORS = [
    "#1a1a2e",  # Deep navy
    "#16213e",  # Dark blue
    "#0f3460",  # Royal blue
    "#1b1b2f",  # Dark purple
    "#2c2c54",  # Purple
    "#191919",  # Near black
]

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #poetrylovers #hindiwriters #dil"


# ============================================================
# STEP 1: Fetch poems from Wix blog
# ============================================================
def fetch_blog_posts():
    print("Fetching poems from blog...")

    try:
        feed = feedparser.parse(BLOG_RSS_URL)
        if feed.entries:
            print(f"Found {len(feed.entries)} poems via RSS")
            return feed.entries
    except Exception as e:
        print(f"RSS failed: {e}")

    print("Trying direct scrape...")
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(BLOG_URL, headers=headers, timeout=15)
    soup = BeautifulSoup(response.text, "html.parser")

    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/post/" in href:
            full_url = href if href.startswith("http") else f"https://anvaykumar.wixsite.com{href}"
            if full_url not in links:
                links.append(full_url)

    print(f"Found {len(links)} poem links via scraping")
    return [{"link": url, "title": url.split("/post/")[-1]} for url in links]


def fetch_poem_content(post):
    url = post.get("link") or post.get("url", "")
    if not url:
        return None

    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.text, "html.parser")

        for selector in ["div.post-content", "div[data-hook='post-description']", "article", "main"]:
            content = soup.select_one(selector)
            if content:
                text = content.get_text(separator="\n").strip()
                if len(text) > 100:
                    return text

        paragraphs = soup.find_all("p")
        text = "\n".join(p.get_text() for p in paragraphs if p.get_text().strip())
        return text if len(text) > 50 else None

    except Exception as e:
        print(f"Error fetching poem: {e}")
        return None


# ============================================================
# STEP 2: Pick a random stanza
# ============================================================
def pick_random_stanza(poem_text, poem_title):
    print("Picking a random stanza...")

    stanzas = [s.strip() for s in poem_text.split("\n\n") if s.strip()]
    good_stanzas = [s for s in stanzas if len(s.split("\n")) >= 2 and len(s) < 300]

    if not good_stanzas:
        good_stanzas = stanzas

    stanza = random.choice(good_stanzas)
    print(f"Selected stanza: {stanza[:60]}...")

    caption = f"A verse from '{poem_title}'\n\nRead the full poem at the link in bio.\n\n{HASHTAGS}"
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

    # Load fonts — tries Windows first, then Linux (for GitHub Actions)
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

    lines = []
    for line in stanza_text.split("\n"):
        if line.strip():
            wrapped = textwrap.wrap(line.strip(), width=26)
            lines.extend(wrapped)
        else:
            lines.append("")

    line_height = 64
    total_text_height = len(lines) * line_height
    start_y = (IMG_HEIGHT - total_text_height) // 2 - 40

    draw.text((border + 30, start_y - 60), "\u201c", font=font_poem, fill="#ffffff33")

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        if line:
            bbox = draw.textbbox((0, 0), line, font=font_poem)
            text_width = bbox[2] - bbox[0]
            x = (IMG_WIDTH - text_width) // 2
            draw.text((x + 2, y + 2), line, font=font_poem, fill="#00000066")
            draw.text((x, y), line, font=font_poem, fill="#ffffff")

    draw.text((IMG_WIDTH - border - 60, start_y + total_text_height - 20), "\u201d", font=font_poem, fill="#ffffff33")

    title_display = f"— {poem_title[:40]}"
    bbox = draw.textbbox((0, 0), title_display, font=font_title)
    title_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - title_w) // 2, start_y + total_text_height + 20), title_display, font=font_title, fill="#ffffff88")

    brand = "@the.thoughtswithin"
    bbox = draw.textbbox((0, 0), brand, font=font_brand)
    brand_w = bbox[2] - bbox[0]
    draw.text(((IMG_WIDTH - brand_w) // 2, IMG_HEIGHT - border - 40), brand, font=font_brand, fill="#ffffff55")

    img.save(output_path, "JPEG", quality=95)
    print(f"Image saved: {output_path}")
    return output_path


# ============================================================
# STEP 4: Pick random music and create video
# ============================================================
def pick_random_music():
    music_files = glob.glob(os.path.join(MUSIC_FOLDER, "*.mp3"))
    if not music_files:
        print("No music files found in music/ folder. Will post image only.")
        return None
    chosen = random.choice(music_files)
    print(f"Selected music: {os.path.basename(chosen)}")
    return chosen


def create_video(image_path, music_path, output_path, duration=30):
    print("Creating video with music...")
    try:
        cmd = [
            "ffmpeg", "-y",
            "-loop", "1",
            "-i", image_path,
            "-i", music_path,
            "-c:v", "libx264",
            "-tune", "stillimage",
            "-c:a", "aac",
            "-b:a", "192k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration),
            "-vf", "scale=1080:1080",
            output_path
        ]
        subprocess.run(cmd, check=True, capture_output=True)
        print(f"Video created: {output_path}")
        return output_path
    except Exception as e:
        print(f"Video creation failed: {e}. Will post image instead.")
        return None


# ============================================================
# STEP 5: Upload and post to Instagram
# ============================================================
def upload_image(image_path):
    print("Uploading image to hosting...")

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

    # 1. Fetch posts
    posts = fetch_blog_posts()
    if not posts:
        print("No posts found!")
        return

    # 2. Pick random post and fetch content
    poem_text = None
    selected_post = None
    for _ in range(5):
        post = random.choice(posts)
        print(f"Trying: {post.get('title', 'Unknown')}")
        poem_text = fetch_poem_content(post)
        if poem_text and len(poem_text) > 100:
            selected_post = post
            break

    if not poem_text:
        print("Could not fetch poem content")
        return

    poem_title = selected_post.get("title", "The Thoughts Within")
    poem_title = poem_title.replace("-", " ").strip()

    # 3. Pick random stanza
    stanza_data = pick_random_stanza(poem_text, poem_title)

    # 4. Create image, optionally add music as video
    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "poem.jpg")
        create_poem_image(stanza_data["stanza"], poem_title, image_path)

        # Try to create video with random music
        music_path = pick_random_music()
        if music_path:
            video_path = os.path.join(tmpdir, "poem.mp4")
            create_video(image_path, music_path, video_path)
            # Note: video posting via API requires Reels endpoint (more complex)
            # For now we post the image; video support can be added later
            print("Note: Posting as image. Video/Reels posting can be enabled later.")

        # 5. Upload image and post
        image_url = upload_image(image_path)
        post_to_instagram(image_url, stanza_data["caption"])

    print("\nDone! Your poem has been posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
