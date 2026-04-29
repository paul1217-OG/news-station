"""
main.py v3 — 整合 PDF 生成 + GitHub 上傳 + LINE 推播附 PDF 連結
"""
from __future__ import annotations
import os, sys, json, traceback
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dotenv import load_dotenv
import news_collector, ai_summarizer, image_generator, line_publisher
import pdf_generator, report_uploader


def main():
    print("=" * 60)
    print(f"📰 每日新聞站 v3｜{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
    print("\n[1/5] 📡 抓取 RSS 新聞")
    items = news_collector.collect_all(config_path, lookback_hours=30)
    raw_path = output_dir / "raw_news.json"
    news_collector.save_items(items, str(raw_path))

    if not items:
        print("⚠️ 所有 RSS 來源無法取得，發送空狀態通知")
        empty_news = [{
            "emoji": "ℹ️", "title": "今日新聞來源暫時異常",
            "summary": "請稍後再試或檢查 RSS。", "link": "https://example.com",
            "source": "系統", "tag": "其他", "importance": 3,
        }]
        line_publisher.publish(empty_news, date_str=date_str, output_dir=str(output_dir))
        return

    # === 2. AI 摘要 ===
    print("\n[2/5] 🤖 AI 摘要與排序（含翻譯）")
    weights = {
        "tw": int(os.environ.get("TOPIC_WEIGHTS_TW", 40)),
        "us": int(os.environ.get("TOPIC_WEIGHTS_US", 25)),
        "asia": int(os.environ.get("TOPIC_WEIGHTS_ASIA", 10)),
        "eu": int(os.environ.get("TOPIC_WEIGHTS_EU", 5)),
        "ind": int(os.environ.get("TOPIC_WEIGHTS_INDUSTRY", 15)),
        "macro": int(os.environ.get("TOPIC_WEIGHTS_MACRO", 5)),
    }
    max_items = int(os.environ.get("MAX_NEWS_ITEMS", 8))
    summarized = ai_summarizer.summarize(
        [it.to_dict() for it in items],
        max_items=max_items, weights=weights, today=today_iso,
    )
    sum_path = output_dir / "summarized.json"
    sum_path.write_text(json.dumps(summarized, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"💾 已挑選 {len(summarized)} 條 → {sum_path}")
    if not summarized:
        return

    # === 3. 產 LINE 圖卡 ===
    print("\n[3/5] 🎨 產生 LINE 圖卡")
    image_generator.render_all(summarized, str(cards_dir), date_str)

    # === 4. 產 PDF 報告 + 上傳 GitHub ===
    print("\n[4/5] 📄 產生 PDF 報告")
    pdf_path = output_dir / f"daily_report_{today_iso}.pdf"
    try:
        pdf_generator.generate_pdf(summarized, str(pdf_path), today_iso)
        print(f"✓ PDF 已生成 {pdf_path}（{pdf_path.stat().st_size // 1024} KB）")
    except Exception as ex:
        print(f"❌ PDF 生成失敗：{ex}")
        pdf_path = None

    pdf_url = None
    if pdf_path and pdf_path.exists():
        ok, msg = report_uploader.upload_pdf_to_github(str(pdf_path))
        if ok:
            pdf_url = msg
            print(f"✓ PDF 已上傳：{pdf_url}")
        else:
            print(f"⚠️ PDF 上傳失敗（不影響推播）：{msg}")

    # === 5. LINE 推播 ===
    print("\n[5/5] 📤 LINE 推播")
    line_publisher.publish(summarized, date_str=date_str,
                           pdf_url=pdf_url, output_dir=str(output_dir))

    print("\n" + "=" * 60)
    print("✅ 完成")
    if pdf_url:
        print(f"📥 PDF 報告：{pdf_url}")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except Exception as ex:
        print(f"\n❌ 主程式發生例外：{ex}")
        traceback.print_exc()
        sys.exit(1)
