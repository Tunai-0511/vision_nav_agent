"""
Telegram Bot API 直連客戶端

設定方式：
  TELEGRAM_BOT_TOKEN  (env)  從 @BotFather /newbot 取得
  TELEGRAM_CHAT_ID    (env)  你跟 bot 對話的 chat id
                              （傳訊息給 bot 後到 https://api.telegram.org/bot<TOKEN>/getUpdates 找）
"""
import logging
import os
from typing import Optional

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org"


class TelegramClient:
    def __init__(self, bot_token: Optional[str] = None, chat_id: Optional[str] = None):
        self.bot_token = bot_token or os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
        self.chat_id = chat_id or os.environ.get("TELEGRAM_CHAT_ID", "").strip()

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def send_message(self, text: str, parse_mode: Optional[str] = None) -> bool:
        if not self.is_configured():
            logger.warning("Telegram 未設定 (缺 TELEGRAM_BOT_TOKEN 或 TELEGRAM_CHAT_ID)")
            return False
        url = f"{API_BASE}/bot{self.bot_token}/sendMessage"
        payload = {"chat_id": self.chat_id, "text": text}
        if parse_mode:
            payload["parse_mode"] = parse_mode
        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code != 200:
                logger.error(f"Telegram send_message HTTP {r.status_code}: {r.text[:200]}")
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram send_message failed: {e}")
            return False

    def send_photo(self, photo_bytes: bytes, caption: Optional[str] = None) -> bool:
        """發送圖片到 Telegram（供 OpenClaw 處理）"""
        if not self.is_configured():
            logger.warning("Telegram 未設定，無法發送圖片")
            return False
        url = f"{API_BASE}/bot{self.bot_token}/sendPhoto"
        payload = {"chat_id": self.chat_id}
        if caption:
            payload["caption"] = caption
        try:
            r = requests.post(url, files={"photo": ("photo.jpg", photo_bytes, "image/jpeg")}, data=payload, timeout=30)
            if r.status_code != 200:
                logger.error(f"Telegram send_photo HTTP {r.status_code}: {r.text[:200]}")
                return False
            return True
        except Exception as e:
            logger.error(f"Telegram send_photo failed: {e}")
            return False
