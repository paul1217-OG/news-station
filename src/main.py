"""
main.py v4 — 整合 Gemini AI 寫稿 + 公發站 + 報紙風格 PDF
"""
from __future__ import annotations
import os, sys, json, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
import news_collector, ai_summarizer, image_generator, line_publisher
import pdf_generator, report_uploader, ai_writer

# 公發站抓取（選用）
try:
    import mops_fetcher
except ImportError:
    mops_fetcher = None


def main():
    print("=" * 60)
    print(f"📰 每日新聞站 v4｜{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    for env_path in [Path(__file__).parent / ".env", Path(__file__).parent.parent / ".env"]:
        if env_path.exists():
            load_dotenv(env_path)
            print(f"📁 載入 .env：{env_path}")
            break

    today = datetime.now()
    date_str = today.strftime("%Y/%m/%d")
    today_iso = today.strftime("%Y-%m-%d")
    config_path = str(Path(__file__).parent.parent / "config.yaml")
    output_dir = Path(__file__).parent.parent / "output"
    output_dir.mkdir(exist_ok=True)
    cards_dir = output_dir / "cards"
    cards_dir.mkdir(exist_ok=True)

    # === 1. 抓 RSS ===
    print("\n[1/6] 📡 抓取 RSS 新聞")
    items = news_collector.collect_all(config_path, lookback_hours=30)

    # === 2. 抓公發站重大訊息 ===
    print("\n[2/6] 🏢 抓取公開資訊觀測站重大訊息")
    mops_items = []
    if mops_fetcher:
        try:
            import yaml
            cfg = yaml.safe_load(Path(config_path).read_text(encoding="utf-8"))
            keywords = cfg.get("mops_keywords", mops_fetcher.PRIORITY_KEYWORDS)
            mops_items = mops_fetcher.fetch_mops()
            mops_items = mops_fetcher.filter_priority_keywords(mops_items, keywords)
            print(f"  公發站符合關鍵字：{len(mops_items)} 條")
            # 加進主新聞列表（保留最高優先序）
            from news_collector import NewsItem
            for m in mops_items[:5]:  # 最多取 5 條
                items.append(NewsItem(
                    title=m["title"], link=m["link"], summary=m["summary"],
                    published=today.isoformat(), source=m["source"],
                    category=m["category"], weight=m["weight"], hash_id=m["title"][:12],
                ))
        except Exception as ex:
            print(f"  ⚠️ MOPS 抓取錯誤：{ex}")
    else:
        print("  ⚠️ mops_fetcher 模組未載入")

    raw_path = output_dir / "raw_news.json"
    news_collector.save_items(items, str(raw_path))

    if not items:
        print("⚠️ 所有來源無資料，發送空狀態通知")
        empty = [{"emoji": "ℹ️", "title": "今日新聞來源暫時異常",
                  "summary": "請稍後再試。", "link": "https://example.com",
                  "source": "系統", "tag": "其他", "importance": 3}]
        line_publisher.publish(empty, date_str=date_str, output_dir=str(output_dir))
        return

    # === 3. AI 摘要 + 排序（挑出 top 8）===
    print("\n[3/6] 🤖 摘要與排序（含基本翻譯）")
    weights = {
        "tw": int(os.environ.get("TOPIC_WEIGHTS_TW", 35)),
        "us": int(os.environ.get("TOPIC_WEIGHTS_US", 20)),
        "asia": int(os.environ.get("TOPIC_WEIGHTS_ASIA", 8)),
        "eu": int(os.environ.get("TOPIC_WEIGHTS_EU", 4)),
        "ind": int(os.environ.get("TOPIC_WEIGHTS_INDUSTRY", 23)),
        "macro": int(os.environ.get("TOPIC_WEIGHTS_MACRO", 5)),
    }
    max_items = int(os.environ.get("MAX_NEWS_ITEMS", 8))
    summarized = ai_summarizer.summarize(
        [it.to_dict() for it in items],
        max_items=max_items, weights=weights, today=today_iso,
    )
    sum_path = output_dir / "summarized.json"
    sum_path.write_text(json.dumps(summarized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"  已挑選 {len(summarized)} 條精選")
    if not summarized:
        return

    # === 4. Gemini 深度寫稿（每篇 + 編輯導讀 + 明日關注）===
    print("\n[4/6] ✍️ Gemini 深度寫稿")
    extras = ai_writer.enrich_with_ai(summarized)
    enriched_path = output_dir / "enriched.json"
    enriched_path.write_text(json.dumps(
        {"items": summarized, **extras}, ensure_ascii=False, indent=2), encoding="utf-8")

    # === 5. 產 LINE 圖卡 + PDF ===
    print("\n[5/6] 🎨 產生 LINE 圖卡 + 報紙風格 PDF")
    image_generator.render_all(summarized, str(cards_dir), date_str)

    pdf_path = output_dir / f"daily_report_{today_iso}.pdf"
    try:
        pdf_generator.generate_pdf(
            summarized, str(pdf_path), today_iso,
            editorial_text=extras.get("editorial", ""),
            upcoming_text=extras.get("upcoming", ""),
        )
        print(f"  ✓ PDF 已生成 {pdf_path}（{pdf_path.stat().st_size // 1024} KB）")
    except Exception as ex:
        print(f"  ❌ PDF 失敗：{ex}")
        traceback.print_exc()
        pdf_path = None

    pdf_url = None
    if pdf_path and pdf_path.exists():
        ok, msg = report_uploader.upload_pdf_to_github(str(pdf_path))
        if ok:
            pdf_url = msg
            print(f"  ✓ PDF 已上傳：{pdf_url}")
        else:
            print(f"  ⚠️ PDF 上傳失敗：{msg}")

    # === 6. LINE 推播 ===
    print("\n[6/6] 📤 LINE 推播")
    line_publisher.publish(summarized, date_str=date_str,
                           pdf_url=pdf_url, output_dir=str(output_dir))

    print("\n" + "=" * 60)
    print("✅ 完成")
    if extras.get("powered_by_ai"):
        print("   🤖 由 Gemini AI 寫稿")
    if pdf_url:
        print(f"   📥 PDF：{pdf_url}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"\n❌ 主程式例外：{ex}")
        traceback.print_exc()
        sys.exit(1)
