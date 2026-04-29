"""
editorial.py — 規則式編輯部分析（無需 OpenAI）
"""
from __future__ import annotations
from datetime import datetime
from collections import Counter
from typing import List, Dict, Any

SECTOR_NARRATIVE = {
    "台股": "台股投資人關注重點", "美股": "美國市場走勢",
    "亞股": "亞太市場觀察", "歐股": "歐洲財經動態",
    "產業": "產業趨勢與供應鏈", "宏觀": "全球宏觀情勢",
}

INTERPRETATION_RULES = [
    (["AI", "人工智慧", "GPU", "Nvidia", "輝達"],
     "→ AI 浪潮持續推升半導體、雲端伺服器供應鏈需求。台灣相關標的：台積電、鴻海、緯穎、世芯-KY。"),
    (["降息", "rate cut", "Fed", "聯準會"],
     "→ 利率走勢直接影響資金成本與估值，金融股、REITs、成長股對降息敏感。"),
    (["升息", "rate hike", "通膨"],
     "→ 升息壓抑成長股估值，金融股利差擴大有利。"),
    (["台積電", "TSMC", "2330"],
     "→ 台積電動向是台股權值股與整個半導體鏈情緒指標。"),
    (["黃金", "gold", "避險"],
     "→ 避險買盤上升通常反映地緣政治或市場不確定性升溫。"),
    (["原油", "oil", "OPEC"],
     "→ 油價變動影響航運、塑化、運輸類股，並牽動通膨預期。"),
    (["財報", "earnings", "EPS"],
     "→ 財報季是股價催化劑，超預期通常推升，不如預期則修正。"),
    (["央行", "ECB", "BOJ"],
     "→ 主要央行政策影響匯率與跨國資本流動。"),
    (["供應鏈", "supply chain"],
     "→ 供應鏈訊息對台灣製造業具參考價值。"),
]


def detect_main_theme(items):
    weighted = Counter()
    for it in items:
        weighted[it.get("tag", "其他")] += it.get("importance", 5)
    if not weighted:
        return {"sector": "綜合", "narrative": "今日新聞分布平均", "count": 0}
    top, score = weighted.most_common(1)[0]
    count = sum(1 for it in items if it.get("tag") == top)
    return {"sector": top, "narrative": SECTOR_NARRATIVE.get(top, top),
            "count": count, "weighted_score": score}


def interpret_news(item):
    text = (item.get("title", "") + " " + item.get("summary", "")).lower()
    for keywords, comment in INTERPRETATION_RULES:
        if any(k.lower() in text for k in keywords):
            return comment
    tag = item.get("tag", "其他")
    defaults = {
        "台股": "→ 留意對台股盤勢與相關類股之影響。",
        "美股": "→ 影響美國市場走向，對台美科技股具連動效應。",
        "宏觀": "→ 宏觀變動影響跨資產配置邏輯。",
        "產業": "→ 反映產業結構性趨勢，對台廠供應鏈具參考價值。",
        "亞股": "→ 亞太市場連動性高，對台股早盤情緒具指標意義。",
        "歐股": "→ 歐洲動態反映全球經濟情勢，對外銷導向產業有間接影響。",
    }
    return defaults.get(tag, "→ 此訊息對市場具參考價值。")


def upcoming_events():
    now = datetime.now()
    weekday = now.weekday()
    events = []
    if now.day <= 7:
        events.append({"time": "本週", "event": "上月美國非農、CPI、台灣外銷訂單數據陸續公布"})
    if now.month in [4, 7, 10, 1]:
        events.append({"time": "本月", "event": "美國上市企業上一季財報密集公布期"})
        events.append({"time": "中下旬", "event": "台股法說會（台積電、聯發科等權值股）"})
    if weekday in [3, 4]:
        events.append({"time": "週末", "event": "中國 PMI、美國消費者信心可能影響開盤"})
    events.append({"time": "每日", "event": "美股盤後動態（台北時間清晨）；亞洲開盤反應"})
    return events[:4]


def daily_summary_numbers(items):
    by_tag = Counter(it.get("tag", "其他") for it in items)
    avg = sum(it.get("importance", 5) for it in items) / max(len(items), 1)
    return {
        "total": len(items),
        "by_tag": dict(by_tag.most_common()),
        "avg_importance": round(avg, 1),
        "top_news": items[0]["title"][:30] if items else "",
    }


def editor_intro(theme, summary):
    sector = theme.get("sector", "綜合")
    count = theme.get("count", 0)
    narrative = theme.get("narrative", "")
    total = summary.get("total", 0)
    weekday_names = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]
    today = datetime.now()
    weekday = weekday_names[today.weekday()]
    intro = f"今日（{today.strftime('%m/%d')} {weekday}）共彙整 {total} 條精選新聞，"
    if count >= 3:
        intro += f"其中以「{narrative}」為今日主旋律（共 {count} 則相關），值得重點關注。"
    elif count == 2:
        intro += f"報導重心略偏「{narrative}」（{count} 則），其餘為跨類別均衡分布。"
    else:
        intro += "各類別分布均衡，無單一主軸，建議橫向掃讀掌握全局。"
    avg = summary.get("avg_importance", 5)
    if avg >= 8:
        intro += " 整體重要性偏高，市場短期波動值得密切追蹤。"
    elif avg >= 6:
        intro += " 訊息重要性中等偏高，可作為日內操作參考。"
    else:
        intro += " 訊息以例行更新為主，建議重點瀏覽即可。"
    return intro


if __name__ == "__main__":
    import json, sys
    items = json.loads(open(sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json").read())
    theme = detect_main_theme(items)
    summary = daily_summary_numbers(items)
    intro = editor_intro(theme, summary)
    print("=== 主旋律 ===\n", theme)
    print("\n=== 摘要數字 ===\n", summary)
    print("\n=== 編輯導讀 ===\n", intro)
    print("\n=== 各則編輯小評 ===")
    for it in items[:3]:
        print(f"- {it['title'][:30]}")
        print(f"  {interpret_news(it)}")
    print("\n=== 明日關注事件 ===")
    for ev in upcoming_events():
        print(f"  [{ev['time']}] {ev['event']}")
