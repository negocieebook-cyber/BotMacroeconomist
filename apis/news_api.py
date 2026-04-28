"""
Coleta de notícias via RSS com formatação para Telegram.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import feedparser
    FEEDPARSER_AVAILABLE = True
except ImportError:
    FEEDPARSER_AVAILABLE = False
    logger.warning("feedparser não instalado. Rode: pip install feedparser")


# Feeds RSS com cobertura macro ampliada (gratuitos e sem autenticacao)
DEFAULT_FEEDS = [
    {
        "name": "FT Markets",
        "url": "https://www.ft.com/markets?format=rss",
        "emoji": "📊",
    },
    {
        "name": "Reuters Business",
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "emoji": "📰",
    },
    {
        "name": "IMF News",
        "url": "https://www.imf.org/en/News/RSS",
        "emoji": "🌐",
    },
    {
        "name": "Google News — Macro",
        "url": "https://news.google.com/rss/search?q=macroeconomics+inflation+interest+rates+fed&hl=en-US&gl=US&ceid=US:en",
        "emoji": "🔍",
    },
    {
        "name": "Google News — Oil & Commodities",
        "url": "https://news.google.com/rss/search?q=oil+price+commodities+OPEC+geopolitics&hl=en-US&gl=US&ceid=US:en",
        "emoji": "🛢️",
    },
    {
        "name": "Google News — Trade & Tariffs",
        "url": "https://news.google.com/rss/search?q=tariffs+trade+war+WTO+Trump&hl=en-US&gl=US&ceid=US:en",
        "emoji": "⚖️",
    },
    {
        "name": "Google News — Brasil Macro",
        "url": "https://news.google.com/rss/search?q=Selic+IPCA+Copom+Lula+fiscal+cambio+real&hl=pt-BR&gl=BR&ceid=BR:pt-419",
        "emoji": "🇧🇷",
    },
    {
        "name": "ECB Press",
        "url": "https://www.ecb.europa.eu/rss/press.html",
        "emoji": "🏦",
    },
    {
        "name": "Federal Reserve",
        "url": "https://www.federalreserve.gov/feeds/press_all.xml",
        "emoji": "🏛️",
    },
]


class NewsCollector:
    """Coleta e formata notícias de feeds RSS para o Telegram."""

    def fetch_latest(
        self,
        feeds: Optional[List[Dict[str, Any]]] = None,
        limit_per_feed: int = 3,
    ) -> List[Dict[str, Any]]:
        """
        Busca as últimas notícias de todos os feeds.

        Args:
            feeds: Lista de feeds. Se None, usa DEFAULT_FEEDS.
            limit_per_feed: Máximo de notícias por feed.

        Returns:
            Lista de artigos com title, summary, url, source, published_at.
        """
        if not FEEDPARSER_AVAILABLE:
            return []

        target_feeds = feeds or DEFAULT_FEEDS
        articles = []

        for feed_cfg in target_feeds:
            url = feed_cfg.get("url", "")
            name = feed_cfg.get("name", "Feed")
            if not url:
                continue

            try:
                parsed = feedparser.parse(url)
                for entry in parsed.entries[:limit_per_feed]:
                    articles.append(
                        {
                            "source": name,
                            "emoji": feed_cfg.get("emoji", "📰"),
                            "title": entry.get("title", "Sem título"),
                            "summary": (entry.get("summary") or "")[:300],
                            "url": entry.get("link", ""),
                            "published_at": entry.get("published", datetime.now(timezone.utc).isoformat()),
                        }
                    )
            except Exception as exc:
                logger.warning(f"Falha ao buscar feed {name}: {exc}")

        return articles

    def format_news_message(
        self,
        feeds: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> str:
        """
        Formata as últimas notícias em mensagem para Telegram.

        Returns:
            String formatada com notícias recentes.
        """
        articles = self.fetch_latest(feeds=feeds, limit_per_feed=3)

        if not articles:
            if not FEEDPARSER_AVAILABLE:
                return "❌ feedparser não instalado. Rode: pip install feedparser"
            return "❌ Não consegui buscar notícias no momento. Verifique a conexão."

        ts = datetime.now(timezone.utc).strftime("%d/%m %H:%M UTC")
        lines = [f"📰 *Últimas Notícias Macro* — {ts}", ""]

        for i, article in enumerate(articles[:limit], 1):
            emoji = article.get("emoji", "📰")
            source = article.get("source", "")
            title = article.get("title", "Sem título")
            url = article.get("url", "")

            if url:
                lines.append(f"{i}. {emoji} [{title}]({url})")
            else:
                lines.append(f"{i}. {emoji} {title}")

            lines.append(f"   _{source}_")
            lines.append("")

        return "\n".join(lines).strip()

    def format_news_for_context(
        self,
        feeds: Optional[List[Dict[str, Any]]] = None,
        limit: int = 5,
    ) -> str:
        """
        Formata notícias como texto de contexto para o LLM.

        Returns:
            String com notícias formatadas para injetar no prompt.
        """
        articles = self.fetch_latest(feeds=feeds, limit_per_feed=3)

        if not articles:
            return "Nenhuma notícia recente disponível."

        lines = ["Notícias recentes coletadas:"]
        for article in articles[:limit]:
            title = article.get("title", "Sem título")
            source = article.get("source", "Desconhecido")
            summary = article.get("summary", "")
            url = article.get("url", "")
            lines.append(f"- [{source}] {title}")
            if summary:
                lines.append(f"  Resumo: {summary[:200]}")
            if url:
                lines.append(f"  URL: {url}")

        return "\n".join(lines)
