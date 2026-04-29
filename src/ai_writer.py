"""
ai_writer.py — 用 Google Gemini 把新聞寫成繁中段落報告
"""
from __future__ import annotations
import json, os, re
from typing import List, Dict, Any
import requests

GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_MODEL = "gemini-2.0-flash"


def _gemini_generate(prompt: str, api_key: str, model: str = DEFAULT_MODEL,
                     temperature: float = 0.4, max_output_tokens: int = 4096) -> str:
    url = f"{GEMINI_BASE}/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_output_tokens,
        },
        "safetySettings": [
            {"category": c, "threshold": "BLOCK_NONE"} for c in [
                "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT",
            ]
        ],
    }
    r = requests.post(url, json=payload, timeout=60)
    if r.status_code != 200:
        raise RuntimeError(f"Gemini API 錯誤 {r.status_code}: {r.text[:300]}")
    data = r.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError) as ex:
        raise RuntimeError(f"Gemini 回應格式異常: {data}")


# ===== Prompt 模板 =====

REWRITE_PROMPT = """你是台灣財經媒體資深編輯，風格嚴謹、客觀、易讀。

【任務】把下列新聞素材改寫為一篇 250～400 字的繁體中文段落式報導。

【素材】
標題：{title}
類別：{tag}
重要性：{importance}/10
原文摘要：{summary}
來源：{source}

【寫作要求】
1. 全文用繁體中文（台灣用語），不要簡體字、不要中港用語
2. 改寫為 2～3 段，每段 80～150 字，自然流暢，不條列
3. 第一段：事件本身（誰、何時、發生什麼、數字），客觀陳述
4. 第二段：背景脈絡（為什麼會發生、市場既有預期），加入推論性分析
5. （選用）第三段：對台灣投資人的影響（哪些類股或標的可能連動）
6. 不可使用「飆漲」「暴跌」「驚天」「炸裂」等聳動詞
7. 不可給投資建議（不能說「建議買入」之類）
8. 數字、英文公司名、英文專有名詞保留原文（例：Fed, EPS, AI, GPU, TSMC）

【輸出格式】
直接輸出文章內容，不要 markdown、不要前後文字、不要標題。
"""

EDITORIAL_PROMPT = """你是台灣財經日報主編。請根據今日彙整的 {n} 條重點新聞，撰寫一段 200～280 字的「今日導讀」。

【今日新聞主要分類】
{tag_distribution}

【新聞清單】
{headlines}

【寫作要求】
1. 繁體中文（台灣用語）
2. 抓出今日「核心主旋律」：哪 1～2 條故事最值得讀者注意？為什麼？
3. 提供宏觀脈絡：今日新聞的共同訊號是什麼？
4. 不要列點，純粹散文式 2 段
5. 第一段重點，第二段脈絡與啟示
6. 風格類似《華爾街日報中文網》《工商時報》編輯導讀

直接輸出文章內容，不要 markdown 標題。
"""

UPCOMING_PROMPT = """你是台灣財經編輯。請依今日日期 {today}（{weekday}），撰寫「明日 / 本週值得關注」段落，250 字內。

要點：
1. 列出 4～6 個具體事件 / 數據公布 / 法說會 / 央行會議
2. 每個事件 1 句說明為何重要
3. 結尾 1～2 句總結本週主軸
4. 純文字段落式，不用 bullet 點
5. 繁體中文（台灣用語）

可參考的真實事件類別：美國非農、CPI、PMI、Fed FOMC、ECB、BOJ、台灣外銷訂單、上市櫃法說會、財報公布、公開資訊觀測站重大訊息、地緣政治新聞。
"""


def rewrite_article(item: Dict[str, Any], api_key: str, model: str = DEFAULT_MODEL) -> str:
    """把一條新聞改寫為段落式報導"""
    prompt = REWRITE_PROMPT.format(
        title=item.get("title", ""), tag=item.get("tag", "其他"),
        importance=item.get("importance", 5),
        summary=item.get("summary", ""), source=item.get("source", ""),
    )
    return _gemini_generate(prompt, api_key, model, temperature=0.4, max_output_tokens=1200)


def write_editorial(items: List[Dict[str, Any]], api_key: str, model: str = DEFAULT_MODEL) -> str:
    """寫今日導讀"""
    from collections import Counter
    tag_dist = ", ".join(f"{k}({v})" for k, v in Counter(it.get("tag", "其他") for it in items).items())
    headlines = "\n".join(f"- [{it.get('tag', '?')}] {it.get('title', '')[:50]}" for it in items)
    prompt = EDITORIAL_PROMPT.format(n=len(items), tag_distribution=tag_dist, headlines=headlines)
    return _gemini_generate(prompt, api_key, model, temperature=0.5, max_output_tokens=800)


def write_upcoming(api_key: str, today: str = "", weekday: str = "", model: str = DEFAULT_MODEL) -> str:
    """寫明日值得關注"""
    from datetime import datetime
    if not today:
        today = datetime.now().strftime("%Y-%m-%d")
    if not weekday:
        weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][datetime.now().weekday()]
    prompt = UPCOMING_PROMPT.format(today=today, weekday=weekday)
    return _gemini_generate(prompt, api_key, model, temperature=0.6, max_output_tokens=600)


# ===== Fallback：沒 API key 時用簡易模板 =====

def fallback_rewrite(item: Dict[str, Any]) -> str:
    """無 API 時的後備：仍輸出段落，但是模板化"""
    return (
        f"【{item.get('tag', '其他')}】{item.get('title', '')}\n\n"
        f"{item.get('summary', '')}\n\n"
        f"資料來源：{item.get('source', '未署名')}。本則重要性 {item.get('importance', 5)}/10。"
    )


def fallback_editorial(items: List[Dict[str, Any]]) -> str:
    n = len(items)
    return (
        f"今日彙整 {n} 條財經重點新聞，涵蓋台股、美股、國際宏觀、產業趨勢與公開資訊觀測站重大訊息。"
        f"請依個別新聞的編輯小評瞭解細節。明日值得追蹤事件請見後段提醒。"
    )


def fallback_upcoming() -> str:
    return (
        "本週值得關注：美國經濟數據（CPI、PPI、零售）密集公布；"
        "台股法說會進入旺季，留意權值股展望；公開資訊觀測站每日 17:00 後重大訊息更新；"
        "Fed 與其他主要央行官員談話可能牽動匯市。"
    )


# ===== 統一入口 =====

def enrich_with_ai(items: List[Dict[str, Any]], api_key: str | None = None,
                   model: str = DEFAULT_MODEL) -> Dict[str, Any]:
    """為新聞列表做 AI 加工：產生長文 + 編輯導讀 + 明日關注"""
    api_key = api_key or os.environ.get("GEMINI_API_KEY", "").strip()
    use_ai = bool(api_key) and not api_key.startswith("your_")

    if use_ai:
        print(f"🤖 使用 Gemini ({model}) 生成深度報告...")
        try:
            for i, item in enumerate(items, 1):
                print(f"  → 改寫第 {i}/{len(items)} 篇：{item.get('title', '')[:30]}")
                item["long_text"] = rewrite_article(item, api_key, model)
            editorial = write_editorial(items, api_key, model)
            upcoming = write_upcoming(api_key, model=model)
            print("✓ AI 寫稿完成")
            return {"editorial": editorial, "upcoming": upcoming, "powered_by_ai": True}
        except Exception as ex:
            print(f"⚠️ Gemini API 失敗（{ex}），改用 fallback 模板")
            for item in items:
                item["long_text"] = fallback_rewrite(item)
            return {"editorial": fallback_editorial(items),
                    "upcoming": fallback_upcoming(), "powered_by_ai": False}
    else:
        print("⚠️ 沒有 GEMINI_API_KEY，使用 fallback 模板")
        for item in items:
            item["long_text"] = fallback_rewrite(item)
        return {"editorial": fallback_editorial(items),
                "upcoming": fallback_upcoming(), "powered_by_ai": False}


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "../output/enriched.json"
    items = json.loads(open(src, encoding="utf-8").read())
    extras = enrich_with_ai(items)
    payload = {"items": items, **extras}
    open(out, "w", encoding="utf-8").write(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"💾 已存：{out}")
