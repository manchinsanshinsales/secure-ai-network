import os
import sys
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def setup_font():
    """NotoSansJPフォスタを登録する"""
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    font_path = os.path.join(workspace_dir, "assets", "fonts", "NotoSansJP-VF.ttf")
    if not os.path.exists(font_path):
        print(f"Error: Font not found at {font_path}", file=sys.stderr)
        sys.exit(1)
    
    # Register the TrueType font
    pdfmetrics.registerFont(TTFont('NotoSansJP', font_path))
    print(f"[+] NotoSansJP font registered from: {font_path}")

def make_cell(text, style, align="left"):
    """テーブルのセル用にParagraphオブジェクトを生成する（セル内改行を可能にするため）"""
    cell_style = ParagraphStyle(
        'TableCellStyle',
        parent=style,
        fontName='NotoSansJP',
        fontSize=9,
        leading=11,
        alignment=0 if align == "left" else (2 if align == "right" else 1)
    )
    return Paragraph(str(text), cell_style)

def generate_pdf(output_filename="dummy_financials.pdf"):
    setup_font()
    
    # ページ設定: A4サイズ、余白20mm
    doc = SimpleDocTemplate(
        output_filename,
        pagesize=A4,
        rightMargin=20*mm,
        leftMargin=20*mm,
        topMargin=20*mm,
        bottomMargin=20*mm
    )
    
    styles = getSampleStyleSheet()
    
    # カスタムスタイルの定義
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='NotoSansJP',
        fontSize=24,
        leading=28,
        textColor=colors.HexColor('#1A365D'),
        alignment=1, # Center
        spaceAfter=15
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='NotoSansJP',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4A5568'),
        alignment=1,
        spaceAfter=30
    )
    
    h1_style = ParagraphStyle(
        'Heading1',
        parent=styles['Heading1'],
        fontName='NotoSansJP',
        fontSize=16,
        leading=20,
        textColor=colors.HexColor('#1A365D'),
        spaceBefore=15,
        spaceAfter=10,
        keepWithNext=True
    )
    
    body_style = ParagraphStyle(
        'BodyText',
        parent=styles['Normal'],
        fontName='NotoSansJP',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#2D3748'),
        spaceAfter=8
    )

    story = []
    
    # ================= 1ページ目: 表紙 & 会社概要 =================
    story.append(Spacer(1, 40*mm))
    story.append(Paragraph("架空商事株式会社", title_style))
    story.append(Paragraph("第12期 財務諸表報告書<br/>（自 2025年4月1日 至 2026年3月31日）", subtitle_style))
    story.append(Spacer(1, 20*mm))
    
    story.append(Paragraph("■ 会社概要", h1_style))
    company_info_data = [
        [make_cell("商号", body_style), make_cell("架空商事株式会社", body_style)],
        [make_cell("本店所在地", body_style), make_cell("東京都千代田区大手町一丁目1番1号", body_style)],
        [make_cell("設立", body_style), make_cell("2015年4月1日（第12期決算）", body_style)],
        [make_cell("資本金", body_style), make_cell("100,000,000円", body_style)],
        [make_cell("代表者", body_style), make_cell("代表取締役　架空太郎", body_style)],
        [make_cell("主な事業内容", body_style), make_cell("一般輸出入業、国内外における商品の売買及びその仲介", body_style)]
    ]
    
    info_table = Table(company_info_data, colWidths=[40*mm, 120*mm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (0,-1), colors.HexColor('#EDF2F7')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E0')),
    ]))
    story.append(info_table)
    story.append(PageBreak())
    
    # ================= 2ページ目: 貸借対照表 (B/S) =================
    story.append(Paragraph("■ 貸借対照表 (Balance Sheet)", h1_style))
    story.append(Paragraph("（単位: 百万円）", ParagraphStyle('RightText', parent=body_style, alignment=2)))
    
    # B/Sテーブルヘッダー
    bs_header = [
        make_cell("科目", body_style),
        make_cell("第10期<br/>(2023年度末)", body_style, "right"),
        make_cell("第11期<br/>(2024年度末)", body_style, "right"),
        make_cell("第12期<br/>(2025年度末)", body_style, "right")
    ]
    
    bs_rows = [
        bs_header,
        # 資産の部
        [make_cell("<b>【資産の部】</b>", body_style), "", "", ""],
        [make_cell("流動資産", body_style), "", "", ""],
        [make_cell("　現金及び預金", body_style), "300", "380", "450"],
        [make_cell("　受取手形及び売掛金", body_style), "150", "170", "200"],
        [make_cell("　有価証券", body_style), "50", "50", "80"],
        [make_cell("　棚卸資産", body_style), "80", "90", "100"],
        [make_cell("　その他流動資産", body_style), "20", "25", "30"],
        [make_cell("　流動資産合計", body_style), "600", "715", "860"],
        [make_cell("固定資産", body_style), "", "", ""],
        [make_cell("　有形固定資産合計", body_style), "370", "370", "400"],
        [make_cell("　無形固定資産", body_style), "10", "8", "15"],
        [make_cell("　投資その他の資産", body_style), "50", "60", "70"],
        [make_cell("　固定資産合計", body_style), "430", "438", "485"],
        [make_cell("<b>資産合計</b>", body_style), "1,030", "1,153", "1,345"],
        # 負債の部
        [make_cell("<b>【負債の部】</b>", body_style), "", "", ""],
        [make_cell("流動負債", body_style), "", "", ""],
        [make_cell("　支払手形及び買掛金", body_style), "100", "110", "130"],
        [make_cell("　短期借入金", body_style), "150", "235", "365"],
        [make_cell("　未払法人税等", body_style), "12", "25", "32"],
        [make_cell("　その他流動負債", body_style), "38", "45", "53"],
        [make_cell("　流動負債合計", body_style), "300", "415", "580"],
        [make_cell("固定負債", body_style), "", "", ""],
        [make_cell("　社債", body_style), "50", "50", "50"],
        [make_cell("　長期借入金", body_style), "200", "170", "150"],
        [make_cell("　退職給付引当金", body_style), "30", "33", "35"],
        [make_cell("　その他固定負債", body_style), "10", "10", "10"],
        [make_cell("　固定負債合計", body_style), "290", "263", "245"],
        [make_cell("<b>負債合計</b>", body_style), "590", "678", "825"],
        # 純資産の部
        [make_cell("<b>【純資産の部】</b>", body_style), "", "", ""],
        [make_cell("株主資本", body_style), "", "", ""],
        [make_cell("　資本金", body_style), "100", "100", "100"],
        [make_cell("　資本剰余金", body_style), "50", "50", "50"],
        [make_cell("　利益剰余金", body_style), "290", "325", "370"],
        [make_cell("<b>純資産合計</b>", body_style), "440", "475", "520"],
        [make_cell("<b>負債・純資産合計</b>", body_style), "1,030", "1,153", "1,345"]
    ]
    
    # 列幅の設定
    bs_table = Table(bs_rows, colWidths=[70*mm, 30*mm, 30*mm, 30*mm])
    
    # テーブルスタイルの設定
    bs_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A365D')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ])
    
    # ヘッダー行の文字色を白にするためのTableStyle調整
    for i in range(4):
        bs_style.add('TEXTCOLOR', (i,0), (i,0), colors.white)
        
    # 合計行や重要行の背景やフォントウェイトを強調
    highlight_rows = [14, 29, 35, 36]  # 資産合計、負債合計、純資産合計、負債・純資産合計
    for r in highlight_rows:
        bs_style.add('BACKGROUND', (0, r), (-1, r), colors.HexColor('#EDF2F7'))
        bs_style.add('LINEABOVE', (0, r), (-1, r), 1.5, colors.HexColor('#1A365D'))
        bs_style.add('LINEBELOW', (0, r), (-1, r), 1.5, colors.HexColor('#1A365D'))
        
    bs_table.setStyle(bs_style)
    story.append(bs_table)
    story.append(PageBreak())
    
    # ================= 3ページ目: 損益計算書 (P/L) =================
    story.append(Paragraph("■ 損益計算書 (Profit and Loss Statement)", h1_style))
    story.append(Paragraph("（単位: 百万円）", ParagraphStyle('RightText2', parent=body_style, alignment=2)))
    
    pl_header = [
        make_cell("科目", body_style),
        make_cell("第10期<br/>(2023年度)", body_style, "right"),
        make_cell("第11期<br/>(2024年度)", body_style, "right"),
        make_cell("第12期<br/>(2025年度)", body_style, "right")
    ]
    
    pl_rows = [
        pl_header,
        [make_cell("<b>売上高</b>", body_style), "1,000", "1,120", "1,280"],
        [make_cell("　売上原価", body_style), "700", "770", "870"],
        [make_cell("<b>売上総利益</b>", body_style), "300", "350", "410"],
        [make_cell("　販売費及び一般管理費", body_style), "250", "280", "310"],
        [make_cell("　　役員報酬", body_style), "30", "32", "35"],
        [make_cell("　　給与手当", body_style), "120", "135", "150"],
        [make_cell("　　広告宣伝費", body_style), "20", "25", "30"],
        [make_cell("　　地代家賃", body_style), "24", "24", "24"],
        [make_cell("　　その他販管費", body_style), "56", "64", "71"],
        [make_cell("<b>営業利益</b>", body_style), "50", "70", "100"],
        [make_cell("　営業外収益", body_style), "5", "6", "8"],
        [make_cell("　　受取利息配当金", body_style), "1", "1", "2"],
        [make_cell("　　その他営業外収益", body_style), "4", "5", "6"],
        [make_cell("　営業外費用", body_style), "10", "8", "6"],
        [make_cell("　　支払利息", body_style), "8", "6", "4"],
        [make_cell("　　その他営業外費用", body_style), "2", "2", "2"],
        [make_cell("<b>経常利益</b>", body_style), "45", "68", "102"],
        [make_cell("　特別利益", body_style), "0", "10", "0"],
        [make_cell("　　固定資産売却益", body_style), "0", "10", "0"],
        [make_cell("　特別損失", body_style), "5", "0", "2"],
        [make_cell("　　固定資産除却損", body_style), "5", "0", "2"],
        [make_cell("<b>税引前当期純利益</b>", body_style), "40", "78", "100"],
        [make_cell("　法人税、住民税及び事業税", body_style), "15", "28", "35"],
        [make_cell("<b>当期純利益</b>", body_style), "25", "50", "65"]
    ]
    
    pl_table = Table(pl_rows, colWidths=[70*mm, 30*mm, 30*mm, 30*mm])
    
    pl_style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1A365D')),
        ('ALIGN', (0,0), (0,-1), 'LEFT'),
        ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ])
    
    # ヘッダー行文字色
    for i in range(4):
        pl_style.add('TEXTCOLOR', (i,0), (i,0), colors.white)
        
    # 重要行の強調
    highlight_pl_rows = [1, 3, 10, 17, 22, 24]  # 売上高、売上総利益、営業利益、経常利益、税引前当期純利益、当期純利益
    for r in highlight_pl_rows:
        pl_style.add('BACKGROUND', (0, r), (-1, r), colors.HexColor('#EDF2F7'))
        pl_style.add('LINEABOVE', (0, r), (-1, r), 1.2, colors.HexColor('#1A365D'))
        pl_style.add('LINEBELOW', (0, r), (-1, r), 1.2, colors.HexColor('#1A365D'))
        
    pl_table.setStyle(pl_style)
    story.append(pl_table)
    
    # PDFビルド
    print(f"[*] Building PDF: {output_filename}...")
    doc.build(story)
    print(f"[+] PDF generation completed successfully!")

if __name__ == "__main__":
    generate_pdf()
