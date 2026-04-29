"""
pdf_generator.py v4 — 手機友善報紙風格版型
版面：800 × 1280 直式單欄，類似手機螢幕比例
特色：報紙頭版式大標、Drop Cap、引號、分節線、易讀字級
"""
from __future__ import annotations
import os
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black, Color
from reportlab.platypus import (
    BaseDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle,
    Image as RLImage, Frame, PageTemplate
)
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT, TA_JUSTIFY
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus.doctemplate import NextPageTemplate

# 嘗試引入 editorial 與 ai_writer（不一定都有）
try:
    import editorial
except ImportError:
    editorial = None


# === 手機友善頁面尺寸 ===
PAGE_W = 800
PAGE_H = 1280

# === 顏色 ===
INK   = HexColor("#1A1A1A")     # 主文字（不用純黑顯得柔和）
INK_2 = HexColor("#444444")     # 次文字
SOFT  = HexColor("#777777")     # 標註
LINE  = HexColor("#222222")     # 分隔線
CREAM = HexColor("#FAF7F0")     # 紙張底色（米色報紙感）
GOLD  = HexColor("#B8860B")     # 強調金（深金色穩重）
RED   = HexColor("#A82B2B")     # 報紙紅（標頭飾條）

TAG_COLORS = {
    "金融": HexColor("#A82B2B"),
    "台股": HexColor("#A82B2B"),
    "美股": HexColor("#1F4E79"),
    "亞股": HexColor("#C66B0E"),
    "歐股": HexColor("#5B3A8C"),
    "產業": HexColor("#1F6650"),
    "半導體": HexColor("#1F6650"),
    "餐飲": HexColor("#7A4C28"),
    "宏觀": HexColor("#806A1A"),
    "公發站": HexColor("#7A1F1F"),
    "其他": HexColor("#555555"),
}


def _register_font():
    """註冊中文字型"""
    candidates = [
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", "ZH-Bold"),
        ("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc", "ZH-Reg"),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Bold.ttc", "ZH-SerifBold"),
        ("/usr/share/fonts/opentype/noto/NotoSerifCJK-Regular.ttc", "ZH-Serif"),
        ("/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf", "ZH-Fallback"),
        ("/usr/share/fonts/truetype/droid/DroidSansFallback.ttf", "ZH-Fallback"),
        ("C:\\Windows\\Fonts\\msyhbd.ttc", "ZH-Win"),
    ]
    registered = []
    for path, name in candidates:
        if os.path.exists(path) and name not in [r[0] for r in registered]:
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                registered.append((name, path))
            except Exception:
                continue
    return registered


REGISTERED = _register_font()
FONT_BOLD = REGISTERED[0][0] if REGISTERED else "Helvetica-Bold"
FONT_REG = next((n for n, _ in REGISTERED if "Reg" in n or "Serif" in n.replace("Bold", "") and "Bold" not in n), FONT_BOLD)
FONT_SERIF = next((n for n, _ in REGISTERED if "Serif" in n), FONT_BOLD)


# === 樣式 ===

def _styles():
    return {
        # 報頭
        "masthead":     ParagraphStyle("ms",  fontName=FONT_BOLD, fontSize=42, leading=46, textColor=INK,    alignment=TA_LEFT,   tracking=0),
        "masthead_en":  ParagraphStyle("me",  fontName=FONT_REG,  fontSize=11, leading=14, textColor=GOLD,   alignment=TA_LEFT),
        "issue":        ParagraphStyle("is",  fontName=FONT_REG,  fontSize=10, leading=12, textColor=SOFT,   alignment=TA_LEFT),
        # 編輯導讀
        "section_kicker": ParagraphStyle("sk", fontName=FONT_BOLD, fontSize=10, leading=14, textColor=RED,   alignment=TA_LEFT,   spaceAfter=4),
        "section_title": ParagraphStyle("st",  fontName=FONT_BOLD, fontSize=24, leading=30, textColor=INK,   alignment=TA_LEFT,   spaceAfter=12),
        "lead":         ParagraphStyle("ld",  fontName=FONT_REG,  fontSize=14, leading=22, textColor=INK,    alignment=TA_JUSTIFY, firstLineIndent=20, spaceAfter=10),
        # 文章
        "kicker":       ParagraphStyle("kk",  fontName=FONT_BOLD, fontSize=10, leading=12, textColor=RED,    alignment=TA_LEFT),
        "headline":     ParagraphStyle("hd",  fontName=FONT_BOLD, fontSize=28, leading=34, textColor=INK,    alignment=TA_LEFT,   spaceAfter=8),
        "byline":       ParagraphStyle("by",  fontName=FONT_REG,  fontSize=10, leading=14, textColor=SOFT,   alignment=TA_LEFT,   spaceAfter=8),
        "body":         ParagraphStyle("bd",  fontName=FONT_REG,  fontSize=13, leading=22, textColor=INK,    alignment=TA_JUSTIFY, firstLineIndent=24, spaceAfter=8),
        "body_first":   ParagraphStyle("bf",  fontName=FONT_REG,  fontSize=13, leading=22, textColor=INK,    alignment=TA_JUSTIFY, spaceAfter=8),  # 第一段不縮排
        "pullquote":    ParagraphStyle("pq",  fontName=FONT_BOLD, fontSize=18, leading=28, textColor=GOLD,   alignment=TA_CENTER, spaceAfter=12, spaceBefore=12, leftIndent=20, rightIndent=20),
        "tag":          ParagraphStyle("tg",  fontName=FONT_BOLD, fontSize=11, leading=14, textColor=white,   alignment=TA_CENTER),
        "footer":       ParagraphStyle("ft",  fontName=FONT_REG,  fontSize=9,  leading=12, textColor=SOFT,    alignment=TA_LEFT),
        "footer_c":     ParagraphStyle("fc",  fontName=FONT_REG,  fontSize=9,  leading=12, textColor=SOFT,    alignment=TA_CENTER),
    }


# === 頁面背景 ===

def draw_page_bg(canv, doc):
    """每頁紙張底色 + 頁眉頁腳"""
    canv.setFillColor(CREAM)
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # 頁眉細線
    canv.setStrokeColor(LINE)
    canv.setLineWidth(0.5)
    canv.line(40, PAGE_H - 30, PAGE_W - 40, PAGE_H - 30)
    # 頁眉文字（小）
    canv.setFillColor(SOFT)
    canv.setFont(FONT_REG, 9)
    canv.drawString(40, PAGE_H - 22, "每日財經早報")
    canv.drawRightString(PAGE_W - 40, PAGE_H - 22, datetime.now().strftime("%Y/%m/%d"))
    # 頁腳細線
    canv.line(40, 40, PAGE_W - 40, 40)
    canv.drawString(40, 25, "DAILY MARKET BRIEF")
    canv.drawRightString(PAGE_W - 40, 25, f"P. {doc.page}")


def draw_cover_bg(canv, doc):
    """封面：純米色 + 紅色頂條 + 金線"""
    canv.setFillColor(CREAM)
    canv.rect(0, 0, PAGE_W, PAGE_H, fill=1, stroke=0)
    # 紅色頂條
    canv.setFillColor(RED)
    canv.rect(0, PAGE_H - 12, PAGE_W, 12, fill=1, stroke=0)
    # 金色細線（在大標下方）
    canv.setFillColor(GOLD)
    canv.rect(40, PAGE_H - 240, 80, 4, fill=1, stroke=0)
    # 底部裝飾
    canv.rect(0, 0, PAGE_W, 6, fill=1, stroke=0)


# === 工具元件 ===

def _hr(width=PAGE_W - 100, height=0.5, color=LINE, space_before=4, space_after=8):
    t = Table([[""]], colWidths=[width], rowHeights=[height])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
    ]))
    return [Spacer(1, space_before), t, Spacer(1, space_after)]


def _tag_pill(tag: str, font_size: int = 10):
    color = TAG_COLORS.get(tag, TAG_COLORS["其他"])
    text = f"  {tag}  "
    style = ParagraphStyle("tagp", fontName=FONT_BOLD, fontSize=font_size, leading=font_size+2,
                           textColor=white, alignment=TA_CENTER)
    p = Paragraph(text, style)
    t = Table([[p]], colWidths=[60], rowHeights=[font_size + 8])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), color),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
    ]))
    return t


def _drop_cap_paragraph(text: str, body_style: ParagraphStyle) -> Paragraph:
    """段落首字放大（drop cap 效果）"""
    if not text:
        return Paragraph("", body_style)
    first = text[0]
    rest = text[1:]
    cap_html = f'<font size="32" color="#A82B2B"><b>{first}</b></font>{rest}'
    s = ParagraphStyle("dc", fontName=FONT_REG, fontSize=13, leading=22,
                       textColor=INK, alignment=TA_JUSTIFY)
    return Paragraph(cap_html, s)


def _split_paragraphs(text: str) -> List[str]:
    """把長文按段落分（雙換行 / 換行）"""
    if not text:
        return []
    paras = []
    for chunk in text.split("\n\n"):
        chunk = chunk.strip()
        if not chunk:
            continue
        paras.append(chunk)
    if len(paras) <= 1:
        # 沒分段，按單換行嘗試
        paras = [p.strip() for p in text.split("\n") if p.strip()]
    return paras


def _pull_quote_text(text: str, max_len: int = 60) -> str:
    """抽一句當引號"""
    if not text:
        return ""
    # 找第一句句點
    for sep in ["。", "！", "？", "；"]:
        idx = text.find(sep)
        if 30 <= idx <= max_len:
            return text[:idx + 1]
    return text[:max_len] + "…" if len(text) > max_len else text


# === 區塊 ===

def build_cover(items, summary, date_str, weekday_str, styles):
    flow = []
    flow.append(Spacer(1, 60))

    # 「報紙刊頭」
    flow.append(Paragraph('<font color="#A82B2B"><b>VOL. 1</b></font>　|　每日發行', styles["issue"]))
    flow.append(Spacer(1, 8))
    flow.append(Paragraph("每日財經早報", styles["masthead"]))
    flow.append(Paragraph("DAILY MARKET BRIEF　·　Editorially Curated", styles["masthead_en"]))
    flow.append(Spacer(1, 30))
    flow.append(Paragraph(f"{date_str}　{weekday_str}", styles["lead"]))

    flow.append(Spacer(1, 40))

    # 大紅標：今日頭條
    if items:
        top = items[0]
        flow.append(Paragraph("TODAY'S HEADLINE", styles["section_kicker"]))
        flow.append(Paragraph(top.get("title", ""), styles["section_title"]))
        flow.append(Paragraph(f"分類：{top.get('tag', '')}　·　重要性 {top.get('importance', 5)}/10", styles["byline"]))
        flow.append(Spacer(1, 16))

    # 條列今日 8 大重點（給目錄感）
    flow.append(Paragraph("INSIDE THIS ISSUE", styles["section_kicker"]))
    flow.append(Spacer(1, 8))
    rows = [["#", "類別", "標題"]]
    for i, item in enumerate(items, 1):
        title = item.get("title", "")
        if len(title) > 26:
            title = title[:25] + "…"
        rows.append([str(i), item.get("tag", "其他"), title])
    table = Table(rows, colWidths=[30, 60, PAGE_W - 220])
    table.setStyle(TableStyle([
        ("FONT", (0, 0), (-1, -1), FONT_REG, 11),
        ("FONT", (0, 0), (-1, 0), FONT_BOLD, 10),
        ("TEXTCOLOR", (0, 0), (-1, 0), white),
        ("BACKGROUND", (0, 0), (-1, 0), INK),
        ("TEXTCOLOR", (0, 1), (-1, -1), INK),
        ("LINEBELOW", (0, 0), (-1, 0), 0.5, INK),
        ("LINEBELOW", (0, 1), (-1, -1), 0.3, HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    flow.append(table)
    flow.append(PageBreak())
    return flow


def build_editorial(editorial_text, upcoming_text, styles):
    flow = []
    # 編輯導讀
    flow.append(Spacer(1, 20))
    flow.append(Paragraph("EDITORIAL", styles["section_kicker"]))
    flow.append(Paragraph("編輯導讀", styles["section_title"]))

    # 內文段落
    paras = _split_paragraphs(editorial_text)
    for i, p in enumerate(paras):
        if i == 0:
            flow.append(_drop_cap_paragraph(p, styles["body_first"]))
        else:
            flow.append(Paragraph(p, styles["body"]))
    flow.append(Spacer(1, 30))

    # 分節線
    flow.extend(_hr())

    # 明日值得關注
    flow.append(Paragraph("UPCOMING", styles["section_kicker"]))
    flow.append(Paragraph("明日 ‧ 本週值得關注", styles["section_title"]))
    paras = _split_paragraphs(upcoming_text)
    for p in paras:
        flow.append(Paragraph(p, styles["body_first"]))

    flow.append(PageBreak())
    return flow


def build_article_page(item, idx, total, styles):
    flow = []

    # 文章 kicker（編號 + 分類）
    flow.append(Spacer(1, 10))
    tag = item.get("tag", "其他")
    flow.append(Paragraph(f"N° {idx:02d} / {total:02d}　·　{tag}", styles["kicker"]))
    flow.append(Spacer(1, 6))

    # 大標題
    flow.append(Paragraph(item.get("title", ""), styles["headline"]))

    # 來源
    importance = item.get("importance", 5)
    src = item.get("source", "")
    flow.append(Paragraph(f"來源：{src}　·　重要性 {importance}/10", styles["byline"]))

    # 紅金線
    flow.extend(_hr(color=RED, height=2, space_before=2, space_after=14))

    # 內文（用 long_text，若無則用 summary）
    long_text = item.get("long_text") or item.get("summary", "")
    paras = _split_paragraphs(long_text)

    if paras:
        # 第一段 drop cap
        flow.append(_drop_cap_paragraph(paras[0], styles["body_first"]))

        # 中間插個引號（如果段落多）
        if len(paras) >= 2:
            quote = _pull_quote_text(paras[0], max_len=50)
            flow.append(Paragraph(f"「{quote}」", styles["pullquote"]))

        for p in paras[1:]:
            flow.append(Paragraph(p, styles["body"]))

    flow.append(Spacer(1, 16))

    # 編輯小評（規則式）
    if editorial:
        try:
            note = editorial.interpret_news(item)
            if note:
                flow.extend(_hr(width=200, height=0.5))
                flow.append(Paragraph("EDITOR'S NOTE　|　編輯小評", styles["section_kicker"]))
                flow.append(Spacer(1, 4))
                note_style = ParagraphStyle("nt", fontName=FONT_REG, fontSize=12, leading=20,
                                            textColor=INK_2, alignment=TA_LEFT, leftIndent=12)
                flow.append(Paragraph(note, note_style))
        except Exception:
            pass

    # 原文連結
    link = item.get("link", "")
    if link:
        flow.append(Spacer(1, 12))
        link_style = ParagraphStyle("lnk", fontName=FONT_REG, fontSize=9, leading=12,
                                    textColor=SOFT, alignment=TA_LEFT)
        flow.append(Paragraph(f'原文：<link href="{link}"><font color="#5B3A8C">{link[:80]}</font></link>',
                              link_style))

    flow.append(PageBreak())
    return flow


def build_back_cover(styles):
    flow = []
    flow.append(Spacer(1, 200))
    flow.append(Paragraph("— 完 —", styles["section_title"]))
    flow.append(Spacer(1, 30))
    flow.append(Paragraph("感謝閱讀", styles["lead"]))
    flow.append(Paragraph("明日 07:30 同一時間、同一頻道", styles["lead"]))
    flow.append(Spacer(1, 80))
    flow.extend(_hr(width=200, color=GOLD, height=1))
    flow.append(Spacer(1, 12))
    flow.append(Paragraph(
        "本報告由自動化系統彙整，內容僅供資訊參考，不構成投資建議。<br/>"
        "新聞來源：公開財經媒體 RSS · 公開資訊觀測站 OpenAPI<br/>"
        "AI 寫稿：Google Gemini · 編輯部：規則式自動分析",
        styles["footer_c"]))
    return flow


# === 主入口 ===

def generate_pdf(items, output_path, date_str=None,
                 editorial_text="", upcoming_text=""):
    if not date_str:
        date_str = datetime.now().strftime("%Y-%m-%d")

    weekday = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"][datetime.now().weekday()]

    if not editorial_text:
        if editorial:
            theme = editorial.detect_main_theme(items)
            summary = editorial.daily_summary_numbers(items)
            editorial_text = editorial.editor_intro(theme, summary)
        else:
            editorial_text = "今日彙整精選新聞，請依個別內文閱讀。"

    if not upcoming_text:
        if editorial:
            events = editorial.upcoming_events()
            upcoming_text = "本週重點：" + "；".join(f"[{e['time']}] {e['event']}" for e in events)
        else:
            upcoming_text = "明日及本週財經數據與事件，請密切留意公開財經媒體更新。"

    styles = _styles()

    doc = BaseDocTemplate(
        output_path, pagesize=(PAGE_W, PAGE_H),
        leftMargin=50, rightMargin=50,
        topMargin=50, bottomMargin=55,
        title=f"每日財經早報 {date_str}",
        author="DAILY MARKET BRIEF",
    )

    frame = Frame(50, 55, PAGE_W - 100, PAGE_H - 105, id="main")
    cover_template = PageTemplate(id="cover", frames=frame, onPage=draw_cover_bg)
    content_template = PageTemplate(id="content", frames=frame, onPage=draw_page_bg)
    doc.addPageTemplates([cover_template, content_template])

    summary = {"total": len(items)}
    flow = []
    flow.extend(build_cover(items, summary, date_str, weekday, styles))
    flow.append(NextPageTemplate("content"))
    flow.extend(build_editorial(editorial_text, upcoming_text, styles))
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
    # 給每篇加 long_text（測試用）
    for it in items:
        if "long_text" not in it:
            it["long_text"] = (it.get("summary", "") + "\n\n" + 
                               "本則新聞涉及市場關注議題，相關連動值得追蹤。")
    path = generate_pdf(items, out)
    print(f"📄 PDF 已生成：{path}（{os.path.getsize(path) // 1024} KB）")
