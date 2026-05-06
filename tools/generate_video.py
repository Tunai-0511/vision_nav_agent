#!/usr/bin/env python3
"""
解說影片生成器
輸出：output/demo_video.mp4 (1280×720, H.264, ~4:30)

使用前請修改下方 AUTHOR_INFO 填入作者資訊。
"""

import os
import sys
import math
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont

# moviepy 匯入（同時相容 1.x 和 2.x）
try:
    try:
        from moviepy import ImageClip, concatenate_videoclips, CompositeVideoClip
    except ImportError:
        from moviepy.editor import ImageClip, concatenate_videoclips, CompositeVideoClip
except ImportError:
    sys.exit("請先安裝 moviepy：  pip install moviepy")

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ① 作者資訊（與 generate_poster.py 保持一致）
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
# ② 常數
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
VW, VH = 1280, 720
FPS    = 30

BG      = (0,   0,   0  )
PRIMARY = (255, 234, 0  )
ACCENT  = (0,  229, 255 )
WHITE   = (255, 255, 255)
GRAY    = (130, 130, 130)
CARD_BG = (18,  18,  18 )
BORDER  = (55,  55,  55 )
GREEN   = (80,  220, 100)
RED     = (255,  80,  80)

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
    sys.exit("找不到中文字型，請安裝：apt-get install fonts-wqy-zenhei")

FONT_PATH = find_font()

def font(size):
    return ImageFont.truetype(FONT_PATH, size)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ③ 投影片基礎輔助函式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def new_slide():
    img  = Image.new("RGB", (VW, VH), BG)
    draw = ImageDraw.Draw(img)
    return img, draw

def center_x(draw, text, fnt):
    return (VW - draw.textlength(text, font=fnt)) // 2

def draw_slide_header(draw, title, color=PRIMARY):
    draw.rectangle([0, 0, VW, 8], fill=color)
    draw.rectangle([0, VH - 8, VW, VH], fill=color)
    draw.text((40, 18), title, font=font(32), fill=color)
    # 頁碼資訊列
    draw.text((VW - 250, 18), AUTHOR_INFO["title"], font=font(22), fill=GRAY)

def img_to_clip(img, duration, fade=0.4):
    arr = np.array(img)
    # 相容 moviepy 1.x 和 2.x 的 duration 設定方式
    try:
        clip = ImageClip(arr, duration=duration)
    except TypeError:
        clip = ImageClip(arr).set_duration(duration)
    return clip

def draw_progress_bar(draw, current, total, y=VH - 14, color=PRIMARY):
    """底部進度條"""
    w = int(VW * current / total)
    draw.rectangle([0, y, w, VH], fill=color)
    draw.rectangle([w, y, VW, VH], fill=(30, 30, 30))

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ④ 各投影片生成函式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def slide_title(slide_num=1, total=10):
    """封面 (15s)"""
    img, draw = new_slide()

    # 動態感：斜線裝飾
    for i in range(0, VW + VH, 80):
        alpha = max(0, 255 - abs(i - VW // 2) // 2)
        c = (int(PRIMARY[0] * alpha / 255 * 0.08),
             int(PRIMARY[1] * alpha / 255 * 0.08), 0)
        draw.line([(i, 0), (i - VH, VH)], fill=c, width=3)

    # 主標題
    title = AUTHOR_INFO["title"]
    tw = draw.textlength(title, font=font(72))
    draw.text(((VW - tw) // 2, 160), title, font=font(72), fill=PRIMARY)

    # 副標
    sub = AUTHOR_INFO["subtitle"]
    sw = draw.textlength(sub, font=font(38))
    draw.text(((VW - sw) // 2, 265), sub, font=font(38), fill=WHITE)

    # 分隔線
    draw.line([(VW // 2 - 300, 330), (VW // 2 + 300, 330)], fill=PRIMARY, width=3)

    # 作者資訊
    info_lines = [
        AUTHOR_INFO["authors"],
        AUTHOR_INFO["school"],
        AUTHOR_INFO["advisor"],
        AUTHOR_INFO["competition"] + "  ·  " + AUTHOR_INFO["year"],
    ]
    y = 355
    for line in info_lines:
        lw = draw.textlength(line, font=font(30))
        draw.text(((VW - lw) // 2, y), line, font=font(30), fill=WHITE)
        y += 48

    # 底部提示
    hint = "▶  請開啟字幕以獲得最佳觀看體驗"
    hw = draw.textlength(hint, font=font(24))
    draw.text(((VW - hw) // 2, 620), hint, font=font(24), fill=GRAY)

    draw_progress_bar(draw, slide_num, total)
    return img_to_clip(img, 15)

def slide_motivation(slide_num=2, total=10):
    """研究動機 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "01  研究動機與目的")
    draw_progress_bar(draw, slide_num, total)

    # 統計數字
    stats = [
        ("62萬+",  "台灣視障\n與低視力者"),
        ("380萬+", "65歲以上\n高齡人口"),
        ("70%+",   "視障者戶外\n行動困難"),
    ]
    box_w, box_h = 310, 200
    sx = (VW - (box_w * 3 + 60)) // 2
    for i, (num, label) in enumerate(stats):
        bx = sx + i * (box_w + 30)
        draw.rounded_rectangle([bx, 70, bx + box_w, 70 + box_h],
                                radius=15, fill=CARD_BG, outline=PRIMARY, width=3)
        nw = draw.textlength(num, font=font(52))
        draw.text((bx + (box_w - nw) // 2, 85), num, font=font(52), fill=PRIMARY)
        for j, l in enumerate(label.split('\n')):
            lw = draw.textlength(l, font=font(26))
            draw.text((bx + (box_w - lw) // 2, 155 + j * 34), l, font=font(26), fill=WHITE)

    # 問題點
    y = 300
    problems = [
        ("❌", "現有導盲杖、點字磚無法偵測動態障礙物（行人、機車）"),
        ("❌", "商用視障輔具售價高昂，數萬至數十萬元不等"),
        ("❌", "高齡者面對工地、積水、臨時障礙缺乏即時預警"),
    ]
    for icon, text in problems:
        draw.text((80, y), icon, font=font(34), fill=RED)
        draw.text((140, y), text, font=font(34), fill=WHITE)
        y += 56

    # 解決方案宣言
    y += 20
    draw.rounded_rectangle([60, y, VW - 60, y + 90], radius=12,
                            fill=(40, 35, 0), outline=PRIMARY, width=4)
    sol = "✅  「手機即輔具」—— AI 視覺 + 即時語音，零額外硬體成本"
    sw = draw.textlength(sol, font=font(34))
    draw.text(((VW - sw) // 2, y + 25), sol, font=font(34), fill=PRIMARY)

    y += 130
    # 目標
    goals = ["🎯 目標一：低延遲障礙物偵測（< 0.1 秒/幀）",
             "🎯 目標二：語音引導，讓視障者安全獨立行走",
             "🎯 目標三：整合 AI 服務，提升日常生活自主能力"]
    for g in goals:
        draw.text((80, y), g, font=font(30), fill=ACCENT)
        y += 50

    return img_to_clip(img, 30)

def slide_solution_overview(slide_num=3, total=10):
    """解決方案概覽 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "02  解決方案概覽")
    draw_progress_bar(draw, slide_num, total)

    # 核心概念圓圈
    cx, cy, r = VW // 2, 320, 130
    draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(40, 35, 0), outline=PRIMARY, width=6)
    draw.text((cx - draw.textlength("手機", font=font(54)) // 2, cy - 50), "手機", font=font(54), fill=PRIMARY)
    draw.text((cx - draw.textlength("即輔具", font=font(40)) // 2, cy + 15), "即輔具", font=font(40), fill=WHITE)

    # 三大核心能力射線
    abilities = [
        (180, "🚧 即時障礙偵測", "YOLOv8n + OpenCV"),
        (300, "🔊 語音導航警示", "Browser TTS zh-TW"),
        (60,  "🌐 智慧 AI 整合", "OpenClaw + Telegram"),
    ]
    for angle_deg, title, sub in abilities:
        angle = math.radians(angle_deg - 90)
        lx = cx + int((r + 180) * math.cos(angle))
        ly = cy + int((r + 180) * math.sin(angle))
        # 連線
        ex = cx + int(r * math.cos(angle))
        ey = cy + int(r * math.sin(angle))
        draw.line([(ex, ey), (lx, ly)], fill=ACCENT, width=3)
        # 標籤
        tw = draw.textlength(title, font=font(32))
        tx = lx - tw // 2
        draw.text((tx, ly - 22), title, font=font(32), fill=ACCENT)
        sw = draw.textlength(sub, font=font(24))
        draw.text((lx - sw // 2, ly + 18), sub, font=font(24), fill=GRAY)

    # 系統特色
    y = 530
    features = [
        "📱 手機瀏覽器直接使用，無需安裝 App",
        "⚡ 雙層偵測架構：YOLO 辨識 + OpenCV 地面雷達補盲",
        "🌐 ngrok 穿透技術，手機從任何地方連接電腦後端",
    ]
    for f in features:
        fw = draw.textlength(f, font=font(28))
        draw.text(((VW - fw) // 2, y), f, font=font(28), fill=WHITE)
        y += 48

    return img_to_clip(img, 30)

def slide_architecture(slide_num=4, total=10):
    """系統架構動畫 (45s) — 繪製多幀逐步顯示架構圖"""
    def make_arch_frame(step):
        img, draw = new_slide()
        draw_slide_header(draw, "03  系統架構")
        draw_progress_bar(draw, slide_num, total)

        pad = 50
        bw, bh = 220, 70

        def box(label, x, y, fill, outline, show=True):
            if not show:
                return
            draw.rounded_rectangle([x, y, x + bw, y + bh], radius=10,
                                    fill=fill, outline=outline, width=3)
            tw = draw.textlength(label, font=font(26))
            draw.text((x + (bw - tw) // 2, y + (bh - 28) // 2), label, font=font(26), fill=WHITE)

        def arr(x1, y1, x2, y2, show=True):
            if not show:
                return
            draw.line([(x1, y1), (x2, y2)], fill=ACCENT, width=3)
            angle = math.atan2(y2 - y1, x2 - x1)
            for s in [0.4, -0.4]:
                ax = x2 - 20 * math.cos(angle - s)
                ay = y2 - 20 * math.sin(angle - s)
                draw.line([(x2, y2), (ax, ay)], fill=ACCENT, width=3)

        # 第一列：手機 → FastAPI
        phone_x, phone_y = 70, 100
        box("📱 手機瀏覽器", phone_x, phone_y, (30, 25, 0), PRIMARY, step >= 1)
        arr(phone_x + bw, phone_y + bh // 2, phone_x + bw + 80, phone_y + bh // 2, step >= 2)
        draw.text((phone_x + bw + 10, phone_y - 20), "HTTPS", font=font(22), fill=GRAY) if step >= 2 else None
        server_x = phone_x + bw + 80
        box("🖥 FastAPI :8000", server_x, phone_y, (0, 20, 30), ACCENT, step >= 2)

        # 第二列：後端模組
        mods = [
            ("🧠 NavigationAgent", (30, 25, 0), PRIMARY),
            ("👁 ObstacleDetector", (0, 20, 30), ACCENT),
            ("🔍 VisionAnalyzer",  (25, 0, 40), (180, 100, 255)),
            ("📍 HomeDetector",    (0, 25, 0),  GREEN),
        ]
        row2_y = 250
        total_mods = len(mods)
        mod_spacing = (VW - 2 * pad - bw) // (total_mods - 1)
        for i, (name, fill, oc) in enumerate(mods):
            mx = pad + i * mod_spacing
            arr(server_x + bw // 2, phone_y + bh, mx + bw // 2, row2_y, step >= 3)
            box(name, mx, row2_y, fill, oc, step >= 3)

        # 第三列：輸出
        outs = [
            ("🔊 語音TTS",   (40, 35, 0), PRIMARY),
            ("📨 Telegram",  (0, 20, 35), ACCENT),
            ("📅 Calendar",  (0, 25, 10), GREEN),
            ("📸 PhotoLog",  (35, 20, 0), (255, 150, 50)),
        ]
        row3_y = 420
        out_spacing = (VW - 2 * pad - bw) // (len(outs) - 1)
        for i, (name, fill, oc) in enumerate(outs):
            ox = pad + i * out_spacing
            mod_cx = pad + i * mod_spacing + bw // 2
            arr(mod_cx, row2_y + bh, ox + bw // 2, row3_y, step >= 4)
            box(name, ox, row3_y, fill, oc, step >= 4)

        # OpenClaw 標示
        if step >= 3:
            draw.rounded_rectangle([VW - 280, row2_y - 30, VW - 10, row2_y + bh + 30],
                                    radius=10, fill=(20, 10, 30), outline=(180, 100, 255), width=3)
            draw.text((VW - 265, row2_y - 15), "OpenClaw AI", font=font(24), fill=(180, 100, 255))
            draw.text((VW - 275, row2_y + 25), "port: 18789", font=font(20), fill=GRAY)
            draw.line([(mods[2][0] if False else pad + 2 * mod_spacing + bw,
                        row2_y + bh // 2),
                       (VW - 280, row2_y + bh // 2)], fill=(180, 100, 255), width=2)

        # 步驟提示
        hints = ["", "手機透過 HTTPS 傳送影像", "FastAPI 分發給後端模組", "各模組即時處理", "輸出至各整合服務"]
        if step > 0:
            draw.text((60, 600), f"步驟 {step}：{hints[min(step, len(hints)-1)]}",
                      font=font(28), fill=PRIMARY)
        return img

    frames_steps = [(0, 2.0), (1, 2.0), (2, 2.0), (3, 2.0), (4, 3.0)]
    clips = []
    for step, dur in frames_steps:
        frame = make_arch_frame(step)
        clips.append(img_to_clip(frame, dur, fade=0.2))
    # 靜態最終幀
    final = make_arch_frame(4)
    clips.append(img_to_clip(final, 33, fade=0.3))
    return concatenate_videoclips(clips)

def slide_obstacle_detection(slide_num=5, total=10):
    """障礙物偵測 Demo (45s)"""
    def make_detect_frame(phase):
        img, draw = new_slide()
        draw_slide_header(draw, "04  障礙物偵測演示")
        draw_progress_bar(draw, slide_num, total)

        # 模擬相機畫面
        cam_x1, cam_y1, cam_x2, cam_y2 = 60, 80, 700, 520
        draw.rectangle([cam_x1, cam_y1, cam_x2, cam_y2], fill=(8, 15, 8))
        draw.rectangle([cam_x1, cam_y1, cam_x2, cam_y2], outline=BORDER, width=3)
        draw.text((cam_x1 + 10, cam_y1 + 5), "📷 Camera Feed (640×480)", font=font(24), fill=GRAY)

        # YOLO 偵測框（依 phase 動畫顯示）
        objects = [
            (130, 120, 270, 460, "行人", "97%", RED),
            (330, 200, 520, 460, "機車", "88%", (255, 180, 0)),
        ]
        if phase >= 1:
            x1, y1, x2, y2, label, conf, color = objects[0]
            draw.rectangle([cam_x1 + x1, cam_y1 + y1, cam_x1 + x2, cam_y1 + y2],
                           outline=color, width=4)
            draw.text((cam_x1 + x1 + 4, cam_y1 + y1 + 4),
                      f"{label} {conf}", font=font(24), fill=color)
        if phase >= 2:
            x1, y1, x2, y2, label, conf, color = objects[1]
            draw.rectangle([cam_x1 + x1, cam_y1 + y1, cam_x1 + x2, cam_y1 + y2],
                           outline=color, width=4)
            draw.text((cam_x1 + x1 + 4, cam_y1 + y1 + 4),
                      f"{label} {conf}", font=font(24), fill=color)

        # OpenCV 地面雷達（底部 1/3）
        radar_y = cam_y1 + int((cam_y2 - cam_y1) * 0.66)
        if phase >= 3:
            draw.rectangle([cam_x1, radar_y, cam_x2, cam_y2], outline=ACCENT, width=4)
            for gx in range(cam_x1, cam_x2, 40):
                draw.line([(gx, radar_y), (gx, cam_y2)], fill=(0, 50, 50), width=1)
            draw.text((cam_x1 + 5, radar_y + 3), "OpenCV 雷達區", font=font(20), fill=ACCENT)
            if phase >= 4:
                draw.text((cam_x1 + 5, radar_y + 28), "⚡ 偵測到地面雜物！", font=font(22), fill=PRIMARY)

        # 右側：說明面板
        rx = 740
        # 流程圖
        steps_data = [
            ("輸入影格", "640×480 px", GREEN if phase >= 1 else BORDER),
            ("YOLOv8n 推論", "< 0.1s", PRIMARY if phase >= 2 else BORDER),
            ("中文類別轉換", "en→zh 字典", ACCENT if phase >= 2 else BORDER),
            ("OpenCV 雷達", "地面掃描", PRIMARY if phase >= 3 else BORDER),
            ("語音警示輸出", "Browser TTS", GREEN if phase >= 4 else BORDER),
        ]
        sy = 90
        for i, (step_name, sub, color) in enumerate(steps_data):
            draw.rounded_rectangle([rx, sy, rx + 480, sy + 65], radius=10,
                                    fill=CARD_BG, outline=color, width=3)
            draw.text((rx + 15, sy + 8), step_name, font=font(28), fill=color)
            draw.text((rx + 15, sy + 38), sub, font=font(20), fill=GRAY)
            if i < len(steps_data) - 1:
                draw.line([(rx + 240, sy + 65), (rx + 240, sy + 85)], fill=color, width=3)
                draw.text((rx + 230, sy + 70), "▼", font=font(20), fill=color)
            sy += 95

        # 偵測結果標籤
        if phase >= 2:
            y_tag = 570
            labels = [("行人", RED), ("機車", (255, 180, 0))]
            if phase >= 4:
                labels.append(("地面雜物", ACCENT))
            draw.text((60, y_tag - 30), "偵測到的障礙物：", font=font(26), fill=GRAY)
            tx = 60
            for lbl, lc in labels:
                lw = int(draw.textlength(lbl, font=font(28)))
                draw.rounded_rectangle([tx - 4, y_tag - 4, tx + lw + 24, y_tag + 36],
                                        radius=8, fill=(30, 30, 30), outline=lc, width=3)
                draw.text((tx + 10, y_tag), lbl, font=font(28), fill=lc)
                tx += lw + 45

        # 警告語音條
        if phase >= 4:
            draw.rounded_rectangle([40, 620, VW - 40, 690], radius=12,
                                    fill=(40, 30, 0), outline=PRIMARY, width=4)
            warn = "🔊  請小心，前方發現行人、機車、地面雜物"
            ww = draw.textlength(warn, font=font(30))
            draw.text(((VW - ww) // 2, 637), warn, font=font(30), fill=PRIMARY)

        return img

    phases_timing = [(0, 2), (1, 3), (2, 3), (3, 3), (4, 4)]
    clips = []
    for phase, dur in phases_timing:
        f = make_detect_frame(phase)
        clips.append(img_to_clip(f, dur, fade=0.2))
    # 靜態最終幀
    clips.append(img_to_clip(make_detect_frame(4), 30, fade=0.3))
    return concatenate_videoclips(clips)

def slide_voice_nav(slide_num=6, total=10):
    """語音導航介面 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "05  語音導航介面")
    draw_progress_bar(draw, slide_num, total)

    # 手機 UI 示意（縮小版）
    phone_x, phone_y = 50, 70
    phone_w, phone_h = 300, 580
    # 手機外框
    draw.rounded_rectangle([phone_x, phone_y, phone_x + phone_w, phone_y + phone_h],
                            radius=30, fill=(20, 20, 20), outline=PRIMARY, width=4)
    # 螢幕
    draw.rectangle([phone_x + 15, phone_y + 50,
                    phone_x + phone_w - 15, phone_y + phone_h - 50],
                   fill=(5, 5, 5))
    # UI 元素
    draw.text((phone_x + 25, phone_y + 60), "導航系統", font=font(26), fill=PRIMARY)
    draw.rectangle([phone_x + 15, phone_y + 100,
                    phone_x + phone_w - 15, phone_y + 330], fill=(10, 20, 10))
    draw.text((phone_x + 30, phone_y + 190), "[ 相機畫面 ]", font=font(22), fill=GRAY)
    # 按鈕
    btns = [("啟動導航", PRIMARY, 345), ("語音指令", ACCENT, 410),
            ("拍照", (255, 150, 0), 475), ("模式", (120, 0, 180), 510)]
    for label, bc, by in btns:
        draw.rounded_rectangle([phone_x + 25, phone_y + by - 5,
                                 phone_x + phone_w - 25, phone_y + by + 40],
                                radius=8, fill=bc)
        draw.text((phone_x + 45, phone_y + by + 7), label, font=font(22), fill=(0, 0, 0))
    # 警告文字
    draw.rectangle([phone_x + 15, phone_y + 330,
                    phone_x + phone_w - 15, phone_y + 400], fill=(40, 0, 0))
    draw.text((phone_x + 18, phone_y + 348), "⚠ 前方有行人", font=font(22), fill=PRIMARY)

    # 右側：語音流程說明
    rx = 420
    flow = [
        ("YOLO 偵測障礙物", PRIMARY, 80),
        ("中文字串組合", WHITE,   190),
        ("SpeechSynthesisAPI", ACCENT, 300),
        ("瀏覽器語音播放", GREEN, 410),
    ]
    for label, color, fy in flow:
        draw.rounded_rectangle([rx, fy, rx + 380, fy + 75], radius=10,
                                fill=CARD_BG, outline=color, width=3)
        lw = draw.textlength(label, font=font(30))
        draw.text((rx + (380 - lw) // 2, fy + 20), label, font=font(30), fill=color)
        if fy < 410:
            draw.text((rx + 180, fy + 80), "↓", font=font(28), fill=GRAY)

    # 特色說明
    desc_x = 840
    features = [
        ("🌐", "瀏覽器原生 TTS", "無需額外 TTS 引擎"),
        ("🗣", "繁體中文 zh-TW", "自然語音，本地化"),
        ("⚡", "即時無延遲", "YOLO 偵測後立即播報"),
        ("🔇", "雙模式切換", "導航模式 / 助理模式"),
    ]
    fy = 80
    for icon, title, sub in features:
        draw.text((desc_x, fy), icon, font=font(32), fill=WHITE)
        draw.text((desc_x + 55, fy), title, font=font(30), fill=ACCENT)
        draw.text((desc_x + 55, fy + 38), sub, font=font(24), fill=GRAY)
        fy += 100

    return img_to_clip(img, 30)

def slide_gps_home(slide_num=7, total=10):
    """GPS 回家偵測 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "06  GPS 回家偵測")
    draw_progress_bar(draw, slide_num, total)

    # 地圖背景
    map_x1, map_y1, map_x2, map_y2 = 50, 80, 580, 530
    draw.rectangle([map_x1, map_y1, map_x2, map_y2], fill=(10, 15, 10))
    # 格線（模擬地圖）
    for gx in range(map_x1, map_x2, 50):
        draw.line([(gx, map_y1), (gx, map_y2)], fill=(20, 30, 20), width=1)
    for gy in range(map_y1, map_y2, 50):
        draw.line([(map_x1, gy), (map_x2, gy)], fill=(20, 30, 20), width=1)

    # 道路
    draw.rectangle([map_x1 + 200, map_y1, map_x1 + 250, map_y2], fill=(25, 25, 25))
    draw.rectangle([map_x1, map_y1 + 200, map_x2, map_y1 + 250], fill=(25, 25, 25))

    # 家的位置
    hx, hy = map_x1 + 225, map_y1 + 225
    # 安全半徑圓
    for r_i, (r, alpha) in enumerate([(80, 50), (50, 80), (25, 120)]):
        a = int(alpha)
        draw.ellipse([hx - r, hy - r, hx + r, hy + r],
                     outline=(0, a, 0), width=2)
    draw.text((hx - 15, hy - 20), "🏠", font=font(32), fill=GREEN)
    draw.text((hx + 25, hy - 15), "家", font=font(24), fill=GREEN)

    # 使用者當前位置（外出中）
    ux, uy = map_x1 + 380, map_y1 + 380
    draw.ellipse([ux - 12, uy - 12, ux + 12, uy + 12], fill=ACCENT)
    draw.text((ux + 15, uy - 10), "你", font=font(24), fill=ACCENT)

    # 距離線
    draw.line([(hx, hy), (ux, uy)], fill=GRAY, width=2)
    dist = int(math.sqrt((ux - hx) ** 2 + (uy - hy) ** 2) * 1.5)
    draw.text(((hx + ux) // 2 + 5, (hy + uy) // 2), f"{dist}m", font=font(22), fill=GRAY)

    # 右側：事件流程
    rx = 640
    events = [
        ("📍 GPS 回傳 (每 5 秒)", ACCENT),
        ("📐 計算與家距離",       WHITE),
        ("🏠 到家判定 (< 50m)",   GREEN),
        ("📊 觸發每日摘要",        PRIMARY),
        ("📨 傳送 Telegram 報告", (255, 150, 50)),
    ]
    y = 90
    for event, color in events:
        draw.rounded_rectangle([rx, y, rx + 560, y + 65], radius=10,
                                fill=CARD_BG, outline=color, width=3)
        draw.text((rx + 20, y + 17), event, font=font(28), fill=color)
        y += 90

    # 特色
    y += 20
    draw.text((rx, y),      "🔋  低耗電：GPS 每 5s 更新一次",  font=font(26), fill=WHITE)
    draw.text((rx, y + 45), "💾  SQLite 永久記錄出入事件",    font=font(26), fill=WHITE)
    draw.text((rx, y + 90), "🤖  回家即觸發 AI 日誌摘要",      font=font(26), fill=WHITE)

    return img_to_clip(img, 30)

def slide_product_recognition(slide_num=8, total=10):
    """商品辨識 + 整合功能 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "07  商品辨識與 AI 整合")
    draw_progress_bar(draw, slide_num, total)

    # 流程動畫（水平箭頭流）
    steps = [
        ("📷", "拍照",    "手機截圖"),
        ("🧠", "AI 辨識", "OpenClaw\ngemini-3-flash"),
        ("🛒", "搜尋蝦皮", "品名+價格\n+連結"),
        ("📨", "Telegram", "即時推播\n給家人"),
    ]
    box_w, box_h = 240, 160
    total_w = box_w * 4 + 60 * 3
    sx = (VW - total_w) // 2
    y = 100

    for i, (icon, title, sub) in enumerate(steps):
        bx = sx + i * (box_w + 60)
        colors = [PRIMARY, ACCENT, (255, 150, 50), GREEN]
        draw.rounded_rectangle([bx, y, bx + box_w, y + box_h], radius=15,
                                fill=CARD_BG, outline=colors[i], width=4)
        iw = draw.textlength(icon, font=font(42))
        draw.text((bx + (box_w - iw) // 2, y + 10), icon, font=font(42), fill=colors[i])
        tw = draw.textlength(title, font=font(32))
        draw.text((bx + (box_w - tw) // 2, y + 65), title, font=font(32), fill=WHITE)
        for j, sl in enumerate(sub.split('\n')):
            sw = draw.textlength(sl, font=font(22))
            draw.text((bx + (box_w - sw) // 2, y + 108 + j * 28), sl, font=font(22), fill=GRAY)
        if i < 3:
            draw.text((bx + box_w + 18, y + 60), "→", font=font(40), fill=GRAY)

    # JSON 回傳示意
    y = 300
    draw.text((50, y), "OpenClaw AI 回傳 JSON：", font=font(28), fill=GRAY)
    y += 40
    json_demo = [
        ('  "product_name": ', '"台灣菸酒啤酒 600mL"', PRIMARY),
        ('  "price": ',         '"35"',                  GREEN),
        ('  "reviews": ',       '"4.8 / 5.0 (2.3萬評價)"', ACCENT),
        ('  "link": ',          '"https://shopee.tw/..."', (100, 100, 255)),
        ('  "summary": ',       '"清爽台灣啤酒，適合消暑"', WHITE),
    ]
    for key, val, val_color in json_demo:
        draw.text((80, y), key, font=font(24), fill=GRAY)
        draw.text((80 + int(draw.textlength(key, font=font(24))), y), val, font=font(24), fill=val_color)
        y += 36

    # 其他整合功能
    y += 20
    integrations = [
        ("📅 Google Calendar", "語音新增行程：「明天下午三點看醫生」"),
        ("📊 每日 AI 摘要",    "回家時自動觸發，總結今日拍照與行程"),
        ("🔒 SQLite 記錄",     "所有照片、GPS、事件永久本地儲存"),
    ]
    for icon_title, desc in integrations:
        draw.text((50, y), icon_title, font=font(28), fill=ACCENT)
        draw.text((50 + int(draw.textlength(icon_title, font=font(28))) + 20, y),
                  desc, font=font(26), fill=WHITE)
        y += 55

    return img_to_clip(img, 30)

def slide_tech_highlights(slide_num=9, total=10):
    """技術亮點 (30s)"""
    img, draw = new_slide()
    draw_slide_header(draw, "08  技術亮點與效能指標")
    draw_progress_bar(draw, slide_num, total)

    # 效能條形圖
    metrics = [
        ("YOLO 偵測速度",     0.1,  1.0, "0.1s / 幀",   PRIMARY, "< 0.1s 極速"),
        ("語音延遲",          0.05, 0.5, "< 50ms",      GREEN,   "即時播報"),
        ("GPS 更新頻率",      5.0,  30.0, "每 5 秒",    ACCENT,  "低耗電設計"),
        ("圖片壓縮品質",      0.6,  1.0, "60% JPEG",   (255,150,50), "速度與品質平衡"),
        ("支援物件類別",      80,   100,  "80 種",       (180,100,255), "COCO 全類別"),
    ]

    by = 80
    bar_max_w = 500
    for label, val, max_val, text, color, note in metrics:
        bar_w = int(bar_max_w * val / max_val)
        draw.text((50, by), label, font=font(28), fill=WHITE)
        # 背景條
        draw.rounded_rectangle([50, by + 35, 50 + bar_max_w, by + 75], radius=8,
                                fill=(30, 30, 30), outline=BORDER, width=2)
        # 數值條
        if bar_w > 0:
            draw.rounded_rectangle([50, by + 35, 50 + bar_w, by + 75], radius=8, fill=color)
        draw.text((50 + bar_max_w + 20, by + 40), text, font=font(28), fill=color)
        draw.text((50 + bar_max_w + 150, by + 40), note, font=font(22), fill=GRAY)
        by += 100

    # 技術棧徽章
    by += 20
    draw.text((50, by), "技術棧：", font=font(28), fill=GRAY)
    by += 40
    badges = [
        ("Python 3.10", (50, 100, 150)),
        ("YOLOv8n", (0, 100, 50)),
        ("FastAPI", (0, 130, 100)),
        ("OpenCV", (0, 80, 180)),
        ("SQLite", (100, 80, 0)),
        ("Pillow", (120, 0, 120)),
        ("ngrok", (40, 0, 120)),
        ("Telegram Bot", (0, 100, 140)),
    ]
    bx = 50
    for badge, bc in badges:
        bw = int(draw.textlength(badge, font=font(26))) + 24
        draw.rounded_rectangle([bx, by, bx + bw, by + 44], radius=8,
                                fill=bc, outline=(bc[0] + 40, bc[1] + 40, bc[2] + 40), width=2)
        draw.text((bx + 12, by + 8), badge, font=font(26), fill=WHITE)
        bx += bw + 12
        if bx > VW - 200:
            bx = 50
            by += 54

    return img_to_clip(img, 30)

def slide_conclusion(slide_num=10, total=10):
    """結論 + QR Code (15s)"""
    import qrcode as qr_module

    img, draw = new_slide()
    # 漸層背景
    for i in range(VH):
        t = i / VH
        r = int(0  + 10 * t)
        g = int(0  + 8  * t)
        b = int(0)
        draw.line([(0, i), (VW, i)], fill=(r, g, b))

    draw_slide_header(draw, "09  結論與展望")
    draw_progress_bar(draw, slide_num, total)

    # 完成項目
    done = [
        "✅  雙層障礙物偵測（YOLO + OpenCV），< 0.1s/幀",
        "✅  手機網頁端，零 App 安裝成本",
        "✅  多項 AI 整合（商品辨識、Calendar、Telegram）",
        "✅  GPS 回家偵測 + 每日 AI 摘要自動觸發",
        "✅  SQLite 本地資料永久記錄",
    ]
    y = 90
    for d in done:
        draw.text((60, y), d, font=font(28), fill=GREEN)
        y += 50

    # 未來展望
    y += 15
    futures = [
        "🔮  整合離線 TTS 引擎（pyttsx3）",
        "🔮  A* 動態路徑規劃演算法",
        "🔮  自訂 YOLO 模型辨識台灣特有障礙物",
    ]
    for f in futures:
        draw.text((60, y), f, font=font(28), fill=ACCENT)
        y += 50

    # QR Code
    qr = qr_module.QRCode(version=2, box_size=8, border=3,
                          error_correction=qr_module.constants.ERROR_CORRECT_M)
    qr.add_data(AUTHOR_INFO["github_url"])
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white").convert("RGB")
    qr_size = 220
    qr_img = qr_img.resize((qr_size, qr_size), Image.LANCZOS)
    img.paste(qr_img, (VW - qr_size - 60, 100))
    draw.text((VW - qr_size - 60, 330), "掃描查看原始碼", font=font(24), fill=GRAY)

    # 感謝文字
    thanks = "感謝觀看  ·  " + AUTHOR_INFO["authors"] + "  ·  " + AUTHOR_INFO["school"]
    tw = draw.textlength(thanks, font=font(28))
    draw.text(((VW - tw) // 2, 640), thanks, font=font(28), fill=GRAY)

    # 主標題回顯
    title = AUTHOR_INFO["title"]
    tfw = draw.textlength(title, font=font(40))
    draw.text(((VW - tfw) // 2, 590), title, font=font(40), fill=PRIMARY)

    return img_to_clip(img, 15)

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ⑤ 主程式
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
def main():
    os.makedirs("output", exist_ok=True)
    TOTAL = 10

    print("生成各投影片...")
    slides = [
        slide_title(1, TOTAL),
        slide_motivation(2, TOTAL),
        slide_solution_overview(3, TOTAL),
        slide_architecture(4, TOTAL),
        slide_obstacle_detection(5, TOTAL),
        slide_voice_nav(6, TOTAL),
        slide_gps_home(7, TOTAL),
        slide_product_recognition(8, TOTAL),
        slide_tech_highlights(9, TOTAL),
        slide_conclusion(10, TOTAL),
    ]

    print("合成影片...")
    final_clip = concatenate_videoclips(slides, method="compose")

    out_path = "output/demo_video.mp4"
    print(f"輸出至 {out_path}  (解析度: {VW}×{VH}, fps: {FPS})")
    final_clip.write_videofile(
        out_path,
        fps=FPS,
        codec="libx264",
        audio=False,
        preset="fast",
        ffmpeg_params=["-crf", "23"],
        logger=None,
    )
    print(f"✅ 影片已儲存：{out_path}")
    print(f"   預計時長：{final_clip.duration:.1f} 秒 ({final_clip.duration/60:.1f} 分鐘)")
    print(f"   解析度：{VW}×{VH} (720p)")

if __name__ == "__main__":
    main()
