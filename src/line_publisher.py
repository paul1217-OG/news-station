"""
line_publisher.py
=================
組裝 LINE Flex Message 並透過 Messaging API 廣播給所有好友。
若 DRY_RUN=true 或缺 token，只把 JSON 寫到 output/，不實際送出。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests


LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"


def build_flex_message(
    news_items: List[Dict[str, Any]],
    date_str: str,
    cover_image_url: str | None = None,
) -> Dict[str, Any]:
    """產出 LINE Flex Message Carousel JSON"""

    bubbles: List[Dict[str, Any]] = []

    # 封面 bubble
    cover_bubble: Dict[str, Any] = {
        "type": "bubble",
        "size": "kilo",
        "body": {
            "type": "box", "layout": "vertical",
            "backgroundColor": "#0F1932",
            "paddingAll": "20px",
            "contents": [
                {"type": "text", "text": "📰 每日財經早報", "color": "#FFFFFF",
                 "size": "xl", "weight": "bold"},
                {"type": "text", "text": date_str, "color": "#FFC107",
                 "size": "sm", "margin": "sm"},
                {"type": "separator", "margin": "lg", "color": "#FFC107"},
                {"type": "text", "text": f"今日 {len(news_items)} 大重點",
                 "color": "#FFFFFF", "size": "lg", "weight": "bold", "margin": "lg"},
                {"type": "text",
                 "text": "→ 滑右邊查看每一條新聞",
                 "color": "#B4BED2", "size": "xs", "margin": "md"},
            ]
        }
    }
    if cover_image_url:
        cover_bubble["hero"] = {
            "type": "image", "url": cover_image_url,
            "size": "full", "aspectRatio": "4:5", "aspectMode": "cover",
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
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1A2347",
                "paddingAll": "20px",
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
                     "color": "#D4DBED", "size": "sm", "wrap": True,
                     "margin": "lg"},
                    {"type": "text", "text": "⭐" * min(int(importance / 2), 5),
                     "color": "#FFC107", "size": "xs", "margin": "lg"},
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#FFC107",
                     "action": {"type": "uri", "label": "看原文 →", "uri": link}}
                ]
            }
        }
        bubbles.append(bubble)

    return {
        "type": "flex",
        "altText": f"📰 {date_str} 每日財經早報｜{len(news_items)} 大重點",
        "contents": {
            "type": "carousel",
            "contents": bubbles[:12],  # LINE 上限 12
        }
    }


def broadcast(flex_message: Dict[str, Any], access_token: str) -> Dict[str, Any]:
    """實際送出 broadcast"""
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }
    payload = {"messages": [flex_message]}
    r = requests.post(LINE_BROADCAST_URL, headers=headers, json=payload, timeout=20)
    return {
        "status": r.status_code,
        "body": r.text,
        "ok": r.status_code == 200,
    }


def publish(
    news_items: List[Dict[str, Any]],
    date_str: str = "",
    cover_image_url: str | None = None,
    output_dir: str = "../output",
) -> Dict[str, Any]:
    """統一入口：建立 Flex Message → 視 DRY_RUN 旗標決定是否真的送出"""
    if not date_str:
        date_str = datetime.now().strftime("%Y/%m/%d")

    flex = build_flex_message(news_items, date_str, cover_image_url)

    # 寫到本機方便除錯
    out_path = Path(output_dir) / "flex_message.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(flex, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 Flex JSON 已存：{out_path}")

    dry_run = os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()

    if dry_run:
        print("🟡 DRY_RUN 模式：不實際送出 LINE，只產出 JSON")
        return {"sent": False, "reason": "dry_run", "flex": flex}

    if not token or "your_" in token.lower():
        print("⚠️ 找不到 LINE_CHANNEL_ACCESS_TOKEN，跳過實際發送")
        return {"sent": False, "reason": "no_token", "flex": flex}

    print(f"📤 廣播至 LINE 官方帳號好友...")
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
