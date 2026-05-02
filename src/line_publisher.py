"""
line_publisher.py v4 — 單則 newsletter 文字訊息（替代 carousel）
讓使用者像讀電子報一樣連續滑動閱讀，不用左右切換卡片。
最後附一則小 Flex 卡片含 PDF 下載按鈕。
"""
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests


LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
MAX_TEXT_LEN = 4900  # LINE 單則 5000 字上限，留點 buffer


# ====== 文字 newsletter 組裝 ======

def _truncate(text: str, n: int) -> str:
    if not text:
        return ""
    text = text.replace("\n\n\n", "\n\n").strip()
    return text[:n] + ("…" if len(text) > n else "")


def _stars(score: int) -> str:
    full = max(0, min(5, int(score / 2)))
    return "★" * full + "☆" * (5 - full)


def build_newsletter_text(
    news_items: List[Dict[str, Any]],
    date_str: str,
    weekday: str,
    editorial_text: str = "",
    upcoming_text: str = "",
    pdf_url: str | None = None,
) -> str:
    """組合一則完整的 newsletter 文字訊息"""

    lines = []
    lines.append("📰 每日財經早報")
    lines.append(f"{date_str}（{weekday}）")
    lines.append("━━━━━━━━━━━━━━")
    lines.append("")

    # 導讀
    if editorial_text:
        lines.append("▎今日導讀")
        lines.append(_truncate(editorial_text, 360))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━")
        lines.append("")

    # 8 大重點
    lines.append(f"▎今日 {len(news_items)} 大重點")
    lines.append("")

    for i, item in enumerate(news_items, 1):
        emoji = item.get("emoji", "📰")
        tag = item.get("tag", "其他")
        title = item.get("title", "")
        importance = item.get("importance", 5)

        # 標題列
        lines.append(f"【{i}】 {emoji} [{tag}] {_stars(importance)}")
        lines.append(title)

        # 1～2 句重點摘要（用 long_text 第一段，或 summary）
        summary = item.get("long_text") or item.get("summary", "")
        # 抓第一段（雙換行 / 句號 為界）
        first_para = summary.split("\n\n")[0] if summary else ""
        first_para = _truncate(first_para, 160)
        if first_para and first_para != title:
            lines.append(f"　{first_para}")

        # 來源 + 連結（短連結處理）
        src = item.get("source", "")
        link = item.get("link", "")
        if link:
            lines.append(f"　🔗 {src}：{_truncate(link, 50)}")

        lines.append("")

    lines.append("━━━━━━━━━━━━━━")
    lines.append("")

    # 明日關注
    if upcoming_text:
        lines.append("▎明日／本週關注")
        lines.append(_truncate(upcoming_text, 320))
        lines.append("")
        lines.append("━━━━━━━━━━━━━━")
        lines.append("")

    # PDF 連結
    if pdf_url:
        lines.append("📥 完整 PDF 報告（手機友善報紙版）")
        lines.append(pdf_url)
        lines.append("")

    # 落款
    lines.append("⌐ 資料：公開財經媒體 RSS + 公開資訊觀測站")
    lines.append("⌐ AI 寫稿：Google Gemini")
    lines.append("⌐ 明日同一時間 07:30 再見")

    text = "\n".join(lines)

    # 安全裁切
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN - 30] + "\n\n…（內容過長，請見 PDF）"

    return text


# ====== Flex 短卡片（PDF 下載按鈕專用）======

def build_pdf_action_card(date_str: str, pdf_url: str) -> Dict[str, Any]:
    """獨立一則 Flex bubble，只負責 PDF 下載按鈕"""
    return {
        "type": "flex",
        "altText": f"📥 {date_str} 完整 PDF 報告",
        "contents": {
            "type": "bubble",
            "size": "kilo",
            "body": {
                "type": "box", "layout": "vertical",
                "backgroundColor": "#1A1A1A",
                "paddingAll": "20px",
                "contents": [
                    {"type": "text", "text": "📥 完整 PDF 報告",
                     "color": "#F5C038", "size": "lg", "weight": "bold"},
                    {"type": "text", "text": f"{date_str}　報紙風格手機版",
                     "color": "#B4B4B4", "size": "xs", "margin": "sm"},
                    {"type": "separator", "margin": "md", "color": "#444444"},
                    {"type": "text",
                     "text": "含完整繁中翻譯 + AI 編輯導讀 + 明日關注事件",
                     "color": "#FFFFFF", "size": "sm", "wrap": True, "margin": "md"},
                ]
            },
            "footer": {
                "type": "box", "layout": "vertical",
                "contents": [
                    {"type": "button", "style": "primary", "color": "#F5C038",
                     "action": {"type": "uri", "label": "下載 PDF →", "uri": pdf_url}}
                ]
            }
        }
    }


# ====== 後備卡片（沒 pdf_url 時也要保留訊息結構）======

def build_simple_text_message(text: str) -> Dict[str, Any]:
    return {"type": "text", "text": text}


# ====== 廣播 ======

def broadcast(messages: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
    """送出多則訊息"""
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"messages": messages[:5]}  # LINE 一次最多 5 則
    r = requests.post(LINE_BROADCAST_URL, headers=headers, json=payload, timeout=20)
    return {"status": r.status_code, "body": r.text, "ok": r.status_code == 200}


# ====== 主入口 ======

def publish(news_items, date_str="", cover_image_url=None, pdf_url=None,
            editorial_text="", upcoming_text="", output_dir="../output"):
    if not date_str:
        date_str = datetime.now().strftime("%Y/%m/%d")
    weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][datetime.now().weekday()]

    # 主訊息：newsletter 文字
    text_body = build_newsletter_text(
        news_items, date_str, weekday,
        editorial_text=editorial_text,
        upcoming_text=upcoming_text,
        pdf_url=pdf_url,
    )

    messages = [build_simple_text_message(text_body)]

    # 副訊息：PDF 下載 Flex（如果有 PDF URL）
    if pdf_url:
        messages.append(build_pdf_action_card(date_str, pdf_url))

    # 落地存檔（供除錯）
    out_path = Path(output_dir) / "messages.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path = Path(output_dir) / "newsletter_preview.txt"
    txt_path.write_text(text_body, encoding="utf-8")
    print(f"💾 訊息已存：{out_path}")
    print(f"💾 文字預覽：{txt_path}")

    dry_run = os.environ.get("DRY_RUN", "true").lower() in ("1", "true", "yes")
    token = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN", "").strip()

    if dry_run:
        print("🟡 DRY_RUN 模式")
        return {"sent": False, "reason": "dry_run", "messages": messages}

    if not token or "your_" in token.lower():
        print("⚠️ 找不到 LINE_CHANNEL_ACCESS_TOKEN")
        return {"sent": False, "reason": "no_token", "messages": messages}

    print(f"📤 廣播至 LINE（{len(messages)} 則）...")
    result = broadcast(messages, token)
    if result["ok"]:
        print("✅ 推播成功")
    else:
        print(f"❌ 推播失敗：{result['status']} / {result['body']}")
    return {"sent": result["ok"], "result": result, "messages": messages}


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json"
    items = json.loads(Path(src).read_text(encoding="utf-8"))
    publish(items, editorial_text="今日市場以半導體與 AI 為主軸，台積電法說與輝達 Blackwell Ultra 出貨同時推升相關供應鏈情緒。在宏觀面，Fed 議息會議紀要轉鴿派強化降息預期，市場避險與增持成長股的拉鋸延續。",
            upcoming_text="本週關注重點：美國 4 月 CPI、零售銷售、PMI 等數據；Fed 主席演講可能釋出進一步政策訊號；台股法說會進入旺季，鴻海、聯發科等將陸續登場；公開資訊觀測站每日 17:00 後重大訊息。",
            pdf_url="https://github.com/paul1217-OG/news-station/raw/main/reports/2026-04-29.pdf")
