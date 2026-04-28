"""
Handlers de mensagens do Telegram.
Suporta comandos e conversa livre com o macroeconomista.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path

import yaml

from collect.manual_ingest import ingest_manual_item
from memory.retrieval import load_recent_facts

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

def _format_catalog(base_dir: Path) -> str:
    from knowledge.document_learning import build_source_catalog

    catalog = build_source_catalog(base_dir)
    if not catalog:
        return "Nenhuma fonte curada encontrada."

    lines = ["Catálogo curado:"]
    for item in catalog[:20]:
        label = item.get("name", "sem nome")
        role = item.get("role", "sem papel")
        item_type = item.get("type", "item")
        lines.append(f"- {item_type}: {label} | {role}")
    return "\n".join(lines)


def _format_profiles(base_dir: Path) -> str:
    config_path = base_dir / "config" / "x_accounts.yaml"
    if not config_path.exists():
        return "Arquivo config/x_accounts.yaml não encontrado."

    config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    lines = ["Perfis acompanhados no X:"]
    for section in ["news", "macro_specialists", "reference_style"]:
        handles = config.get(section, [])
        if not handles:
            continue
        lines.append(f"{section}: {len(handles)} perfil(is)")
        for handle in handles[:8]:
            lines.append(f"- @{handle}")
    return "\n".join(lines)


def _format_x_drafts(base_dir: Path) -> str:
    from scheduler.content_scheduler import format_latest_x_drafts

    return format_latest_x_drafts(base_dir).replace("`python main.py daily`", "/daily")


def _format_newsletter(base_dir: Path) -> str:
    output = base_dir / "data" / "published" / "newsletter_draft.md"
    if not output.exists():
        return "Nenhuma newsletter encontrada. Rode /weekly primeiro."
    return output.read_text(encoding="utf-8")[:3500]


def _get_market_snapshot_text() -> str:
    """Busca dados de mercado em texto simples para injetar no LLM."""
    try:
        from apis.market_api import MarketDataClient
        client = MarketDataClient()
        snapshot = client.get_market_snapshot()
        quotes = snapshot.get("quotes", {})
        from apis.market_api import DEFAULT_ASSETS
        lines = []
        for ticker, meta in DEFAULT_ASSETS.items():
            q = quotes.get(ticker, {})
            if "price" not in q:
                continue
            price = q["price"]
            chg = q.get("change_pct")
            chg_str = f" ({'+' if chg and chg >= 0 else ''}{chg:.2f}%)" if chg is not None else ""
            prefix = meta.get("prefix", "")
            lines.append(f"{meta['label']}: {prefix} {price}{chg_str}")
        return "\n".join(lines) if lines else "Dados de mercado indisponíveis."
    except Exception as exc:
        logger.warning(f"Falha ao buscar mercado para contexto: {exc}")
        return "Dados de mercado indisponíveis."


def _get_news_context_text() -> str:
    """Busca notícias recentes em texto para injetar no LLM."""
    try:
        from apis.news_api import NewsCollector
        collector = NewsCollector()
        return collector.format_news_for_context(limit=5)
    except Exception as exc:
        logger.warning(f"Falha ao buscar notícias para contexto: {exc}")
        return "Notícias indisponíveis no momento."


def _get_fred_summary() -> str:
    """Busca dados recentes do FRED formatados para Telegram."""
    try:
        from apis.fred_api import MacroeconomicMonitor
        monitor = MacroeconomicMonitor()
        inflation = monitor.get_inflation_metrics()
        policy = monitor.get_fed_policy()
        labor = monitor.get_labor_market()

        lines = ["🏦 *Dados FRED — Federal Reserve*", ""]

        cpi = inflation.get("CPI", {})
        if cpi.get("value"):
            lines.append(f"📊 CPI (Inflação EUA): {cpi['value']:.2f} | {cpi.get('date', '-')}")

        pce = inflation.get("PCE", {})
        if pce.get("value"):
            lines.append(f"📊 PCE: {pce['value']:.2f} | {pce.get('date', '-')}")

        fed = policy.get("FED_FUNDS", {})
        if fed.get("value"):
            lines.append(f"💵 Taxa Fed Funds: {fed['value']:.2f}% | {fed.get('date', '-')}")

        t10 = policy.get("DGS10", {})
        if t10.get("value"):
            lines.append(f"📈 T10Y Yield: {t10['value']:.2f}% | {t10.get('date', '-')}")

        unemp = labor.get("UNEMPLOYMENT_RATE", {})
        if unemp.get("value"):
            lines.append(f"👷 Desemprego EUA: {unemp['value']:.1f}% | {unemp.get('date', '-')}")

        payroll = labor.get("NONFARM_PAYROLLS", {})
        if payroll.get("value"):
            val = payroll["value"]
            lines.append(f"💼 Nonfarm Payrolls: {val:,.0f}k | {payroll.get('date', '-')}")

        return "\n".join(lines) if len(lines) > 2 else "Dados do FRED indisponíveis no momento."
    except Exception as exc:
        logger.warning(f"Falha ao buscar FRED: {exc}")
        return f"❌ Erro ao buscar dados do FRED: {exc}"


# ---------------------------------------------------------------------------
# Handler principal
# ---------------------------------------------------------------------------

def handle_message(base_dir: Path, text: str, agent=None, chat_id: str = "telegram") -> str:
    text = text.strip()

    # -----------------------------------------------------------------------
    # /start — boas-vindas
    # -----------------------------------------------------------------------
    if text.startswith("/start"):
        return (
            "👋 Olá! Sou seu macroeconomista pessoal.\n\n"
            "Você pode conversar comigo livremente sobre qualquer tema macro — "
            "inflação, juros, câmbio, crescimento, mercado — ou usar os comandos:\n\n"
            "📊 /mercado — cotações em tempo real\n"
            "📰 /noticias — últimas notícias macro\n"
            "🏦 /fred — dados do Federal Reserve\n"
            "📌 /ticker AAPL — cotação de qualquer ativo\n"
            "🧠 /thesis <tema> — tese macro fundamentada\n"
            "🔍 /buscar <tema> — busca na memória\n"
            "📋 /status — estado do agente\n"
            "❓ /help — todos os comandos\n\n"
            "Ou simplesmente me escreva: 'qual sua leitura sobre o dólar hoje?' 😊"
        )

    # -----------------------------------------------------------------------
    # /help
    # -----------------------------------------------------------------------
    if text.startswith("/help"):
        return (
            "📋 *Comandos disponíveis:*\n\n"
            "📊 /mercado — cotações em tempo real (Dólar, BTC, S&P, Ibovespa...)\n"
            "📰 /noticias — últimas notícias Reuters, IMF, FT\n"
            "🏦 /fred — dados do Federal Reserve (CPI, Juros, Payroll)\n"
            "📌 /ticker AAPL — cotação de qualquer ativo (PETR4.SA, BTC-USD...)\n"
            "🧠 /thesis <tema> — tese macro com evidências e riscos\n"
            "🔍 /buscar <tema> — busca na memória do agente\n"
            "💾 /guardar <texto> — salva nota manual\n"
            "📌 /fatos <tema> — fatos recentes sobre um tema\n"
            "🔄 /daily — pipeline editorial diário\n"
            "📅 /weekly — pipeline editorial semanal\n"
            "🔁 /fullcycle — ciclo completo (daily + weekly + learning)\n"
            "📝 /xdrafts — drafts para X/Twitter\n"
            "📧 /newsletter — newsletter mais recente\n"
            "📚 /catalog — fontes curadas\n"
            "👥 /profiles — perfis monitorados no X\n"
            "📊 /status — estado do agente\n\n"
            "💬 Ou converse livremente! Ex: 'qual sua leitura sobre o Copom?'"
        )

    # -----------------------------------------------------------------------
    # /mercado — cotações em tempo real
    # -----------------------------------------------------------------------
    if text.startswith("/mercado"):
        try:
            from apis.market_api import MarketDataClient
            client = MarketDataClient()
            snapshot = client.get_market_snapshot()
            market_msg = client.format_market_message(snapshot)

            # Se o agente estiver disponível, adiciona leitura macro
            if agent is not None and agent.llm.is_available():
                news_ctx = _get_news_context_text()
                market_text = _get_market_snapshot_text()
                analysis = agent.llm.answer_market_question(
                    question="Faça uma leitura macro rápida das cotações atuais. O que está movendo os mercados?",
                    market_snapshot=market_text,
                    news_context=news_ctx,
                    conversation=agent.conversations.get(chat_id, []),
                )
                if analysis:
                    return market_msg + "\n\n💡 *Leitura Macro:*\n" + analysis

            return market_msg
        except ImportError:
            return "❌ yfinance não instalado. Rode: pip install yfinance"
        except Exception as exc:
            logger.warning(f"Erro em /mercado: {exc}")
            return f"❌ Erro ao buscar cotações: {exc}"

    # -----------------------------------------------------------------------
    # /noticias — últimas notícias RSS
    # -----------------------------------------------------------------------
    if text.startswith("/noticias"):
        try:
            from apis.news_api import NewsCollector
            collector = NewsCollector()
            return collector.format_news_message(limit=6)
        except ImportError:
            return "❌ feedparser não instalado. Rode: pip install feedparser"
        except Exception as exc:
            logger.warning(f"Erro em /noticias: {exc}")
            return f"❌ Erro ao buscar notícias: {exc}"

    # -----------------------------------------------------------------------
    # /fred — dados do Federal Reserve
    # -----------------------------------------------------------------------
    if text.startswith("/fred"):
        return _get_fred_summary()

    # -----------------------------------------------------------------------
    # /ticker <symbol> — cotação de qualquer ativo
    # -----------------------------------------------------------------------
    if text.startswith("/ticker"):
        parts = text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            return (
                "📌 Use: /ticker <símbolo>\n\n"
                "Exemplos:\n"
                "  /ticker USDBRL=X  → Dólar\n"
                "  /ticker PETR4.SA  → Petrobras\n"
                "  /ticker BTC-USD   → Bitcoin\n"
                "  /ticker ^BVSP     → Ibovespa\n"
                "  /ticker AAPL      → Apple"
            )
        ticker = parts[1].strip().upper()
        try:
            from apis.market_api import MarketDataClient
            client = MarketDataClient()
            return client.format_ticker_message(ticker)
        except ImportError:
            return "❌ yfinance não instalado. Rode: pip install yfinance"
        except Exception as exc:
            return f"❌ Erro ao buscar {ticker}: {exc}"

    # -----------------------------------------------------------------------
    # /guardar — salva nota manual
    # -----------------------------------------------------------------------
    if text.startswith("/guardar "):
        note = text.replace("/guardar ", "", 1).strip()
        ingest_manual_item(base_dir, {"text": note, "source": "telegram"})
        return "✅ Nota salva na memória do agente."

    # -----------------------------------------------------------------------
    # /fatos — fatos recentes
    # -----------------------------------------------------------------------
    if text.startswith("/fatos"):
        parts = text.split(maxsplit=1)
        topic = parts[1].strip() if len(parts) > 1 else None
        facts = load_recent_facts(base_dir, topic=topic, limit=5)
        if not facts:
            return "Sem fatos recentes para esse tema."
        return "\n".join(f"- {item['topic']}: {item['title']}" for item in facts)

    # -----------------------------------------------------------------------
    # /buscar — busca na memória + resposta LLM
    # -----------------------------------------------------------------------
    if text.startswith("/buscar "):
        topic = text.replace("/buscar ", "", 1).strip()
        if agent is None:
            return f"Pedido recebido para analisar o tema: {topic}"

        market_ctx = _get_market_snapshot_text()
        news_ctx = _get_news_context_text()

        response = agent.answer_learning_question(topic, n_results=6, session_id=chat_id)
        answer = response.get("answer", "")

        # Se o LLM estiver disponível, usa o método rico
        if agent.llm.is_available():
            sources = response.get("sources", [])
            rich_answer = agent.llm.answer_question(
                question=topic,
                sources=sources,
                conversation=agent.conversations.get(chat_id, []),
                market_context=market_ctx,
                news_context=news_ctx,
            )
            if rich_answer:
                answer = rich_answer

        return answer or "Não encontrei informações relevantes sobre isso na minha memória."

    # -----------------------------------------------------------------------
    # /thesis — tese macro fundamentada
    # -----------------------------------------------------------------------
    if text.startswith("/thesis "):
        topic = text.replace("/thesis ", "", 1).strip()
        if agent is None:
            return "Agente indisponível para montar tese agora."

        market_ctx = _get_market_snapshot_text()
        news_ctx = _get_news_context_text()
        thesis = agent.build_source_backed_thesis(topic, n_results=5)

        # Enriquece tese com dados frescos se LLM disponível
        if agent.llm.is_available():
            memory_results = agent.memory.search(topic, n_results=5).get("results", [])
            source_results = agent.memory.search(
                topic, n_results=5, where={"type": "source_article"}
            ).get("results", [])
            rich = agent.llm.build_thesis(
                topic=topic,
                memory_results=memory_results,
                source_results=source_results,
                market_context=market_ctx,
                news_context=news_ctx,
            )
            if rich:
                thesis["thesis"] = rich.get("thesis", thesis.get("thesis", ""))
                thesis["evidence"] = rich.get("evidence", thesis.get("evidence", []))
                thesis["risks"] = rich.get("risks", thesis.get("risks", []))

        evidence = thesis.get("evidence", [])
        risks = thesis.get("risks", [])
        confidence = thesis.get("confidence", "")

        lines = [
            f"🧠 *Tese Macro: {topic}*",
            "",
            thesis.get("thesis", "Sem tese disponível."),
            "",
            "📌 *Evidências:*",
        ]
        lines.extend(f"• {item}" for item in evidence[:5] or ["Sem evidências suficientes."])
        lines.append("")
        lines.append("⚠️ *Riscos:*")
        lines.extend(f"• {item}" for item in risks[:4] or ["Sem riscos mapeados."])

        if confidence:
            lines.append(f"\n🎯 Confiança: {confidence}")

        return "\n".join(lines)

    # -----------------------------------------------------------------------
    # /status
    # -----------------------------------------------------------------------
    if text.startswith("/status"):
        if agent is None:
            return "Agente indisponível para consultar status agora."
        status = agent.get_agent_status()
        memory = status.get("memory", {})
        task_stats = status.get("task_stats", {})
        system = status.get("system", {})
        llm_ok = agent.llm.is_available() if agent else False
        return "\n".join([
            "📊 *Status do BotMacroeconomist*",
            f"🧠 Documentos na memória: {memory.get('total_documents', 0)}",
            f"✅ Execuções bem-sucedidas: {task_stats.get('successful', 0)}",
            f"❌ Falhas: {task_stats.get('failed', 0)}",
            f"🤖 LLM disponível: {'✅ sim' if llm_ok else '❌ não'}",
            f"📡 FRED: {'✅' if system.get('fred_available') else '❌'}",
            f"🌐 IMF: {'✅' if system.get('imf_available') else '❌'}",
            f"🏦 World Bank: {'✅' if system.get('worldbank_available') else '❌'}",
        ])

    # -----------------------------------------------------------------------
    # /daily, /weekly, /fullcycle
    # -----------------------------------------------------------------------
    if text.startswith("/daily"):
        from scheduler.daily_jobs import run_daily_pipeline
        run_daily_pipeline(base_dir)
        return "✅ Pipeline diário executado.\n\n" + _format_x_drafts(base_dir)

    if text.startswith("/weekly"):
        from scheduler.weekly_jobs import run_weekly_pipeline
        run_weekly_pipeline(base_dir)
        return "✅ Pipeline semanal executado.\n\n" + _format_newsletter(base_dir)

    if text.startswith("/fullcycle"):
        from scheduler.daily_jobs import run_daily_pipeline
        from scheduler.weekly_jobs import run_learning_pipeline, run_weekly_pipeline
        run_daily_pipeline(base_dir)
        run_weekly_pipeline(base_dir)
        run_learning_pipeline(base_dir)
        return "✅ Ciclo completo executado: daily, weekly e editorial learning."

    # -----------------------------------------------------------------------
    # /xdrafts, /newsletter, /catalog, /profiles
    # -----------------------------------------------------------------------
    if text.startswith("/xdrafts"):
        return _format_x_drafts(base_dir)

    if text.startswith("/newsletter"):
        return _format_newsletter(base_dir)

    if text.startswith("/catalog"):
        return _format_catalog(base_dir)

    if text.startswith("/profiles"):
        return _format_profiles(base_dir)

    # -----------------------------------------------------------------------
    # Conversa livre — macroeconomista responde qualquer pergunta
    # -----------------------------------------------------------------------
    if agent is not None:
        market_ctx = _get_market_snapshot_text()
        news_ctx = _get_news_context_text()

        # Busca contexto na memória
        response = agent.answer_learning_question(text, n_results=6, session_id=chat_id)
        sources = response.get("sources", [])
        conversation = agent.conversations.get(chat_id, [])

        # Se LLM disponível, usa persona rica com dados em tempo real
        if agent.llm.is_available():
            rich_answer = agent.llm.answer_question(
                question=text,
                sources=sources,
                conversation=conversation,
                market_context=market_ctx,
                news_context=news_ctx,
            )
            if rich_answer:
                agent._remember_turn(chat_id, text, rich_answer)
                return rich_answer

        # Fallback: resposta baseada em regras
        return response.get("answer", "Não entendi. Use /help para ver os comandos disponíveis.")

    return "Não entendi. Use /help para ver os comandos disponíveis."
