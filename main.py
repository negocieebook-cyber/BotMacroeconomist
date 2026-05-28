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
    python main.py economic-calendar
    python main.py report
    python main.py charts
    python main.py telegram-charts
    python main.py status
    python main.py run
    python main.py telegram-test
    python main.py telegram-chat-id
"""

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


_HR = "  " + "─" * 38


def _ok(val: bool) -> str:
    return "✓" if val else "✗"


def _row(label: str, value, width: int = 24) -> str:
    return f"  {label:<{width}} {value}"


def format_status_text(status: dict) -> str:
    task_stats = status.get("task_stats", {})
    memory = status.get("memory", {})
    system = status.get("system", {})

    total = task_stats.get("total_executions", 0)
    ok    = task_stats.get("successful", 0)
    fail  = task_stats.get("failed", 0)

    return "\n".join([
        "",
        _HR,
        "   BotMacroeconomist — Status",
        _HR,
        f"   {status.get('timestamp', '-')}",
        "",
        "   MEMÓRIA",
        _row("  └ Documentos", memory.get("total_documents", 0)),
        "",
        "   TAREFAS",
        _row("  ├ Total", total),
        _row("  ├ Sucesso", ok),
        _row("  └ Falhas", fail),
        "",
        "   APIS",
        _row("  ├ FRED", _ok(system.get("fred_available"))),
        _row("  ├ IMF", _ok(system.get("imf_available"))),
        _row("  ├ World Bank", _ok(system.get("worldbank_available"))),
        _row("  ├ OECD", _ok(system.get("oecd_available"))),
        _row("  ├ BIS", _ok(system.get("bis_available"))),
        _row("  └ Calendar FMP", _ok(system.get("fmp_calendar_available"))),
        _HR,
    ])


def format_cycle_summary(label: str, data: dict) -> str:
    size = len(str(data))
    keys = ", ".join(list(data.keys())[:6]) if isinstance(data, dict) else "—"
    return f"  [{label}]  {size:,} chars  |  {keys}"


def format_learning_text(snapshot: dict) -> str:
    memory = snapshot.get("memory", {})
    docs   = snapshot.get("recent_documents", [])
    ts     = snapshot.get("timestamp", "-")
    total  = memory.get("total_documents", 0)

    lines = [
        "",
        _HR,
        "   Aprendizado do Agente",
        _HR,
        f"   {ts}  |  {total} docs na memória",
        "",
    ]

    if not docs:
        lines.append("   Nenhum aprendizado armazenado ainda.")
        return "\n".join(lines)

    last = len(docs)
    for i, item in enumerate(docs, 1):
        meta = item.get("metadata", {})
        branch = "└" if i == last else "├"
        pipe   = " " if i == last else "│"
        preview = (item.get("preview") or "")[:80]
        lines += [
            f"  {branch} [{i}] {meta.get('focus_area', 'Sem foco')}",
            f"  {pipe}    API: {meta.get('api', '?')}  |  {meta.get('timestamp', '-')}",
            f"  {pipe}    {preview}",
            "",
        ]

    lines.append(_HR)
    return "\n".join(lines).strip()


def format_thesis_text(thesis: dict) -> str:
    lines = [
        "",
        _HR,
        f"   Tese Macro: {thesis.get('topic', '-')}",
        _HR,
        f"   {thesis.get('timestamp', '-')}  |  "
        f"{thesis.get('source_count', 0)} fontes  |  "
        f"{thesis.get('memory_count', 0)} memórias",
        "",
        f"   {thesis.get('thesis', '-')}",
        "",
        "   EVIDÊNCIAS",
    ]
    for item in thesis.get("evidence", []):
        lines.append(f"   • {item}")

    lines += ["", "   RISCOS"]
    for item in thesis.get("risks", []):
        lines.append(f"   • {item}")

    citations = thesis.get("citations", [])
    if citations:
        lines += ["", "   FONTES"]
        for c in citations:
            title  = c.get("title", "Sem título")
            source = c.get("source", "fonte")
            pub    = c.get("published_at", "-")
            url    = c.get("url", "")
            suffix = f"  → {url}" if url else ""
            lines.append(f"   • {title} | {source} | {pub}{suffix}")

    lines += [_HR, ""]
    return "\n".join(lines)


def format_chat_answer(response: dict) -> str:
    lines = [response.get("answer", "Sem resposta.")]

    sources = response.get("sources", [])
    if sources:
        lines += ["", "─── Fontes ──────────────────────────────"]
        for item in sources[:3]:
            meta = item.get("metadata", {})
            label = (
                meta.get("title") or meta.get("focus_area")
                or meta.get("source_name") or meta.get("api") or "Memória"
            )
            lines.append(f"  • {label}  |  {meta.get('timestamp', '-')}")

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


def run_economic_calendar() -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        result = agent.collect_and_store_economic_calendar()
        analysis = agent.build_economic_calendar_analysis(store_memory=True)
        text = (
            "Calendario economico FMP\n"
            f"Intervalo: {result.get('from', '-')} a {result.get('to', '-')}\n"
            f"Eventos encontrados: {result.get('events', 0)}\n"
            f"Armazenado na memoria: {'sim' if result.get('stored') else 'nao'}\n"
            f"Analise integrada: {analysis.get('status', '-')}, {analysis.get('events', 0)} eventos relevantes"
        )
        if not result.get("configured", True):
            text += "\nFMP_API_KEY ainda nao esta configurada no .env."
        logger.info("\n" + text)
        maybe_send_telegram(text)
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


def run_charts(send_telegram: bool = False) -> None:
    agent = MacroeconomistAgent(enable_scheduler=False)
    try:
        report = agent.build_global_macro_visual_report(store_memory=True)
        artifacts = report.get("artifacts", [])
        if not artifacts:
            logger.warning("Nenhum grafico macro foi gerado.")
            return

        logger.info(f"Graficos gerados: {len(artifacts)}")
        for artifact in artifacts:
            logger.info(f"- {artifact.title}: {artifact.path}")

        if send_telegram:
            notifier = TelegramNotifier()
            notifier.send_long_message(report.get("text", "Relatorio macro visual gerado."))
            for photo in report.get("photos", []):
                notifier.send_photo(photo.get("path", ""), caption=photo.get("caption", ""))
            logger.info("Graficos enviados para o Telegram")
    finally:
        agent.shutdown()


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
        "\n".join([
            "",
            _HR,
            "   BotMacroeconomist — Comandos",
            _HR,
            "",
            "   EXECUÇÃO",
            "   start              modo completo (scheduler + Telegram)",
            "   run                scheduler sem Telegram",
            "   once               coleta única de dados",
            "   demo               demonstração rápida",
            "   status             estado do agente",
            "",
            "   CHAT",
            "   chat               conversa com memória técnica",
            "   macro-chat         conversa como consultor macro",
            "   ask <pergunta>     pergunta direta à memória",
            "",
            "   ANÁLISE",
            "   thesis <tema>      tese macro com evidências e riscos",
            "   thesis             padrão: inflacao e juros reais",
            "   daily-thesis       tese diária automática",
            "",
            "   PIPELINES",
            "   daily              pipeline editorial diário",
            "   weekly             pipeline editorial semanal",
            "   editorial-learn    pipeline de aprendizado",
            "   full-cycle         daily + weekly + learning",
            "   topic <tema>       pipeline por tema",
            "",
            "   COLETA",
            "   learn-now          aprendizado técnico imediato",
            "   collect-articles   coleta de artigos de pesquisa",
            "   news-now           coleta RSS agora",
            "   rss <url> [nome]   ingere feed RSS",
            "   ingest [opts]      ingere dado manual",
            "                      --text --url --fact --source --topic",
            "",
            "   CONTEÚDO",
            "   newsletter-preview newsletter atual",
            "   newsletter-draft   gera e exibe newsletter",
            "   x-drafts           drafts para X/Twitter",
            "   x-schedule         agendamento da semana no X",
            "   x-tomorrow         gera drafts para amanhã",
            "   x-check            diagnóstico da API do X",
            "",
            "   RELATÓRIOS",
            "   report             relatório de mercado completo",
            "   charts             gráficos macro (data/charts/)",
            "   briefing           briefing de fechamento do dia",
            "   economic-calendar  calendário econômico FMP",
            "   daily-digest       digest de aprendizado via Telegram",
            "",
            "   TELEGRAM",
            "   telegram-listen    escuta mensagens do bot",
            "   telegram-editorial bot editorial",
            "   telegram-test      envia mensagem de teste",
            "   telegram-charts    envia gráficos ao Telegram",
            "   telegram-chat-id   descobre seu chat id",
            "",
            "   BOOTSTRAP",
            "   bootstrap-learning inicializa base de conhecimento",
            "   bootstrap-assets   reconstrói assets curados",
            "   learning-catalog   exibe catálogo de fontes",
            "   tracked-profiles   perfis monitorados no X",
            "   source-demo        ingere artigo de demonstração",
            _HR,
        ])
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
    elif command in {"economic-calendar", "calendar", "calendario"}:
        run_economic_calendar()
    elif command == "briefing":
        run_briefing()
    elif command == "news-now":
        run_news_now()
    elif command == "report":
        run_report()
    elif command == "charts":
        run_charts(send_telegram=False)
    elif command == "telegram-charts":
        run_charts(send_telegram=True)
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
