from __future__ import annotations

import time
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import requests
from dotenv import load_dotenv

from interfaces.telegram_handlers import handle_message
from utils import TelegramNotifier

if TYPE_CHECKING:
    from agents.macroeconomist import MacroeconomistAgent


def start_telegram_bot(base_dir: Path, agent: Optional["MacroeconomistAgent"] = None) -> None:
    load_dotenv(base_dir / ".env")
    notifier = TelegramNotifier()

    if not notifier.can_discover_chat_id():
        print("TELEGRAM_BOT_TOKEN nao configurado. O bot nao foi iniciado.")
        return

    managed_agent = agent is None
    if managed_agent:
        from agents.macroeconomist import MacroeconomistAgent

        agent = MacroeconomistAgent(enable_scheduler=False)

    offset = None
    consecutive_failures = 0
    print("Escutando mensagens do Telegram via polling.")
    print("Envie uma mensagem para o bot e use Ctrl+C para encerrar.")

    try:
        while True:
            try:
                updates = notifier.get_updates(offset=offset, timeout=30)
                consecutive_failures = 0
            except requests.RequestException as exc:
                consecutive_failures += 1
                wait_seconds = min(60, 5 * consecutive_failures)
                print(
                    f"Falha temporaria no polling do Telegram ({exc}). "
                    f"Tentando novamente em {wait_seconds}s."
                )
                time.sleep(wait_seconds)
                continue

            for update in updates:
                try:
                    offset = update.get("update_id", 0) + 1
                    message = update.get("message") or update.get("channel_post")
                    if not message:
                        continue

                    chat = message.get("chat", {})
                    chat_id = chat.get("id")
                    text = (message.get("text") or "").strip()
                    message_id = message.get("message_id")

                    if not chat_id or not text:
                        continue

                    reply = handle_message(
                        base_dir=base_dir,
                        text=text,
                        agent=agent,
                        chat_id=str(chat_id),
                    )
                    notifier.send_long_message_to_chat(
                        chat_id=str(chat_id),
                        text=reply,
                        reply_to_message_id=message_id,
                    )
                except requests.RequestException as exc:
                    print(f"Falha ao processar/enviar mensagem do Telegram: {exc}")
                except Exception as exc:
                    print(f"Erro ao tratar mensagem do Telegram: {exc}")
    except KeyboardInterrupt:
        print("Escuta do Telegram encerrada.")
    finally:
        if managed_agent and agent is not None:
            agent.shutdown()
