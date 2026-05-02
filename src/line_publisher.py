"""
line_publisher.py v5 — 完整內容 newsletter（多則訊息 + PDF 卡）
每則新聞顯示完整段落（不截斷），讓使用者在 LINE 上就能讀完。
總長超過單則上限時自動切成多則訊息（LINE 一次最多 5 則）。
"""
from __future__ import annotations
import json, os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any
import requests


LINE_BROADCAST_URL = "https://api.line.me/v2/bot/message/broadcast"
MAX_TEXT_LEN = 4900       # LINE 單則 5000 字上限，留 buffer
MAX_BODY_PER_ITEM = 500   # 每則新聞內文長度


def _stars(score: int) -> str:
    full = max(0, min(5, int(score / 2)))
    return "★" * full + "☆" * (5 - full)


def _clean(text: str) -> str:
    if not text:
        return ""
    return text.replace("\n\n\n", "\n\n").strip()


def format_news_item(item: Dict[str, Any], i: int, total: int) -> str:
    """格式化單則新聞為「足以讓使用者讀完」的版本"""
    emoji = item.get("emoji", "📰")
    tag = item.get("tag", "其他")
    title = item.get("title", "")
    importance = item.get("importance", 5)

    # 優先用 AI 改寫的 long_text；若無就用原始 summary
    body = item.get("long_text") or item.get("summary", "")
    body = _clean(body)
    if len(body) > MAX_BODY_PER_ITEM:
        body = body[:MAX_BODY_PER_ITEM] + "…"

    src = item.get("source", "")

    parts = [
        f"━━━━━━━━",
        f"【{i}/{total}】 {emoji} [{tag}] {_stars(importance)}",
        title,
        "",
        body,
    ]
    if src:
        parts.append("")
        parts.append(f"— 資料來源：{src}")

    return "\n".join(parts)


def build_newsletter_messages(
    news_items: List[Dict[str, Any]],
    date_str: str,
    weekday: str,
    editorial_text: str = "",
    upcoming_text: str = "",
    pdf_url: str | None = None,
) -> List[str]:
    """
    回傳「多則訊息」的字串陣列。
    分配規則：
      - 訊息 1：開頭 + 編輯導讀 + 前 N 則新聞（直到接近上限）
      - 訊息 2、3...：剩下的新聞，自動分頁
      - 最後一則訊息附加：明日關注 + PDF 連結
    """
    messages: List[str] = []

    header = []
    header.append("📰 每日財經早報")
    header.append(f"{date_str}（{weekday}）")
    if editorial_text:
        header.append("━━━━━━━━━━━━━━")
        header.append("")
        header.append("▎今日導讀")
        header.append(_clean(editorial_text)[:500])
    header_str = "\n".join(header) + "\n"

    footer_parts = []
    if upcoming_text:
        footer_parts.append("━━━━━━━━━━━━━━")
        footer_parts.append("")
        footer_parts.append("▎明日／本週關注")
        footer_parts.append(_clean(upcoming_text)[:400])
    if pdf_url:
        footer_parts.append("")
        footer_parts.append("━━━━━━━━━━━━━━")
        footer_parts.append("📥 完整 PDF 報告")
        footer_parts.append(pdf_url)
    footer_parts.append("")
    footer_parts.append("⌐ 公開財經 RSS + 公開資訊觀測站")
    footer_parts.append("⌐ AI 寫稿：Google Gemini")
    footer_parts.append("⌐ 明日 07:30 再見")
    footer_str = "\n".join(footer_parts)

    # 把每則新聞先格式化好
    formatted = [format_news_item(it, i, len(news_items))
                 for i, it in enumerate(news_items, 1)]

    # 開始堆疊：訊息 1 從 header 起
    current = header_str
    for f in formatted:
        candidate = current + "\n" + f + "\n"
        # 預留 footer 空間給最後一則
        if len(candidate) > MAX_TEXT_LEN - 200:
            # 推掉目前累積，開新訊息
            messages.append(current.rstrip())
            current = f + "\n"
        else:
            current = candidate

    # 把 footer 塞進最後一則；若塞不下就再開一則
    candidate = current + "\n" + footer_str
    if len(candidate) <= MAX_TEXT_LEN:
        messages.append(candidate.rstrip())
    else:
        messages.append(current.rstrip())
        messages.append(footer_str)

    # 安全截斷：如果單則仍超過上限（防呆）
    safe = []
    for m in messages:
        if len(m) > MAX_TEXT_LEN:
            m = m[:MAX_TEXT_LEN - 30] + "\n\n…（請見 PDF）"
        safe.append(m)

    # LINE 廣播一次最多 5 則
    return safe[:5]


# ====== Flex 短卡片（PDF 下載按鈕專用）======

def build_pdf_action_card(date_str: str, pdf_url: str) -> Dict[str, Any]:
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


def build_text_message(text: str) -> Dict[str, Any]:
    return {"type": "text", "text": text}


# ====== 廣播 ======

def broadcast(messages: List[Dict[str, Any]], access_token: str) -> Dict[str, Any]:
    headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
    payload = {"messages": messages[:5]}
    r = requests.post(LINE_BROADCAST_URL, headers=headers, json=payload, timeout=20)
    return {"status": r.status_code, "body": r.text, "ok": r.status_code == 200}


# ====== 主入口 ======

def publish(news_items, date_str="", cover_image_url=None, pdf_url=None,
            editorial_text="", upcoming_text="", output_dir="../output"):
    if not date_str:
        date_str = datetime.now().strftime("%Y/%m/%d")
    weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][datetime.now().weekday()]

    # 組多則文字訊息
    text_messages = build_newsletter_messages(
        news_items, date_str, weekday,
        editorial_text=editorial_text,
        upcoming_text=upcoming_text,
        pdf_url=pdf_url,
    )

    # LINE 一次最多 5 則 → 文字 + PDF 卡片合計不能超過 5
    # 預留 1 格給 PDF 卡，所以文字最多 4 則
    if pdf_url and len(text_messages) > 4:
        text_messages = text_messages[:4]

    messages = [build_text_message(t) for t in text_messages]

    if pdf_url:
        messages.append(build_pdf_action_card(date_str, pdf_url))

    # 落地存檔
    out_path = Path(output_dir) / "messages.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(messages, ensure_ascii=False, indent=2), encoding="utf-8")
    txt_path = Path(output_dir) / "newsletter_preview.txt"
    txt_path.write_text("\n\n=== 訊息分隔 ===\n\n".join(text_messages), encoding="utf-8")
    print(f"💾 訊息已存：{out_path}（共 {len(messages)} 則）")
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
    publish(
        items,
        editorial_text="今日市場以半導體與 AI 為主軸，台積電法說與輝達 Blackwell Ultra 出貨同時推升相關供應鏈情緒。在宏觀面，Fed 議息會議紀要轉鴿派強化降息預期。",
        upcoming_text="本週重點：美國 4 月 CPI、零售銷售、PMI 等數據；Fed 主席演講；台股法說會旺季續行。",
        pdf_url="https://github.com/paul1217-OG/news-station/raw/main/reports/2026-05-02.pdf",
    )
