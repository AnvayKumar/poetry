#!/usr/bin/env python3
# The Thoughts Within - Daily Promotional Post
# Real photo backgrounds from Unsplash + authentic copy from Anvay's story

import os
import glob
import random
import base64
import time
import requests
import tempfile
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from io import BytesIO

# ============================================================
# CONFIGURATION
# ============================================================
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "17841426948301170")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")

BLOG_URL = "https://anvaykumar.wixsite.com/thethoughtswithin/blog"
IMG_WIDTH = 1080
IMG_HEIGHT = 1080

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #hindiwriters #blogpost #kavitapremi"

# ============================================================
# PHOTO SEARCH THEMES
# Each tuple: (unsplash search term, mood label)
# Curated to match the blog's aesthetic — calm, reflective, real moments
# ============================================================
PHOTO_THEMES = [
    ("tea cup notebook morning", "morning"),
    ("pen journal window rain", "rain"),
    ("notebook coffee rustic wood", "coffee"),
    ("writing desk lamp evening", "evening"),
    ("nature path solitude calm", "nature"),
    ("busy street people blur", "city"),
    ("autumn leaves bench park", "autumn"),
    ("hands writing paper pen", "writing"),
    ("window seat book rain", "window"),
    ("candle notebook night", "night"),
    ("old book pages poetry", "books"),
    ("quiet cafe journal morning", "cafe"),
]

# ============================================================
# AUTHENTIC COPY — derived from Anvay's actual story
# Hindi lines that reflect WHY he writes, not generic filler
# Each entry: (hindi_line, english_caption_for_instagram)
# ============================================================
COPY_PAIRS = [
    (
        "शोर में भी\nएक आवाज़ थी मेरी।",
        "I began writing to find calm in the noise.\n\nMaybe you'll find yours here too. 🔗 Link in bio"
    ),
    (
        "कुछ एहसास\nसिर्फ कविता समझती है।",
        "Some feelings are too big for words — and just right for poetry.\n\nRead more at the link in bio. ✍️"
    ),
    (
        "रुकना भी\nज़रूरी होता है।",
        "In a world moving too fast, this is your pause.\n\nद Thoughts Within — link in bio 🌿"
    ),
    (
        "बिखरे ख़यालों को\nयहाँ घर मिला।",
        "Scattered thoughts. Quiet reflections. A place to slow down.\n\nJoin us — link in bio 📖"
    ),
    (
        "अनकहा भी\nकहीं लिखा होता है।",
        "What you couldn't say out loud — it's written here.\n\nFollow @the.thoughtswithin 🖊️"
    ),
    (
        "तुम्हारे जज़्बात भी\nइन्हीं शब्दों में हैं।",
        "These words carry feelings you might recognize too — calm, hope, fear, meaning.\n\nLink in bio 🌸"
    ),
    (
        "ये जगह\nसबकी है।",
        "This space belongs to all of us who find comfort in words.\n\nFollow for more ✨"
    ),
    (
        "सवालों के साथ\nबैठना सीखा।",
        "I learned it's okay to be uncertain. Poetry taught me that.\n\nRead more — link in bio 🌿"
    ),
    (
        "छोटे लम्हों में\nबड़े मतलब छुपे हैं।",
        "Simple moments can hold meaning — if you pause long enough to notice.\n\nद Thoughts Within 📖"
    ),
    (
        "जो तुम सोचते हो,\nवो हम लिखते हैं।",
        "Started as scattered thoughts scribbled at unexpected times.\n\nNow shared for the connection that comes from noticing together. 🔗 Link in bio"
    ),
]


# ============================================================
# FETCH PHOTO FROM UNSPLASH (no API key needed)
# ============================================================
def fetch_unsplash_photo(search_term):
    """Fetch a random photo from Unsplash using source.unsplash.com"""
    # Format search term for URL
    query = search_term.replace(" ", ",")
    url = f"https://source.unsplash.com/{IMG_WIDTH}x{IMG_HEIGHT}/?{query}"

    print(f"Fetching photo: {url}")
    try:
        response = requests.get(url, timeout=20, allow_redirects=True)
        if response.status_code == 200 and len(response.content) > 10000:
            img = Image.open(BytesIO(response.content)).convert("RGB")
            img = img.resize((IMG_WIDTH, IMG_HEIGHT), Image.LANCZOS)
            print(f"Photo fetched: {img.size}")
            return img
        else:
            print(f"Photo fetch failed: status {response.status_code}, size {len(response.content)}")
            return None
    except Exception as e:
        print(f"Photo fetch error: {e}")
        return None


def create_darkened_overlay(img):
    """Add a semi-transparent dark overlay so text is readable over photos."""
    overlay = Image.new("RGBA", (IMG_WIDTH, IMG_HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Gradient overlay — darker at top and bottom, lighter in middle
    for y in range(IMG_HEIGHT):
        if y < IMG_HEIGHT * 0.35:
            # Top: moderate dark
            alpha = int(160 * (1 - y / (IMG_HEIGHT * 0.35)) + 100)
        elif y > IMG_HEIGHT * 0.65:
            # Bottom: darker
            alpha = int(180 * ((y - IMG_HEIGHT * 0.65) / (IMG_HEIGHT * 0.35)) + 80)
        else:
            # Middle: lightest — photo shows through more
            alpha = 80
        alpha = min(200, max(60, alpha))
        draw.line([(0, y), (IMG_WIDTH, y)], fill=(0, 0, 0, alpha))

    img_rgba = img.convert("RGBA")
    result = Image.alpha_composite(img_rgba, overlay)
    return result.convert("RGB")


def find_hindi_font():
    import subprocess
    try:
        result = subprocess.run(
            ["fc-list", ":lang=hi", "--format=%{file}\n"],
            capture_output=True, text=True
        )
        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        # Prefer bold for main copy on photos
        bold = [p for p in paths if "Bold" in p and "Devanagari" in p and "Condensed" not in p]
        regular = [p for p in paths if "Regular" in p and "Devanagari" in p and "Condensed" not in p]
        if bold:
            return bold[0], regular[0] if regular else bold[0]
        if regular:
            return regular[0], regular[0]
    except Exception as e:
        print(f"fc-list error: {e}")

    fallback = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf"
    bold_fallback = "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Bold.ttf"
    bold_path = bold_fallback if os.path.exists(bold_fallback) else fallback
    reg_path = fallback if os.path.exists(fallback) else bold_path
    return bold_path, reg_path


def find_latin_font():
    paths = [
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


# ============================================================
# CREATE PROMO IMAGE
# ============================================================
def create_promo_image(hindi_copy, output_path):
    print("Creating promo image...")

    # Pick a random photo theme
    theme, mood = random.choice(PHOTO_THEMES)
    print(f"Theme: {theme} ({mood})")

    # Fetch photo
    photo = fetch_unsplash_photo(theme)

    if photo:
        img = create_darkened_overlay(photo)
    else:
        # Fallback: beautiful gradient if photo fails
        print("Using gradient fallback")
        img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT), (30, 25, 40))
        draw_fallback = ImageDraw.Draw(img)
        for y in range(IMG_HEIGHT):
            t = y / IMG_HEIGHT
            r = int(30 + 20 * t)
            g = int(25 + 15 * t)
            b = int(40 + 30 * t)
            draw_fallback.line([(0, y), (IMG_WIDTH, y)], fill=(r, g, b))

    draw = ImageDraw.Draw(img)
    hindi_bold, hindi_reg = find_hindi_font()
    latin_font_path = find_latin_font()

    # Fonts
    font_copy = ImageFont.truetype(hindi_bold, 72)
    font_brand_h = ImageFont.truetype(hindi_reg, 30)
    font_brand_l = ImageFont.truetype(latin_font_path, 30) if latin_font_path else font_brand_h
    font_url = ImageFont.truetype(latin_font_path, 22) if latin_font_path else font_brand_h

    TEXT_WHITE = (255, 255, 255)
    TEXT_OFF = (220, 215, 205)
    TEXT_DIM = (170, 165, 155)

    cx = IMG_WIDTH // 2
    border = 55

    # Subtle border
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border],
                   outline=(255, 255, 255, 40), width=1)

    # ── MAIN HINDI COPY (vertically centred) ──
    lines = [l.strip() for l in hindi_copy.split("\n") if l.strip()]
    line_height = int(72 * 1.85)
    total_h = len(lines) * line_height
    start_y = (IMG_HEIGHT - total_h) // 2 - 30

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_copy)
        w = bbox[2] - bbox[0]
        x = (cx - w // 2)
        # Soft shadow for readability
        draw.text((x + 3, y + 3), line, font=font_copy, fill=(0, 0, 0, 120))
        draw.text((x, y), line, font=font_copy, fill=TEXT_WHITE)

    # ── BLOG URL below copy ──
    url_text = "anvaykumar.wixsite.com/thethoughtswithin"
    url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
    url_w = url_bbox[2] - url_bbox[0]
    url_y = start_y + total_h + 40
    draw.text(((IMG_WIDTH - url_w) // 2, url_y), url_text, font=font_url, fill=TEXT_DIM)

    # ── DIVIDER above brand ──
    div_y = IMG_HEIGHT - border - 90
    draw.line([(cx - 100, div_y), (cx + 100, div_y)], fill=(255, 255, 255, 80), width=1)
    draw.ellipse([(cx - 3, div_y - 3), (cx + 3, div_y + 3)], fill=TEXT_DIM)

    # ── BRAND: "द Thoughts Within" ──
    hindi_part = "द "
    latin_part = "Thoughts Within"
    h_bbox = draw.textbbox((0, 0), hindi_part, font=font_brand_h)
    l_bbox = draw.textbbox((0, 0), latin_part, font=font_brand_l)
    total_brand_w = (h_bbox[2] - h_bbox[0]) + (l_bbox[2] - l_bbox[0])
    brand_x = (IMG_WIDTH - total_brand_w) // 2
    brand_y = div_y + 18
    draw.text((brand_x, brand_y), hindi_part, font=font_brand_h, fill=TEXT_OFF)
    draw.text((brand_x + (h_bbox[2] - h_bbox[0]), brand_y), latin_part, font=font_brand_l, fill=TEXT_OFF)

    img.save(output_path, "JPEG", quality=95)
    print(f"Promo image saved: {output_path}")
    return output_path


# ============================================================
# UPLOAD AND POST
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
    raise Exception(f"Upload failed: {result}")


def post_to_instagram(image_url, caption):
    print("Posting to Instagram...")
    create_url = f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media"
    result = requests.post(create_url, data={
        "image_url": image_url,
        "caption": caption,
        "access_token": PAGE_ACCESS_TOKEN
    }).json()

    if "id" not in result:
        raise Exception(f"Failed to create container: {result}")

    container_id = result["id"]
    print(f"Container created: {container_id}")
    print("Waiting 20 seconds...")
    time.sleep(20)

    status = requests.get(
        f"https://graph.facebook.com/v18.0/{container_id}?fields=status_code&access_token={PAGE_ACCESS_TOKEN}"
    ).json()
    print(f"Status: {status.get('status_code')}")

    result = requests.post(
        f"https://graph.facebook.com/v18.0/{INSTAGRAM_BUSINESS_ACCOUNT_ID}/media_publish",
        data={"creation_id": container_id, "access_token": PAGE_ACCESS_TOKEN}
    ).json()

    if "id" not in result:
        raise Exception(f"Failed to publish: {result}")

    print(f"Posted! ID: {result['id']}")
    return result["id"]


# ============================================================
# MAIN
# ============================================================
def main():
    print("Starting promo post...\n")

    hindi_copy, english_caption = random.choice(COPY_PAIRS)

    caption = (
        f"{english_caption}\n\n"
        f"📖 {BLOG_URL}\n\n"
        f"{HASHTAGS}"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "promo.jpg")
        create_promo_image(hindi_copy, image_path)
        image_url = upload_image(image_path)
        post_to_instagram(image_url, caption)

    print("\nDone! Promo posted to @the.thoughtswithin")


if __name__ == "__main__":
    main()
