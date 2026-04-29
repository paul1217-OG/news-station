"""
mops_fetcher.py — 抓公開資訊觀測站重大訊息
TWSE OpenAPI: https://openapi.twse.com.tw/
"""
from __future__ import annotations
import requests
from datetime import datetime
from typing import List, Dict, Any

# 上市公司每日重大訊息
TWSE_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap04_L"
# 上櫃公司每日重大訊息
TPEX_URL = "https://www.tpex.org.tw/openapi/v1/mopsfin_t187ap04_O"


def fetch_mops(limit: int = 30) -> List[Dict[str, Any]]:
    """抓今日上市櫃重大訊息，轉成統一 NewsItem 格式"""
    items: List[Dict[str, Any]] = []

    for url, market in [(TWSE_URL, "上市"), (TPEX_URL, "上櫃")]:
        try:
            r = requests.get(url, timeout=15, headers={"User-Agent": "news-station/1.0"})
            if r.status_code != 200:
                print(f"  [WARN] MOPS {market} HTTP {r.status_code}")
                continue
            data = r.json()
            print(f"  ✓ MOPS {market}：拿到 {len(data)} 筆")

            for entry in data[:limit]:
                # TWSE 欄位通常是：出表日期 公司代號 公司簡稱 主旨 ...
                code = entry.get("公司代號") or entry.get("Code") or ""
                name = entry.get("公司名稱") or entry.get("Name") or entry.get("公司簡稱") or ""
                subject = entry.get("主旨") or entry.get("Subject") or ""
                if not subject:
                    continue
                date_raw = entry.get("發言日期") or entry.get("出表日期") or ""

                items.append({
                    "title": f"[{market} {code}] {name}：{subject}"[:120],
                    "summary": subject,
                    "link": f"https://mops.twse.com.tw/mops/web/t05st01?TYPEK={'sii' if market == '上市' else 'otc'}&co_id={code}",
                    "source": f"公開資訊觀測站（{market}）",
                    "category": "MOPS",
                    "tag": "公發站",
                    "weight": 1.0,
                    "raw_date": date_raw,
                })
        except Exception as ex:
            print(f"  [ERROR] MOPS {market}：{ex}")

    return items


def filter_priority_keywords(items: List[Dict[str, Any]], keywords: List[str]) -> List[Dict[str, Any]]:
    """挑出含關鍵字的重大訊息（例如：金融、餐飲、半導體、財報、配息）"""
    out = []
    for it in items:
        text = it.get("title", "") + " " + it.get("summary", "")
        if any(k in text for k in keywords):
            out.append(it)
    return out


PRIORITY_KEYWORDS = [
    # 金融
    "增資", "減資", "現金股利", "股票股利", "盈餘分配", "董事會",
    # 重大投資
    "投資", "併購", "收購", "處分", "出售", "讓與",
    # 財報相關
    "財報", "EPS", "營收", "獲利", "虧損",
    # 半導體 / 餐飲特別關注
    "半導體", "晶圓", "封測", "餐飲", "連鎖",
    # 公司治理
    "重大訊息", "更正", "停牌", "暫停交易", "下市",
    # 其他關鍵字
    "新台幣", "美元", "億元",
]


if __name__ == "__main__":
    items = fetch_mops()
    print(f"\n總計 {len(items)} 條 MOPS 訊息")
    filtered = filter_priority_keywords(items, PRIORITY_KEYWORDS)
    print(f"關鍵字過濾後：{len(filtered)} 條")
    for it in filtered[:5]:
        print(f"  - {it['title']}")
