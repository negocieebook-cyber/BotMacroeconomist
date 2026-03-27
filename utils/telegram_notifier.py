"""
Notificador simples para Telegram.
"""

import logging
from typing import Dict, List, Optional

import requests

from config import REQUEST_TIMEOUT, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

logger = logging.getLogger(__name__)


class TelegramNotifier:
    """Cliente minimo para enviar mensagens ao Telegram."""

    def __init__(
        self,
        bot_token: str = TELEGRAM_BOT_TOKEN,
        chat_id: str = TELEGRAM_CHAT_ID,
    ):
        self.bot_token = bot_token
        self.chat_id = str(chat_id) if chat_id else ""
        self.base_url = (
            f"https://api.telegram.org/bot{self.bot_token}" if self.bot_token else ""
        )

    def is_configured(self) -> bool:
        return bool(self.bot_token and self.chat_id)

    def can_discover_chat_id(self) -> bool:
        return bool(self.bot_token)

    def send_message(self, text: str) -> Dict:
        if not self.is_configured():
            raise ValueError("Telegram nao configurado. Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")

        return self.send_message_to_chat(self.chat_id, text)

    def send_message_to_chat(self, chat_id: str, text: str, reply_to_message_id: Optional[int] = None) -> Dict:
        if not self.bot_token:
            raise ValueError("Telegram nao configurado. Defina TELEGRAM_BOT_TOKEN.")

        response = requests.post(
            f"{self.base_url}/sendMessage",
            json={
                "chat_id": str(chat_id),
                "text": text,
                "reply_to_message_id": reply_to_message_id,
            },
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        return response.json()

    def send_long_message(self, text: str, chunk_size: int = 3500) -> None:
        if not self.is_configured():
            raise ValueError("Telegram nao configurado. Defina TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID.")

        self.send_long_message_to_chat(self.chat_id, text, chunk_size=chunk_size)

    def send_long_message_to_chat(
        self,
        chat_id: str,
        text: str,
        chunk_size: int = 3500,
        reply_to_message_id: Optional[int] = None,
    ) -> None:
        if not self.bot_token:
            raise ValueError("Telegram nao configurado. Defina TELEGRAM_BOT_TOKEN.")

        chunks = []
        current = ""

        for line in text.splitlines():
            candidate = f"{current}\n{line}".strip() if current else line
            if len(candidate) <= chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = line

        if current:
            chunks.append(current)

        for index, chunk in enumerate(chunks):
            self.send_message_to_chat(
                chat_id=chat_id,
                text=chunk,
                reply_to_message_id=reply_to_message_id if index == 0 else None,
            )

    def get_latest_chat_id(self) -> Optional[str]:
        if not self.can_discover_chat_id():
            raise ValueError("Telegram bot token nao configurado.")

        response = requests.get(
            f"{self.base_url}/getUpdates",
            timeout=REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()

        updates = data.get("result", [])
        if not updates:
            return None

        for update in reversed(updates):
            message = update.get("message") or update.get("channel_post")
            if message and message.get("chat", {}).get("id") is not None:
                return str(message["chat"]["id"])

        return None

    def get_updates(self, offset: Optional[int] = None, timeout: int = 30) -> List[Dict]:
        if not self.can_discover_chat_id():
            raise ValueError("Telegram bot token nao configurado.")

        params = {
            "timeout": timeout,
        }
        if offset is not None:
            params["offset"] = offset

        response = requests.get(
            f"{self.base_url}/getUpdates",
            params=params,
            timeout=timeout + REQUEST_TIMEOUT,
        )
        response.raise_for_status()
        data = response.json()
        return data.get("result", [])
