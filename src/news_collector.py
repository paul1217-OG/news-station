"""
news_collector.py
=================
從多個 RSS 來源並行抓取新聞，去除重複與過期內容。
"""

from __future__ import annotations

import hashlib
import json
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Dict, Any
from urllib.parse import urlparse

import feedparser
import yaml


@dataclass
class NewsItem:
    title: str
    link: str
    summary: str
    published: str  # ISO format
    source: str
    category: str
    weight: float = 1.0
    hash_id: str = ""
    score: float = 0.0  # 由 AI summarizer 填入

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _make_hash(title: str, link: str) -> str:
    """以標題＋連結產生唯一 ID，用於去重"""
    s = (title.strip().lower() + "|" + link.strip().lower()).encode("utf-8")
    return hashlib.md5(s).hexdigest()[:12]


def _strip_html(text: str) -> str:
    """去除 HTML tag、多餘空白"""
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_date(entry: dict) -> str:
    """從 feedparser entry 抽出時間，統一為 ISO 格式"""
    for k in ("published_parsed", "updated_parsed"):
        t = entry.get(k)
        if t:
            try:
                dt = datetime(*t[:6], tzinfo=timezone.utc)
                return dt.isoformat()
            except Exception:
                pass
    return datetime.now(timezone.utc).isoformat()


def fetch_one(source: dict, lookback_hours: int = 30) -> List[NewsItem]:
    """抓單一 RSS，回傳近 N 小時內的新聞"""
    items: List[NewsItem] = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback_hours)

    try:
        # feedparser 會自帶 timeout，但我們再加一層
        d = feedparser.parse(source["url"])
        if d.bozo and not d.entries:
            print(f"  [WARN] {source['name']} 解析失敗：{d.bozo_exception}")
            return items

        for e in d.entries[:30]:  # 每源最多抓 30 條
            title = _strip_html(e.get("title", "")).strip()
            link = e.get("link", "").strip()
            if not title or not link:
                continue

            summary = _strip_html(e.get("summary", "") or e.get("description", ""))
            # 太短的摘要用 title 填補
            if len(summary) < 20:
                summary = title

            published = _parse_date(e)
            try:
                pub_dt = datetime.fromisoformat(published.replace("Z", "+00:00"))
                if pub_dt < cutoff:
                    continue
            except Exception:
                pass

            items.append(NewsItem(
                title=title[:200],
                link=link,
                summary=summary[:500],
                published=published,
                source=source["name"],
                category=source.get("category", "GENERAL"),
                weight=source.get("weight", 1.0),
                hash_id=_make_hash(title, link),
            ))
    except Exception as ex:
        print(f"  [ERROR] {source['name']}: {ex}")

    return items


def collect_all(config_path: str, lookback_hours: int = 30) -> List[NewsItem]:
    """並行抓取所有來源並去重"""
    cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
    sources = cfg.get("sources", [])
    print(f"📡 開始從 {len(sources)} 個來源抓取（並行）...")

    all_items: List[NewsItem] = []
    seen: set[str] = set()

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = {pool.submit(fetch_one, s, lookback_hours): s for s in sources}
        for fut in as_completed(futures):
            src = futures[fut]
            try:
                got = fut.result(timeout=30)
                # 來源內去重 + 全域去重
                added = 0
                for item in got:
                    if item.hash_id in seen:
                        continue
                    seen.add(item.hash_id)
                    all_items.append(item)
                    added += 1
                print(f"  ✓ {src['name']}: 拿到 {len(got)} 條，新增 {added}")
            except Exception as ex:
                print(f"  ✗ {src['name']}: {ex}")

    print(f"📦 合計 {len(all_items)} 條獨立新聞（已去重）")
    return all_items


def save_items(items: List[NewsItem], path: str) -> None:
    """寫成 JSON 供下游使用"""
    data = [it.to_dict() for it in items]
    Path(path).write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"💾 已存檔：{path}（{len(data)} 條）")


if __name__ == "__main__":
    import sys
    cfg_path = sys.argv[1] if len(sys.argv) > 1 else "../config.yaml"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "../output/raw_news.json"
    items = collect_all(cfg_path, lookback_hours=30)
    save_items(items, out_path)
