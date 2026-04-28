"""
Briefing de Fechamento do Dia — Macroeconomista Pessoal.

Consolida tudo que foi aprendido e observado no dia:
  - Mercados (cotações em tempo real)
  - Notícias relevantes
  - Dados econômicos coletados
  - Aprendizado técnico do dia
  - Tese do dia
  - Pontos de atenção / riscos
  - Sugestão de post para o X (para postar no dia seguinte)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from memory.chromadb_manager import ChromaDBManager
    from utils import MacroLLMClient, TelegramNotifier

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Helpers de formatação
# ---------------------------------------------------------------------------

def _brt_timestamp() -> str:
    """Retorna data/hora no fuso de Brasília (UTC-3)."""
    from datetime import timedelta
    brt = datetime.now(timezone.utc) - timedelta(hours=3)
    return brt.strftime("%d/%m/%Y às %H:%M (BRT)")


def _date_utc() -> str:
    return datetime.now(timezone.utc).date().isoformat()


def _section(title: str, lines: List[str], empty_msg: str = "Nenhuma informação disponível.") -> str:
    body = "\n".join(lines) if lines else empty_msg
    return f"{title}\n{body}"


# ---------------------------------------------------------------------------
# Builder principal
# ---------------------------------------------------------------------------

class DailyBriefingBuilder:
    """
    Constrói o briefing de fechamento do dia consolidando toda a memória
    acumulada durante o dia com dados ao vivo.
    """

    def __init__(
        self,
        memory: "ChromaDBManager",
        llm: Optional["MacroLLMClient"] = None,
        base_dir: Optional[Path] = None,
    ):
        self.memory = memory
        self.llm = llm
        self.base_dir = base_dir or Path.cwd()

    # ------------------------------------------------------------------
    # Ponto de entrada público
    # ------------------------------------------------------------------

    def build(self) -> str:
        """Gera o briefing completo como string formatada para Telegram."""
        today = _date_utc()
        documents = self.memory.get_documents_for_date(today)

        news        = self._filter(documents, "news_insight")
        tech        = self._filter(documents, "technical_learning")
        market_data = self._filter(documents, "market_data")
        source_art  = self._filter(documents, "source_article")
        thesis_docs = self._filter(documents, "daily_thesis")

        market_live = self._get_live_market()
        news_live   = self._get_live_news()

        # Monta bloco de todos os fatos do dia para o LLM analisar
        raw_context = self._build_raw_context(
            market_live, news_live, news, tech, market_data, source_art, thesis_docs
        )

        # Tenta gerar analise rica com LLM
        try:
            from scheduler.content_scheduler import format_latest_x_drafts

            drafts_text = format_latest_x_drafts(self.base_dir)
            if "Nenhum draft" not in drafts_text:
                return f"{title}\n{drafts_text}"
        except Exception as exc:
            logger.debug(f"Leitura dos drafts oficiais do X falhou: {exc}")

        if self.llm and self.llm.is_available():
            try:
                analysis = self.llm.analyze_day(raw_context, market_live, news_live)
                if analysis:
                    return analysis + "\n\n" + self._section_x_post_suggestion(news_live, thesis_docs, market_live)
            except Exception as exc:
                logger.debug(f"LLM analyze_day falhou, usando texto estruturado: {exc}")

        # Fallback: estrutura manual
        sections: List[str] = [
            f"⛔️ *Fechamento do Dia — {_brt_timestamp()}*",
            "",
            self._section_markets(market_live),
            "",
            self._section_news(news, news_live),
            "",
            self._section_economic_data(market_data, source_art),
            "",
            self._section_technical_learning(tech),
            "",
            self._section_thesis(thesis_docs),
            "",
            self._section_risks(news, market_data, source_art, thesis_docs),
            "",
            self._section_x_post_suggestion(news_live, thesis_docs, market_live),
        ]
        return "\n".join(sections)

    def _build_raw_context(
        self,
        market_live: str,
        news_live: str,
        news: List[Dict],
        tech: List[Dict],
        market_data: List[Dict],
        source_art: List[Dict],
        thesis_docs: List[Dict],
    ) -> str:
        """Monta um bloco de texto com todos os fatos do dia para o LLM."""
        parts: List[str] = []

        if market_live:
            parts.append(f"COTAÇÕES EM TEMPO REAL:\n{market_live}")

        if news_live:
            parts.append(f"NOTÍCIAS AO VIVO (RSS):\n{news_live[:2000]}")

        stored_titles = []
        for item in (news + source_art)[:10]:
            meta = item.get("metadata", {})
            title = meta.get("title", "")
            source = meta.get("source_name", meta.get("api", ""))
            if title:
                stored_titles.append(f"- [{source}] {title}")
        if stored_titles:
            parts.append("NOTÍCIAS E ARTIGOS ARMAZENADOS HOJE:\n" + "\n".join(stored_titles))

        if tech:
            meta = tech[-1].get("metadata", {})
            parts.append(
                f"APRENDIZADO TÉCNICO DO DIA:\n"
                f"Tema: {meta.get('title','')}, Domínio: {meta.get('domain','')}"
            )

        if thesis_docs:
            doc = thesis_docs[-1].get("document", "")
            parts.append(f"TESE ACUMULADA DO DIA:\n{doc[:600]}")

        return "\n\n".join(parts)


    # ------------------------------------------------------------------
    # Seções
    # ------------------------------------------------------------------

    def _section_markets(self, market_text: str) -> str:
        if not market_text:
            market_text = "Dados de mercado indisponíveis no momento."
        return f"📊 *MERCADOS*\n{market_text}"

    def _section_news(self, stored_news: List[Dict], live_news: str) -> str:
        lines: List[str] = []

        # Notícias ao vivo têm prioridade visual
        if live_news:
            for line in live_news.strip().split("\n")[:8]:
                if line.strip():
                    lines.append(line)

        # Completar com notícias salvas no ChromaDB que ainda não apareceram
        if not lines:
            for item in stored_news[:5]:
                meta = item.get("metadata", {})
                title = meta.get("title", "")
                source = meta.get("source_name", meta.get("api", "Fonte"))
                if title:
                    lines.append(f"• [{source}] {title}")

        return _section("📰 *PRINCIPAIS NOTÍCIAS DO DIA*", lines)

    def _section_economic_data(self, market_data: List[Dict], source_art: List[Dict]) -> str:
        lines: List[str] = []
        seen: set = set()

        for item in (market_data + source_art)[:6]:
            meta = item.get("metadata", {})
            focus = meta.get("focus_area", meta.get("type", ""))
            title = meta.get("title", "")
            key = title or focus
            if key in seen:
                continue
            seen.add(key)
            label = title or focus.replace("_", " ")
            if label:
                lines.append(f"• {label}")

        return _section("📈 *DADOS ECONÔMICOS COLETADOS HOJE*", lines)

    def _section_technical_learning(self, tech: List[Dict]) -> str:
        if not tech:
            return "🧠 *APRENDIZADO TÉCNICO DO DIA*\nNenhum aprendizado registrado ainda."

        item = tech[-1]  # Pega o mais recente
        meta = item.get("metadata", {})
        domain = meta.get("domain", "Macroeconomia")
        title = meta.get("title", "Conceito do dia")
        doc = item.get("document", "")

        # Extrai apenas o corpo do texto (pula o cabeçalho padrão de 5 linhas)
        body_lines = doc.split("\n")[5:] if "\n" in doc else [doc]
        body = " ".join(body_lines).strip()[:600]
        if len(body) == 600:
            body += "..."

        return f"🧠 *APRENDIZADO TÉCNICO DO DIA*\n*Tema:* {title} ({domain})\n{body}"

    def _section_thesis(self, thesis_docs: List[Dict]) -> str:
        if not thesis_docs:
            return "🎯 *TESE DO DIA*\nNenhuma tese gerada ainda hoje."

        item = thesis_docs[-1]
        doc = item.get("document", "")

        # Extrai linhas relevantes do texto salvo
        lines_raw = doc.split("\n")
        tese_line = next((l for l in lines_raw if l.startswith("Tese:")), "")
        evidencias = [l for l in lines_raw if l.startswith("- ") and "Riscos" not in l][:3]
        riscos = [l for l in lines_raw if l.startswith("- ") and l not in evidencias][:2]

        content_lines: List[str] = []
        if tese_line:
            content_lines.append(tese_line)
        if evidencias:
            content_lines.append("\n*Evidências:*")
            content_lines.extend(evidencias)
        if riscos:
            content_lines.append("\n*Riscos:*")
            content_lines.extend(riscos)

        body = "\n".join(content_lines) if content_lines else doc[:400]
        return f"🎯 *TESE DO DIA*\n{body}"

    def _section_risks(
        self,
        news: List[Dict],
        market_data: List[Dict],
        source_art: List[Dict],
        thesis_docs: List[Dict],
    ) -> str:
        risk_keywords = [
            "risco", "risk", "tensão", "tension", "queda", "crise", "stress",
            "alerta", "warning", "inflação", "default", "recessão", "recession",
            "incerteza", "uncertainty", "volatilidade", "volatility",
        ]
        found: List[str] = []

        all_docs = news + source_art + thesis_docs + market_data
        for item in all_docs:
            doc_text = (item.get("document", "") or "").lower()
            meta = item.get("metadata", {})
            title = meta.get("title", "")
            for kw in risk_keywords:
                if kw in doc_text and title and title not in [f[0] for f in found]:
                    found.append(f"⚠️ {title}")
                    break

        if not found:
            found = ["Nenhum alerta especial identificado nos dados de hoje."]

        return _section("⚠️ *PONTOS DE ATENÇÃO PARA AMANHÃ*", found[:5])

    def _section_x_post_suggestion(
        self,
        news_text: str,
        thesis_docs: List[Dict],
        market_text: str,
    ) -> str:
        """Gera 4 posts para o X, um de cada tipo editorial, com base no dia."""
        title = "📝 *SUGESTÕES DE POST PARA O X (amanha)*"
        if self.llm and self.llm.is_available():
            try:
                raw = self.llm.answer_question(
                    question=(
                        "Escreva EXATAMENTE 4 tweets para o X, para eu postar amanha, usando os eventos macro de hoje. "
                        "Cada tweet deve ter no maximo 280 caracteres e deve vir com o rotulo do tipo editorial. "
                        "Os 4 tipos obrigatorios sao: VALOR, CRESCIMENTO, PROVA, PERSONALIDADE. "
                        "VALOR deve ensinar uma leitura util do tema atual. "
                        "CRESCIMENTO deve tornar o tema macro acessivel e compartilhavel para nao-especialistas. "
                        "PROVA deve construir autoridade mostrando evidencia, confirmacao, erro comum ou leitura dos dados. "
                        "PERSONALIDADE deve mostrar processo, rotina, cautela ou aprendizado da pessoa por tras da conta. "
                        "Use linhas curtas, espaco em branco entre blocos e ritmo parecido com posts curtos do X. "
                        "Nao use hashtags. Nao use emojis. "
                        "Base-se APENAS nos dados e noticias fornecidos no contexto. Nao invente dados. "
                        "Responda em ingles, mantendo os rotulos em portugues: "
                        "[VALOR], [CRESCIMENTO], [PROVA], [PERSONALIDADE]."
                    ),
                    sources=[],
                    conversation=[],
                    market_context=market_text,
                    news_context=news_text,
                )
                if raw and len(raw.strip()) > 30:
                    return f"{title}\n{raw.strip()[:1400]}"
            except Exception as exc:
                logger.debug(f"LLM X posts falhou: {exc}")

        if thesis_docs:
            doc = thesis_docs[-1].get("document", "")
            lines_raw = doc.split("\n")
            tese = next((l.replace("Tese:", "").strip() for l in lines_raw if l.startswith("Tese:")), "")
            if tese:
                base = tese[:120]
                return (
                    f"{title}\n"
                    f"[VALOR]\nHow I would read tomorrow's setup:\n\n{base}\n\nNone of this is a trade by itself.\n\n"
                    f"[CRESCIMENTO]\nWhat the market may already be pricing:\n\n+ {base}\n\nWhich part is still underestimated?\n\n"
                    "[PROVA]\nA recurring mistake in macro:\n\n\"One headline explains the whole move.\"\n\nIt is not that simple.\n\nCorrelation is not a thesis.\n\n"
                    "[PERSONALIDADE]\nI try not to react too fast when the tape gets noisy.\n\nThe first read is usually emotional.\n\nSo I start with the setup."
                )

        return (
            f"{title}\n"
            "[VALOR]\nHow I would read tomorrow's setup:\n\nStart with the data, then the policy path.\n\n"
            "[CRESCIMENTO]\nWhat the market may already be pricing:\n\n+ Growth\n+ Inflation\n+ Liquidity\n\n"
            "[PROVA]\nA recurring mistake in macro:\n\n\"One headline explains the whole move.\"\n\nCorrelation is not a thesis.\n\n"
            "[PERSONALIDADE]\nI try not to react too fast when macro gets noisy.\n\nThe pause protects conviction."
        )


    # ------------------------------------------------------------------
    # Dados ao vivo
    # ------------------------------------------------------------------

    def _get_live_market(self) -> str:
        try:
            from apis.market_api import DEFAULT_ASSETS, MarketDataClient
            client = MarketDataClient()
            snapshot = client.get_market_snapshot()
            quotes = snapshot.get("quotes", {})
            lines: List[str] = []
            for ticker, meta in DEFAULT_ASSETS.items():
                q = quotes.get(ticker, {})
                if "price" not in q:
                    continue
                price = q["price"]
                chg = q.get("change_pct")
                chg_str = (
                    f" ({'+' if chg and chg >= 0 else ''}{chg:.2f}%)"
                    if chg is not None else ""
                )
                prefix = meta.get("prefix", "")
                lines.append(f"• {meta['label']}: {prefix}{price}{chg_str}")
            return "\n".join(lines)
        except Exception as exc:
            logger.debug(f"Mercado indisponível: {exc}")
            return ""

    def _get_live_news(self) -> str:
        try:
            from apis.news_api import NewsCollector
            collector = NewsCollector()
            return collector.format_news_for_context(limit=6)
        except Exception as exc:
            logger.debug(f"Notícias indisponíveis: {exc}")
            return ""

    # ------------------------------------------------------------------
    # Utilitários internos
    # ------------------------------------------------------------------

    @staticmethod
    def _filter(documents: List[Dict], doc_type: str) -> List[Dict]:
        return [d for d in documents if (d.get("metadata") or {}).get("type") == doc_type]
