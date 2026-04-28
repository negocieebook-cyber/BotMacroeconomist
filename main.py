"""
Ponto de entrada simples para o agente.

Comandos:
    python main.py start
    python main.py demo
    python main.py once
    python main.py learning
    python main.py ask <pergunta>
    python main.py chat
    python main.py macro-chat
    python main.py telegram-listen
    python main.py learn-now
    python main.py collect-articles
    python main.py daily-thesis
    python main.py bootstrap-learning
    python main.py bootstrap-assets
    python main.py learning-catalog
    python main.py daily
    python main.py weekly
    python main.py editorial-learn
    python main.py full-cycle
    python main.py topic <tema>
    python main.py ingest [--text ... --url ... --fact ... --source ... --topic ...]
    python main.py tracked-profiles
    python main.py x-drafts
    python main.py x-schedule
    python main.py x-tomorrow
    python main.py x-check
    python main.py newsletter-preview
    python main.py newsletter-draft
    python main.py telegram-editorial
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

import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml
from agents.macroeconomist import MacroeconomistAgent
from collect.x_collect import diagnose_x_api
from collect.manual_ingest import ingest_manual_item
from config import ENABLE_TELEGRAM_NOTIFICATIONS, LOG_FILE, LOG_LEVEL
from interfaces.telegram_bot import start_telegram_bot
from knowledge.document_learning import build_source_catalog
from learn.bootstrap_user_context import bootstrap_user_learning
from scheduler.content_scheduler import format_latest_x_drafts, format_week_schedule
from scheduler.daily_jobs import run_content_generation_pipeline, run_daily_pipeline, run_topic_pipeline
from scheduler.weekly_jobs import run_learning_pipeline, run_weekly_pipeline
from utils import (
    TelegramNotifier,
    build_market_report,
    build_telegram_market_brief,
    save_report,
    setup_logger,
)

logger = setup_logger(LOG_LEVEL, LOG_FILE)


def _file_is_current(path: Path, scope: str = "day") -> bool:
    if not path.exists():
        return False

    modified = datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc)
    now = datetime.now(timezone.utc)

    if scope == "week":
        return modified.isocalendar()[:2] == now.isocalendar()[:2]

    return modified.date() == now.date()


def ensure_startup_pipelines(base_dir: Path) -> None:
    """Garante que os artefatos principais do fluxo expandido existam ao subir o projeto."""
    daily_history = base_dir / "data" / "processed" / "daily_history.json"
    weekly_history = base_dir / "data" / "processed" / "weekly_history.json"
    learning_history = base_dir / "data" / "processed" / "learning_history.json"

    if not _file_is_current(daily_history, scope="day"):
        logger.info("Pipeline diario ainda nao foi gerado hoje. Executando sincronizacao inicial...")
        try:
            run_daily_pipeline(base_dir)
        except Exception as e:
            logger.warning(f"Nao foi possivel concluir a sincronizacao diaria inicial: {str(e)}")
    else:
        logger.info("Pipeline diario ja esta atualizado para hoje.")

    if not _file_is_current(weekly_history, scope="week"):
        logger.info("Pipeline semanal ainda nao foi gerado nesta semana. Executando sincronizacao inicial...")
        try:
            run_weekly_pipeline(base_dir)
        except Exception as e:
            logger.warning(f"Nao foi possivel concluir a sincronizacao semanal inicial: {str(e)}")
    else:
        logger.info("Pipeline semanal ja esta atualizado nesta semana.")

    if not _file_is_current(learning_history, scope="week"):
        logger.info("Pipeline de aprendizado ainda nao foi gerado nesta semana. Executando sincronizacao inicial...")
        try:
            run_learning_pipeline(base_dir)
        except Exception as e:
            logger.warning(f"Nao foi possivel concluir a sincronizacao de aprendizado inicial: {str(e)}")
    else:
        logger.info("Pipeline de aprendizado ja esta atualizado nesta semana.")


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
    lines = [response.get("answer", "Sem resposta.")]

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
    agent = MacroeconomistAgent(enable_scheduler=False, quiet_console=True)
    try:
        print("Chat iniciado. Digite sua pergunta ou 'sair' para encerrar.")
        print("Exemplo: o que voce aprendeu hoje sobre inflacao?")

        while True:
            question = input("\nVoce: ").strip()
            if not question:
                continue
            if question.lower() in {"sair", "exit", "quit"}:
                print("Chat encerrado.")
                break

            response = agent.answer_learning_question(
                question,
                n_results=5,
                session_id="terminal_chat",
            )
            print("\nBot:\n" + format_chat_answer(response))
    finally:
        agent.shutdown()


def run_macro_chat() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False, quiet_console=True)
    try:
        print("Macro Chat iniciado. Digite 'sair' para encerrar.")
        print("Aqui a conversa e sobre processo, tese, riscos e leitura de cenario.")
        print("Exemplo: como voce esta formando sua tese hoje?")

        while True:
            question = input("\nVoce: ").strip()
            if not question:
                continue
            if question.lower() in {"sair", "exit", "quit"}:
                print("Macro Chat encerrado.")
                break

            response = agent.answer_macro_consultant_question(
                question,
                n_results=6,
                session_id="terminal_macro_chat",
            )
            print("\nMacro:\n" + format_chat_answer(response))
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


def run_bootstrap_learning() -> None:
    summary = bootstrap_user_learning(Path(__file__).resolve().parent)
    logger.info(f"Bootstrap de conhecimento concluido: {summary}")


def run_bootstrap_assets() -> None:
    """Reconstroi ou sincroniza os assets de conhecimento curado (seed_profiles, cards, etc)."""
    base_dir = Path(__file__).resolve().parent
    summary = bootstrap_user_learning(base_dir)
    catalog = build_source_catalog(base_dir)
    logger.info(f"Bootstrap de assets concluido. Conhecimento: {summary} | Catalogo: {len(catalog)} item(ns)")


def run_learning_catalog() -> None:
    catalog = build_source_catalog(Path(__file__).resolve().parent)
    if not catalog:
        logger.info("Nenhuma fonte curada encontrada em knowledge/seed_profiles.json")
        return

    lines = ["Catalogo de aprendizado curado:"]
    for item in catalog:
        label = item.get("name", "sem nome")
        role = item.get("role", "sem papel")
        item_type = item.get("type", "item")
        url = item.get("url", "")
        suffix = f" | {url}" if url else ""
        lines.append(f"- {item_type}: {label} | {role}{suffix}")

    logger.info("\n" + "\n".join(lines))


def run_editorial_daily() -> None:
    run_daily_pipeline(Path(__file__).resolve().parent)


def run_editorial_weekly() -> None:
    run_weekly_pipeline(Path(__file__).resolve().parent)


def run_editorial_learning() -> None:
    run_learning_pipeline(Path(__file__).resolve().parent)


def run_full_cycle() -> None:
    base_dir = Path(__file__).resolve().parent
    logger.info("Executando ciclo completo unificado: daily -> weekly -> editorial-learn")
    run_daily_pipeline(base_dir)
    run_weekly_pipeline(base_dir)
    run_learning_pipeline(base_dir)
    logger.info("Ciclo completo finalizado.")


def run_editorial_topic(topic_name: str) -> None:
    run_topic_pipeline(Path(__file__).resolve().parent, topic_name)


def run_editorial_ingest(command_args: list) -> None:
    payload = {
        "text": None,
        "url": None,
        "fact": None,
        "source": "manual",
        "topic": None,
    }

    key = None
    for item in command_args:
        if item.startswith("--"):
            key = item[2:]
            continue
        if key in payload:
            payload[key] = item
            key = None

    ingest_manual_item(Path(__file__).resolve().parent, payload)
    logger.info("Conteudo manual salvo no inbox.")


def run_editorial_telegram() -> None:
    start_telegram_bot(Path(__file__).resolve().parent)


def run_tracked_profiles() -> None:
    config_path = Path(__file__).resolve().parent / "config" / "x_accounts.yaml"
    if not config_path.exists():
        logger.info("Arquivo config/x_accounts.yaml nao encontrado.")
        return

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    lines = ["Perfis acompanhados no X:"]

    for section in ["news", "macro_specialists", "reference_style"]:
        handles = config.get(section, [])
        if not handles:
            continue
        lines.append(f"{section}: {len(handles)} perfil(is)")
        for handle in handles:
            meta = (config.get("metadata", {}) or {}).get(handle, {})
            role = meta.get("role", section)
            url = meta.get("url", "")
            suffix = f" | {url}" if url else ""
            lines.append(f"- @{handle} | {role}{suffix}")

    logger.info("\n" + "\n".join(lines))


def run_x_drafts_preview() -> None:
    logger.info("\n" + format_latest_x_drafts(Path(__file__).resolve().parent))


def run_x_schedule() -> None:
    text = format_week_schedule(Path(__file__).resolve().parent)
    logger.info("\n" + text)


def run_x_tomorrow() -> None:
    base_dir = Path(__file__).resolve().parent
    payload = run_content_generation_pipeline(base_dir, send_telegram=True)
    tomorrow = payload["tomorrow"]
    lines = [f"Drafts gerados para {tomorrow['date']}:"]
    for draft in tomorrow.get("drafts", []):
        lines.append(f"- {draft['time_brt']} | {draft['type']}: {draft['text'][:80]}")
    logger.info("\n" + "\n".join(lines))


def run_x_check() -> None:
    result = diagnose_x_api(Path(__file__).resolve().parent)
    lines = [
        "Diagnostico do X API",
        f"Status: {result.get('status', '-')}",
        f"Mensagem: {result.get('message', '-')}",
        f"Handle testado: {result.get('handle_tested', '-')}",
        f"HTTP: {result.get('http_status', '-')}",
        f"Base: {result.get('api_base', '-')}",
    ]
    details = result.get("details", {})
    if details:
        lines.append("Detalhes:")
        for key, value in details.items():
            lines.append(f"- {key}: {value}")
    logger.info("\n" + "\n".join(lines))


def run_newsletter_preview() -> None:
    output = Path(__file__).resolve().parent / "data" / "published" / "newsletter_draft.md"
    if not output.exists():
        logger.info("Nenhuma newsletter encontrada. Rode `python main.py weekly` primeiro.")
        return

    logger.info("\nNewsletter atual:\n" + output.read_text(encoding="utf-8"))


def run_newsletter_draft() -> None:
    base_dir = Path(__file__).resolve().parent
    run_weekly_pipeline(base_dir)
    run_newsletter_preview()


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


def run_briefing() -> None:
    """Gera e envia o Briefing de Fechamento do Dia imediatamente (para testes ou sob demanda)."""
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Gerando Briefing de Fechamento do Dia...")
        result = agent.generate_end_of_day_briefing()
        if result.get("status") == "generated":
            logger.info(
                f"Briefing gerado com sucesso: {result.get('length', 0)} chars | "
                f"Data: {result.get('date', '-')}"
            )
        else:
            logger.warning(f"Briefing nao foi gerado: {result}")
    finally:
        agent.shutdown()


def run_news_now() -> None:
    """Coleta noticias RSS agora e salva na memoria (sem esperar o scheduler)."""
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        logger.info("Coletando noticias agora...")
        result = agent.collect_and_store_news()
        stored = result.get("stored", 0)
        dupes = result.get("duplicates", 0)
        logger.info(f"Noticias coletadas: {stored} novas, {dupes} duplicatas ignoradas")
        if result.get("error"):
            logger.warning(f"Aviso: {result['error']}")
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
        now = datetime.now(timezone.utc).isoformat()
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
    try:
        start_telegram_bot(Path(__file__).resolve().parent, agent=agent)
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
    base_dir = Path(__file__).resolve().parent
    agent = MacroeconomistAgent(enable_scheduler=True)

    try:
        ensure_startup_pipelines(base_dir)
        serve_telegram(agent)
    except KeyboardInterrupt:
        logger.info("Encerramento solicitado")
    except Exception as e:
        logger.warning(f"Telegram indisponivel no momento, mas o projeto continuara rodando: {str(e)}")
        logger.info("Scheduler e memoria seguem ativos. Use Ctrl+C para encerrar.")
        try:
            while True:
                time.sleep(1)
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
                "  python main.py macro-chat",
                "  python main.py telegram-listen",
                "  python main.py learn-now",
                "  python main.py collect-articles",
                "  python main.py daily-thesis",
                "  python main.py bootstrap-learning",
                "  python main.py bootstrap-assets",
                "  python main.py learning-catalog",
                "  python main.py daily",
                "  python main.py weekly",
                "  python main.py editorial-learn",
                "  python main.py full-cycle",
                "  python main.py topic <tema>",
                "  python main.py ingest [--text ... --url ... --fact ... --source ... --topic ...]",
                "  python main.py tracked-profiles",
                "  python main.py x-drafts",
                "  python main.py x-schedule",
                "  python main.py x-tomorrow",
                "  python main.py x-check",
                "  python main.py newsletter-preview",
                "  python main.py newsletter-draft",
                "  python main.py telegram-editorial",
                "  python main.py thesis <tema>",
                "  python main.py source-demo",
                "  python main.py rss <feed_url> [source_name]",
                "  python main.py daily-digest",
                "  python main.py briefing         # Briefing de fechamento do dia (22h BRT)",
                "  python main.py news-now          # Coleta noticias RSS agora",
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
    elif command in {"macro-chat", "macrochat", "consultor"}:
        run_macro_chat()
    elif command == "telegram-listen":
        telegram_listen()
    elif command == "learn-now":
        run_learn_now()
    elif command == "collect-articles":
        run_collect_articles()
    elif command == "daily-thesis":
        run_daily_thesis()
    elif command == "bootstrap-learning":
        run_bootstrap_learning()
    elif command == "bootstrap-assets":
        run_bootstrap_assets()
    elif command == "learning-catalog":
        run_learning_catalog()
    elif command == "daily":
        run_editorial_daily()
    elif command == "weekly":
        run_editorial_weekly()
    elif command == "editorial-learn":
        run_editorial_learning()
    elif command == "full-cycle":
        run_full_cycle()
    elif command == "topic":
        topic = " ".join(command_args).strip()
        if not topic:
            print_help()
            return
        run_editorial_topic(topic)
    elif command == "ingest":
        run_editorial_ingest(command_args)
    elif command == "tracked-profiles":
        run_tracked_profiles()
    elif command == "x-drafts":
        run_x_drafts_preview()
    elif command == "x-schedule":
        run_x_schedule()
    elif command == "x-tomorrow":
        run_x_tomorrow()
    elif command == "x-check":
        run_x_check()
    elif command == "newsletter-preview":
        run_newsletter_preview()
    elif command == "newsletter-draft":
        run_newsletter_draft()
    elif command == "telegram-editorial":
        run_editorial_telegram()
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
    elif command == "briefing":
        run_briefing()
    elif command == "news-now":
        run_news_now()
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
