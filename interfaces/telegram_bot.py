"""
Telegram bot — polling assíncrono com streaming de respostas LLM.
Comandos (/mercado, /status, etc.) rodam em thread; texto livre faz streaming.
"""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import aiohttp
from dotenv import load_dotenv

from config import TELEGRAM_ALLOWED_USER_IDS
from interfaces.telegram_handlers import build_streaming_messages, handle_message

if TYPE_CHECKING:
    from agents.macroeconomist import MacroeconomistAgent

logger = logging.getLogger(__name__)

_TG = "https://api.telegram.org/bot{token}/{method}"


# ── Helpers Telegram API ─────────────────────────────────────────────────────

async def _api(session: aiohttp.ClientSession, token: str, method: str, **kw) -> dict:
    url = _TG.format(token=token, method=method)
    try:
        async with session.post(url, json=kw, timeout=aiohttp.ClientTimeout(total=15)) as r:
            return await r.json()
    except Exception as exc:
        logger.debug(f"Telegram {method} falhou: {exc}")
        return {}


async def _send(session, token, chat_id, text, reply_to=None) -> dict:
    kw = {"chat_id": chat_id, "text": text[:4096], "parse_mode": "Markdown"}
    if reply_to:
        kw["reply_to_message_id"] = reply_to
    return await _api(session, token, "sendMessage", **kw)


async def _edit(session, token, chat_id, msg_id, text: str) -> None:
    await _api(session, token, "editMessageText",
               chat_id=chat_id, message_id=msg_id,
               text=text[:4096], parse_mode="Markdown")


async def _send_photo(session, token, chat_id: str, path: str, caption: str = "") -> None:
    url = _TG.format(token=token, method="sendPhoto")
    try:
        with open(path, "rb") as f:
            data = aiohttp.FormData()
            data.add_field("chat_id", chat_id)
            data.add_field("caption", caption[:1024])
            data.add_field("photo", f, filename=Path(path).name, content_type="image/png")
            async with session.post(url, data=data, timeout=aiohttp.ClientTimeout(total=30)) as r:
                await r.json()
    except Exception as exc:
        logger.warning(f"Erro ao enviar foto: {exc}")


async def _get_updates(session, token: str, offset: Optional[int], timeout: int = 30) -> list:
    url = _TG.format(token=token, method="getUpdates")
    params: dict = {"timeout": timeout}
    if offset is not None:
        params["offset"] = offset
    try:
        async with session.get(
            url, params=params,
            timeout=aiohttp.ClientTimeout(total=timeout + 10),
        ) as r:
            return (await r.json()).get("result", [])
    except Exception as exc:
        logger.warning(f"Erro no polling: {exc}")
        return []


# ── Streaming ────────────────────────────────────────────────────────────────

async def _stream_reply(
    session, token, chat_id: str, reply_to: Optional[int],
    agent: "MacroeconomistAgent", text: str, base_dir: Path,
) -> None:
    """Envia placeholder, transmite LLM em chunks e edita a mensagem ao vivo."""
    sent = await _send(session, token, chat_id, "⏳ _Analisando..._", reply_to=reply_to)
    msg_id = (sent.get("result") or {}).get("message_id")
    if not msg_id:
        return

    messages = await asyncio.to_thread(
        build_streaming_messages, agent, chat_id, text, base_dir
    )

    accumulated = ""
    last_len = 0
    last_t = asyncio.get_event_loop().time()

    async for chunk in agent.llm.stream_response(messages):
        accumulated += chunk
        now = asyncio.get_event_loop().time()
        if len(accumulated) - last_len >= 150 or (now - last_t) >= 0.8:
            try:
                await _edit(session, token, chat_id, msg_id, accumulated + " ▌")
                last_len = len(accumulated)
                last_t = now
            except Exception:
                pass

    if accumulated:
        await _edit(session, token, chat_id, msg_id, accumulated)
        await asyncio.to_thread(agent._remember_turn, chat_id, text, accumulated)
    else:
        await _edit(session, token, chat_id, msg_id, "Não consegui gerar uma resposta agora.")


# ── Dispatcher ───────────────────────────────────────────────────────────────

async def _handle_update(
    session, token: str, base_dir: Path,
    agent: Optional["MacroeconomistAgent"], message: dict,
) -> None:
    chat_id = str((message.get("chat") or {}).get("id", ""))
    text = (message.get("text") or "").strip()
    msg_id = message.get("message_id")
    if not chat_id or not text:
        return

    user_id = (message.get("from") or {}).get("id")
    if TELEGRAM_ALLOWED_USER_IDS and user_id not in TELEGRAM_ALLOWED_USER_IDS:
        logger.warning(f"Mensagem ignorada — user_id não autorizado: {user_id}")
        return

    use_stream = (
        not text.startswith("/")
        and agent is not None
        and agent.llm.is_available()
    )

    if use_stream:
        await _stream_reply(session, token, chat_id, msg_id, agent, text, base_dir)
        return

    # Comandos e fallback: handler síncrono em thread
    reply = await asyncio.to_thread(
        handle_message, base_dir=base_dir, text=text, agent=agent, chat_id=chat_id,
    )

    if isinstance(reply, dict):
        reply_text = reply.get("text", "")
        photos = reply.get("photos", [])
    else:
        reply_text = str(reply)
        photos = []

    if reply_text:
        for i in range(0, len(reply_text), 3500):
            await _send(session, token, chat_id, reply_text[i:i + 3500],
                        reply_to=msg_id if i == 0 else None)
    for photo in photos:
        await _send_photo(session, token, chat_id, photo.get("path", ""), photo.get("caption", ""))


# ── Entry points ─────────────────────────────────────────────────────────────

async def start_telegram_bot_async(
    base_dir: Path, agent: Optional["MacroeconomistAgent"] = None
) -> None:
    load_dotenv(base_dir / ".env")

    from utils import TelegramNotifier
    notifier = TelegramNotifier()
    if not notifier.can_discover_chat_id():
        print("TELEGRAM_BOT_TOKEN não configurado. Bot não iniciado.")
        return

    token = notifier.bot_token
    managed = agent is None
    if managed:
        from agents.macroeconomist import MacroeconomistAgent
        agent = await asyncio.to_thread(MacroeconomistAgent, False)

    offset: Optional[int] = None
    failures = 0
    print("Bot Telegram iniciado (async + streaming). Ctrl+C para encerrar.")

    try:
        async with aiohttp.ClientSession() as session:
            while True:
                updates = await _get_updates(session, token, offset)

                if not updates and failures == 0:
                    pass
                elif not updates:
                    failures += 1
                    await asyncio.sleep(min(60, 5 * failures))
                    continue
                else:
                    failures = 0

                tasks = []
                for upd in updates:
                    offset = upd.get("update_id", 0) + 1
                    msg = upd.get("message") or upd.get("channel_post")
                    if msg:
                        tasks.append(
                            _handle_update(session, token, base_dir, agent, msg)
                        )

                if tasks:
                    results = await asyncio.gather(*tasks, return_exceptions=True)
                    for r in results:
                        if isinstance(r, Exception):
                            logger.error(f"Erro ao processar mensagem: {r}")

    except KeyboardInterrupt:
        print("Bot encerrado.")
    finally:
        if managed and agent:
            await asyncio.to_thread(agent.shutdown)


def start_telegram_bot(base_dir: Path, agent: Optional["MacroeconomistAgent"] = None) -> None:
    """Wrapper síncrono — mantém compatibilidade com chamadas existentes."""
    asyncio.run(start_telegram_bot_async(base_dir, agent))
