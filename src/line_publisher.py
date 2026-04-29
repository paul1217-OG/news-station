"""
line_publisher.py v3 — 加上 PDF 下載按鈕在封面 bubble
"""
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests


LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def build_flex_message(news_items, date_str, cover_image_url=None, pdf_url=None):
    bubbles = []

    cover_body_contents = [
        {"type": "text", "text": "📰 每日財經早報", "color": "#FFFFFF",
         "size": "xl", "weight": "bold"},
        {"type": "text", "text": date_str, "color": "#FFC107",
         "size": "sm", "margin": "sm"},
        {"type": "separator", "margin": "lg", "color": "#FFC107"},
        {"type": "text", "text": f"今日 {len(news_items)} 大重點",
         "color": "#FFFFFF", "size": "lg", "weight": "bold", "margin": "lg"},
        {"type": "text", "text": "→ 滑右邊看每一則",
         "color": "#B4BED2", "size": "xs", "margin": "md"},
    ]

    cover_bubble = {
        "type": "bubble", "size": "kilo",
        "body": {"type": "box", "layout": "vertical",
                 "backgroundColor": "#0F1932", "paddingAll": "20px",
                 "contents": cover_body_contents}
    }
    if cover_image_url:
        cover_bubble["hero"] = {"type": "image", "url": cover_image_url,
                                "size": "full", "aspectRatio": "4:5", "aspectMode": "cover"}

    # 封面加 PDF 下載按鈕
    if pdf_url:
        cover_bubble["footer"] = {
            "type": "box", "layout": "vertical", "spacing": "sm",
            "contents": [
                {"type": "button", "style": "primary", "color": "#FFC107",
                 "action": {"type": "uri", "label": "📥 下載完整 PDF 報告", "uri": pdf_url}},
                {"type": "text", "text": "繁體中文 / 含編輯小評",
                 "color": "#B4BED2", "size": "xxs", "align": "center", "margin": "sm"},
            ]
        }

    bubbles.append(cover_bubble)

    # 各新聞 bubble
    for i, item in enumerate(news_items, 1):
        emoji = item.get("emoji", "📰")
        title = item.get("title", "")
        summary = item.get("summary", "")
        link = item.get("link", "https://example.com")
        tag = item.get("tag", "其他")
        importance = item.get("importance", 5)

        bubble = {
            "type": "bubble", "size": "kilo",
            "body": {"type": "box", "layout": "vertical",
                     "backgroundColor": "#1A2347", "paddingAll": "20px",
                     "contents": [
                         {"type": "box", "layout": "horizontal",
                          "contents": [
                              {"type": "text", "text": tag, "color": "#FFC107",
                               "size": "sm", "weight": "bold", "flex": 0},
                              {"type": "text", "text": f"{i}/{len(news_items)}",
                               "color": "#B4BED2", "size": "sm", "align": "end"},
                          ]},
                         {"type": "text", "text": f"{emoji} {title}",
                          "color": "#FFFFFF", "size": "lg", "weight": "bold",
                          "wrap": True, "margin": "md"},
                         {"type": "separator", "margin": "lg", "color": "#3A4570"},
                         {"type": "text", "text": summary[:140],
                          "color": "#D4DBED", "size": "sm", "wrap": True, "margin": "lg"},
                         {"type": "text", "text": "⭐" * min(int(importance / 2), 5),
                          "color": "#FFC107", "size": "xs", "margin": "lg"},
                     ]},
            "footer": {"type": "box", "layout": "vertical",
                       "contents": [
                           {"type": "button", "style": "primary", "color": "#FFC107",
                            "action": {"type": "uri", "label": "看原文 →", "uri": link}}
                       ]}
        }
        bubbles.append(bubble)

    return {
        "type": "flex",
        "altText": f"📰 {date_str} 每日財經早報｜{len(news_items)} 大重點" + (" + PDF" if pdf_url else ""),
        "contents": {"type": "carousel", "contents": bubbles[:12]}
    }


def broadcast(flex_message, access_token):
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"messages": [flex_message]}
    r = requests.post(LINE_BROADCAST_URL, headers=headers, json=payload, timeout=20)
    return {"status": r.status_code, "body": r.text, "ok": r.status_code == 200}


def publish(news_items, date_str="", cover_image_url=None, pdf_url=None, output_dir="../output"):
    if not date_str:
        date_str = datetime.now().strftime("%Y/%m/%d")

    flex = build_flex_message(news_items, date_str, cover_image_url, pdf_url)

    out_path = Path(output_dir) / "flex_message.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(flex, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Flex JSON 已存：{out_path}")

    dry_run = os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()

    if dry_run:
        print("🟡 DRY_RUN 模式")
        return {"sent": False, "reason": "dry_run", "flex": flex}

    if not token or "your_" in token.lower():
        print("⚠️ 找不到 LINE_CHANNEL_ACCESS_TOKEN")
        return {"sent": False, "reason": "no_token", "flex": flex}

    print(f"📤 廣播至 LINE...")
    result = broadcast(flex, token)
    if result["ok"]:
        print("✅ 推播成功")
    else:
        print(f"❌ 推播失敗：{result['status']} / {result['body']}")
    return {"sent": result["ok"], "result": result, "flex": flex}


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json"
    items = json.loads(Path(src).read_text(encoding="utf-8"))
    publish(items)
