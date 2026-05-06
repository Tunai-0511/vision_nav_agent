#!/usr/bin/env python3
"""
電子海報生成器
輸出：output/poster.png (7087×10630px @ 300 DPI)
      output/poster.pdf

使用前請修改下方 AUTHOR_INFO 填入作者資訊。
"""

import os
import sys
import math
import io
import textwrap

from PIL import Image, ImageDraw, ImageFont
import qrcode
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.lib.units import cm

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ① 作者資訊（使用者填入）
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
AUTHOR_INFO = {
    "title":       "智慧視障輔助導航系統",
    "subtitle":    "Vision-Aided AR Navigation System",
    "authors":     "【作者姓名】",
    "school":      "【學校名稱】",
    "advisor":     "指導老師：【老師姓名】",
    "year":        "2026",
    "competition": "【競賽名稱】",
    "github_url":  "https://github.com/tunai-0511/vision_nav_agent",
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ② 尺寸與配色常數
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
W, H  = 7087, 10630   # 60cm × 90cm @ 300 DPI
DPI   = 300
PAD   = 130           # 外邊距

BG       = (0,   0,   0  )   # 背景黑
PRIMARY  = (255, 234, 0  )   # #FFEA00 黃
ACCENT   = (0,  229, 255 )   # #00E5FF 青
WHITE    = (255, 255, 255)
CARD_BG  = (18,  18,  18 )
BORDER   = (55,  55,  55 )
GRAY     = (130, 130, 130)
RED      = (255,  80,  80)
GREEN    = (80,  220, 100)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ③ 字型載入
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/noto/NotoSansCJKtc-Regular.otf",
    "/usr/share/fonts/wqy/wqy-zenhei.ttc",
]

def find_font():
    for p in FONT_CANDIDATES:
        if os.path.exists(p):
            return p
    sys.exit("找不到中文字型，請安裝 fonts-wqy-zenhei：\n  apt-get install fonts-wqy-zenhei")

FONT_PATH = find_font()
print(f"使用字型：{FONT_PATH}")

def font(size):
    return ImageFont.truetype(FONT_PATH, size)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ④ 通用繪圖輔助函式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def draw_rounded_rect(draw, x0, y0, x1, y1, r=30, fill=None, outline=None, width=3):
    draw.rounded_rectangle([x0, y0, x1, y1], radius=r, fill=fill, outline=outline, width=width)

def draw_centered_text(draw, text, cx, cy, fnt, color):
    bbox = draw.textbbox((0, 0), text, font=fnt)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    draw.text((cx - tw // 2, cy - th // 2), text, font=fnt, fill=color)

def draw_wrapped_text(draw, text, x, y, max_width, fnt, color, line_spacing=1.4):
    """繪製自動換行文字，回傳最終 y 座標"""
    lines = []
    for paragraph in text.split('\n'):
        # 估算每行可容納字數
        avg_char_w = fnt.getlength('中') or 1
        chars_per_line = max(1, int(max_width / avg_char_w))
        wrapped = textwrap.wrap(paragraph, width=chars_per_line) or ['']
        lines.extend(wrapped)

    line_h = int(fnt.size * line_spacing)
    for line in lines:
        draw.text((x, y), line, font=fnt, fill=color)
        y += line_h
    return y

def draw_arrow(draw, x1, y1, x2, y2, color, width=6, arrow_size=30):
    draw.line([(x1, y1), (x2, y2)], fill=color, width=width)
    # 箭頭頭部
    angle = math.atan2(y2 - y1, x2 - x1)
    for side in [+0.4, -0.4]:
        ax = x2 - arrow_size * math.cos(angle - side)
        ay = y2 - arrow_size * math.sin(angle - side)
        draw.line([(x2, y2), (ax, ay)], fill=color, width=width)

def section_title(draw, text, x, y, w, color=PRIMARY):
    """繪製區塊標題（帶左側色條）"""
    bar_w = 18
    bar_h = int(font(70).size * 1.2)
    draw.rectangle([x, y, x + bar_w, y + bar_h], fill=color)
    draw.text((x + bar_w + 25, y), text, font=font(70), fill=color)
    return y + bar_h + 30

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⑤ 各區塊繪製函式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def draw_header(img, draw):
    """頂部標題區塊 (0~900px)"""
    # 漸層橫帶（用多條水平線模擬）
    for i in range(900):
        t = i / 900
        r = int(255 * (1 - t * 0.4))
        g = int(234 * (1 - t * 0.5))
        b = int(0   + 40 * t)
        draw.line([(0, i), (W, i)], fill=(r, g, b))

    # 主標題
    draw_centered_text(draw, AUTHOR_INFO["title"], W // 2, 250, font(160), (0, 0, 0))
    # 英文副標
    draw_centered_text(draw, AUTHOR_INFO["subtitle"], W // 2, 430, font(80), (30, 30, 30))
    # 分隔線
    draw.line([(PAD, 530), (W - PAD, 530)], fill=(0, 0, 0, 80), width=3)
    # 作者資訊列
    info_text = (f"{AUTHOR_INFO['authors']}  ｜  {AUTHOR_INFO['school']}  "
                 f"｜  {AUTHOR_INFO['advisor']}  ｜  {AUTHOR_INFO['year']}")
    draw_centered_text(draw, info_text, W // 2, 720, font(55), (20, 20, 20))
    # 競賽名稱標籤
    comp = AUTHOR_INFO["competition"]
    comp_bbox = draw.textbbox((0, 0), comp, font=font(50))
    comp_w = comp_bbox[2] + 40
    comp_x = (W - comp_w) // 2
    draw_rounded_rect(draw, comp_x, 820, comp_x + comp_w, 890, r=15,
                      fill=(0, 0, 0, 120), outline=(0, 0, 0, 80), width=2)
    draw_centered_text(draw, comp, W // 2, 855, font(50), (20, 20, 20))

def draw_motivation(img, draw, y_start):
    """① 研究動機與目的 (y: ~950~1700)"""
    y = section_title(draw, "① 研究動機與目的", PAD, y_start, W - 2 * PAD)

    # 統計數據卡片（三欄）
    stats = [
        ("62萬+", "台灣視障與低視力人口\n(衛福部 2023)"),
        ("380萬+", "65歲以上高齡人口\n(佔總人口16.4%)"),
        ("70%+", "視障者表示戶外\n獨立行動困難"),
    ]
    card_w = (W - 2 * PAD - 60) // 3
    for i, (num, desc) in enumerate(stats):
        cx = PAD + i * (card_w + 30)
        draw_rounded_rect(draw, cx, y, cx + card_w, y + 320, r=20,
                          fill=CARD_BG, outline=PRIMARY, width=4)
        draw_centered_text(draw, num,  cx + card_w // 2, y + 110, font(100), PRIMARY)
        draw_wrapped_text(draw, desc,  cx + 30,           y + 190, card_w - 60, font(48), WHITE)
    y += 360

    # 問題描述
    problems = [
        "❌  現有導盲杖、點字磚等輔具功能有限，無法即時偵測動態障礙物",
        "❌  商用輔具設備昂貴（數萬至數十萬），一般家庭難以負擔",
        "❌  高齡者面對複雜路況（積水、工地、隨意停放機車）缺乏即時警示",
    ]
    for p in problems:
        draw.text((PAD + 20, y), p, font=font(52), fill=WHITE)
        y += 85

    y += 30
    # 解決方案宣言
    draw_rounded_rect(draw, PAD, y, W - PAD, y + 120, r=15,
                      fill=(40, 35, 0), outline=PRIMARY, width=5)
    draw_centered_text(draw,
        "✅  本系統以「手機即輔具」為核心理念，利用 AI 視覺 + 即時語音，零額外硬體成本實現智慧導航",
        W // 2, y + 60, font(52), PRIMARY)
    return y + 150

def draw_architecture(img, draw, y_start):
    """② 系統架構圖 (y: ~1850~3200)"""
    y = section_title(draw, "② 系統架構", PAD, y_start, W - 2 * PAD)

    # 背景
    arch_h = 1200
    draw_rounded_rect(draw, PAD, y, W - PAD, y + arch_h, r=25,
                      fill=(10, 10, 10), outline=BORDER, width=3)

    inner_y = y + 60
    box_h = 120
    box_r = 18

    def box(label, sub, x, bx_y, bw, fc, oc):
        draw_rounded_rect(draw, x, bx_y, x + bw, bx_y + box_h, r=box_r, fill=fc, outline=oc, width=4)
        draw_centered_text(draw, label, x + bw // 2, bx_y + 38, font(52), WHITE)
        if sub:
            draw_centered_text(draw, sub, x + bw // 2, bx_y + 85, font(36), GRAY)

    # 第一列：手機端
    phone_x = PAD + 200
    box("📱 手機瀏覽器", "Browser WebSpeech / GPS / Camera", phone_x, inner_y, 2000, (30, 25, 0), PRIMARY)

    # 箭頭（雙向）
    mid_x = phone_x + 2060
    draw_arrow(draw, phone_x + 2000, inner_y + 60, mid_x + 40, inner_y + 60, ACCENT, width=8)
    draw.text((mid_x - 60, inner_y + 20), "HTTPS", font=font(40), fill=ACCENT)
    draw.text((mid_x - 80, inner_y + 75), "/api/*", font=font(40), fill=GRAY)

    server_x = mid_x + 80
    box("🖥 FastAPI Server", "web_main.py  port:8000", server_x, inner_y, 1800, (0, 25, 30), ACCENT)

    # 第二列：後端模組（五個）
    modules = [
        ("🧠 NavigationAgent", "AI 決策大腦", PRIMARY),
        ("👁 ObstacleDetector", "YOLOv8n + OpenCV", ACCENT),
        ("🔍 VisionAnalyzer", "OpenClaw WebSocket", (180, 100, 255)),
        ("📍 HomeDetector", "GPS 回家偵測", GREEN),
        ("🗄 SQLite DB", "軌跡 / 照片 / 事件", GRAY),
    ]
    mod_row_y = inner_y + 260
    mod_w = (W - 2 * PAD - 200 - 40 * 4) // 5
    server_bottom_cx = server_x + 900   # 從 FastAPI box 底部中心扇出
    for i, (name, sub, oc) in enumerate(modules):
        mx = PAD + 100 + i * (mod_w + 40)
        draw_arrow(draw, server_bottom_cx, inner_y + box_h, mx + mod_w // 2, mod_row_y, BORDER, width=5)
        box(name, sub, mx, mod_row_y, mod_w, CARD_BG, oc)

    # 第三列：輸出整合
    out_row_y = mod_row_y + 260
    outputs = [
        ("🔊 語音警示", "Browser TTS", PRIMARY),
        ("📨 Telegram", "Bot API 通知", ACCENT),
        ("📅 Google Calendar", "行程語音新增", GREEN),
        ("📸 照片日誌", "蝦皮商品辨識", (255, 150, 50)),
        ("📊 每日摘要", "AI 行程總結", (180, 100, 255)),
    ]
    out_w = (W - 2 * PAD - 200 - 40 * 4) // 5
    for i, (name, sub, oc) in enumerate(outputs):
        ox = PAD + 100 + i * (out_w + 40)
        mod_mid_x = PAD + 100 + i * (mod_w + 40) + mod_w // 2
        draw_arrow(draw, mod_mid_x, mod_row_y + box_h, ox + out_w // 2, out_row_y, BORDER, width=4)
        box(name, sub, ox, out_row_y, out_w, (5, 5, 5), oc)

    return y + arch_h + 80

def draw_features_and_tech(img, draw, y_start):
    """③ 核心功能  ④ 技術規格 (雙欄, ~1900px)"""
    section_h = 2000
    col_w = (W - 2 * PAD - 80) // 2
    left_x  = PAD
    right_x = PAD + col_w + 80

    # 標題
    y_l = section_title(draw, "③ 核心功能", left_x,  y_start, col_w)
    y_r = section_title(draw, "④ 技術規格", right_x, y_start, col_w)
    y_l = y_r = max(y_l, y_r)

    # 左欄：核心功能卡片
    features = [
        ("🚧", "即時障礙物偵測",
         "YOLOv8n 辨識 80 種 COCO 物件（行人、汽車、機車…），\nOpenCV Canny 邊緣雷達補強地面未知突起物，\n每幀處理時間 < 0.1 秒。"),
        ("🔊", "語音導航警示",
         "瀏覽器內建 SpeechSynthesisAPI（繁體中文 zh-TW），\n自動播報障礙物種類與方位，支援導航/助理雙模式切換。"),
        ("📍", "GPS 回家偵測",
         "手機持續回傳 GPS 座標，以設定的家座標為基準，\n自動偵測到家/出門事件，觸發每日行程摘要。"),
        ("🛒", "商品辨識 + 蝦皮搜尋",
         "拍照後送 OpenClaw AI 識別商品品牌與規格，\n自動搜尋蝦皮台灣，回傳商品名稱、價格、連結。"),
        ("📨", "Telegram 即時通報",
         "障礙警示、商品辨識結果即時推播給家人，\n每日回家時自動傳送行程摘要報告。"),
        ("📅", "Google Calendar 語音整合",
         "語音說出行程（「明天下午三點看醫生」），\n系統自動解析並新增至 Google Calendar。"),
    ]

    for icon, title, desc in features:
        draw_rounded_rect(draw, left_x, y_l, left_x + col_w, y_l + 340, r=18,
                          fill=CARD_BG, outline=BORDER, width=3)
        # 圖示圓圈
        draw.ellipse([left_x + 25, y_l + 25, left_x + 125, y_l + 125],
                     fill=(40, 35, 0), outline=PRIMARY, width=3)
        draw_centered_text(draw, icon, left_x + 75, y_l + 75, font(55), WHITE)
        draw.text((left_x + 150, y_l + 30), title, font=font(58), fill=PRIMARY)
        draw_wrapped_text(draw, desc, left_x + 150, y_l + 110, col_w - 170, font(43), WHITE, 1.5)
        y_l += 360

    # 右欄：技術規格表格
    tech_rows = [
        ("視覺偵測",    "Ultralytics YOLOv8n",        "80 種 COCO 類別 + 地面雷達"),
        ("影像前處理",  "OpenCV 4.8+",                 "Canny 邊緣偵測、影格截圖"),
        ("後端框架",    "FastAPI + Uvicorn",            "AsyncIO, ThreadPool, port 8000"),
        ("AI 推論",     "OpenClaw AI (port 18789)",    "WebSocket RPC + HTTP REST 備援"),
        ("語音輸出",    "Browser SpeechSynthesisAPI",  "繁體中文 zh-TW, 1.3× 語速"),
        ("語音輸入",    "WebAudio API → Google STT",   "16kHz PCM WAV, zh-TW"),
        ("外網穿透",    "ngrok HTTPS 隧道",             "手機 HTTPS 連接本機伺服器"),
        ("資料庫",      "SQLite3",                      "軌跡/照片/回家事件 永久儲存"),
        ("第三方整合",  "Telegram Bot API",             "即時訊息推播給家人"),
        ("行程整合",    "Google Calendar API v3",      "OAuth2, 語音新增/查詢事件"),
        ("環境",        "Python 3.10+",                 "Pillow, NumPy, pydantic, yaml"),
        ("部署方式",    "手機瀏覽器 (Web Mode)",        "行動裝置無須安裝 App"),
    ]

    # 表格標題
    draw_rounded_rect(draw, right_x, y_r, right_x + col_w, y_r + 75, r=12,
                      fill=(40, 35, 0), outline=PRIMARY, width=3)
    cols_x = [right_x + 15, right_x + 260, right_x + 690]
    headers = ["類別", "技術 / 工具", "說明"]
    for hx, ht in zip(cols_x, headers):
        draw.text((hx, y_r + 15), ht, font=font(48), fill=PRIMARY)
    y_r += 80

    for idx, (cat, tech, note) in enumerate(tech_rows):
        row_h = 115
        row_fill = (12, 12, 12) if idx % 2 == 0 else (20, 20, 20)
        draw.rectangle([right_x, y_r, right_x + col_w, y_r + row_h], fill=row_fill)
        draw.line([(right_x, y_r + row_h), (right_x + col_w, y_r + row_h)], fill=BORDER, width=2)
        draw.text((cols_x[0], y_r + 15), cat,  font=font(44), fill=ACCENT)
        draw.text((cols_x[1], y_r + 10), tech, font=font(42), fill=WHITE)
        draw.text((cols_x[2], y_r + 10), note, font=font(36), fill=GRAY)
        draw.line([(right_x + 255, y_r), (right_x + 255, y_r + row_h)], fill=BORDER, width=2)
        draw.line([(right_x + 685, y_r), (right_x + 685, y_r + row_h)], fill=BORDER, width=2)
        y_r += row_h
    draw.rectangle([right_x, y_start + 155, right_x + col_w, y_r], outline=BORDER, width=3)

    return max(y_l, y_r) + 80

def draw_demo_screenshot(img, draw, y_start):
    """⑤ 系統操作介面 Demo — 繪製 1920×1080 模擬畫面嵌入海報"""
    y = section_title(draw, "⑤ 系統操作介面展示", PAD, y_start, W - 2 * PAD)

    # ── 生成左側：手機 UI 截圖 (1920×1080) ──────────────────────
    UI_W, UI_H = 1920, 1080

    ui_img = Image.new("RGB", (UI_W, UI_H), (0, 0, 0))
    uid = ImageDraw.Draw(ui_img)

    # 頂部導航列
    uid.rectangle([0, 0, UI_W, 100], fill=(20, 20, 0))
    uid.text((30, 15), "🧠 智慧視障導航系統", font=font(60), fill=PRIMARY)
    uid.text((UI_W - 350, 15), "🔊 導航模式", font=font(55), fill=PRIMARY)

    # 模擬相機畫面
    uid.rectangle([0, 100, UI_W, 750], fill=(15, 25, 15))
    # 模擬 YOLO 偵測框（行人）
    uid.rectangle([300, 150, 700, 700], outline=(255, 80, 80), width=8)
    uid.text((305, 155), "行人  95%", font=font(50), fill=(255, 80, 80))
    # 模擬第二個偵測框（機車）
    uid.rectangle([900, 300, 1300, 700], outline=(255, 180, 0), width=8)
    uid.text((905, 305), "機車  88%", font=font(50), fill=(255, 180, 0))
    # 地面雷達區域（底部 1/3 標示）
    uid.rectangle([0, 618, UI_W, 750], outline=ACCENT, width=5)
    uid.text((30, 625), "OpenCV 地面雷達掃描區", font=font(40), fill=ACCENT)
    # 偵測網格線
    for gx in range(0, UI_W, 120):
        uid.line([(gx, 618), (gx, 750)], fill=(0, 80, 80), width=1)

    # 警告文字橫幅
    uid.rectangle([0, 750, UI_W, 870], fill=(60, 0, 0))
    warn_text = "⚠️  請小心，前方發現：行人、機車、地面雜物"
    uid.text((UI_W // 2 - uid.textlength(warn_text, font=font(58)) // 2, 795),
             warn_text, font=font(58), fill=PRIMARY)

    # 底部按鈕列
    uid.rectangle([0, 870, UI_W, UI_H], fill=(10, 10, 10))
    buttons = [
        (240, "🚀 啟動導航", (255, 234, 0), (0, 0, 0)),
        (680, "🎤 語音指令", (0, 229, 255), (0, 0, 0)),
        (1120, "📸 拍照辨識", (255, 140, 0), (0, 0, 0)),
        (1560, "🔇 切換模式", (120, 0, 180), (255, 255, 255)),
    ]
    for bx, label, bg, fg in buttons:
        uid.rounded_rectangle([bx - 190, 885, bx + 190, 1060], radius=25, fill=bg)
        uid.text((bx - uid.textlength(label, font=font(48)) // 2, 950), label, font=font(48), fill=fg)

    # GPS 狀態列
    uid.text((30, 880), "📍 GPS: 25.0330°N, 121.5654°E  ｜  🏠 距家 234m", font=font(38), fill=GRAY)

    # ── 生成右側：YOLO 偵測示意圖 (1920×1080) ─────────────────
    det_img = Image.new("RGB", (UI_W, UI_H), (5, 5, 15))
    ded = ImageDraw.Draw(det_img)

    # 標題
    ded.rectangle([0, 0, UI_W, 90], fill=(0, 10, 40))
    ded.text((UI_W // 2 - 400, 15), "YOLOv8n + OpenCV 障礙物偵測流程", font=font(58), fill=ACCENT)

    # 輸入幀示意
    ded.rounded_rectangle([80, 130, 580, 500], radius=15, fill=(15, 25, 15), outline=GRAY, width=3)
    ded.text((95, 145), "📷 輸入影格 (640×480)", font=font(40), fill=GRAY)
    ded.rectangle([100, 200, 560, 480], fill=(20, 40, 20))
    ded.text((200, 310), "Camera\nFrame", font=font(55), fill=GRAY)

    # YOLO 處理框
    draw_arrow(ded, 590, 315, 700, 315, ACCENT, width=7)
    ded.rounded_rectangle([710, 180, 1160, 450], radius=15, fill=(0, 20, 40), outline=ACCENT, width=5)
    ded.text((760, 200), "🧠 YOLOv8n", font=font(55), fill=ACCENT)
    ded.text((730, 275), "COCO 80 類別", font=font(44), fill=WHITE)
    ded.text((730, 335), "conf > 0.30", font=font(44), fill=GRAY)
    ded.text((730, 395), "< 0.1s/frame", font=font(44), fill=GREEN)

    # OpenCV 雷達框
    draw_arrow(ded, 1170, 315, 1280, 315, PRIMARY, width=7)
    ded.rounded_rectangle([1290, 180, 1840, 450], radius=15, fill=(30, 20, 0), outline=PRIMARY, width=5)
    ded.text((1340, 200), "📡 OpenCV 雷達", font=font(55), fill=PRIMARY)
    ded.text((1310, 275), "Canny 邊緣偵測", font=font(44), fill=WHITE)
    ded.text((1310, 335), "底部 1/3 ROI", font=font(44), fill=GRAY)
    ded.text((1310, 395), "密度 > 4% 觸發", font=font(44), fill=GREEN)

    # 偵測結果示意
    ded.rounded_rectangle([80, 540, 1840, 840], radius=15, fill=(8, 8, 8), outline=BORDER, width=3)
    ded.text((100, 555), "偵測結果（中文化輸出）：", font=font(48), fill=GRAY)
    detections = [
        ("行人",     "97.3%", (255, 80, 80)),
        ("機車",     "88.1%", (255, 180, 0)),
        ("腳踏車",   "72.4%", (0, 229, 255)),
        ("地面雜物", "OpenCV", PRIMARY),
    ]
    dx = 100
    for dname, dconf, dc in detections:
        ded.rounded_rectangle([dx, 615, dx + 380, 720], radius=12, fill=(30, 30, 30), outline=dc, width=4)
        ded.text((dx + 15, 630), f"{dname}", font=font(50), fill=dc)
        ded.text((dx + 15, 700), dconf, font=font(40), fill=GRAY)
        dx += 420

    # 語音輸出
    ded.rounded_rectangle([80, 850, 1840, 1000], radius=15, fill=(40, 30, 0), outline=PRIMARY, width=5)
    ded.text((120, 890), "🔊  語音警示輸出：「請小心，前方發現行人、機車、腳踏車、地面雜物」",
             font=font(52), fill=PRIMARY)

    # ── 縮放並嵌入海報 ──────────────────────────────────────────
    available_w = (W - 2 * PAD - 60) // 2
    scale_h = int(available_w * UI_H / UI_W)

    ui_resized  = ui_img.resize((available_w, scale_h), Image.LANCZOS)
    det_resized = det_img.resize((available_w, scale_h), Image.LANCZOS)

    # 邊框
    def framed(src_img):
        frm = Image.new("RGB", (available_w + 10, scale_h + 10), PRIMARY)
        frm.paste(src_img, (5, 5))
        return frm

    img.paste(framed(ui_resized),  (PAD,                        y))
    img.paste(framed(det_resized), (PAD + available_w + 60 - 5, y))

    # 圖說
    y += scale_h + 20
    draw.text((PAD + available_w // 2 - 300, y), "▲ 手機端操作介面 (Web UI)", font=font(45), fill=GRAY)
    draw.text((PAD + available_w + 60 + available_w // 2 - 300, y),
              "▲ YOLO + OpenCV 偵測流程示意", font=font(45), fill=GRAY)
    return y + 80

def draw_results(img, draw, y_start):
    """⑥ 成果與驗證"""
    y = section_title(draw, "⑥ 成果與驗證", PAD, y_start, W - 2 * PAD)

    # 四欄指標卡
    metrics = [
        ("< 0.1s",  "每幀偵測時間",      "(YOLOv8n Nano 極速推論)",    ACCENT),
        ("80+",     "支援物件類別",      "(COCO 資料集全類別)",         PRIMARY),
        ("2 模式",  "部署模式",          "(桌面直連 / 手機網頁)",       GREEN),
        ("$0",      "額外硬體成本",      "(僅需一支 Android/iPhone)",   (255, 150, 50)),
    ]
    mw = (W - 2 * PAD - 90) // 4
    for i, (val, title, sub, color) in enumerate(metrics):
        mx = PAD + i * (mw + 30)
        draw_rounded_rect(draw, mx, y, mx + mw, y + 280, r=20,
                          fill=CARD_BG, outline=color, width=5)
        draw_centered_text(draw, val,   mx + mw // 2, y + 85,  font(110), color)
        draw_centered_text(draw, title, mx + mw // 2, y + 185, font(52),  WHITE)
        draw_centered_text(draw, sub,   mx + mw // 2, y + 245, font(38),  GRAY)
    y += 320

    # 完成功能清單
    done = [
        "✅  YOLOv8n + OpenCV 雙層障礙物偵測（< 0.1s/幀）",
        "✅  FastAPI 後端 + ngrok 穿透，手機無需安裝 App",
        "✅  瀏覽器 TTS 繁體中文語音警示（zh-TW, 1.3× 語速）",
        "✅  GPS 回家偵測 + SQLite 事件記錄",
        "✅  OpenClaw 商品辨識 + 蝦皮搜尋（WebSocket RPC 協定）",
        "✅  Telegram Bot 即時推播通知",
        "✅  Google Calendar 語音行程新增/查詢",
        "✅  每日 AI 行程摘要（回家時自動觸發）",
    ]
    col_h = 55 * len(done) // 2 + 20
    for i, d in enumerate(done[:4]):
        draw.text((PAD + 20, y + i * 65), d, font=font(50), fill=GREEN)
    for i, d in enumerate(done[4:]):
        draw.text((W // 2 + 20, y + i * 65), d, font=font(50), fill=GREEN)
    return y + col_h + 80

def draw_conclusion(img, draw, y_start):
    """⑦ 結論與未來展望"""
    y = section_title(draw, "⑦ 結論與未來展望", PAD, y_start, W - 2 * PAD)

    col_w = (W - 2 * PAD - 80) // 2
    # 左：結論
    draw_rounded_rect(draw, PAD, y, PAD + col_w, y + 500, r=18,
                      fill=CARD_BG, outline=GREEN, width=4)
    draw.text((PAD + 30, y + 20), "📋  本研究結論", font=font(58), fill=GREEN)
    conclusions = [
        "• 以零額外硬體成本實現即時 AI 視覺導航",
        "• 雙層偵測架構有效覆蓋 YOLO 盲區",
        "• 手機 Web 架構降低使用門檻，老人易用",
        "• 整合多項 AI 服務（OCR、STT、LLM）",
        "• 系統已通過基本功能驗證測試",
    ]
    cy = y + 105
    for c in conclusions:
        draw.text((PAD + 40, cy), c, font=font(48), fill=WHITE)
        cy += 68

    # 右：未來展望
    draw_rounded_rect(draw, PAD + col_w + 80, y, W - PAD, y + 500, r=18,
                      fill=CARD_BG, outline=ACCENT, width=4)
    draw.text((PAD + col_w + 110, y + 20), "🚀  未來強化方向", font=font(58), fill=ACCENT)
    futures = [
        "• 整合 pyttsx3 本地 TTS 引擎（離線語音）",
        "• 實作 A* / D* Lite 動態路徑規劃演算法",
        "• 訓練自訂 YOLO 模型辨識台灣特有障礙",
        "• 加入 ARKit / ARCore 空間定位增強",
        "• 開發原生 iOS / Android App 版本",
    ]
    fy = y + 105
    for f in futures:
        draw.text((PAD + col_w + 120, fy), f, font=font(48), fill=WHITE)
        fy += 68

    return y + 540

def draw_references_and_qr(img, draw, y_start):
    """參考文獻 + QR Code"""
    y = section_title(draw, "參考文獻", PAD, y_start, W // 2)

    refs = [
        "[1] Jocher G. et al., Ultralytics YOLOv8, 2023. https://ultralytics.com",
        "[2] 衛生福利部，身心障礙者人數統計，2023.",
        "[3] FastAPI documentation, Sebastián Ramírez, 2023.",
        "[4] Google Speech-to-Text API documentation, Google LLC, 2024.",
        "[5] OpenCV documentation, OpenCV contributors, 2023.",
    ]
    for ref in refs:
        draw.text((PAD + 20, y), ref, font=font(40), fill=GRAY)
        y += 58

    # QR Code
    qr = qrcode.QRCode(version=2, box_size=14, border=3,
                       error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(AUTHOR_INFO["github_url"])
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = 700
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)

    qr_x = W - PAD - qr_size
    qr_y = y_start + 90
    img.paste(qr_img, (qr_x, qr_y))
    draw.text((qr_x + qr_size // 2 - 200, qr_y + qr_size + 20),
              "掃描查看原始碼", font=font(48), fill=GRAY)
    draw.text((qr_x + qr_size // 2 - 280, qr_y + qr_size + 80),
              AUTHOR_INFO["github_url"], font=font(35), fill=GRAY)

    return y + 80

def draw_footer(img, draw):
    """底部色塊"""
    fy = H - 200
    for i in range(200):
        t = i / 200
        r = int(255 * t * 0.9)
        g = int(234 * t * 0.9)
        b = 0
        draw.line([(0, fy + i), (W, fy + i)], fill=(r, g, b))

    draw_centered_text(draw, AUTHOR_INFO["competition"], W // 2, fy + 65,  font(65), (0, 0, 0))
    draw_centered_text(draw, f"{AUTHOR_INFO['school']}  ·  {AUTHOR_INFO['year']}",
                       W // 2, fy + 150, font(55), (30, 30, 30))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⑥ 主程式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    os.makedirs("output", exist_ok=True)
    print(f"建立畫布 {W}×{H} px ...")
    img  = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(img)

    # 繪製各區塊
    print("繪製標題列...")
    draw_header(img, draw)

    print("繪製研究動機...")
    y = draw_motivation(img, draw, y_start=950)

    print("繪製系統架構...")
    y = draw_architecture(img, draw, y_start=y + 80)

    print("繪製功能與技術規格...")
    y = draw_features_and_tech(img, draw, y_start=y + 80)

    print("繪製 Demo 截圖...")
    y = draw_demo_screenshot(img, draw, y_start=y + 80)

    print("繪製成果指標...")
    y = draw_results(img, draw, y_start=y + 80)

    print("繪製結論展望...")
    y = draw_conclusion(img, draw, y_start=y + 80)

    print("繪製參考文獻 + QR Code...")
    y = draw_references_and_qr(img, draw, y_start=y + 80)

    draw_footer(img, draw)

    # ── 儲存 PNG ────────────────────────────────────────────────
    out_png = "output/poster.png"
    img.save(out_png, "PNG", dpi=(DPI, DPI))
    print(f"✅ 海報已儲存：{out_png}  ({W}×{H}px @ {DPI}DPI)")

    # ── 儲存 PDF ────────────────────────────────────────────────
    out_pdf = "output/poster.pdf"
    pdf_w_pt = 60 / 2.54 * 72   # 60cm in points
    pdf_h_pt = 90 / 2.54 * 72   # 90cm in points
    c = rl_canvas.Canvas(out_pdf, pagesize=(pdf_w_pt, pdf_h_pt))
    # 將 PNG 嵌入 PDF
    c.drawInlineImage(out_png, 0, 0, pdf_w_pt, pdf_h_pt)
    c.save()
    print(f"✅ PDF 已儲存：{out_pdf}")

if __name__ == "__main__":
    main()
