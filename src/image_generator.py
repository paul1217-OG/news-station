"""
image_generator.py v2 - 精緻化新聞卡片
"""
from __future__ import annotations
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Tuple
from PIL import Image, ImageDraw, ImageFont
import os

W, H = 1080, 1350

PALETTE = {
    "ink_900":    (8, 14, 32),
    "ink_800":    (16, 24, 50),
    "ink_700":    (24, 38, 75),
    "ink_600":    (40, 60, 110),
    "card":       (22, 32, 60),
    "card_alt":   (30, 42, 78),
    "stroke":     (60, 80, 130),
    "gold":       (245, 192, 56),
    "gold_dim":   (200, 160, 60),
    "white":      (250, 251, 254),
    "soft":       (180, 195, 220),
    "muted":      (130, 145, 175),
}

TAG_STYLE = {
    "台股":   {"bg": (220, 70, 80),  "fg": (255, 255, 255)},
    "美股":   {"bg": (60, 130, 220), "fg": (255, 255, 255)},
    "亞股":   {"bg": (250, 140, 50), "fg": (255, 255, 255)},
    "歐股":   {"bg": (140, 90, 200), "fg": (255, 255, 255)},
    "產業":   {"bg": (45, 175, 140), "fg": (255, 255, 255)},
    "宏觀":   {"bg": (200, 160, 70), "fg": (40, 40, 40)},
    "其他":   {"bg": (110, 120, 150),"fg": (255, 255, 255)},
}

EMOJI_FALLBACK = {
    "🔥": "▲", "📈": "↑", "📉": "↓", "💰": "$",
    "🇹🇼": "TW", "🇺🇸": "US", "🇪🇺": "EU", "🇯🇵": "JP", "🇰🇷": "KR",
    "🌏": "◐", "🏭": "⚙", "📊": "▤", "📰": "◳", "⭐": "★",
    "👉": "▶", "🤖": "☷", "ℹ️": "i",
}


def _find_font(size: int) -> ImageFont.FreeTypeFont:
    candidates = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc",
        "/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf",
        "/usr/share/fonts/truetype/droid/DroidSansFallback.ttf",
        "/System/Library/Fonts/PingFang.ttc",
        "C:\\Windows\\Fonts\\msyhbd.ttc",
        "C:\\Windows\\Fonts\\msjh.ttc",
    ]
    for p in candidates:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                continue
    return ImageFont.load_default()


def _safe_text(text: str) -> str:
    for k, v in EMOJI_FALLBACK.items():
        text = text.replace(k, v)
    return text


def _gradient_bg(w, h, c1, c2, c3=None):
    img = Image.new("RGB", (w, h), c1)
    px = img.load()
    if c3 is None:
        for y in range(h):
            r = y / h
            color = tuple(int(c1[i] * (1 - r) + c2[i] * r) for i in range(3))
            for x in range(w):
                px[x, y] = color
    else:
        mid = h // 2
        for y in range(h):
            if y < mid:
                r = y / mid
                color = tuple(int(c1[i] * (1 - r) + c2[i] * r) for i in range(3))
            else:
                r = (y - mid) / (h - mid)
                color = tuple(int(c2[i] * (1 - r) + c3[i] * r) for i in range(3))
            for x in range(w):
                px[x, y] = color
    return img


def _rounded_rect(draw, xy, radius, fill=None, outline=None, width=1):
    draw.rounded_rectangle(xy, radius=radius, fill=fill, outline=outline, width=width)


def _wrap_text(text, font, max_w):
    text = _safe_text(text or "")
    if not text:
        return []
    lines = []
    current = ""
    for ch in text:
        test = current + ch
        bbox = font.getbbox(test)
        if (bbox[2] - bbox[0]) > max_w and current:
            lines.append(current)
            current = ch
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def _draw_tag_pill(draw, x, y, tag, font):
    style = TAG_STYLE.get(tag, TAG_STYLE["其他"])
    text = f"  {tag}  "
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_y = 8
    rect = (x, y, x + tw + 16, y + th + pad_y * 2)
    _rounded_rect(draw, rect, radius=(th + pad_y * 2) // 2, fill=style["bg"])
    draw.text((x + 16, y + pad_y), tag, font=font, fill=style["fg"])
    return rect[2]


def _draw_top_bar(draw, date_str, label="DAILY MARKET BRIEF"):
    f_brand = _find_font(28)
    f_date = _find_font(24)
    draw.rectangle([(60, 60), (140, 68)], fill=PALETTE["gold"])
    draw.text((60, 90), label, font=f_brand, fill=PALETTE["white"])
    bbox = f_date.getbbox(date_str)
    draw.text((W - 60 - (bbox[2] - bbox[0]), 95), date_str, font=f_date, fill=PALETTE["muted"])


def render_cover(news_items, date_str, output_path):
    img = _gradient_bg(W, H, PALETTE["ink_900"], PALETTE["ink_700"], PALETTE["ink_900"])
    draw = ImageDraw.Draw(img)

    _draw_top_bar(draw, date_str)

    f_zh_title = _find_font(82)
    f_count = _find_font(40)
    f_item = _find_font(36)
    f_footer = _find_font(22)
    f_minitag = _find_font(20)
    f_num = _find_font(22)

    draw.text((60, 180), "每日財經早報", font=f_zh_title, fill=PALETTE["white"])
    draw.rectangle([(60, 295), (220, 299)], fill=PALETTE["gold"])
    draw.text((60, 320), f"今日精選 {len(news_items)} 條", font=f_count, fill=PALETTE["gold"])

    cat_count = {}
    for item in news_items:
        tag = item.get("tag", "其他")
        cat_count[tag] = cat_count.get(tag, 0) + 1

    y = 410
    for i, item in enumerate(news_items[:8], 1):
        tag = item.get("tag", "其他")
        title = _safe_text(item.get("title", ""))[:24]

        cx, cy = 80, y + 18
        radius = 22
        style = TAG_STYLE.get(tag, TAG_STYLE["其他"])
        draw.ellipse([(cx - radius, cy - radius), (cx + radius, cy + radius)], fill=style["bg"])
        nbox = f_num.getbbox(str(i))
        draw.text((cx - (nbox[2] - nbox[0]) // 2, cy - (nbox[3] - nbox[1]) // 2 - 3), str(i), font=f_num, fill=style["fg"])

        draw.text((130, y), title, font=f_item, fill=PALETTE["white"])
        tbox = f_minitag.getbbox(tag)
        draw.text((W - 60 - (tbox[2] - tbox[0]), y + 8), tag, font=f_minitag, fill=PALETTE["muted"])

        y += 78

    draw.rectangle([(0, H - 110), (W, H - 105)], fill=PALETTE["gold"])
    draw.rectangle([(0, H - 105), (W, H)], fill=PALETTE["ink_900"])
    draw.text((60, H - 80), "AI 編輯彙整 / 資料來自公開財經媒體", font=f_footer, fill=PALETTE["muted"])
    draw.text((60, H - 50), "分類分布：" + " · ".join(f"{k}{v}" for k, v in cat_count.items()), font=f_footer, fill=PALETTE["soft"])

    img.save(output_path, "JPEG", quality=92)
    print(f"🎨 封面已存：{output_path}")
    return output_path


def render_news_card(item, idx, total, date_str, output_path):
    img = _gradient_bg(W, H, PALETTE["ink_900"], PALETTE["ink_800"])
    draw = ImageDraw.Draw(img)

    f_top = _find_font(22)
    f_tag = _find_font(28)
    f_idx = _find_font(160)
    f_title = _find_font(60)
    f_summary = _find_font(34)
    f_src = _find_font(22)
    f_meta = _find_font(24)

    _draw_top_bar(draw, date_str)

    big_num = f"{idx:02d}"
    nbox = f_idx.getbbox(big_num)
    draw.text((W - 60 - (nbox[2] - nbox[0]), 145), big_num, font=f_idx, fill=PALETTE["ink_700"])

    prog_y = 160
    draw.text((60, prog_y), f"{idx} / {total}", font=f_top, fill=PALETTE["gold"])
    pw = 180
    draw.rectangle([(60, prog_y + 35), (60 + pw, prog_y + 39)], fill=PALETTE["ink_600"])
    draw.rectangle([(60, prog_y + 35), (60 + int(pw * idx / total), prog_y + 39)], fill=PALETTE["gold"])

    tag = item.get("tag", "其他")
    _draw_tag_pill(draw, 60, 240, tag, f_tag)

    card_top = 320
    card_bot = H - 200
    _rounded_rect(draw, (40, card_top, W - 40, card_bot), radius=24, fill=PALETTE["card"], outline=PALETTE["stroke"], width=2)

    content_x = 80
    content_w = W - 160

    title_lines = _wrap_text(item.get("title", ""), f_title, content_w)
    y = card_top + 50
    for line in title_lines[:3]:
        draw.text((content_x, y), line, font=f_title, fill=PALETTE["white"])
        y += 78

    y += 20
    draw.rectangle([(content_x, y), (content_x + 100, y + 4)], fill=PALETTE["gold"])
    y += 35

    summary_lines = _wrap_text(item.get("summary", ""), f_summary, content_w)
    for line in summary_lines[:7]:
        draw.text((content_x, y), line, font=f_summary, fill=PALETTE["soft"])
        y += 50

    bottom_y = card_bot - 70
    src = item.get("source", "")
    if src:
        draw.text((content_x, bottom_y), f"來源：{src}", font=f_src, fill=PALETTE["muted"])

    importance = item.get("importance", 5)
    full_stars = min(int(importance / 2), 5)
    stars = "★" * full_stars + "☆" * (5 - full_stars)
    star_text = f"重要性 {stars}"
    sbox = f_src.getbbox(star_text)
    draw.text((W - 80 - (sbox[2] - sbox[0]), bottom_y), star_text, font=f_src, fill=PALETTE["gold"])

    draw.text((60, H - 140), "▶ 下一張", font=f_meta, fill=PALETTE["muted"])
    draw.text((W - 230, H - 140), "點 LINE 看原文", font=f_meta, fill=PALETTE["gold_dim"])
    draw.rectangle([(0, H - 6), (W, H)], fill=PALETTE["gold"])

    img.save(output_path, "JPEG", quality=92)
    return output_path


def render_empty_state(date_str, output_path, reason=""):
    img = _gradient_bg(W, H, PALETTE["ink_900"], PALETTE["ink_700"])
    draw = ImageDraw.Draw(img)
    _draw_top_bar(draw, date_str)
    f_big = _find_font(72)
    f_msg = _find_font(36)
    f_tip = _find_font(28)
    draw.text((60, 350), "今日暫無更新", font=f_big, fill=PALETTE["white"])
    draw.rectangle([(60, 460), (220, 464)], fill=PALETTE["gold"])
    msg = reason or "新聞來源暫時無法取得，明日再見。"
    lines = _wrap_text(msg, f_msg, W - 120)
    y = 510
    for line in lines:
        draw.text((60, y), line, font=f_msg, fill=PALETTE["soft"])
        y += 50
    draw.text((60, H - 100), "若連續 2 日無更新，請檢查 RSS 來源設定", font=f_tip, fill=PALETTE["muted"])
    img.save(output_path, "JPEG", quality=92)
    return output_path


def render_all(news_items, output_dir, date_str=""):
    if not date_str:
        date_str = datetime.now().strftime("%Y/%m/%d")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if not news_items:
        empty = render_empty_state(date_str, str(out_dir / "00_empty.jpg"))
        return {"cover": empty, "cards": [], "total": 1}
    cover = render_cover(news_items, date_str, str(out_dir / "00_cover.jpg"))
    cards = []
    for i, item in enumerate(news_items, 1):
        path = str(out_dir / f"{i:02d}_card.jpg")
        render_news_card(item, i, len(news_items), date_str, path)
        cards.append(path)
    return {"cover": cover, "cards": cards, "total": len(cards) + 1}


if __name__ == "__main__":
    import json, sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "../output/cards"
    items = json.loads(open(src, encoding="utf-8").read())
    result = render_all(items, out)
    print(f"OK: {result['total']} images")
