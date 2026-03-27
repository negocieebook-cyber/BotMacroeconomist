"""
Agente macroeconomista principal.
Versao simplificada para manter o projeto funcional e facil de entender.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List

from apis.bis_api import BISClient
from apis.fred_api import FREDClient, MacroeconomicMonitor
from apis.imf_api import BalanceOfPayments, IMFClient
from apis.oecd_api import OECDClient
from apis.research_monitor import ResearchMonitor
from apis.worldbank_api import WorldBankClient
from analysis import ThesisEngine
from config import (
    DAILY_DIGEST_HOUR_UTC,
    DAILY_DIGEST_MINUTE_UTC,
    DAILY_RESEARCH_HOUR_UTC,
    DAILY_RESEARCH_MINUTE_UTC,
    DAILY_TECHNICAL_LEARNING_HOUR_UTC,
    DAILY_TECHNICAL_LEARNING_MINUTE_UTC,
    DAILY_THESIS_HOUR_UTC,
    DAILY_THESIS_MINUTE_UTC,
    DAILY_THESIS_TOPIC,
    DEFAULT_RESEARCH_FEEDS,
    ENABLE_TELEGRAM_NOTIFICATIONS,
    FRED_API_KEY,
    LOG_FILE,
    LOG_LEVEL,
    RESEARCH_FEED_LIMIT,
)
from memory.chromadb_manager import ChromaDBManager, MemoryAnalyzer
from scheduler.weekly_schedule import TaskManager, WeeklyScheduler
from utils import (
    TelegramNotifier,
    build_daily_learning_digest,
    get_macro_learning_cards,
)
from utils.logger import setup_logger

logger = logging.getLogger(__name__)


class MacroeconomistAgent:
    """Agente principal com coleta, memoria e scheduler."""

    def __init__(self, enable_scheduler: bool = True):
        setup_logger(LOG_LEVEL, LOG_FILE)
        self.enable_scheduler = enable_scheduler

        logger.info("=" * 60)
        logger.info("INICIALIZANDO AGENTE MACROECONOMISTA")
        logger.info("=" * 60)

        logger.info("Inicializando APIs...")
        self.fred = FREDClient()
        self.imf = IMFClient()
        self.worldbank = WorldBankClient()
        self.oecd = OECDClient()
        self.bis = BISClient()
        self.research_monitor = ResearchMonitor()
        self.macro_monitor = MacroeconomicMonitor()
        self.thesis_engine = ThesisEngine()

        logger.info("Inicializando memoria...")
        self.memory = ChromaDBManager()
        self.memory_analyzer = MemoryAnalyzer(self.memory)

        logger.info("Inicializando scheduler...")
        self.scheduler = WeeklyScheduler()
        self.task_manager = TaskManager()
        self.conversations: Dict[str, List[Dict[str, str]]] = {}

        if enable_scheduler:
            self._setup_schedule()
            self.scheduler.start()
            self.ensure_daily_learning()
            self.ensure_daily_research_articles()
            self.ensure_daily_thesis()

        logger.info("Agente pronto")

    def monday_inflation_policy(self) -> Dict:
        logger.info("SEGUNDA: Inflacao e politica monetaria")
        self.task_manager.log_task_execution("inflation_policy", "started")

        try:
            data = {
                "fred": self.macro_monitor.get_inflation_metrics(),
                "fed_policy": self.macro_monitor.get_fed_policy(),
                "imf_inflation": self.imf.get_global_inflation(),
            }

            self._store_in_memory(data, "FRED_IMF", "Inflation_Policy")
            self._notify_learning("Inflation_Policy", "FRED_IMF", data)
            self.task_manager.log_task_execution("inflation_policy", "completed")
            return data
        except Exception as e:
            logger.error(f"Erro na coleta de segunda: {str(e)}")
            self.task_manager.log_task_execution("inflation_policy", "failed", error=str(e))
            return {}

    def tuesday_economic_growth(self) -> Dict:
        logger.info("TERCA: Crescimento economico")
        self.task_manager.log_task_execution("economic_growth", "started")

        try:
            data = {
                "gdp_nominal": self.worldbank.get_gdp_all_countries(),
                "gdp_growth": self.worldbank.get_gdp_growth_all(),
                "gdp_forecast": self.macro_monitor.get_gdp_forecast(),
            }

            self._store_in_memory(data, "WORLD_BANK_FRED", "Economic_Growth")
            self._notify_learning("Economic_Growth", "WORLD_BANK_FRED", data)
            self.task_manager.log_task_execution("economic_growth", "completed")
            return data
        except Exception as e:
            logger.error(f"Erro na coleta de terca: {str(e)}")
            self.task_manager.log_task_execution("economic_growth", "failed", error=str(e))
            return {}

    def wednesday_labor_market(self) -> Dict:
        logger.info("QUARTA: Mercado de trabalho")
        self.task_manager.log_task_execution("labor_market", "started")

        try:
            data = {
                "us_labor": self.macro_monitor.get_labor_market(),
                "unemployment_global": self.worldbank.get_unemployment_rate(),
            }

            self._store_in_memory(data, "FRED_WORLD_BANK", "Labor_Market")
            self._notify_learning("Labor_Market", "FRED_WORLD_BANK", data)
            self.task_manager.log_task_execution("labor_market", "completed")
            return data
        except Exception as e:
            logger.error(f"Erro na coleta de quarta: {str(e)}")
            self.task_manager.log_task_execution("labor_market", "failed", error=str(e))
            return {}

    def thursday_trade_finance(self) -> Dict:
        logger.info("QUINTA: Comercio e financas globais")
        self.task_manager.log_task_execution("trade_finance", "started")

        try:
            bop = BalanceOfPayments()
            data = {
                "current_account": bop.get_current_account(),
                "fdi": bop.get_fdi(),
                "global_credit": self.bis.get_global_credit(),
                "credit_households": self.bis.get_credit_to_households(),
                "derivatives": self.bis.get_derivatives_markets(),
            }

            self._store_in_memory(data, "IMF_BIS", "Trade_Finance")
            self._notify_learning("Trade_Finance", "IMF_BIS", data)
            self.task_manager.log_task_execution("trade_finance", "completed")
            return data
        except Exception as e:
            logger.error(f"Erro na coleta de quinta: {str(e)}")
            self.task_manager.log_task_execution("trade_finance", "failed", error=str(e))
            return {}

    def friday_forecasts_consensus(self) -> Dict:
        logger.info("SEXTA: Previsoes e consensus")
        self.task_manager.log_task_execution("forecasts", "started")

        try:
            data = {
                "weo_growth": self.imf.get_world_economic_outlook("NGDPD"),
                "weo_inflation": self.imf.get_world_economic_outlook("PCPIPCH"),
                "leading_indicators": self.oecd.get_leading_indicators(),
                "consumer_confidence": self.oecd.get_consumer_confidence(),
            }

            self._store_in_memory(data, "IMF_OECD", "Forecasts_Consensus")
            self._notify_learning("Forecasts_Consensus", "IMF_OECD", data)
            self.task_manager.log_task_execution("forecasts", "completed")
            return data
        except Exception as e:
            logger.error(f"Erro na coleta de sexta: {str(e)}")
            self.task_manager.log_task_execution("forecasts", "failed", error=str(e))
            return {}

    def analyze_indicator(self, indicator_name: str) -> Dict:
        logger.info(f"Analisando indicador: {indicator_name}")
        search_result = self.memory_analyzer.search_by_indicator(indicator_name, n_results=10)

        return {
            "indicator": indicator_name,
            "timestamp": datetime.utcnow().isoformat(),
            "historical_data": search_result,
            "insights": self._generate_insights(search_result),
        }

    def search_knowledge(self, query: str, n_results: int = 5) -> Dict:
        logger.info(f"Buscando: {query}")
        results = self.memory.search(query, n_results=n_results)
        return {
            "query": query,
            "results_count": len(results["results"]),
            "results": results["results"],
            "timestamp": datetime.utcnow().isoformat(),
        }

    def answer_learning_question(
        self,
        question: str,
        n_results: int = 5,
        session_id: str = "default",
    ) -> Dict:
        """Responde em linguagem natural com base no que foi aprendido e armazenado."""
        normalized_question = (question or "").strip()
        if not normalized_question:
            return {
                "question": question,
                "timestamp": datetime.utcnow().isoformat(),
                "answer": "Faca uma pergunta sobre o que o bot aprendeu, por exemplo: o que voce aprendeu hoje sobre inflacao?",
                "results_count": 0,
                "sources": [],
            }

        conversation = self.conversations.setdefault(session_id, [])
        direct_answer = self._answer_meta_question(normalized_question, conversation)
        if direct_answer:
            response = {
                "question": normalized_question,
                "timestamp": datetime.utcnow().isoformat(),
                "answer": direct_answer,
                "results_count": 0,
                "sources": [],
            }
            self._remember_turn(session_id, normalized_question, direct_answer)
            return response

        action_answer = self._answer_conversation_action(normalized_question, conversation)
        if action_answer:
            response = {
                "question": normalized_question,
                "timestamp": datetime.utcnow().isoformat(),
                "answer": action_answer,
                "results_count": 0,
                "sources": [],
            }
            self._remember_turn(session_id, normalized_question, action_answer)
            return response

        search_question = self._build_contextual_question(normalized_question, conversation)

        lowered = search_question.lower()
        if "hoje" in lowered and any(
            token in lowered for token in ["aprendeu", "aprendizado", "aprendeu hoje", "o que sabe"]
        ):
            today = datetime.utcnow().date().isoformat()
            documents = self.memory.get_documents_for_date(today)
            sources = self._build_chat_sources(documents[:n_results], search_question)
            if self._is_priority_question(lowered):
                answer = self._build_priority_answer(sources, normalized_question)
            else:
                answer = self._build_daily_learning_answer(today, sources, normalized_question)
            response = {
                "question": normalized_question,
                "timestamp": datetime.utcnow().isoformat(),
                "answer": answer,
                "results_count": len(sources),
                "sources": sources,
            }
            self._remember_turn(session_id, normalized_question, answer)
            return response

        results = self.memory.search(search_question, n_results=n_results)
        sources = self._build_chat_sources(results.get("results", []), search_question)
        if self._is_priority_question(lowered):
            answer = self._build_priority_answer(sources, normalized_question)
        else:
            answer = self._build_learning_answer(normalized_question, sources, conversation)

        response = {
            "question": normalized_question,
            "timestamp": datetime.utcnow().isoformat(),
            "answer": answer,
            "results_count": len(sources),
            "sources": sources,
        }
        self._remember_turn(session_id, normalized_question, answer)
        return response

    def ingest_source_document(
        self,
        title: str,
        content: str,
        source_name: str,
        url: str = "",
        published_at: str = "",
        tags: List[str] = None,
    ) -> Dict:
        """Armazena artigo, nota ou fonte externa para uso em teses."""
        tags = tags or []
        if self.memory.has_source_document(url=url, title=title):
            logger.info(f"Fonte ja existente na memoria: {title}")
            return {
                "status": "duplicate",
                "title": title,
                "source_name": source_name,
                "url": url,
            }

        text = (
            f"Fonte: {source_name}\n"
            f"Titulo: {title}\n"
            f"Publicado em: {published_at or datetime.utcnow().isoformat()}\n"
            f"URL: {url}\n"
            f"Tags: {', '.join(tags)}\n\n"
            f"{content}"
        )
        metadata = {
            "api": "SOURCE_DOC",
            "focus_area": "Source_Based_Research",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "source_article",
            "title": title,
            "source_name": source_name,
            "url": url,
            "published_at": published_at or datetime.utcnow().isoformat(),
            "tags": ", ".join(tags),
        }

        self.memory.add_data([text], [metadata])
        logger.info(f"Fonte adicionada na memoria: {title}")

        return {
            "status": "stored",
            "title": title,
            "source_name": source_name,
            "url": url,
        }

    def build_source_backed_thesis(self, topic: str, n_results: int = 5) -> Dict:
        """Monta tese com base em memoria tecnica e fontes armazenadas."""
        technical = self.memory.search(
            query=topic,
            n_results=n_results,
            where={"type": "technical_learning"},
        ).get("results", [])
        market_memory = self.memory.search(
            query=topic,
            n_results=n_results,
            where={"type": "market_data"},
        ).get("results", [])
        source_results = self.memory.search(
            query=topic,
            n_results=n_results,
            where={"type": "source_article"},
        ).get("results", [])

        combined_memory = technical + market_memory
        thesis = self.thesis_engine.build_thesis(topic, combined_memory, source_results)
        thesis["technical_results"] = len(technical)
        thesis["market_results"] = len(market_memory)
        return thesis

    def ingest_rss_feed(self, feed_url: str, source_name: str, limit: int = 5) -> Dict:
        """Coleta um feed RSS/Atom e armazena entradas como fontes citaveis."""
        entries = self.research_monitor.fetch_feed(feed_url, limit=limit)
        stored = []
        duplicates = 0

        for entry in entries:
            if not entry.get("title"):
                continue

            result = self.ingest_source_document(
                title=entry.get("title", "Sem titulo"),
                content=entry.get("summary", ""),
                source_name=source_name,
                url=entry.get("url", ""),
                published_at=entry.get("published_at", ""),
                tags=["rss", "research_feed"],
            )
            if result.get("status") == "stored":
                stored.append(result)
            elif result.get("status") == "duplicate":
                duplicates += 1

        return {
            "feed_url": feed_url,
            "source_name": source_name,
            "stored_count": len(stored),
            "duplicates": duplicates,
            "items": stored,
        }

    def collect_daily_research_articles(self) -> Dict:
        """Ingere artigos dos feeds configurados para manter o agente atualizado diariamente."""
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "feeds_processed": 0,
            "articles_stored": 0,
            "duplicates": 0,
            "feeds": [],
        }

        for feed in DEFAULT_RESEARCH_FEEDS:
            feed_url = feed.get("feed_url", "")
            source_name = feed.get("source_name", "Research Feed")
            if not feed_url:
                continue

            try:
                result = self.ingest_rss_feed(
                    feed_url=feed_url,
                    source_name=source_name,
                    limit=RESEARCH_FEED_LIMIT,
                )
                summary["feeds_processed"] += 1
                summary["articles_stored"] += result.get("stored_count", 0)
                summary["duplicates"] += result.get("duplicates", 0)
                summary["feeds"].append(result)
            except Exception as e:
                logger.warning(f"Nao foi possivel ingerir feed {source_name}: {str(e)}")
                summary["feeds"].append(
                    {
                        "feed_url": feed_url,
                        "source_name": source_name,
                        "stored_count": 0,
                        "duplicates": 0,
                        "error": str(e),
                    }
                )

        self._notify_research_ingestion(summary)
        return summary

    def ensure_daily_research_articles(self) -> Dict:
        """Garante que haja artigos ingeridos no dia atual."""
        today = datetime.utcnow().date().isoformat()
        if self.memory.has_document_for_date(today, metadata_type="source_article"):
            logger.info("Artigos do dia ja presentes na memoria")
            return {"status": "already_collected", "date": today}

        try:
            summary = self.collect_daily_research_articles()
            summary["status"] = "collected"
            summary["date"] = today
            return summary
        except Exception as e:
            logger.warning(f"Nao foi possivel garantir artigos diarios: {str(e)}")
            return {"status": "failed", "date": today, "error": str(e)}

    def generate_daily_thesis(self, topic: str = DAILY_THESIS_TOPIC, n_results: int = 5) -> Dict:
        """Gera a tese diaria, salva na memoria e envia ao Telegram."""
        today = datetime.utcnow().date().isoformat()

        if self.memory.has_document_for_date(today, metadata_type="daily_thesis"):
            logger.info("Tese diaria ja registrada hoje")
            return {"status": "already_generated", "date": today, "topic": topic}

        thesis = self.build_source_backed_thesis(topic, n_results=n_results)
        text = (
            f"Tese diaria\n"
            f"Data: {today}\n"
            f"Tema: {thesis.get('topic', topic)}\n"
            f"Tese: {thesis.get('thesis', '')}\n\n"
            f"Evidencias:\n- " + "\n- ".join(thesis.get("evidence", [])) + "\n\n"
            f"Riscos:\n- " + "\n- ".join(thesis.get("risks", []))
        )
        metadata = {
            "api": "THESIS_ENGINE",
            "focus_area": "Daily_Thesis",
            "timestamp": datetime.utcnow().isoformat(),
            "type": "daily_thesis",
            "title": thesis.get("topic", topic),
            "topic": topic,
            "source_count": str(thesis.get("source_count", 0)),
        }

        self.memory.add_data([text], [metadata])
        logger.info(f"Tese diaria registrada: {topic}")
        self._notify_daily_thesis(thesis)

        return {
            "status": "generated",
            "date": today,
            "topic": topic,
            "thesis": thesis,
        }

    def ensure_daily_thesis(self) -> Dict:
        """Garante que a tese do dia exista."""
        try:
            return self.generate_daily_thesis()
        except Exception as e:
            logger.warning(f"Nao foi possivel garantir tese diaria: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def get_agent_status(self) -> Dict:
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "memory": self.memory.get_collection_stats(),
            "scheduler": self.scheduler.get_jobs(),
            "task_stats": self.task_manager.get_stats(),
            "recent_executions": self.task_manager.get_history(limit=5),
            "system": {
                "fred_available": bool(self.fred) and FRED_API_KEY != "seu_fred_api_key_aqui",
                "imf_available": bool(self.imf),
                "worldbank_available": bool(self.worldbank),
                "oecd_available": bool(self.oecd),
                "bis_available": bool(self.bis),
            },
        }

    def get_learning_snapshot(self, limit: int = 5) -> Dict:
        """Retorna um resumo do que esta armazenado na memoria."""
        recent_documents = self.memory.get_recent_documents(limit=limit)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "memory": self.memory.get_collection_stats(),
            "recent_documents": recent_documents,
        }

    def get_daily_learning_snapshot(self, date_str: str = None) -> Dict:
        """Retorna os aprendizados armazenados em uma data especifica UTC."""
        date_str = date_str or datetime.utcnow().date().isoformat()
        documents = self.memory.get_documents_for_date(date_str)

        return {
            "timestamp": datetime.utcnow().isoformat(),
            "date": date_str,
            "memory": self.memory.get_collection_stats(),
            "documents": documents,
        }

    def send_daily_learning_digest(self) -> None:
        """Envia ao Telegram um resumo do que o agente aprendeu no dia."""
        if not ENABLE_TELEGRAM_NOTIFICATIONS:
            logger.info("Digest diario desativado: Telegram desligado")
            return

        try:
            snapshot = self.get_daily_learning_snapshot()
            message = build_daily_learning_digest(snapshot)
            notifier = TelegramNotifier()
            notifier.send_long_message(message)
            logger.info("Digest diario enviado para o Telegram")
        except Exception as e:
            logger.warning(f"Nao foi possivel enviar digest diario: {str(e)}")

    def answer_telegram_message(self, message_text: str, chat_id: str = "telegram") -> str:
        """Gera uma resposta curta para conversa via Telegram."""
        response = self.answer_learning_question(message_text, n_results=5, session_id=chat_id)
        return response.get("answer", "Nao consegui montar uma resposta agora.")

    def learn_daily_technical_content(self) -> Dict:
        """Armazena um card tecnico diario na memoria do agente."""
        today = datetime.utcnow().date().isoformat()
        focus_area = "Daily_Technical_Learning"

        if self.memory.has_document_for_date(
            today,
            metadata_type="technical_learning",
            focus_area=focus_area,
        ):
            logger.info("Aprendizado tecnico diario ja registrado hoje")
            return {"status": "already_learned", "date": today}

        cards = get_macro_learning_cards()
        if not cards:
            logger.warning("Biblioteca tecnica vazia; nenhum aprendizado diario registrado")
            return {"status": "no_cards", "date": today}

        day_index = datetime.utcnow().toordinal() % len(cards)
        card = cards[day_index]

        text = (
            f"Aprendizado tecnico diario\n"
            f"Data: {today}\n"
            f"Dominio: {card['domain']}\n"
            f"Tema: {card['title']}\n\n"
            f"{card['content']}"
        )
        metadata = {
            "api": "MACRO_LIBRARY",
            "focus_area": focus_area,
            "timestamp": datetime.utcnow().isoformat(),
            "type": "technical_learning",
            "domain": card["domain"],
            "title": card["title"],
        }

        self.memory.add_data([text], [metadata])
        logger.info(f"Aprendizado tecnico diario registrado: {card['title']}")
        self._notify_technical_learning(card)

        return {
            "status": "learned",
            "date": today,
            "card": card,
        }

    def ensure_daily_learning(self) -> Dict:
        """Garante pelo menos um aprendizado tecnico por dia."""
        try:
            return self.learn_daily_technical_content()
        except Exception as e:
            logger.warning(f"Nao foi possivel garantir aprendizado diario: {str(e)}")
            return {"status": "failed", "error": str(e)}

    def _setup_schedule(self) -> None:
        self.scheduler.schedule_task("Monday Inflation", self.monday_inflation_policy, "monday", 14)
        self.scheduler.schedule_task("Tuesday Growth", self.tuesday_economic_growth, "tuesday", 14)
        self.scheduler.schedule_task("Wednesday Labor", self.wednesday_labor_market, "wednesday", 14)
        self.scheduler.schedule_task("Thursday Trade", self.thursday_trade_finance, "thursday", 14)
        self.scheduler.schedule_task("Friday Forecasts", self.friday_forecasts_consensus, "friday", 14)
        self.scheduler.schedule_daily_task(
            "Daily Technical Learning",
            self.learn_daily_technical_content,
            DAILY_TECHNICAL_LEARNING_HOUR_UTC,
            DAILY_TECHNICAL_LEARNING_MINUTE_UTC,
        )
        self.scheduler.schedule_daily_task(
            "Daily Research Articles",
            self.collect_daily_research_articles,
            DAILY_RESEARCH_HOUR_UTC,
            DAILY_RESEARCH_MINUTE_UTC,
        )
        self.scheduler.schedule_daily_task(
            "Daily Thesis",
            self.generate_daily_thesis,
            DAILY_THESIS_HOUR_UTC,
            DAILY_THESIS_MINUTE_UTC,
        )
        if ENABLE_TELEGRAM_NOTIFICATIONS:
            self.scheduler.schedule_daily_task(
                "Daily Learning Digest",
                self.send_daily_learning_digest,
                DAILY_DIGEST_HOUR_UTC,
                DAILY_DIGEST_MINUTE_UTC,
            )

    def _store_in_memory(self, data: Dict, api_source: str, focus_area: str) -> None:
        try:
            text = f"{focus_area} ({api_source}): {json.dumps(data, indent=2, default=str)}"
            if len(text) > 10000:
                text = text[:10000] + "... [truncado]"

            metadata = {
                "api": api_source,
                "focus_area": focus_area,
                "timestamp": datetime.utcnow().isoformat(),
                "type": "market_data",
            }

            self.memory.add_data([text], [metadata])
            logger.info(f"{focus_area} armazenado na memoria")
        except Exception as e:
            logger.warning(f"Erro ao armazenar na memoria: {str(e)}")

    def _generate_insights(self, data: Dict) -> List[str]:
        insights = []
        if data.get("results"):
            insights.append(f"Encontrados {len(data['results'])} resultados historicos")
            insights.append("Revise esses resultados para montar a interpretacao economica")
        else:
            insights.append("Ainda nao ha dados suficientes na memoria para esse indicador")
        return insights

    def _notify_learning(self, focus_area: str, api_source: str, data: Dict) -> None:
        """Envia um resumo curto ao Telegram quando a coleta automatica aprende algo novo."""
        if not self.enable_scheduler or not ENABLE_TELEGRAM_NOTIFICATIONS:
            return

        try:
            notifier = TelegramNotifier()
            top_level_keys = list(data.keys())[:6] if isinstance(data, dict) else []
            memory_docs = self.memory.get_collection_stats().get("total_documents", 0)

            lines = [
                "Novo aprendizado do agente",
                f"Foco: {focus_area}",
                f"API: {api_source}",
                f"Horario: {datetime.utcnow().isoformat()}",
                f"Blocos coletados: {', '.join(top_level_keys) if top_level_keys else 'nenhum'}",
                f"Documentos totais na memoria: {memory_docs}",
            ]

            notifier.send_long_message("\n".join(lines))
            logger.info(f"Notificacao de aprendizado enviada: {focus_area}")
        except Exception as e:
            logger.warning(f"Nao foi possivel enviar notificacao de aprendizado: {str(e)}")

    def _notify_technical_learning(self, card: Dict) -> None:
        """Envia ao Telegram o aprendizado tecnico diario."""
        if not self.enable_scheduler or not ENABLE_TELEGRAM_NOTIFICATIONS:
            return

        try:
            notifier = TelegramNotifier()
            message = "\n".join(
                [
                    "Novo aprendizado tecnico do agente",
                    f"Dominio: {card.get('domain', 'Macro')}",
                    f"Tema: {card.get('title', '-')}",
                    f"Horario: {datetime.utcnow().isoformat()}",
                    f"Resumo: {card.get('content', '')[:700]}",
                ]
            )
            notifier.send_long_message(message)
            logger.info(f"Notificacao de aprendizado tecnico enviada: {card.get('title', '-')}")
        except Exception as e:
            logger.warning(f"Nao foi possivel enviar aprendizado tecnico ao Telegram: {str(e)}")

    def _notify_research_ingestion(self, summary: Dict) -> None:
        """Envia um resumo da ingestao diaria de artigos."""
        if not self.enable_scheduler or not ENABLE_TELEGRAM_NOTIFICATIONS:
            return

        try:
            notifier = TelegramNotifier()
            lines = [
                "Nova coleta diaria de artigos",
                f"Horario: {summary.get('timestamp', '-')}",
                f"Feeds processados: {summary.get('feeds_processed', 0)}",
                f"Artigos novos: {summary.get('articles_stored', 0)}",
                f"Duplicados ignorados: {summary.get('duplicates', 0)}",
            ]

            for feed in summary.get("feeds", [])[:4]:
                lines.append(
                    f"- {feed.get('source_name', 'Feed')}: {feed.get('stored_count', 0)} novo(s)"
                )

            notifier.send_long_message("\n".join(lines))
            logger.info("Notificacao de coleta diaria de artigos enviada")
        except Exception as e:
            logger.warning(f"Nao foi possivel enviar resumo de artigos ao Telegram: {str(e)}")

    def _notify_daily_thesis(self, thesis: Dict) -> None:
        """Envia a tese diaria ao Telegram."""
        if not self.enable_scheduler or not ENABLE_TELEGRAM_NOTIFICATIONS:
            return

        try:
            notifier = TelegramNotifier()
            lines = [
                "Tese diaria do agente",
                f"Tema: {thesis.get('topic', '-')}",
                f"Horario: {thesis.get('timestamp', '-')}",
                f"Tese: {thesis.get('thesis', '-')}",
                f"Fontes: {thesis.get('source_count', 0)}",
                "",
                "Evidencias principais:",
            ]

            for item in thesis.get("evidence", [])[:4]:
                lines.append(f"- {item}")

            if thesis.get("citations"):
                lines.append("")
                lines.append("Citacoes:")
                for citation in thesis.get("citations", [])[:4]:
                    lines.append(
                        f"- {citation.get('title', 'Sem titulo')} | {citation.get('source', 'fonte')} | {citation.get('url', '')}"
                    )

            notifier.send_long_message("\n".join(lines))
            logger.info("Tese diaria enviada ao Telegram")
        except Exception as e:
            logger.warning(f"Nao foi possivel enviar tese diaria ao Telegram: {str(e)}")

    def shutdown(self) -> None:
        logger.info("Encerrando agente...")
        self.scheduler.stop()
        logger.info("Agente encerrado")

    def _build_learning_answer(
        self,
        question: str,
        sources: List[Dict],
        conversation: List[Dict[str, str]],
    ) -> str:
        direct_response = self._answer_small_talk(question, conversation)
        if direct_response:
            return direct_response

        if not sources:
            return (
                "Ainda nao encontrei algo forte na memoria sobre isso. "
                "Se quiser, me pergunta de outro jeito ou me pede especificamente sobre inflacao, juros, crescimento, emprego, risco ou o que eu aprendi hoje."
            )

        opening = self._build_consultant_opening(question, sources)
        regime_view = self._build_regime_view(question)
        implications = self._build_implications(question)
        risk_line = self._build_risk_line(sources)
        lines = [opening]
        lines.append(f"Cenario: {regime_view}")
        lines.append(f"Implicacao pratica: {implications}")
        lines.append(f"Principal risco da leitura: {risk_line}")
        lines.append("")
        lines.append("Base da minha leitura:")

        for item in sources[:2]:
            metadata = item.get("metadata", {})
            label = (
                metadata.get("title")
                or metadata.get("focus_area")
                or metadata.get("source_name")
                or metadata.get("api")
                or "Memoria"
            )
            lines.append(f"- {label}: {item.get('snippet', '')}")

        lines.append("")
        lines.append(
            "Se quiser, eu posso responder como consultor macro em um destes formatos: cenario-base, riscos, implicacoes para mercado ou leitura simplificada."
        )
        return "\n\n".join(lines)

    def _build_daily_learning_answer(self, date_str: str, sources: List[Dict], question: str) -> str:
        if not sources:
            return f"Ainda nao encontrei registros do dia {date_str} na memoria."

        lines = [self._build_daily_opening(question, date_str, len(sources))]
        lines.append(
            "Leitura de consultoria: hoje o mais util e separar o que muda o cenario macro do que e apenas ruido informacional."
        )

        for item in sources[:3]:
            metadata = item.get("metadata", {})
            label = (
                metadata.get("title")
                or metadata.get("focus_area")
                or metadata.get("source_name")
                or metadata.get("api")
                or "Memoria"
            )
            lines.append(f"- {label}: {item.get('snippet', '')}")

        lines.append(
            "Se quiser, eu tambem posso te entregar isso como abertura de mercado, tese central ou mapa de riscos."
        )
        return "\n\n".join(lines)

    def _build_chat_sources(self, results: List[Dict], question: str) -> List[Dict]:
        sources = []
        for result in results:
            metadata = result.get("metadata", {}) or {}
            document = result.get("document", "")
            sources.append(
                {
                    "id": result.get("id"),
                    "metadata": metadata,
                    "snippet": self._extract_relevant_snippet(document, question),
                    "document": document,
                    "distance": result.get("distance"),
                }
            )
        return sources

    def _extract_relevant_snippet(self, document: str, question: str, max_chars: int = 280) -> str:
        text = str(document or "").strip()
        if not text:
            return "Sem conteudo textual disponivel."

        compact = " ".join(text.split())
        question_terms = [term for term in question.lower().split() if len(term) >= 4]

        best_start = 0
        best_score = -1
        lowered = compact.lower()

        for term in question_terms[:8]:
            index = lowered.find(term)
            if index >= 0:
                score = len(term)
                if score > best_score:
                    best_score = score
                    best_start = max(0, index - 80)

        snippet = compact[best_start : best_start + max_chars].strip()
        if best_start > 0:
            snippet = "..." + snippet
        if best_start + max_chars < len(compact):
            snippet = snippet + "..."
        return snippet

    def _build_contextual_question(
        self,
        question: str,
        conversation: List[Dict[str, str]],
    ) -> str:
        if not conversation:
            return question

        lowered = question.lower().strip()
        follow_up_starters = [
            "e",
            "e no brasil",
            "e nos eua",
            "e isso",
            "e sobre",
            "mas",
            "entao",
            "por que",
            "como assim",
            "explica melhor",
            "resume",
            "aprofunda",
        ]
        if len(lowered.split()) <= 6 or any(lowered.startswith(item) for item in follow_up_starters):
            last_user_topics = [turn["user"] for turn in conversation[-2:] if turn.get("user")]
            if last_user_topics:
                return f"{' | '.join(last_user_topics)} | {question}"
        return question

    def _remember_turn(self, session_id: str, user_text: str, assistant_text: str) -> None:
        conversation = self.conversations.setdefault(session_id, [])
        conversation.append({"user": user_text, "assistant": assistant_text})
        if len(conversation) > 6:
            self.conversations[session_id] = conversation[-6:]

    def _answer_small_talk(
        self,
        question: str,
        conversation: List[Dict[str, str]],
    ) -> str:
        lowered = question.lower().strip()

        if lowered in {"oi", "ola", "olá", "bom dia", "boa tarde", "boa noite"}:
            return (
                "Oi. Eu posso ser seu consultor macro e te responder com leitura de cenario, riscos e implicacoes praticas. "
                "Se quiser, me pergunta algo como 'qual e sua leitura sobre juros?' ou 'o que voce aprendeu hoje?'."
            )

        if "quem e voce" in lowered or "quem é voce" in lowered:
            return (
                "Eu sou o BotMacroeconomist. Posso atuar como seu consultor macro, acompanhando dados e textos macroeconomicos, organizando uma tese e te devolvendo a leitura mais importante."
            )

        if "o que voce sabe" in lowered or "o que você sabe" in lowered:
            return (
                "Eu consigo te ajudar principalmente com inflacao, juros, crescimento, mercado de trabalho, comercio global, artigos recentes e teses diarias, sempre tentando transformar isso em leitura de cenario."
            )

        if lowered in {"obrigado", "obrigada", "valeu"}:
            return "Sempre que quiser, sigo aqui como seu consultor macro."

        if lowered in {"sim", "quero", "pode"} and conversation:
            last_user = conversation[-1].get("user", "")
            return (
                f"Claro. Como consultor macro, eu posso aprofundar a parte mais importante de '{last_user}' ou transformar isso em tese, risco e implicacao pratica."
            )

        return ""

    def _answer_meta_question(
        self,
        question: str,
        conversation: List[Dict[str, str]],
    ) -> str:
        lowered = question.lower().strip()
        compact = " ".join(lowered.split())

        capability_markers = [
            "o que voce consegue fazer",
            "o que você consegue fazer",
            "o que voce faz",
            "o que você faz",
            "como voce pode me ajudar",
            "como você pode me ajudar",
            "como voce me ajuda",
            "como você me ajuda",
            "no que voce ajuda",
            "no que você ajuda",
        ]
        if any(marker in compact for marker in capability_markers):
            return (
                "Eu posso agir como seu consultor macro. Consigo conversar com voce sobre inflacao, juros, crescimento, emprego, risco e noticias que eu aprendi.\n\n"
                "Na pratica, eu posso:\n"
                "- te dar uma leitura de cenario\n"
                "- resumir o que aprendi hoje\n"
                "- destacar o que parece mais importante\n"
                "- transformar uma noticia em tese, risco e implicacao para mercado\n"
                "- continuar a conversa entendendo o contexto da sua pergunta\n\n"
                "Se quiser, testa comigo assim: 'qual e sua leitura sobre juros?'"
            )

        help_markers = [
            "como falar com voce",
            "como falar com você",
            "como conversar com voce",
            "como conversar com você",
            "como te perguntar",
        ]
        if any(marker in compact for marker in help_markers):
            return (
                "Pode falar comigo de forma natural, como numa conversa. Quanto mais direto voce for, melhor.\n\n"
                "Exemplos:\n"
                "- 'qual e sua leitura sobre inflacao?'\n"
                "- 'o que voce aprendeu hoje?'\n"
                "- 'e no brasil?'\n"
                "- 'resume isso'\n"
                "- 'qual o principal risco dessa tese?'"
            )

        if compact in {"me ajuda", "pode me ajudar?", "pode me ajudar", "me ajuda?"}:
            return (
                "Posso, sim. Me diz o tema macro e eu te respondo como consultor. Por exemplo: 'qual e sua leitura sobre juros?'"
            )

        if compact in {"o que voce consegue", "o que você consegue"}:
            return (
                "Consigo conversar com voce como consultor macro e transformar o que aprendi em leitura de cenario, risco e implicacao pratica."
            )

        return ""

    def _answer_conversation_action(
        self,
        question: str,
        conversation: List[Dict[str, str]],
    ) -> str:
        if not conversation:
            return ""

        compact = " ".join(question.lower().strip().split())
        last_turn = conversation[-1]
        last_user = last_turn.get("user", "")
        last_answer = last_turn.get("assistant", "")
        reference_topic = self._infer_topic_from_text(last_user)
        if reference_topic == "macro":
            reference_topic = self._infer_topic_from_text(last_answer)

        if compact in {"resume", "resume isso", "resume isso pra mim", "resuma", "resuma isso"}:
            return self._summarize_previous_answer(last_answer, reference_topic)

        if compact in {
            "explica melhor",
            "explique melhor",
            "aprofunda",
            "aprofunde",
            "como assim",
        }:
            return self._expand_previous_answer(reference_topic, last_answer)

        if any(marker in compact for marker in ["traduz isso para mercado", "e para mercado", "impacto no mercado"]):
            return self._translate_to_market(reference_topic)

        if any(marker in compact for marker in ["qual o principal risco", "qual o risco principal", "e o risco", "qual risco dessa tese", "qual o principal risco dessa tese"]):
            extracted = self._extract_named_line(last_answer, "Principal risco da leitura:")
            if extracted:
                return f"O principal risco que eu destacaria e: {extracted}"
            return self._default_risk_answer(reference_topic)

        if any(marker in compact for marker in ["qual a tese", "qual é a tese", "tese central", "qual a leitura central"]):
            opening = self._extract_first_meaningful_line(last_answer)
            if opening:
                return f"A tese central, de forma bem direta, e esta: {opening}"

        if compact.startswith("e no brasil"):
            return self._regional_follow_up("brasil", reference_topic)

        if compact.startswith("e nos eua") or compact.startswith("e nos eua?") or compact.startswith("e nos eua"):
            return self._regional_follow_up("eua", reference_topic)

        if compact.startswith("e na europa") or compact.startswith("e na zona do euro"):
            return self._regional_follow_up("europa", reference_topic)

        return ""

    def _build_consultant_opening(self, question: str, sources: List[Dict]) -> str:
        top_meta = sources[0].get("metadata", {}) if sources else {}
        top_label = (
            top_meta.get("title")
            or top_meta.get("focus_area")
            or top_meta.get("source_name")
            or top_meta.get("api")
            or "esse tema"
        )

        lowered = question.lower()
        if "inflacao" in lowered:
            return f"Minha leitura inicial sobre inflacao e que {top_label} ajuda a ancorar o cenario."
        if "juro" in lowered:
            return f"Minha leitura inicial sobre juros parte de {top_label}."
        if "crescimento" in lowered or "pib" in lowered:
            return f"Minha leitura inicial sobre crescimento e que {top_label} e o melhor ponto de partida."
        return f"Minha leitura inicial e que {top_label} concentra o sinal mais util para essa pergunta."

    def _build_daily_opening(self, question: str, date_str: str, source_count: int) -> str:
        lowered = question.lower()
        if "hoje" in lowered:
            return f"Hoje, em {date_str}, eu registrei {source_count} aprendizado(s) que podem te interessar."
        return f"Na data {date_str}, eu encontrei {source_count} registro(s) relacionados a isso."

    def _is_priority_question(self, lowered_question: str) -> bool:
        markers = [
            "mais importante",
            "mais relevante",
            "principal",
            "o que importa mais",
            "qual desses",
        ]
        return any(marker in lowered_question for marker in markers)

    def _build_priority_answer(self, sources: List[Dict], question: str) -> str:
        if not sources:
            return (
                "Eu ainda nao tenho base suficiente na memoria para dizer o que parece mais importante nisso."
            )

        top = sources[0]
        metadata = top.get("metadata", {})
        label = (
            metadata.get("title")
            or metadata.get("focus_area")
            or metadata.get("source_name")
            or metadata.get("api")
            or "esse registro"
        )

        return (
            f"Se eu tivesse que te dar uma prioridade como consultor macro, eu destacaria {label}. "
            f"Esse foi o sinal mais forte na minha memoria para a sua pergunta.\n\n"
            f"Por que ele importa: {top.get('snippet', '')}\n\n"
            "Se quiser, eu posso traduzir isso em tese central, risco principal ou implicacao para mercado."
        )

    def _build_regime_view(self, question: str) -> str:
        lowered = question.lower()
        if "inflacao" in lowered:
            return "o foco deve estar em persistencia inflacionaria versus desaceleracao suficiente para aliviar a postura monetaria."
        if "juro" in lowered:
            return "o mercado tende a oscilar entre manutencao de juros altos por mais tempo e expectativa de alivio adiante."
        if "crescimento" in lowered or "pib" in lowered:
            return "o ponto central e diferenciar desaceleracao saudavel de perda mais forte de tracao."
        if "emprego" in lowered or "trabalho" in lowered:
            return "o ponto central e saber se o mercado de trabalho continua apertado ou se comeca a perder folego."
        return "eu separaria esse tema entre sinal de tendencia, confirmacao por dados e risco de revisao."

    def _build_implications(self, question: str) -> str:
        lowered = question.lower()
        if "inflacao" in lowered:
            return "se a desinflacao perder ritmo, a leitura para juros fica mais dura e o espaco para alivio diminui."
        if "juro" in lowered:
            return "juros altos por mais tempo costumam pressionar atividade, credito e ativos mais sensiveis a desconto."
        if "crescimento" in lowered or "pib" in lowered:
            return "crescimento mais fraco muda a discussao para cortes, fiscal e qualidade do lucro das empresas."
        if "emprego" in lowered or "trabalho" in lowered:
            return "qualquer perda de folego mais clara no emprego pode alterar rapidamente a leitura de politica monetaria."
        return "eu usaria isso para ajustar a leitura de cenario, e nao apenas para acompanhar a noticia isolada."

    def _build_risk_line(self, sources: List[Dict]) -> str:
        top_meta = sources[0].get("metadata", {}) if sources else {}
        source_type = top_meta.get("type", "memory")
        if source_type == "source_article":
            return "o texto pode capturar bem a narrativa do momento, mas nao necessariamente confirma sozinho a direcao dos dados."
        if source_type == "daily_thesis":
            return "teses ajudam a organizar a leitura, mas precisam ser revalidadas quando entram dados novos."
        return "a memoria da casa ajuda no contexto, mas a leitura pode mudar com revisoes e novas divulgacoes."

    def _infer_topic_from_text(self, text: str) -> str:
        lowered = text.lower()
        if "inflacao" in lowered:
            return "inflacao"
        if "juro" in lowered:
            return "juros"
        if "crescimento" in lowered or "pib" in lowered:
            return "crescimento"
        if "emprego" in lowered or "trabalho" in lowered:
            return "emprego"
        if "credito" in lowered:
            return "credito"
        return "macro"

    def _extract_named_line(self, text: str, prefix: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped.startswith(prefix):
                return stripped.replace(prefix, "", 1).strip()
        return ""

    def _extract_first_meaningful_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("- ") and ":" not in stripped[:28]:
                return stripped
        return ""

    def _summarize_previous_answer(self, last_answer: str, topic: str) -> str:
        first_line = self._extract_first_meaningful_line(last_answer)
        if first_line:
            return (
                f"Resumo rapido: {first_line} "
                f"Em outras palavras, minha leitura central sobre {topic} e essa."
            )
        return f"Resumo rapido: minha leitura central sobre {topic} ainda depende de mais contexto."

    def _expand_previous_answer(self, topic: str, last_answer: str) -> str:
        return (
            f"Expandindo a ideia: quando eu falo de {topic}, estou tentando separar sinal estrutural de ruido de curto prazo. "
            "A pergunta principal e se o movimento observado muda a direcao do cenario ou apenas a intensidade dele."
        )

    def _translate_to_market(self, topic: str) -> str:
        if topic == "inflacao":
            return "Traduzindo para mercado: inflacao mais resistente tende a sustentar juros mais altos, pressionar duration e reduzir o apetite por ativos mais sensiveis a desconto."
        if topic == "juros":
            return "Traduzindo para mercado: juros altos por mais tempo costumam ser melhores para caixa e piores para ativos dependentes de crescimento e credito frouxo."
        if topic == "crescimento":
            return "Traduzindo para mercado: se crescimento perde tracao, o mercado passa a precificar alivio monetario, revisao de lucros e maior seletividade em risco."
        if topic == "emprego":
            return "Traduzindo para mercado: se o mercado de trabalho enfraquece, a leitura para atividade e juros muda rapido e isso costuma contaminar varios ativos ao mesmo tempo."
        return "Traduzindo para mercado: eu olharia para como isso altera juros esperados, crescimento implicito e premio de risco."

    def _default_risk_answer(self, topic: str) -> str:
        if topic == "inflacao":
            return "O principal risco e confundir alivio temporario com desinflacao sustentada."
        if topic == "juros":
            return "O principal risco e o mercado precificar alivio cedo demais e depois precisar corrigir a expectativa."
        if topic == "crescimento":
            return "O principal risco e tratar uma perda de folego mais estrutural como simples oscilacao de curto prazo."
        return "O principal risco e construir uma tese forte demais em cima de sinais ainda incompletos."

    def _regional_follow_up(self, region: str, topic: str) -> str:
        if region == "brasil":
            return (
                f"No Brasil, eu olharia para {topic} junto com fiscal, cambio e credibilidade da politica monetaria. "
                "Esses tres elementos costumam amplificar ou suavizar o sinal macro."
            )
        if region == "eua":
            return (
                f"Nos EUA, eu olharia para {topic} junto com Fed, payroll e condicoes financeiras. "
                "Normalmente e isso que define o tom dominante do mercado."
            )
        return (
            f"Na Europa, eu olharia para {topic} junto com BCE, energia e atividade industrial. "
            "Essa combinacao costuma mudar bastante a leitura do cenario."
        )
