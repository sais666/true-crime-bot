"""
Thumbnail generator — Option B (Pexels real photo) with Option A (Gemini AI) fallback.
Produces a 1280x720 JPEG matching true crime channel aesthetics.
"""
import os, io, json, random, requests
import google.generativeai as genai
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

W, H = 1280, 720
PEXELS_PHOTO_API = "https://api.pexels.com/v1/search"

# Dark atmospheric photo keywords mapped to script content
PHOTO_KEYWORDS = [
    "dark foggy forest night",
    "abandoned house night eerie",
    "dark rainy city street night",
    "misty road night atmospheric",
    "dark alley night urban",
    "empty road night fog",
    "dark woods mysterious",
    "old abandoned building night",
    "night cemetery fog",
    "dark river night mist",
]


# ── OPTION B: PEXELS REAL PHOTO BACKGROUND ────────────────────
def fetch_pexels_photo(keyword: str) -> Image.Image | None:
    try:
        resp = requests.get(
            PEXELS_PHOTO_API,
            headers={"Authorization": os.environ["PEXELS_API_KEY"]},
            params={"query": keyword, "per_page": 5, "orientation": "landscape"},
            timeout=15,
        )
        resp.raise_for_status()
        photos = resp.json().get("photos", [])
        if not photos: return None
        photo = random.choice(photos)
        img_url = photo["src"].get("large2x") or photo["src"]["large"]
        img_resp = requests.get(img_url, timeout=30)
        img_resp.raise_for_status()
        return Image.open(io.BytesIO(img_resp.content)).convert("RGB")
    except Exception as e:
        print(f"      Pexels fetch failed ({keyword}): {e}")
        return None


def get_background_photo(script_text: str) -> Image.Image | None:
    """Try multiple dark atmospheric keywords until one returns a photo."""
    keywords = PHOTO_KEYWORDS.copy()
    random.shuffle(keywords)
    # Try topic-relevant keywords first
    lower = script_text.lower()
    priority = []
    if any(w in lower for w in ["forest","woods","trail","hike","trees"]): priority.insert(0,"dark foggy forest night")
    if any(w in lower for w in ["city","street","urban","downtown"]): priority.insert(0,"dark rainy city street night")
    if any(w in lower for w in ["house","home","building","room"]): priority.insert(0,"abandoned house night eerie")
    if any(w in lower for w in ["road","highway","car","drive"]): priority.insert(0,"misty road night atmospheric")
    for kw in (priority + keywords):
        img = fetch_pexels_photo(kw)
        if img: return img
    return None


# ── OPTION A: GEMINI AI GENERATED BACKGROUND (fallback) ───────
def generate_ai_background(topic: str) -> Image.Image | None:
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel("gemini-2.0-flash-exp-image-generation")
        prompt = (
            f"Cinematic dark atmospheric photograph for a true crime YouTube thumbnail. "
            f"Scene: {topic[:80]}. "
            "Style: moody noir, deep shadows, foggy night, photorealistic, "
            "cinematic colour grade, dark teal and black palette, "
            "professional photography lighting. No text, no people, no faces. "
            "16:9 landscape composition. Ultra high quality."
        )
        response = model.generate_content(
            prompt,
            generation_config={"response_modalities": ["image"]},
        )
        for part in response.candidates[0].content.parts:
            if hasattr(part, "inline_data") and part.inline_data:
                return Image.open(io.BytesIO(part.inline_data.data)).convert("RGB")
    except Exception as e:
        print(f"      Gemini image generation failed: {e}")
    return None


# ── PHOTO PROCESSING: cinematic grade ─────────────────────────
def grade_photo(img: Image.Image) -> Image.Image:
    """Apply cinematic dark colour grade to match true crime aesthetic."""
    img = img.resize((W, H), Image.LANCZOS)

    # Darken significantly
    enhancer = ImageEnhance.Brightness(img)
    img = enhancer.enhance(0.38)

    # Desaturate slightly — cold, grim feel
    enhancer = ImageEnhance.Color(img)
    img = enhancer.enhance(0.65)

    # Contrast boost
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(1.3)

    # Apply teal-black colour cast via overlay
    draw_overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(draw_overlay)

    # Dark vignette — heavy
    for i in range(60):
        alpha = int((i / 60) ** 1.8 * 220)
        margin = i * 9
        d.rectangle([margin, margin, W-margin, H-margin],
                    outline=(0,0,0,alpha), width=9)

    # Teal tint overlay
    teal_layer = Image.new("RGBA", (W, H), (0, 30, 25, 40))
    img = img.convert("RGBA")
    img = Image.alpha_composite(img, teal_layer)
    img = Image.alpha_composite(img, draw_overlay)
    return img.convert("RGB")


# ── TYPOGRAPHY ─────────────────────────────────────────────────
def _font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-B.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _font_reg(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    for p in candidates:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(ctx, text, font, max_w, max_lines):
    words = text.split()
    lines, cur = [], ""
    for w in words:
        test = (cur + " " + w).strip()
        bbox = ctx.textbbox((0,0), test, font=font)
        if bbox[2] <= max_w: cur = test
        else:
            if cur: lines.append(cur)
            cur = w
            if len(lines) >= max_lines-1:
                lines.append(cur); cur = ""; break
    if cur and len(lines) < max_lines: lines.append(cur)
    return lines[:max_lines]


def _shadow_text(draw, text, x, y, font, fill, shadow_col=(0,0,0), blur_r=3, offset=3):
    # Shadow pass
    draw.text((x+offset, y+offset), text, font=font, fill=shadow_col)
    # Main text
    draw.text((x, y), text, font=font, fill=fill)


def add_typography(img: Image.Image, title: str, channel: str = "The Archives") -> Image.Image:
    draw = ImageDraw.Draw(img)
    pad = int(W * 0.055)
    max_text_w = W - pad * 2 - 20

    # ── Channel badge — top left ───────────────────────────────
    badge_font = _font_reg(22)
    badge_h = int(H * 0.068)
    badge_w = int(W * 0.26)
    # Dark semi-transparent pill
    badge_layer = Image.new("RGBA", img.size, (0,0,0,0))
    bd = ImageDraw.Draw(badge_layer)
    bd.rounded_rectangle([pad, int(H*.055), pad+badge_w, int(H*.055)+badge_h], radius=4, fill=(0,0,0,165))
    # Red left bar on badge
    bd.rectangle([pad, int(H*.055), pad+4, int(H*.055)+badge_h], fill=(190,15,15,240))
    img = Image.alpha_composite(img.convert("RGBA"), badge_layer).convert("RGB")
    draw = ImageDraw.Draw(img)
    draw.text((pad+14, int(H*.055) + badge_h//2 - 11), channel, font=badge_font, fill=(230,220,220))

    # ── Main title ─────────────────────────────────────────────
    title_up = title.upper()
    # Pick font size based on title length
    for fs in [96, 82, 70, 60]:
        f = _font(fs)
        lines = _wrap(draw, title_up, f, max_text_w, 3)
        if lines: break

    lh = int(fs * 1.18)
    total_title_h = len(lines) * lh
    # Position: lower 40% of frame
    start_y = int(H * 0.48)

    for i, line in enumerate(lines):
        x = pad + 14
        y = start_y + i * lh
        # Thick shadow for legibility
        for dx, dy in [(4,4),(3,3),(5,5),(-1,4)]:
            draw.text((x+dx, y+dy), line, font=f, fill=(0,0,0))
        # Red first word on first line only
        if i == 0:
            words_in_line = line.split()
            fw = words_in_line[0] if words_in_line else ""
            fw_bbox = draw.textbbox((x, y), fw + " ", font=f)
            fw_w = fw_bbox[2] - fw_bbox[0]
            draw.text((x, y), fw, font=f, fill=(220, 30, 30))
            rest = " ".join(words_in_line[1:])
            if rest:
                draw.text((x + fw_w, y), rest, font=f, fill=(255, 255, 255))
        else:
            draw.text((x, y), line, font=f, fill=(255, 255, 255))

    # ── Thin red accent line above subtitle ───────────────────
    rule_y = start_y + total_title_h + int(fs * 0.15)
    draw.rectangle([pad+14, rule_y, pad+14+int(W*0.42), rule_y+2], fill=(180,20,20))

    # ── Subtitle / hook teaser ─────────────────────────────────
    sub_font = _font_reg(28)
    sub_y = rule_y + 10
    hook_words = title.split()[:7]
    sub_text = "Full case — watch now"
    sub_shadow = (0,0,0)
    for dx,dy in [(2,2),(1,2)]:
        draw.text((pad+14+dx, sub_y+dy), sub_text, font=sub_font, fill=sub_shadow)
    draw.text((pad+14, sub_y), sub_text, font=sub_font, fill=(200,170,170))

    # ── UNSOLVED stamp — bottom right ─────────────────────────
    stamp_font = _font(26)
    stamp = "UNSOLVED"
    sb = draw.textbbox((0,0), stamp, font=stamp_font)
    sw = sb[2]-sb[0]
    sx = W - pad - sw
    sy = int(H * 0.91)
    draw.text((sx+2, sy+2), stamp, font=stamp_font, fill=(0,0,0))
    draw.text((sx, sy), stamp, font=stamp_font, fill=(180,20,20))

    return img


# ── MAIN ENTRY POINTS ──────────────────────────────────────────
def generate_thumbnail(title: str, script_text: str = "", output_path: str = "output/thumbnail.jpg") -> str:
    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else "output", exist_ok=True)

    print("      Fetching Pexels background photo...")
    bg = get_background_photo(script_text or title)

    if bg is None:
        print("      Pexels failed — trying Gemini AI background...")
        bg = generate_ai_background(title)

    if bg is None:
        print("      Both sources failed — using procedural dark background")
        bg = Image.new("RGB", (W, H), (8, 6, 12))

    print("      Applying cinematic colour grade...")
    bg = grade_photo(bg)

    print("      Adding typography...")
    final = add_typography(bg, title)

    final.save(output_path, "JPEG", quality=92, optimize=True)
    size_kb = os.path.getsize(output_path) // 1024
    print(f"      Saved: {output_path} ({size_kb} KB)")
    return output_path


def upload_thumbnail(video_id: str, thumbnail_path: str, access_token: str) -> bool:
    url = "https://www.googleapis.com/upload/youtube/v3/thumbnails/set"
    with open(thumbnail_path, "rb") as f:
        resp = requests.post(
            url,
            headers={"Authorization": f"Bearer {access_token}", "Content-Type": "image/jpeg"},
            params={"videoId": video_id},
            data=f, timeout=60,
        )
    ok = resp.status_code == 200
    print(f"      Thumbnail upload {'OK' if ok else f'FAILED {resp.status_code}'}: {video_id}")
    return ok
