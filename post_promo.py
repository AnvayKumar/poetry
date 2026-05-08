#!/usr/bin/env python3
# The Thoughts Within - Daily Promotional Post Generator
# Creates a visually compelling promo post for the poetry blog
# Posted daily to @the.thoughtswithin

import os
import glob
import random
import base64
import time
import requests
import textwrap
import tempfile
from PIL import Image, ImageDraw, ImageFont

# ============================================================
# CONFIGURATION
# ============================================================
INSTAGRAM_BUSINESS_ACCOUNT_ID = os.environ.get("IG_ACCOUNT_ID", "17841426948301170")
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
IMGBB_API_KEY = os.environ.get("IMGBB_API_KEY", "")

BLOG_URL = "https://anvaykumar.wixsite.com/thethoughtswithin/blog"
MUSIC_FOLDER = "music"
IMG_WIDTH = 1080
IMG_HEIGHT = 1080

# Compelling Hindi copy lines (max ~10 words each), all blog-relevant
HINDI_COPY_LINES = [
    "जो अनकहा रह गया,\nवो यहाँ लिखा है।",
    "दिल की बात,\nशब्दों में पिरोई है।",
    "हर एहसास को\nआवाज़ मिली है यहाँ।",
    "ज़िंदगी के रंग,\nकविता में ढले हैं।",
    "जो सोचते हो तुम,\nवो लिखते हैं हम।",
    "कुछ बातें सिर्फ\nकविता कह सकती है।",
    "अपने जज़्बातों को\nयहाँ पहचानो।",
    "शब्दों का सफ़र,\nदिल तक पहुँचता है।",
    "हर कविता एक\nनई दुनिया है।",
    "तुम्हारी कहानी भी\nइन्हीं शब्दों में है।",
]

CTA_LINES = [
    "पूरा ब्लॉग पढ़ें — link in bio 🔗",
    "Follow करें और जुड़ें हमारे सफ़र से 🌿",
    "Link in bio — और भी कविताएँ पढ़ें ✨",
    "Follow @the.thoughtswithin 🖊️",
    "हमें follow करें, कविता से जुड़े रहें 🌸",
]

HASHTAGS = "#hindi #hindikavita #hindishayari #poetry #poem #indianpoetry #thoughtswithin #shayari #kavita #hindipoetry #poetrycommunity #wordsmith #hindiwriters #blogpost #kavitapremi"

# Rich dark gradient themes for promo (different feel from poem posts)
PROMO_GRADIENTS = [
    ((20, 20, 40), (50, 30, 80), (80, 40, 100), (40, 20, 60)),      # Deep purple
    ((10, 30, 50), (20, 60, 90), (30, 80, 110), (15, 45, 70)),      # Midnight blue
    ((40, 20, 20), (80, 35, 35), (100, 50, 30), (60, 25, 20)),      # Deep red
    ((15, 40, 30), (30, 70, 55), (45, 90, 65), (20, 55, 40)),       # Forest green
    ((35, 25, 10), (70, 55, 20), (90, 70, 30), (55, 40, 15)),       # Dark gold
    ((20, 20, 20), (45, 40, 50), (60, 55, 65), (30, 28, 35)),       # Charcoal
]

TEXT_WHITE = (255, 255, 255)
TEXT_OFFWHITE = (230, 225, 215)
TEXT_DIM = (170, 160, 150)


def draw_gradient_background(img):
    stops = random.choice(PROMO_GRADIENTS)
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


def find_hindi_font():
    import subprocess
    try:
        result = subprocess.run(
            ["fc-list", ":lang=hi", "--format=%{file}\n"],
            capture_output=True, text=True
        )
        paths = [p.strip() for p in result.stdout.strip().splitlines() if p.strip()]
        if paths:
            return paths[0]
    except:
        pass
    fallback = [
        "/usr/share/fonts/truetype/noto/NotoSansDevanagari-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSerifDevanagari-Regular.ttf",
        "C:/Windows/Fonts/mangal.ttf",
    ]
    for p in fallback:
        if os.path.exists(p):
            return p
    return None


def find_latin_font():
    paths = [
        "/usr/share/fonts/truetype/lato/Lato-Regular.ttf",
        "/usr/share/fonts/truetype/lato/Lato-Light.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "C:/Windows/Fonts/arial.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return p
    return None


def create_promo_image(hindi_copy, output_path):
    print("Creating promo image...")

    img = Image.new("RGB", (IMG_WIDTH, IMG_HEIGHT))
    draw_gradient_background(img)
    draw = ImageDraw.Draw(img)

    hindi_font = find_hindi_font()
    latin_font = find_latin_font()

    if not hindi_font:
        print("No Hindi font found!")
        return None

    border = 55

    # Subtle border
    draw.rectangle([border, border, IMG_WIDTH - border, IMG_HEIGHT - border],
                   outline=(255, 255, 255, 30), width=1)

    # Decorative top accent line
    cx = IMG_WIDTH // 2
    draw.line([(cx - 80, border + 40), (cx + 80, border + 40)], fill=(255, 255, 255, 60), width=1)
    draw.ellipse([(cx - 4, border + 36), (cx + 4, border + 44)], fill=TEXT_DIM)

    # ── MAIN HINDI COPY (centre of image) ──
    font_copy = ImageFont.truetype(hindi_font, 68)
    lines = [l.strip() for l in hindi_copy.split("\n") if l.strip()]
    line_height = int(68 * 1.9)
    total_h = len(lines) * line_height
    start_y = (IMG_HEIGHT - total_h) // 2 - 40

    for i, line in enumerate(lines):
        y = start_y + i * line_height
        bbox = draw.textbbox((0, 0), line, font=font_copy)
        w = bbox[2] - bbox[0]
        x = (IMG_WIDTH - w) // 2
        # Subtle glow effect
        draw.text((x + 2, y + 2), line, font=font_copy, fill=(0, 0, 0, 80))
        draw.text((x, y), line, font=font_copy, fill=TEXT_WHITE)

    # ── BLOG URL ──
    font_url = ImageFont.truetype(latin_font, 26) if latin_font else ImageFont.truetype(hindi_font, 26)
    url_text = "anvaykumar.wixsite.com/thethoughtswithin"
    url_bbox = draw.textbbox((0, 0), url_text, font=font_url)
    url_w = url_bbox[2] - url_bbox[0]
    url_y = start_y + total_h + 50
    draw.text(((IMG_WIDTH - url_w) // 2, url_y), url_text, font=font_url, fill=TEXT_DIM)

    # Decorative bottom accent line
    div_y = IMG_HEIGHT - border - 90
    draw.line([(cx - 80, div_y), (cx + 80, div_y)], fill=(255, 255, 255, 40), width=1)
    draw.ellipse([(cx - 4, div_y - 3), (cx + 4, div_y + 3)], fill=TEXT_DIM)

    # ── BRAND at bottom ──
    font_brand_h = ImageFont.truetype(hindi_font, 28)
    font_brand_l = ImageFont.truetype(latin_font, 28) if latin_font else font_brand_h

    hindi_part = "द "
    latin_part = "Thoughts Within"
    h_bbox = draw.textbbox((0, 0), hindi_part, font=font_brand_h)
    l_bbox = draw.textbbox((0, 0), latin_part, font=font_brand_l)
    total_brand_w = (h_bbox[2] - h_bbox[0]) + (l_bbox[2] - l_bbox[0])
    brand_x = (IMG_WIDTH - total_brand_w) // 2
    brand_y = div_y + 18
    draw.text((brand_x, brand_y), hindi_part, font=font_brand_h, fill=TEXT_OFFWHITE)
    draw.text((brand_x + (h_bbox[2] - h_bbox[0]), brand_y), latin_part, font=font_brand_l, fill=TEXT_OFFWHITE)

    img.save(output_path, "JPEG", quality=95)
    print(f"Promo image saved: {output_path}")
    return output_path


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
    print("Waiting 20 seconds...")
    time.sleep(20)

    status = requests.get(
        f"https://graph.facebook.com/v18.0/{container_id}?fields=status_code&access_token={PAGE_ACCESS_TOKEN}"
    ).json()
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


def main():
    print("Starting promo post...\n")

    # Pick random Hindi copy and CTA
    hindi_copy = random.choice(HINDI_COPY_LINES)
    cta = random.choice(CTA_LINES)

    # Build caption
    caption = (
        f"{hindi_copy}\n\n"
        f"📖 पूरा ब्लॉग पढ़ें:\n{BLOG_URL}\n\n"
        f"{cta}\n\n"
        f"{HASHTAGS}"
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        image_path = os.path.join(tmpdir, "promo.jpg")
        create_promo_image(hindi_copy, image_path)
        image_url = upload_image(image_path)
        post_to_instagram(image_url, caption)

    print("\nDone! Promo post published to @the.thoughtswithin")


if __name__ == "__main__":
    main()
