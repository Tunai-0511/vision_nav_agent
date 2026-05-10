"""
戶外行動版 Web 伺服器主程式 (Web_Main)
提供 FastAPI 作為接收手機端畫面與提供網頁的後端口
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import base64
import numpy as np
import cv2
import uvicorn
import os
import sys
import time
import io

# 強制將輸出錯誤設定為取代模式，避免 Windows cp950 控制台遇到 Emoji 報錯
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(errors='replace')

from agent.navigation_agent import NavigationAgent
from audio.voice_interface import VoiceInterface
from vision.vision_analyzer import VisionAnalyzer
from location.home_detector import HomeDetector
from storage.db import get_db
from integrations.telegram import TelegramClient

# 載入 .env (Telegram bot token / chat id 等)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

app = FastAPI(title="Vision Nav Mobile API")
# 初始化 OpenClaw 決策大腦
agent = NavigationAgent()
voice = VoiceInterface()
vision_analyzer = VisionAnalyzer()
telegram_client = TelegramClient()

# 家裡偵測 + DB（DB 第一次呼叫時才建立 sqlite 檔）
def _on_arrive_home(ts: float):
    print(f"\n[🏠 偵測到回家] ts={ts}")
    get_db().insert_home_event(ts, "arrived_home")
    # 在背景跑每日總結，不阻塞 GPS ingestion
    import threading
    from agent.daily_summary import run as run_daily_summary
    threading.Thread(
        target=run_daily_summary,
        args=(vision_analyzer, telegram_client),
        daemon=True,
    ).start()

def _on_leave_home(ts: float):
    print(f"\n[🚶 偵測到出門] ts={ts}")
    get_db().insert_home_event(ts, "left_home")

home_detector = HomeDetector(
    on_arrive_home=_on_arrive_home,
    on_leave_home=_on_leave_home,
)

# Google Calendar 採延遲初始化：token.json 不存在也不該擋住伺服器啟動
_calendar_client = None

def get_calendar_client():
    global _calendar_client
    if _calendar_client is None:
        from integrations.google_calendar import GoogleCalendarClient
        _calendar_client = GoogleCalendarClient(
            token_path=os.path.join(os.path.dirname(__file__), "..", "token.json")
        )
    return _calendar_client

class ImagePayload(BaseModel):
    image_b64: str

class CommandPayload(BaseModel):
    command: str

class PhotoCommandPayload(BaseModel):
    """拍照指令：包含語音辨識文字和截圖；GPS 為選填，方便 PhotoJournal 記錄地點"""
    text: str
    image_b64: str
    lat: Optional[float] = None
    lng: Optional[float] = None

class ScheduleEventPayload(BaseModel):
    """新增 Google Calendar 事件"""
    title: str
    start: str  # ISO 8601 字串，例如 "2026-05-03T10:00:00"
    end: Optional[str] = None
    location: Optional[str] = None
    description: Optional[str] = None

class LocationPayload(BaseModel):
    """手機回傳的 GPS 點"""
    lat: float
    lng: float
    accuracy: Optional[float] = None
    timestamp: Optional[float] = None  # 秒，None 則用 server time

class SetHomePayload(BaseModel):
    """把當前位置存為家"""
    lat: float
    lng: float

@app.get("/")
async def get_index():
    """回傳給手機端的前端 UI 介面"""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    with open(html_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.post("/api/analyze")
def analyze_frame(payload: ImagePayload):
    """
    接收手機發來的 Base64 照片字串，傳給大腦分析。
    使用 def (而非 async def) 讓 FastAPI 自動將耗時任務放入 ThreadPool 中，避免卡死伺服器！
    """
    start_t = time.time()
    try:
        b64_img = payload.image_b64
        if not b64_img:
            return {"warning": "沒有接收到影像資料"}

        img_bytes = base64.b64decode(b64_img)
        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        print(f"[效能診斷] 1. 前端影像接收與解碼完畢: {time.time() - start_t:.2f} 秒")
        
        t_yolo = time.time()
        visual_data = {"frame": frame}
        decision = agent.analyze_environment(visual_data)
        
        print(f"[效能診斷] 2. 總決策花費時間 (YOLO + OpenClaw): {time.time() - t_yolo:.2f} 秒")
        print(f"[效能診斷] =========================================")
        
        return {
            "warning": decision.get("warning"),
            "action": decision.get("action")
        }
        
    except Exception as e:
        return {"warning": f"電腦端系統錯誤: {str(e)}"}

@app.post("/api/photo")
async def process_photo_command(payload: PhotoCommandPayload):
    """
    接收截圖 + 語音指令，進行商品辨識，並寫入 PhotoJournal（含 GPS）
    """
    print(f"\n[📸 收到拍照指令] 文字: {payload.text} GPS: ({payload.lat}, {payload.lng})")
    voice.speak("收到，正在分析商品")

    try:
        # 解碼圖片
        img_bytes = base64.b64decode(payload.image_b64)
        np_arr = np.frombuffer(img_bytes, dtype=np.uint8)
        frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)

        if frame is None:
            voice.speak("無法解讀圖片")
            return {"reply": "無法解讀圖片", "text": payload.text}

        # 寫入 PhotoJournal（保留記錄）
        from storage.photo_journal import save_photo
        try:
            journal_entry = save_photo(
                image_bytes=img_bytes,
                lat=payload.lat,
                lng=payload.lng,
                recognition=None,
            )
            print(f"[📝 PhotoJournal] 寫入 #{journal_entry['id']}")
        except Exception as je:
            print(f"[📝 PhotoJournal 寫入失敗] {je}")

        # 語音引導使用者去 Telegram 發送照片給 Bot
        voice.speak("請到 Telegram 發送照片給 Bot，進行商品辨識")
        bot_username = "tempo_casing_bot"
        return {
            "reply": f"請到 Telegram 傳送照片給 @{bot_username}，Bot 會自動回覆商品分析結果",
            "text": payload.text,
            "telegram_bot": bot_username
        }

    except Exception as e:
        print(f"[📸 拍照處理失敗] {e}")
        voice.speak("圖片處理失敗")
        return {"reply": f"處理失敗：{str(e)}", "text": payload.text}

@app.post("/api/command_audio")
async def process_audio_command(request: Request):
    """
    (新版) 接收前端純 JS 編碼的 WAV 音軌二進制檔案，後端直接送 Google STT
    若語音包含「拍照」，則拍攝無壓縮圖片傳送給 OpenClaw 進行商品辨識
    """
    audio_data = await request.body()
    print(f"\n[⬇️ 伺服器收到純音訊] 大小: {len(audio_data)} bytes")

    import speech_recognition as sr
    import io

    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(io.BytesIO(audio_data)) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio, language="zh-TW")

            print(f"\n" + "!"*40)
            print(f"[🔴 後端錄音直出解析結果] 🗣️: {text}")
            print("!"*40 + "\n")

            # 檢查是否包含「拍照」關鍵字
            if "拍照" in text or "拍一張" in text:
                print("[📸 偵測到拍照指令] 請發送截圖...")
                voice.speak("收到，請發送截圖")
                return {"reply": "收到拍照指令，請發送截圖", "text": text, "need_photo": True}
            else:
                # 一般指令
                voice.speak(f"收到指令：{text}")
                return {"reply": f"系統收到指令：{text}", "text": text}

    except sr.UnknownValueError:
        print("[🔴 後端辨識失敗] 聽不清楚或沒有講話")
        return {"reply": "聽不清楚，請再講一次", "text": ""}
    except Exception as e:
        print(f"[🔴 後端辨識異常] {e}")
        return {"reply": "連線辨識系統失敗", "text": ""}

@app.post("/api/schedule")
def add_schedule(payload: ScheduleEventPayload):
    """新增一筆事件到 Google Calendar"""
    try:
        client = get_calendar_client()
        start_dt = datetime.fromisoformat(payload.start)
        end_dt = datetime.fromisoformat(payload.end) if payload.end else None
        event = client.add_event(
            title=payload.title,
            start=start_dt,
            end=end_dt,
            location=payload.location,
            description=payload.description,
        )
        return {
            "ok": True,
            "event_id": event.get("id"),
            "html_link": event.get("htmlLink"),
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"建立事件失敗: {e}"}

@app.post("/api/schedule_voice")
def add_schedule_voice(payload: CommandPayload):
    """
    接收自然語言語音轉文字內容，用 Python 解析時間地點後建立 Google Calendar 事件
    """
    text = payload.command
    print(f"\n[📅 行事曆語音新增] 收到文字: {text}")

    try:
        from dateutil import parser as dateparser
        from datetime import datetime, timedelta
        import re

        now = datetime.now()

        # 解析相對時間關鍵字
        text_lower = text.lower()

        # 計算日期
        if any(k in text_lower for k in ['明天', '明日']):
            base_date = now + timedelta(days=1)
        elif any(k in text_lower for k in ['後天']):
            base_date = now + timedelta(days=2)
        elif any(k in text_lower for k in ['下禮拜', '下週', '下个星期']):
            base_date = now + timedelta(days=7 - now.weekday())
        elif any(k in text_lower for k in ['禮拜', '週', '星期']):
            # 找出「禮拜X」中的數字
            weekday_map = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4, '六': 5, '日': 6, '天': 6}
            for k, v in weekday_map.items():
                if k in text_lower:
                    days_ahead = (v - now.weekday()) % 7
                    if days_ahead == 0: days_ahead = 7
                    base_date = now + timedelta(days=days_ahead)
                    break
            else:
                base_date = now
        else:
            base_date = now

        # 解析時間（時:分）
        time_match = re.search(r'(\d{1,2})[點过:](\d{0,2})', text)
        if time_match:
            hour = int(time_match.group(1))
            minute = int(time_match.group(2)) if time_match.group(2) else 0
        else:
            # 早上/下午/中午/晚上 預設
            if any(k in text_lower for k in ['早上', '上午']):
                hour, minute = 9, 0
            elif any(k in text_lower for k in ['中午']):
                hour, minute = 12, 0
            elif any(k in text_lower for k in ['下午']):
                hour, minute = 14, 0
            elif any(k in text_lower for k in ['晚上', '夜間']):
                hour, minute = 19, 0
            else:
                hour, minute = 9, 0

        # 開始時間
        start_dt = datetime(base_date.year, base_date.month, base_date.day, hour, minute)

        # 結束時間（預設 +1 小時）
        end_dt = start_dt + timedelta(hours=1)

        # 標題：移除時間相關關鍵字
        title = text
        for kw in ['明天', '明日', '後天', '今天', '早上', '上午', '中午', '下午', '晚上', '夜間',
                   '點', '過', ':', '禮拜', '週', '星期', '下禮拜', '下週', '下个星期']:
            title = re.sub(kw, '', title)
        title = re.sub(r'\d{1,2}[點过:]\d{0,2}', '', title).strip()
        if not title:
            title = '新事件'

        location = None
        loc_match = re.search(r'在(.+?)[，,]|$', text)
        if loc_match and loc_match.group(1):
            location = loc_match.group(1).strip()

        client = get_calendar_client()
        event = client.add_event(
            title=title,
            start=start_dt,
            end=end_dt,
            location=location,
        )
        print(f"[📅 行事曆事件已建立] {title} @ {start_dt}")
        return {"ok": True, "event_id": event.get("id"), "title": title}
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        print(f"[📅 行事曆語音新增失敗] {e}")
        return {"ok": False, "error": f"建立事件失敗: {e}"}

@app.post("/api/location")
def ingest_location(payload: LocationPayload):
    """
    收手機 GPS 點：
      - 寫入 SQLite
      - 餵給 HomeDetector
      - 回傳當前距家狀態
    """
    ts = payload.timestamp if payload.timestamp else time.time()
    try:
        get_db().insert_location(ts, payload.lat, payload.lng, payload.accuracy)
        status = home_detector.ingest(ts, payload.lat, payload.lng)
        return {"ok": True, **status}
    except Exception as e:
        return {"ok": False, "error": f"{e}"}

@app.post("/api/set_home")
def set_home(payload: SetHomePayload):
    """把當前位置存為家"""
    try:
        home_detector.set_home(payload.lat, payload.lng)
        return {"ok": True, "home": {"lat": payload.lat, "lng": payload.lng}}
    except Exception as e:
        return {"ok": False, "error": f"{e}"}

@app.get("/api/home_status")
def home_status():
    """回傳家裡座標 + 是否在家 + 最近一次回家/出門事件"""
    return {
        "has_home": home_detector.has_home(),
        "home": {"lat": home_detector.home_lat, "lng": home_detector.home_lng}
                if home_detector.has_home() else None,
        "is_home": home_detector._is_home,
        "latest_event": get_db().latest_home_event(),
    }

@app.post("/api/daily_summary/run")
def daily_summary_run():
    """手動觸發每日總結（測試用，正式情況由回家偵測自動觸發）"""
    try:
        from agent.daily_summary import run as run_daily_summary
        text = run_daily_summary(vision_analyzer, telegram_client)
        return {"ok": True, "summary": text, "telegram_configured": telegram_client.is_configured()}
    except Exception as e:
        return {"ok": False, "error": f"{e}"}

@app.get("/api/photos/today")
def photos_today():
    """今天 00:00 ~ 隔天 00:00 的所有拍照記錄（不含原圖二進位）"""
    from datetime import datetime as _dt
    now = _dt.now()
    start_of_day = _dt(now.year, now.month, now.day).timestamp()
    end_of_day = start_of_day + 86400
    photos = get_db().fetch_photos_between(start_of_day, end_of_day)
    return {"ok": True, "count": len(photos), "photos": photos}

@app.get("/api/photo/{photo_id}/image")
def photo_image(photo_id: int):
    """回傳指定 photo 的原圖檔"""
    photo = get_db().fetch_photo(photo_id)
    if not photo:
        raise HTTPException(status_code=404, detail="photo not found")
    path = photo["file_path"]
    # 防止 path traversal：必須在 data/photos 下
    photos_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "photos"))
    if not os.path.abspath(path).startswith(photos_root):
        raise HTTPException(status_code=403, detail="invalid path")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="file missing on disk")
    return FileResponse(path, media_type="image/jpeg")

@app.get("/api/track/today")
def track_today():
    """今天 00:00 ~ 隔天 00:00 的所有 GPS 點"""
    from datetime import datetime as _dt
    now = _dt.now()
    start_of_day = _dt(now.year, now.month, now.day).timestamp()
    end_of_day = start_of_day + 86400
    points = get_db().fetch_locations_between(start_of_day, end_of_day)
    return {"ok": True, "count": len(points), "points": points}

@app.get("/api/schedule/today")
def list_schedule_today():
    """列出今天 Google Calendar 上的事件"""
    try:
        client = get_calendar_client()
        events = client.list_events_today()
        return {
            "ok": True,
            "events": [
                {
                    "id": e.get("id"),
                    "title": e.get("summary"),
                    "start": e.get("start", {}).get("dateTime") or e.get("start", {}).get("date"),
                    "end": e.get("end", {}).get("dateTime") or e.get("end", {}).get("date"),
                    "location": e.get("location"),
                }
                for e in events
            ],
        }
    except FileNotFoundError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        return {"ok": False, "error": f"讀取事件失敗: {e}"}

if __name__ == "__main__":
    print("\n" + "="*50)
    print(" 🚀 戶外微服務伺服器已啟動 ...")
    print(" 【下一步請執行】在電腦的其他終端機執行：")
    print("                 ngrok http 8000")
    print(" 然後用手機打開 ngrok 產生的 https 網址！")
    print("="*50 + "\n")
    # 開啟 FastAPI 在 8000 Port
    uvicorn.run(app, host="0.0.0.0", port=8000)
