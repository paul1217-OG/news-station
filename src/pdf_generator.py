"""
pdf_generator.py — Wire 雜誌風格的每日 PDF 報告
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image as RLImage, KeepTogether, Frame, PageTemplate, BaseDocTemplate
)
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

import editorial


# ===== 設計系統（呼應圖卡視覺）=====
INK_900 = HexColor("#080E20")
INK_800 = HexColor("#101832")
INK_700 = HexColor("#18264B")
INK_600 = HexColor("#283C6E")
GOLD   = HexColor("#F5C038")
WHITE  = HexColor("#FAFBFE")
SOFT   = HexColor("#B4C3DC")
MUTED  = HexColor("#8291AF")

TAG_COLORS = {
    "台股": HexColor("#DC4650"), "美股": HexColor("#3C82DC"),
    "亞股": HexColor("#FA8C32"), "歐股": HexColor("#8C5AC8"),
    "產業": HexColor("#2DAF8C"), "宏觀": HexColor("#C8A046"),
    "其他": HexColor("#6E7896"),
}


def _register_chinese_font():
    """註冊可用的中文字型給 ReportLab"""
    candidates = [
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "NotoSansBold"),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "NotoSansReg"),
        ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "DroidFallback"),
        ("/usr/share/fonts/truetype/droid/DroidSansFallback.ttf", "DroidFallback"),
        ("C:\\Windows\\Fonts\\msyhbd.ttc", "MSYahei"),
        ("C:\\Windows\\Fonts\\msjh.ttc", "MSJhengHei"),
    ]
    for path, name in candidates:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                return name
            except Exception:
                continue
    return "Helvetica"


FONT = _register_chinese_font()


def _styles():
    """建立所有段落樣式"""
    return {
        "cover_title":     ParagraphStyle("ct",  fontName=FONT, fontSize=42, leading=52, textColor=WHITE,  alignment=TA_LEFT),
        "cover_sub":       ParagraphStyle("cs",  fontName=FONT, fontSize=14, leading=20, textColor=GOLD,   alignment=TA_LEFT),
        "cover_meta":      ParagraphStyle("cm",  fontName=FONT, fontSize=10, leading=14, textColor=SOFT,   alignment=TA_LEFT),
        "section_h":       ParagraphStyle("sh",  fontName=FONT, fontSize=18, leading=24, textColor=GOLD,   alignment=TA_LEFT, spaceAfter=8),
        "h_eyebrow":       ParagraphStyle("he",  fontName=FONT, fontSize=8,  leading=12, textColor=GOLD,   alignment=TA_LEFT),
        "headline":        ParagraphStyle("hd",  fontName=FONT, fontSize=22, leading=28, textColor=WHITE,  alignment=TA_LEFT, spaceAfter=4),
        "deck":            ParagraphStyle("dk",  fontName=FONT, fontSize=11, leading=16, textColor=SOFT,   alignment=TA_LEFT, spaceAfter=8),
        "body":            ParagraphStyle("bd",  fontName=FONT, fontSize=10, leading=16, textColor=WHITE,  alignment=TA_JUSTIFY),
        "interpretation":  ParagraphStyle("ip",  fontName=FONT, fontSize=9.5,leading=15, textColor=GOLD,   alignment=TA_LEFT,  leftIndent=8, borderPadding=4),
        "byline":          ParagraphStyle("bl",  fontName=FONT, fontSize=8,  leading=12, textColor=MUTED,  alignment=TA_LEFT),
        "intro":           ParagraphStyle("in",  fontName=FONT, fontSize=11, leading=18, textColor=WHITE,  alignment=TA_JUSTIFY),
        "tag":             ParagraphStyle("tg",  fontName=FONT, fontSize=9,  leading=11, textColor=WHITE,  alignment=TA_CENTER),
        "footer":          ParagraphStyle("ft",  fontName=FONT, fontSize=7,  leading=10, textColor=MUTED,  alignment=TA_CENTER),
    }


# === 頁面背景與邊飾 ===
def draw_page_bg(canv, doc):
    """每頁背景：深色 + 上下金線"""
    w, h = A4
    canv.setFillColor(INK_900)
    canv.rect(0, 0, w, h, fill=1, stroke=0)

    # 頂部金條
    canv.setFillColor(GOLD)
    canv.rect(0, h - 4*mm, w, 4*mm, fill=1, stroke=0)

    # 底部金線細條
    canv.rect(0, 0, w, 1.5*mm, fill=1, stroke=0)

    # 頁碼 + 日期 footer
    canv.setFillColor(MUTED)
    canv.setFont(FONT, 8)
    canv.drawString(15*mm, 5*mm, f"DAILY MARKET BRIEF · {datetime.now().strftime('%Y/%m/%d')}")
    canv.drawRightString(w - 15*mm, 5*mm, f"P. {doc.page}")


def draw_cover_bg(canv, doc):
    """封面頁特別背景"""
    w, h = A4
    canv.setFillColor(INK_900)
    canv.rect(0, 0, w, h, fill=1, stroke=0)
    # 大金條
    canv.setFillColor(GOLD)
    canv.rect(0, h - 8*mm, w, 8*mm, fill=1, stroke=0)
    canv.rect(0, 0, w, 6*mm, fill=1, stroke=0)
    # 縱向裝飾線
    canv.setFillColor(GOLD)
    canv.rect(15*mm, h - 50*mm, 30*mm, 2*mm, fill=1, stroke=0)


# === Tag 膠囊（用 Table 模擬）===
def make_tag_pill(tag, styles):
    color = TAG_COLORS.get(tag, TAG_COLORS["其他"])
    t = Table([[Paragraph(f"<b>{tag}</b>", styles["tag"])]],
              colWidths=[28*mm], rowHeights=[7*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), color),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("TEXTCOLOR", (0,0), (-1,-1), white),
        ("BOX", (0,0), (-1,-1), 0, color),
    ]))
    return t


def importance_stars(score):
    full = min(int(score / 2), 5)
    return "★" * full + "☆" * (5 - full)


# === 各區段建構函式 ===

def build_cover(items, theme, summary, styles):
    flow = []
    flow.append(Spacer(1, 50*mm))
    flow.append(Paragraph(f'<font color="#F5C038">{datetime.now().strftime("%Y / %m / %d")}</font>', styles["cover_sub"]))
    flow.append(Spacer(1, 8*mm))
    flow.append(Paragraph("每日財經早報", styles["cover_title"]))
    flow.append(Spacer(1, 4*mm))
    flow.append(Paragraph("DAILY MARKET BRIEF", styles["cover_sub"]))
    flow.append(Spacer(1, 30*mm))

    # 主旋律 box
    sector = theme.get("sector", "綜合")
    narrative = theme.get("narrative", "")
    count = theme.get("count", 0)
    flow.append(Paragraph(f'<font color="#F5C038">今 日 主 旋 律</font>', styles["h_eyebrow"]))
    flow.append(Spacer(1, 2*mm))
    flow.append(Paragraph(f"<b>{narrative}</b>", styles["headline"]))
    flow.append(Paragraph(f"今日 {summary['total']} 則精選中，{count} 則涉及此主題；平均重要性 {summary['avg_importance']}/10", styles["deck"]))

    flow.append(Spacer(1, 10*mm))

    # 分類分布條
    by_tag = summary.get("by_tag", {})
    rows = [["分類", "則數"]]
    for k, v in by_tag.items():
        rows.append([k, str(v)])
    table = Table(rows, colWidths=[35*mm, 25*mm])
    table.setStyle(TableStyle([
        ("FONT", (0,0), (-1,-1), FONT),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("TEXTCOLOR", (0,0), (-1,-1), WHITE),
        ("BACKGROUND", (0,0), (-1,0), GOLD),
        ("TEXTCOLOR", (0,0), (-1,0), INK_900),
        ("BACKGROUND", (0,1), (-1,-1), INK_700),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [INK_700, INK_800]),
        ("GRID", (0,0), (-1,-1), 0.3, INK_600),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("LEFTPADDING", (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]))
    flow.append(table)

    flow.append(PageBreak())
    return flow


def build_editorial_section(intro_text, events, styles):
    flow = []
    flow.append(Paragraph('<font color="#F5C038">EDITORIAL · 編 輯 部</font>', styles["h_eyebrow"]))
    flow.append(Spacer(1, 3*mm))
    flow.append(Paragraph("今日導讀", styles["section_h"]))
    flow.append(Paragraph(intro_text, styles["intro"]))
    flow.append(Spacer(1, 10*mm))

    flow.append(Paragraph('<font color="#F5C038">UPCOMING · 值 得 關 注</font>', styles["h_eyebrow"]))
    flow.append(Spacer(1, 3*mm))
    flow.append(Paragraph("明日 / 本週留意", styles["section_h"]))
    for ev in events:
        flow.append(Paragraph(f"<b><font color='#F5C038'>[{ev['time']}]</font></b> &nbsp;&nbsp; {ev['event']}", styles["body"]))
        flow.append(Spacer(1, 2*mm))

    flow.append(PageBreak())
    return flow


def build_article_page(item, idx, total, styles):
    flow = []
    tag = item.get("tag", "其他")
    importance = item.get("importance", 5)

    # eyebrow（編號 + 分類）
    flow.append(Paragraph(
        f'<font color="#F5C038">N° {idx:02d} / {total:02d}</font> &nbsp;&nbsp;|&nbsp;&nbsp; <font color="#B4C3DC">{tag}</font>',
        styles["h_eyebrow"]
    ))
    flow.append(Spacer(1, 4*mm))

    # 標題
    flow.append(Paragraph(item.get("title", ""), styles["headline"]))
    flow.append(Spacer(1, 2*mm))

    # 副標
    deck = f"來源：{item.get('source', '未署名')}　·　重要性 {importance_stars(importance)} ({importance}/10)"
    flow.append(Paragraph(deck, styles["deck"]))

    # 金線分隔
    line = Table([[""]], colWidths=[40*mm], rowHeights=[1*mm])
    line.setStyle(TableStyle([("BACKGROUND", (0,0), (-1,-1), GOLD)]))
    flow.append(line)
    flow.append(Spacer(1, 4*mm))

    # 內文（翻譯後摘要）
    summary_text = item.get("summary", "")
    flow.append(Paragraph(summary_text, styles["body"]))
    flow.append(Spacer(1, 6*mm))

    # 編輯小評
    interpretation = editorial.interpret_news(item)
    flow.append(Paragraph('<font color="#F5C038"><b>EDITOR\'S NOTE</b></font>', styles["h_eyebrow"]))
    flow.append(Paragraph(interpretation, styles["interpretation"]))
    flow.append(Spacer(1, 4*mm))

    # 原文連結
    link = item.get("link", "")
    if link:
        flow.append(Paragraph(f'<link href="{link}"><font color="#8291AF">原文連結 → {link[:60]}{"..." if len(link) > 60 else ""}</font></link>', styles["byline"]))

    flow.append(PageBreak())
    return flow


def build_back_cover(styles):
    flow = []
    flow.append(Spacer(1, 80*mm))
    flow.append(Paragraph('<font color="#F5C038">— END OF BRIEFING —</font>', styles["section_h"]))
    flow.append(Spacer(1, 8*mm))
    flow.append(Paragraph("感謝閱讀。明日 07:30 同一時間、同一頻道。", styles["intro"]))
    flow.append(Spacer(1, 30*mm))
    flow.append(Paragraph(
        "本報告由自動化系統彙整，內容僅供資訊參考，不構成投資建議。<br/>"
        "新聞來源：公開財經媒體 RSS。翻譯：Google Translate。<br/>"
        "編輯部：規則式自動分析（無 AI 介入）。",
        styles["footer"]
    ))
    return flow


# === 主入口 ===

def generate_pdf(items, output_path, date_str=None):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 編輯部分析
    theme = editorial.detect_main_theme(items)
    summary = editorial.daily_summary_numbers(items)
    intro_text = editorial.editor_intro(theme, summary)
    events = editorial.upcoming_events()

    styles = _styles()

    # 自訂模板
    doc = BaseDocTemplate(
        output_path,
        pagesize=A4,
        leftMargin=15*mm, rightMargin=15*mm,
        topMargin=18*mm, bottomMargin=12*mm,
        title=f"每日財經早報 {date_str}",
        author="DAILY MARKET BRIEF",
    )

    # 兩種模板：封面 + 內頁
    frame = Frame(15*mm, 12*mm, A4[0]-30*mm, A4[1]-30*mm, id="main")
    cover_template = PageTemplate(id="cover", frames=frame, onPage=draw_cover_bg)
    content_template = PageTemplate(id="content", frames=frame, onPage=draw_page_bg)
    doc.addPageTemplates([cover_template, content_template])

    flow = []
    flow.extend(build_cover(items, theme, summary, styles))
    flow.append(__import__("reportlab.platypus.doctemplate", fromlist=["NextPageTemplate"]).NextPageTemplate("content"))
    flow.extend(build_editorial_section(intro_text, events, styles))
    for i, item in enumerate(items, 1):
        flow.extend(build_article_page(item, i, len(items), styles))
    flow.extend(build_back_cover(styles))

    doc.build(flow)
    return output_path


if __name__ == "__main__":
    import json, sys
    src = sys.argv[1] if len(sys.argv) > 1 else "../output/summarized.json"
    out = sys.argv[2] if len(sys.argv) > 2 else "../output/daily_report.pdf"
    items = json.loads(open(src, encoding="utf-8").read())
    path = generate_pdf(items, out)
    print(f"📄 PDF 已生成：{path}")
    print(f"   大小：{os.path.getsize(path) / 1024:.1f} KB")
