# 智慧視障輔助導航系統
## Vision-Aided AR Navigation System

---

## 目录 / Contents

1. [問題背景 Problem](#問題背景)
2. [系統架構 System Architecture](#系統架構)
3. [核心技術 Core Technologies](#核心技術)
4. [雙模式展示 Dual Mode](#雙模式展示)
5. [障礙偵測實測 Obstacle Detection](#障礙偵測實測)
6. [AI 整合 AI Integration](#ai-整合)
7. [功能演示 Features](#功能演示)
8. [技術規格 Specifications](#技術規格)
9. [結論 Conclusion](#結論)

---

<!-- slide -->
## 問題背景 Problem

### 挑戰 Challenges

| 統計數據 | 說明 |
|---------|------|
| 全球 2.85 億 | 視障人口 |
|老年人跌倒 | 死亡率主因之一 |
| 傳統白手杖 | 僅能探測地面障礙，無法向上偵測頭部高度障礙 |

### 我們的使命

> **讓每一位視障者與高齡者都能安全、自由地行動**

<!-- slide -->
## 系統架構 System Architecture

### 雙模式設計 Dual Mode Design

```
┌────────────────────────────────────────────────────┐
│           智慧視障輔助導航系統                       │
├────────────────────┬───────────────────────────────┤
│  桌面直接模式       │  行動網頁模式                  │
│  python src/main.py │  python src/web_main.py       │
│  USB Camera + 語音  │  行動瀏覽器 + ngrok HTTPS      │
└────────────────────┴───────────────────────────────┘
                     │
           ┌────────┴────────┐
           ▼                 ▼
   ┌──────────────┐  ┌──────────────┐
   │NavigationAgent│  │ VisionAnalyzer│
   │  決策大腦     │  │  商品辨識    │
   └──────┬───────┘  └──────┬───────┘
          │                 │
   ┌──────┴───────┐  ┌──────┴───────┐
   │ObstacleDetector│ │  OpenClaw AI │
   │ YOLOv8+OpenCV │  │ (port 18789) │
   └──────────────┘  └──────────────┘
```

### 技術堆疊 Tech Stack

- **視覺**：Ultralytics YOLOv8n + OpenCV
- **AI 推理**：OpenClaw (WebSocket RPC / HTTP REST)
- **語音**：Web Speech API + Google STT
- **網頁服務**：FastAPI + Uvicorn
- **地圖定位**：Browser Geolocation API
- **行事曆**：Google Calendar API

<!-- slide -->
## 核心技術 Core Technologies

### YOLOv8 障礙偵測

| 項目 | 規格 |
|------|------|
| 模型 | YOLOv8n (nano) |
| 速度 | ~0.1 秒/幀 |
| 類別數 | 51 種障礙物 |
| 翻譯 | 英文 → 中文 即時轉換 |

**支援障礙物類別（部分）**：
行人、腳踏車、汽車、機車、公車、紅綠燈、消防栓、停車標誌、長椅、貓咪、狗狗、背包、雨傘、行李箱、滑板、瓶子、杯子、叉子、刀子、湯匙、碗、香蕉、蘋果、三明治、披薩、甜甜圈、蛋糕、椅子、沙發、盆栽、床鋪、餐桌、馬桶、筆電、滑鼠、鍵盤、手機、微波爐、烤箱、冰箱、書本、時鐘、花瓶、剪刀、泰迪熊...

### OpenCV 盲點雷達

| 項目 | 說明 |
|------|------|
| 掃描區域 | 畫面最下方 1/3（腳步前方）|
| 演算法 | Canny 邊緣檢測 |
| 判斷標準 | 邊緣密度 > 4% 判定為有障礙 |
| 用途 | 補足 YOLO 無法偵測的地面突起物 |

### 雙層偵測流程

```
Frame 輸入
    │
    ├── 第一層：YOLOv8 即時偵測
    │         輸出：常見障礙物（行人、車輛...）
    │
    └── 第二層：OpenCV 盲點雷達
              掃描：地面邊緣密度
              輸出：未知地面障礙（電風扇、垃圾堆...）
    │
    ▼
Warning 輸出 + 語音播報
```

<!-- slide -->
## 雙模式展示 Dual Mode

### 桌面直接模式 Desktop Mode

**啟動命令**：
```bash
python src/main.py
```

**功能特色**：
- OpenCV 視窗顯示即時 camera 畫面
- 障礙物偵測結果即時疊加顯示
- 鍵盤快捷鍵：
  - `q` — 結束程式
  - `m` — 切換導航/助理模式
  - `v` — 拍照商品辨識

### 行動網頁模式 Mobile Mode

**啟動命令**：
```bash
python src/web_main.py
ngrok http 8000  # 另一個終端機
```

**功能特色**：
- 透過瀏覽器存取，無需安裝 App
- 手機後鏡頭作為輸入源
- 全觸控操作，適合室外使用
- 結合 GPS 定位與行事曆

<!-- slide -->
## 障礙偵測實測 Obstacle Detection

### 即時偵測展示

**偵測場景**：
1. 行人靠近 → 「請小心，前方發現行人」
2. 車輛通過 → 「請小心，前方發現汽車」
3. 地面障礙 → 「請小心，前方發現地面雜物」

### 技術實現

```python
# obstacle_detector.py — YOLO 偵測
results = self.model(frame, conf=0.3, verbose=False)
for r in results:
    for box in r.boxes:
        class_name = self.model.names[c_id]
        zh_name = self.en_to_zh_map.get(class_name, class_name)
        detected_items.append(zh_name)

# OpenCV 盲點雷達
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
ROI = gray[int(h*0.66):h, :]  # 下 1/3 區域
edges = cv2.Canny(ROI, 50, 150)
edge_density = np.sum(edges > 0) / total_pixels
if edge_density > 0.04:
    detected_items.append("地面雜物")
```

### 效能表現

| 指標 | 數值 |
|------|------|
| 偵測延遲 | < 0.1 秒 |
| 語音播報延遲 | < 0.3 秒 |
| 總回應時間 | < 0.5 秒 |

<!-- slide -->
## AI 整合 AI Integration

### OpenClaw 決策大腦

| 項目 | 規格 |
|------|------|
| 端點 | http://127.0.0.1:18789 |
| 協定 | WebSocket RPC（優先）/ HTTP REST |
| 認證 | Bearer Token |
| 模型 | gemini-3-flash |

### 連線流程

```
1. 嘗試 WebSocket 連線
   └─ 失敗則降級至 HTTP REST

2. WebSocket 握手：
   nonce challenge → response → 驗證成功後開始 RPC 通訊

3. 傳送請求：
   chat.send({ prompt, imageBase64 })
```

### 應用場景

| 場景 | 說明 |
|------|------|
| 複雜推理 | 當 YOLO 無法判斷時，AI 提供決策建議 |
| 商品辨識 | 拍攝產品外包裝，自動搜尋 Shopee 價格與評論 |
| 每日摘要 | 回家時自動生成行程摘要，發送至 Telegram |

<!-- slide -->
## 功能演示 Features

### 障礙偵測與語音警告

- 即時偵測前方障礙物
- 中文語音朗讀警告內容
- 導航模式：語音播報開啟
- 助理模式：僅顯示文字警告

### 語音指令

- 按下 🎤 按鈕開始錄音
- 說出指令（如「拍照」）
- 系統執行並語音回應

### 回家偵測

- GPS 持續追蹤位置
- 接近家的範圍（20m）自動提醒
- 「歡迎回家」語音通知

### 行事曆整合

- 語音新增 Google Calendar 事件
- 支援自然語言：「明天九點看醫生」
- 查詢今日行程

### 商品辨識

- 拍攝產品外包裝
- OpenClaw AI 分析圖片
- 回傳：產品名稱、價格、Shopee 連結

<!-- slide -->
## 技術規格 Specifications

### 系統架構

| 元件 | 技術 |
|------|------|
| 障礙偵測 | YOLOv8n + OpenCV Canny |
| AI 推理 | OpenClaw WebSocket RPC |
| 網頁服務 | FastAPI + Uvicorn |
| 前端介面 | 純 HTML/CSS/JS（無框架）|
| 語音合成 | Web Speech API |
| 語音辨識 | Google Speech Recognition |
| 地圖定位 | Browser Geolocation API |
| 行事曆 | Google Calendar API |
| 訊息推播 | Telegram Bot |

### 設定參數

| 參數 | 預設值 |
|------|--------|
| Camera Index | 1（外部 USB 攝影機）|
| YOLO 信心閾值 | 0.3 |
| 盲點雷達閾值 | 0.04（4% 邊緣密度）|
| 安全距離 | 1.0 公尺 |
| 警告距離 | 3.0 公尺 |
| API 冷卻時間 | 3.0 秒 |

### 支援平台

- **桌面**：Windows/macOS/Linux（需 Python 3.8+）
- **行動**：iOS Safari/Android Chrome（需 ngrok HTTPS）

<!-- slide -->
## 結論 Conclusion

### 我們解決了什麼？

| 問題 | 我們的方案 |
|------|-----------|
| 白手杖無法偵測頭部高度障礙 | YOLOv8 即時偵測 51 種障礙物 |
| 地面障礙（電風扇、垃圾）YOLO 看不見 | OpenCV 盲點雷達補足死角 |
| 複雜情境需要智慧判斷 | OpenClaw AI 提供推理建議 |
| 視障者操作不便 | 全語音介面，無需觸控 |
| 外出時無法使用 | 行動網頁模式，跨平台支援 |

### 未來展望

- [ ] 加入 A* 路徑規劃
- [ ] 整合更多 AI 模型
- [ ] 支援更多語言
- [ ] 離線模式強化

---

## 感謝聆聽

**智慧視障輔助導航系統**

github.com/你的專案

*謝謝*