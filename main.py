"""
Ponto de entrada simples para o agente.

Comandos:
    python main.py start
    python main.py demo
    python main.py once
    python main.py learning
    python main.py ask <pergunta>
    python main.py chat
    python main.py telegram-listen
    python main.py learn-now
    python main.py collect-articles
    python main.py daily-thesis
    python main.py thesis <tema>
    python main.py source-demo
    python main.py rss <feed_url> [source_name]
    python main.py daily-digest
    python main.py report
    python main.py status
    python main.py run
    python main.py telegram-test
    python main.py telegram-chat-id
"""

import sys
import time
from datetime import datetime, timezone

from agents.macroeconomist import MacroeconomistAgent
from config import ENABLE_TELEGRAM_NOTIFICATIONS, LOG_FILE, LOG_LEVEL
from utils import (
    TelegramNotifier,
    build_market_report,
    build_telegram_market_brief,
    save_report,
    setup_logger,
)

logger = setup_logger(LOG_LEVEL, LOG_FILE)


def format_status_text(status: dict) -> str:
    task_stats = status.get("task_stats", {})
    memory = status.get("memory", {})
    system = status.get("system", {})

    lines = [
        "Status do BotMacroeconomist",
        f"Horario: {status.get('timestamp', '-')}",
        f"Documentos na memoria: {memory.get('total_documents', 0)}",
        f"Execucoes: {task_stats.get('total_executions', 0)}",
        f"Sucesso: {task_stats.get('successful', 0)}",
        f"Falhas: {task_stats.get('failed', 0)}",
        f"FRED pronto: {'sim' if system.get('fred_available') else 'nao'}",
        f"IMF pronto: {'sim' if system.get('imf_available') else 'nao'}",
        f"World Bank pronto: {'sim' if system.get('worldbank_available') else 'nao'}",
        f"OECD pronto: {'sim' if system.get('oecd_available') else 'nao'}",
        f"BIS pronto: {'sim' if system.get('bis_available') else 'nao'}",
    ]
    return "\n".join(lines)


def format_cycle_summary(label: str, data: dict) -> str:
    content_size = len(str(data))
    top_level_keys = list(data.keys())[:8] if isinstance(data, dict) else []
    return (
        f"Resumo da coleta: {label}\n"
        f"Tamanho bruto: {content_size} caracteres\n"
        f"Principais blocos: {', '.join(top_level_keys) if top_level_keys else 'nenhum'}"
    )


def format_learning_text(snapshot: dict) -> str:
    memory = snapshot.get("memory", {})
    recent_documents = snapshot.get("recent_documents", [])

    lines = [
        "O que o agente esta aprendendo",
        f"Horario: {snapshot.get('timestamp', '-')}",
        f"Documentos na memoria: {memory.get('total_documents', 0)}",
        "",
    ]

    if not recent_documents:
        lines.append("Nenhum aprendizado foi armazenado ainda.")
        return "\n".join(lines)

    for index, item in enumerate(recent_documents, 1):
        metadata = item.get("metadata", {})
        lines.extend(
            [
                f"{index}. {metadata.get('focus_area', 'Sem foco definido')}",
                f"API: {metadata.get('api', 'desconhecida')}",
                f"Quando: {metadata.get('timestamp', '-')}",
                f"Preview: {item.get('preview', '')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def format_thesis_text(thesis: dict) -> str:
    lines = [
        f"Tese macro: {thesis.get('topic', '-')}",
        f"Horario: {thesis.get('timestamp', '-')}",
        f"Tese: {thesis.get('thesis', '-')}",
        f"Fontes encontradas: {thesis.get('source_count', 0)}",
        f"Memoria tecnica/mercado: {thesis.get('memory_count', 0)}",
        "",
        "Evidencias:",
    ]

    for item in thesis.get("evidence", []):
        lines.append(f"- {item}")

    lines.extend(["", "Riscos:"])
    for item in thesis.get("risks", []):
        lines.append(f"- {item}")

    lines.extend(["", "Citacoes:"])
    citations = thesis.get("citations", [])
    if not citations:
        lines.append("- Nenhuma citacao disponivel.")
    else:
        for citation in citations:
            title = citation.get("title", "Sem titulo")
            source = citation.get("source", "fonte")
            published_at = citation.get("published_at", "-")
            url = citation.get("url", "")
            lines.append(f"- {title} | {source} | {published_at} {url}".strip())

    return "\n".join(lines)


def format_chat_answer(response: dict) -> str:
    lines = [
        "Conversa com a memoria do bot",
        f"Horario: {response.get('timestamp', '-')}",
        "",
        response.get("answer", "Sem resposta."),
    ]

    sources = response.get("sources", [])
    if sources:
        lines.extend(["", "Fontes usadas:"])
        for item in sources[:3]:
            metadata = item.get("metadata", {})
            label = (
                metadata.get("title")
                or metadata.get("focus_area")
                or metadata.get("source_name")
                or metadata.get("api")
                or "Memoria"
            )
            timestamp = metadata.get("timestamp", "-")
            lines.append(f"- {label} | {timestamp}")

    return "\n".join(lines)


def maybe_send_telegram(message: str) -> None:
    if not ENABLE_TELEGRAM_NOTIFICATIONS:
        return

    try:
        notifier = TelegramNotifier()
        notifier.send_long_message(message)
        logger.info("Resumo enviado para o Telegram")
    except Exception as e:
        logger.warning(f"Nao foi possivel enviar ao Telegram: {str(e)}")


def run_status() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        status = agent.get_agent_status()
        text = format_status_text(status)
        logger.info("\n" + text)
        maybe_send_telegram(text)
    finally:
        agent.shutdown()


def run_once() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Rodando uma coleta simples...")

        monday = agent.monday_inflation_policy()
        monday_summary = format_cycle_summary("segunda", monday)
        logger.info("\n" + monday_summary)

        tuesday = agent.tuesday_economic_growth()
        tuesday_summary = format_cycle_summary("terca", tuesday)
        logger.info("\n" + tuesday_summary)

        status = agent.get_agent_status()
        final_text = (
            monday_summary
            + "\n\n"
            + tuesday_summary
            + "\n\n"
            + format_status_text(status)
        )
        maybe_send_telegram(final_text)
    finally:
        agent.shutdown()


def run_learning() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        snapshot = agent.get_learning_snapshot(limit=5)
        text = format_learning_text(snapshot)
        logger.info("\n" + text)
    finally:
        agent.shutdown()


def run_ask(question: str) -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        response = agent.answer_learning_question(question, n_results=5)
        logger.info("\n" + response.get("answer", "Sem resposta."))
    finally:
        agent.shutdown()


def run_chat() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Modo chat iniciado. Digite sua pergunta ou 'sair' para encerrar.")
        logger.info("Exemplo: o que voce aprendeu hoje sobre inflacao?")

        while True:
            question = input("\nVoce: ").strip()
            if not question:
                continue
            if question.lower() in {"sair", "exit", "quit"}:
                logger.info("Chat encerrado.")
                break

            response = agent.answer_learning_question(
                question,
                n_results=5,
                session_id="terminal_chat",
            )
            print("\nBot:\n" + response.get("answer", "Sem resposta."))
    finally:
        agent.shutdown()


def run_learn_now() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        result = agent.learn_daily_technical_content()
        logger.info(f"Aprendizado tecnico: {result}")
    finally:
        agent.shutdown()


def run_collect_articles() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        result = agent.collect_daily_research_articles()
        logger.info(f"Coleta de artigos: {result}")
    finally:
        agent.shutdown()


def run_daily_thesis() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        result = agent.generate_daily_thesis()
        logger.info(f"Tese diaria: {result}")
    finally:
        agent.shutdown()


def run_source_demo() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        demo_content = (
            "Artigo de exemplo: juros reais elevados seguem restringindo credito e "
            "atividade, enquanto o mercado monitora desinflacao e premio de prazo."
        )
        result = agent.ingest_source_document(
            title="Exemplo de artigo macro",
            content=demo_content,
            source_name="Demo Research Feed",
            url="https://example.com/macro-demo",
            published_at=datetime.now(timezone.utc).isoformat(),
            tags=["juros", "inflacao", "credito"],
        )
        logger.info(f"Fonte demo: {result}")
    finally:
        agent.shutdown()


def run_thesis(topic: str) -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        thesis = agent.build_source_backed_thesis(topic, n_results=5)
        logger.info("\n" + format_thesis_text(thesis))
    finally:
        agent.shutdown()


def run_rss(feed_url: str, source_name: str) -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        result = agent.ingest_rss_feed(feed_url=feed_url, source_name=source_name, limit=5)
        logger.info(f"RSS ingerido: {result}")
    finally:
        agent.shutdown()


def run_daily_digest() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        agent.send_daily_learning_digest()
    finally:
        agent.shutdown()


def run_report() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Gerando relatorio do mercado...")

        collected = {
            "inflacao_politica": agent.monday_inflation_policy(),
            "crescimento": agent.tuesday_economic_growth(),
        }
        status = agent.get_agent_status()

        report_text = build_market_report(collected, status)
        report_path = save_report(report_text)
        telegram_brief = build_telegram_market_brief(collected, status)

        logger.info(f"Relatorio salvo em: {report_path}")
        logger.info("\n" + report_text)
        maybe_send_telegram(telegram_brief + "\n\nArquivo completo: " + report_path)
    finally:
        agent.shutdown()


def run_demo() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Demo iniciado")

        status_before = format_status_text(agent.get_agent_status())
        logger.info("\n" + status_before)

        monday = agent.monday_inflation_policy()
        logger.info("\n" + format_cycle_summary("segunda", monday))

        search_results = agent.search_knowledge("inflacao juros crescimento", n_results=3)
        logger.info(f"Busca na memoria retornou {search_results['results_count']} resultado(s)")

        analysis = agent.analyze_indicator("CPI")
        logger.info(
            f"Analise pronta para {analysis['indicator']} com "
            f"{len(analysis['historical_data'].get('results', []))} resultado(s) historico(s)"
        )

        status_after = format_status_text(agent.get_agent_status())
        logger.info("\n" + status_after)
    finally:
        agent.shutdown()


def run_scheduler() -> None:
    logger.info("Iniciando modo continuo com scheduler...")
    agent = MacroeconomistAgent(enable_scheduler=True)

    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        logger.info("Encerramento solicitado")
    finally:
        agent.shutdown()


def telegram_test() -> None:
    try:
        notifier = TelegramNotifier()
        now = datetime.utcnow().isoformat()
        notifier.send_message(f"Teste do BotMacroeconomist em {now}")
        logger.info("Mensagem de teste enviada para o Telegram")
    except Exception as e:
        logger.error(f"Nao foi possivel enviar mensagem: {str(e)}")
        logger.info("Confirme TELEGRAM_BOT_TOKEN e TELEGRAM_CHAT_ID no arquivo .env")


def telegram_chat_id() -> None:
    try:
        notifier = TelegramNotifier()
        chat_id = notifier.get_latest_chat_id()

        if chat_id:
            logger.info(f"Seu chat id mais recente e: {chat_id}")
        else:
            logger.info("Nao encontrei chat id. Primeiro mande uma mensagem para o bot no Telegram.")
    except Exception as e:
        logger.error(f"Nao foi possivel consultar o chat id: {str(e)}")
        logger.info("Confirme TELEGRAM_BOT_TOKEN no arquivo .env")


def serve_telegram(agent: MacroeconomistAgent) -> None:
    notifier = TelegramNotifier()
    offset = None

    try:
        if not notifier.can_discover_chat_id():
            logger.error("Telegram nao configurado. Defina TELEGRAM_BOT_TOKEN no arquivo .env")
            return

        logger.info("Escutando mensagens do Telegram via polling...")
        logger.info("Envie uma mensagem para o bot no Telegram. Para parar localmente, use Ctrl+C.")

        while True:
            updates = notifier.get_updates(offset=offset, timeout=30)
            for update in updates:
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

                logger.info(f"Mensagem recebida do Telegram em chat {chat_id}: {text}")
                reply = agent.answer_telegram_message(text, chat_id=str(chat_id))
                notifier.send_long_message_to_chat(
                    chat_id=str(chat_id),
                    text=reply,
                    reply_to_message_id=message_id,
                )
                logger.info(f"Resposta enviada para chat {chat_id}")
    except KeyboardInterrupt:
        logger.info("Escuta do Telegram encerrada")
    except Exception as e:
        logger.error(f"Erro na escuta do Telegram: {str(e)}")


def telegram_listen() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        serve_telegram(agent)
    finally:
        agent.shutdown()


def run_start() -> None:
    logger.info("Iniciando modo completo: scheduler, memoria e Telegram...")
    agent = MacroeconomistAgent(enable_scheduler=True)

    try:
        serve_telegram(agent)
    except KeyboardInterrupt:
        logger.info("Encerramento solicitado")
    finally:
        agent.shutdown()


def print_help() -> None:
    logger.info(
        "\n".join(
            [
                "Comandos disponiveis:",
                "  python main.py start",
                "  python main.py demo",
                "  python main.py once",
                "  python main.py learning",
                "  python main.py ask <pergunta>",
                "  python main.py chat",
                "  python main.py telegram-listen",
                "  python main.py learn-now",
                "  python main.py collect-articles",
                "  python main.py daily-thesis",
                "  python main.py thesis <tema>",
                "  python main.py source-demo",
                "  python main.py rss <feed_url> [source_name]",
                "  python main.py daily-digest",
                "  python main.py report",
                "  python main.py status",
                "  python main.py run",
                "  python main.py telegram-test",
                "  python main.py telegram-chat-id",
            ]
        )
    )


def main() -> None:
    command = sys.argv[1].lower() if len(sys.argv) > 1 else "start"
    command_args = sys.argv[2:]

    if command == "start":
        run_start()
    elif command == "demo":
        run_demo()
    elif command == "once":
        run_once()
    elif command == "learning":
        run_learning()
    elif command == "ask":
        question = " ".join(command_args).strip()
        if not question:
            print_help()
            return
        run_ask(question)
    elif command == "chat":
        run_chat()
    elif command == "telegram-listen":
        telegram_listen()
    elif command == "learn-now":
        run_learn_now()
    elif command == "collect-articles":
        run_collect_articles()
    elif command == "daily-thesis":
        run_daily_thesis()
    elif command == "source-demo":
        run_source_demo()
    elif command == "thesis":
        topic = " ".join(command_args).strip() or "inflacao e juros reais"
        run_thesis(topic)
    elif command == "rss":
        feed_url = command_args[0] if command_args else ""
        source_name = " ".join(command_args[1:]).strip() or "RSS Feed"
        if not feed_url:
            print_help()
            return
        run_rss(feed_url, source_name)
    elif command == "daily-digest":
        run_daily_digest()
    elif command == "report":
        run_report()
    elif command == "status":
        run_status()
    elif command == "run":
        run_scheduler()
    elif command == "telegram-test":
        telegram_test()
    elif command == "telegram-chat-id":
        telegram_chat_id()
    else:
        print_help()


if __name__ == "__main__":
    main()
