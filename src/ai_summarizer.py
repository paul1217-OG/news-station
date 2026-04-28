"""
ai_summarizer.py v2
- 真 AI 模式：呼叫 OpenAI / Anthropic
- Mock 模式：規則式排序 + deep_translator 自動翻譯英文標題為繁中
"""
from __future__ import annotations
import json, os, re
from pathlib import Path
from typing import List, Dict, Any

PROMPT_TEMPLATE = """你是一位資深財經新聞編輯，服務對象為台灣的散戶投資人。

【任務】
針對下列新聞素材，執行：
1. 過濾：剔除娛樂、運動、政治八卦、地方瑣事
2. 合併：報導同一事件的多篇新聞合併為一條
3. 翻譯：所有外文標題與摘要，全部以繁體中文重寫
4. 排序：依「對台灣投資人的重要性」由高到低
5. 挑選 top {max_items} 條，每條輸出 emoji/title/summary/link/source/tag/importance

【權重】台股 {tw_w}% / 美股 {us_w}% / 亞股 {asia_w}% / 歐股 {eu_w}% / 產業 {ind_w}% / 宏觀 {macro_w}%
【日期】{today}

【嚴格要求】
- 中性、不帶情緒、不做投資建議
- 不可使用「飆漲」「暴跌」「驚天」等聳動詞
- 全部繁體中文（台灣用語），不要簡體字
- 風格類似華爾街日報中文版

只輸出 JSON {{"items":[...]}}

【素材】
{materials}
"""


TRANSLATE_DICT = {
    "stocks": "股市", "stock": "股票", "shares": "股票",
    "market": "市場", "markets": "市場", "trading": "交易",
    "earnings": "財報", "revenue": "營收", "profit": "獲利", "loss": "虧損",
    "rate cut": "降息", "rate hike": "升息", "interest rate": "利率",
    "inflation": "通膨", "deflation": "通縮",
    "Fed": "聯準會", "Federal Reserve": "聯準會",
    "ECB": "歐洲央行", "BOJ": "日本央行",
    "Treasury": "美債", "yield": "殖利率", "bond": "債券",
    "dollar": "美元", "yen": "日圓", "yuan": "人民幣", "euro": "歐元",
    "oil": "原油", "crude": "原油", "gold": "黃金",
    "Apple": "蘋果", "Microsoft": "微軟", "Amazon": "亞馬遜",
    "Meta": "Meta", "Nvidia": "輝達", "Tesla": "特斯拉", "Intel": "英特爾",
    "TSMC": "台積電", "Samsung": "三星",
    "rises": "上漲", "rose": "上漲", "gains": "上漲",
    "falls": "下跌", "fell": "下跌", "drops": "下跌",
    "soars": "大漲", "plunges": "重挫", "jumps": "跳漲",
    "beats": "超預期", "misses": "不如預期",
    "billion": "億", "million": "百萬", "trillion": "兆",
    "Q1": "第一季", "Q2": "第二季", "Q3": "第三季", "Q4": "第四季",
}


def quick_translate(text: str) -> str:
    if not text or any('一' <= c <= '鿿' for c in text):
        return text
    out = text
    for eng, zh in sorted(TRANSLATE_DICT.items(), key=lambda x: -len(x[0])):
        out = re.sub(r'\b' + re.escape(eng) + r'\b', zh, out, flags=re.IGNORECASE)
    return out


def try_deep_translator(text: str) -> str:
    try:
        from deep_translator import GoogleTranslator
        if any('一' <= c <= '鿿' for c in text):
            return text
        result = GoogleTranslator(source='auto', target='zh-TW').translate(text)
        return result if result else text
    except Exception:
        return quick_translate(text)


def _build_materials(items, limit=60):
    lines = []
    for i, it in enumerate(items[:limit], 1):
        lines.append(f"[{i}] ({it['category']}) {it['title']}\n  來源:{it['source']}\n  摘要:{it['summary'][:200]}\n  連結:{it['link']}")
    return "\n\n".join(lines)


def summarize_with_openai(items, api_key, model, max_items, weights, today):
    from openai import OpenAI
    weights = weights or {"tw": 40, "us": 25, "asia": 10, "eu": 5, "ind": 15, "macro": 5}
    materials = _build_materials(items)
    prompt = PROMPT_TEMPLATE.format(
        max_items=max_items, tw_w=weights["tw"], us_w=weights["us"],
        asia_w=weights["asia"], eu_w=weights["eu"],
        ind_w=weights["ind"], macro_w=weights["macro"],
        today=today, materials=materials,
    )
    client = OpenAI(api_key=api_key)
    print(f"🤖 呼叫 {model}...")
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "你是專業財經編輯，只用繁體中文回應 JSON。"},
            {"role": "user", "content": prompt},
        ],
        temperature=0.3,
        response_format={"type": "json_object"},
    )
    parsed = json.loads(resp.choices[0].message.content.strip())
    if isinstance(parsed, dict):
        for k in ("items", "news", "data", "results"):
            if k in parsed and isinstance(parsed[k], list):
                return parsed[k][:max_items]
        for v in parsed.values():
            if isinstance(v, list):
                return v[:max_items]
    return parsed[:max_items] if isinstance(parsed, list) else []


def summarize_mock(items, max_items=8):
    print("⚠️ 沒有 OPENAI_API_KEY，使用 mock 摘要器（規則式 + 自動翻譯）")
    cat_map = {
        "TW": ("台股", "🇹🇼", 10), "US": ("美股", "🇺🇸", 9),
        "INDUSTRY": ("產業", "🏭", 8), "MACRO": ("宏觀", "📊", 7),
        "ASIA": ("亞股", "🌏", 6), "EU": ("歐股", "🇪🇺", 5),
    }
    use_online = os.environ.get("USE_ONLINE_TRANSLATE", "false").lower() in ("1", "true", "yes")
    translate_fn = try_deep_translator if use_online else quick_translate

    sorted_items = sorted(items,
        key=lambda x: (cat_map.get(x.get("category", "OTHER"), ("其他", "📰", 3))[2], x.get("weight", 0.5)),
        reverse=True)

    result = []
    seen = set()
    for it in sorted_items:
        title = translate_fn(it.get("title", ""))
        summary = translate_fn(it.get("summary", ""))
        key = title[:12]
        if key in seen: continue
        seen.add(key)
        cat = it.get("category", "OTHER")
        tag, emoji, importance = cat_map.get(cat, ("其他", "📰", 3))
        result.append({
            "emoji": emoji, "title": title[:60],
            "summary": (summary[:140] if summary else f"來自 {it.get('source', '')} 的快訊。"),
            "link": it.get("link", ""),
            "source": it.get("source", ""),
            "tag": tag, "importance": importance,
        })
        if len(result) >= max_items: break
    return result


def summarize(items, max_items=8, weights=None, today=""):
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    if api_key and api_key.startswith("sk-") and "your_" not in api_key.lower():
        try:
            return summarize_with_openai(items, api_key, model, max_items, weights, today)
        except Exception as ex:
            print(f"⚠️ OpenAI 失敗（{ex}），改用 mock")
            return summarize_mock(items, max_items)
    return summarize_mock(items, max_items)


if __name__ == "__main__":
    import sys
    raw_path = sys.argv[1] if len(sys.argv) > 1 else "../output/raw_news.json"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "../output/summarized.json"
    items = json.loads(Path(raw_path).read_text(encoding="utf-8"))
    summarized = summarize(items, max_items=8, today="2026-04-28")
    Path(out_path).write_text(json.dumps(summarized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 摘要已存：{out_path}（{len(summarized)} 條）")
