"""
API de dados de mercado em tempo real via yfinance.
Gratuito, sem chave de API necessária.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import yfinance as yf
    YFINANCE_AVAILABLE = True
except ImportError:
    YFINANCE_AVAILABLE = False
    logger.warning("yfinance não instalado. Rode: pip install yfinance")


# Ativos monitorados por padrão
DEFAULT_ASSETS = {
    "USDBRL=X": {"label": "Dólar/Real", "emoji": "💵", "prefix": "R$"},
    "EURBRL=X": {"label": "Euro/Real",  "emoji": "💶", "prefix": "R$"},
    "BTC-USD":  {"label": "Bitcoin",    "emoji": "₿",  "prefix": "US$"},
    "GC=F":     {"label": "Ouro",       "emoji": "🥇", "prefix": "US$"},
    "^GSPC":    {"label": "S&P 500",    "emoji": "📈", "prefix": ""},
    "^BVSP":    {"label": "Ibovespa",   "emoji": "🇧🇷", "prefix": ""},
    "CL=F":     {"label": "Petróleo WTI","emoji": "🛢️", "prefix": "US$"},
    "^TNX":     {"label": "T10Y Yield", "emoji": "🏦", "prefix": "%"},
}


class MarketDataClient:
    """Busca cotações em tempo real via Yahoo Finance."""

    def get_quote(self, ticker: str) -> Dict:
        """
        Retorna cotação de um ticker específico.

        Args:
            ticker: Ticker do Yahoo Finance (ex: 'USDBRL=X', 'PETR4.SA', 'AAPL')

        Returns:
            Dict com price, change_pct, name, timestamp
        """
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance não instalado"}

        try:
            t = yf.Ticker(ticker)
            info = t.fast_info

            price = getattr(info, "last_price", None)
            prev_close = getattr(info, "previous_close", None)

            if price is None:
                hist = t.history(period="1d", interval="1m")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
                    prev_close = float(hist["Close"].iloc[0])

            if price is None:
                return {"ticker": ticker, "error": "Sem dados disponíveis"}

            change_pct = None
            if prev_close and prev_close != 0:
                change_pct = ((price - prev_close) / prev_close) * 100

            return {
                "ticker": ticker,
                "price": round(float(price), 4),
                "prev_close": round(float(prev_close), 4) if prev_close else None,
                "change_pct": round(change_pct, 2) if change_pct is not None else None,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        except Exception as exc:
            logger.warning(f"Erro ao buscar {ticker}: {exc}")
            return {"ticker": ticker, "error": str(exc)}

    def get_market_snapshot(self, tickers: Optional[List[str]] = None) -> Dict:
        """
        Busca cotações de um conjunto de ativos.

        Args:
            tickers: Lista de tickers. Se None, usa DEFAULT_ASSETS.

        Returns:
            Dict indexado por ticker com dados de preço.
        """
        if not YFINANCE_AVAILABLE:
            return {"error": "yfinance não instalado", "quotes": {}}

        target = tickers or list(DEFAULT_ASSETS.keys())
        quotes = {}

        for ticker in target:
            quotes[ticker] = self.get_quote(ticker)

        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "quotes": quotes,
        }

    def format_market_message(self, snapshot: Optional[Dict] = None) -> str:
        """
        Formata cotações em mensagem legível para Telegram.

        Returns:
            String formatada com emojis e variações.
        """
        if snapshot is None:
            snapshot = self.get_market_snapshot()

        if "error" in snapshot:
            return f"❌ Mercado indisponível: {snapshot['error']}"

        ts = snapshot.get("timestamp", "")
        try:
            dt = datetime.fromisoformat(ts)
            ts_fmt = dt.strftime("%d/%m %H:%M UTC")
        except Exception:
            ts_fmt = ts

        lines = [f"📊 *Mercado em Tempo Real* — {ts_fmt}", ""]

        for ticker, meta in DEFAULT_ASSETS.items():
            quote = snapshot.get("quotes", {}).get(ticker, {})
            if "error" in quote or "price" not in quote:
                lines.append(f"{meta['emoji']} {meta['label']}: indisponível")
                continue

            price = quote["price"]
            chg = quote.get("change_pct")
            prefix = meta["prefix"]

            if chg is not None:
                arrow = "▲" if chg >= 0 else "▼"
                sign = "+" if chg >= 0 else ""
                chg_str = f"  {arrow} {sign}{chg:.2f}%"
            else:
                chg_str = ""

            # Formatação do preço
            if price >= 1000:
                price_str = f"{price:,.0f}".replace(",", ".")
            elif price >= 10:
                price_str = f"{price:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
            else:
                price_str = f"{price:.4f}"

            if prefix:
                lines.append(f"{meta['emoji']} {meta['label']}: {prefix} {price_str}{chg_str}")
            else:
                lines.append(f"{meta['emoji']} {meta['label']}: {price_str}{chg_str}")

        return "\n".join(lines)

    def format_ticker_message(self, ticker: str) -> str:
        """Formata mensagem de cotação de um ticker específico."""
        quote = self.get_quote(ticker)

        if "error" in quote:
            return f"❌ Não encontrei dados para `{ticker}`: {quote['error']}"

        price = quote["price"]
        chg = quote.get("change_pct")
        meta = DEFAULT_ASSETS.get(ticker, {})
        label = meta.get("label", ticker)
        emoji = meta.get("emoji", "📌")
        prefix = meta.get("prefix", "")

        chg_str = ""
        if chg is not None:
            arrow = "▲" if chg >= 0 else "▼"
            sign = "+" if chg >= 0 else ""
            chg_str = f" ({arrow} {sign}{chg:.2f}%)"

        price_str = f"{price:,.4f}" if price < 10 else f"{price:,.2f}"

        lines = [
            f"{emoji} *{label}* ({ticker})",
            f"Preço: {prefix} {price_str}{chg_str}",
            f"Horário: {quote.get('timestamp', '-')[:19].replace('T', ' ')} UTC",
        ]
        return "\n".join(lines)
