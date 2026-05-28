from __future__ import annotations

import logging
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

import pandas as pd
import requests

from config import FRED_API_KEY, REQUEST_TIMEOUT, WORLD_BANK_API_BASE

logger = logging.getLogger(__name__)


def _get_pyplot():
    """Carrega matplotlib em modo headless para evitar erros de tkinter no bot."""
    import matplotlib

    matplotlib.use("Agg", force=True)
    import matplotlib.pyplot as plt

    return plt


@dataclass
class ChartArtifact:
    title: str
    path: Path
    caption: str
    status_lines: List[str]


FRED_SERIES = {
    "fed_policy": {
        "title": "EUA: juros, inflacao e desemprego",
        "series": {
            "FEDFUNDS": "Fed funds (%)",
            "CPILFESL_PC1": "Core CPI YoY (%)",
            "UNRATE": "Desemprego (%)",
        },
    },
    "yield_curve": {
        "title": "EUA: curva curta vs longa",
        "series": {
            "DGS2": "Treasury 2 anos (%)",
            "DGS10": "Treasury 10 anos (%)",
        },
    },
    "commodities": {
        "title": "Commodities macro",
        "series": {
            "DCOILWTICO": "Petroleo WTI (US$/barril)",
            "PCOPPUSDM": "Cobre (US$/mt)",
        },
    },
}

WORLD_BANK_COUNTRIES = ["US", "CN", "DE", "JP", "GB", "BR", "IN", "MX"]
WORLD_BANK_INDICATORS = {
    "growth": ("NY.GDP.MKTP.KD.ZG", "Crescimento do PIB real (%)"),
    "inflation": ("FP.CPI.TOTL.ZG", "Inflacao ao consumidor (%)"),
    "debt": ("GC.DOD.TOTL.GD.ZS", "Divida publica bruta (% do PIB)"),
}


def generate_global_macro_charts(base_dir: Path, years_back: int = 8) -> List[ChartArtifact]:
    """Gera graficos macro globais em PNG usando fontes gratuitas."""
    output_dir = base_dir / "data" / "charts" / "global_macro"
    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: List[ChartArtifact] = []

    for slug, config in FRED_SERIES.items():
        frames = _load_fred_series(config["series"].keys(), years_back=years_back)
        if frames:
            artifact = _plot_time_series(
                frames=frames,
                labels=config["series"],
                title=config["title"],
                output_path=output_dir / f"{slug}.png",
                source="FRED",
            )
            artifacts.append(artifact)

    wb = _load_world_bank_snapshot()
    for slug, (_, label) in WORLD_BANK_INDICATORS.items():
        frame = wb.get(slug)
        if frame is None or frame.empty:
            continue
        artifact = _plot_country_bar(
            frame=frame,
            value_label=label,
            title=f"Global: {label}",
            output_path=output_dir / f"world_bank_{slug}.png",
        )
        artifacts.append(artifact)

    return artifacts


def build_global_macro_visual_report(base_dir: Path, force_send_all: bool = False) -> Dict:
    artifacts = generate_global_macro_charts(base_dir)
    update_state = _detect_chart_updates(base_dir, artifacts)
    if force_send_all:
        artifacts_to_send = artifacts
    else:
        artifacts_to_send = [
            artifact
            for artifact in artifacts
            if artifact.title in update_state["updated_titles"] or artifact.title in update_state["relevant_titles"]
        ]
    data_status = _format_data_status(artifacts)
    market_context = _get_market_context()
    news_context = _get_news_context()
    update_context = _format_update_context(update_state)
    analysis = _build_macro_analysis(
        data_status=f"{update_context}\n\n{data_status}",
        market_context=market_context,
        news_context=news_context,
    )

    photos = [{"path": str(item.path), "caption": item.caption} for item in artifacts_to_send]
    _save_chart_state(base_dir, artifacts)
    return {
        "text": analysis,
        "photos": photos,
        "artifacts": artifacts,
        "data_status": data_status,
        "updates": update_state,
    }


def _load_fred_series(series_ids: Iterable[str], years_back: int) -> Dict[str, pd.DataFrame]:
    start_year = datetime.now(timezone.utc).year - years_back
    frames: Dict[str, pd.DataFrame] = {}

    for series_id in series_ids:
        frame = _load_fred_series_csv(series_id)
        if frame.empty and not series_id.endswith("_PC1"):
            api_frame = _load_fred_series_api(series_id, start_year)
            frame = api_frame if api_frame is not None else pd.DataFrame()
        if frame.empty:
            continue
        frame = frame[frame["date"].dt.year >= start_year].copy()
        if not frame.empty:
            frames[series_id] = frame

    return frames


def _load_fred_series_api(series_id: str, start_year: int) -> Optional[pd.DataFrame]:
    if not FRED_API_KEY or FRED_API_KEY == "seu_fred_api_key_aqui":
        return None

    url = "https://api.stlouisfed.org/fred/series/observations"
    params = {
        "series_id": series_id,
        "api_key": FRED_API_KEY,
        "file_type": "json",
        "observation_start": f"{start_year}-01-01",
    }

    try:
        response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        observations = response.json().get("observations", [])
        frame = pd.DataFrame(observations)
        if frame.empty:
            return frame
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        return frame.dropna(subset=["value"]).sort_values("date")
    except Exception as exc:
        logger.warning("Falha ao carregar FRED API %s: %s", series_id, exc)
        return None


def _load_fred_series_csv(series_id: str) -> pd.DataFrame:
    url = "https://fred.stlouisfed.org/graph/fredgraph.csv"
    try:
        frame = pd.read_csv(f"{url}?id={series_id}")
        if frame.empty or series_id not in frame.columns:
            return pd.DataFrame()
        frame = frame.rename(columns={"observation_date": "date", series_id: "value"})
        frame["date"] = pd.to_datetime(frame["date"])
        frame["value"] = pd.to_numeric(frame["value"], errors="coerce")
        return frame.dropna(subset=["value"]).sort_values("date")
    except Exception as exc:
        logger.warning("Falha ao carregar FRED CSV %s: %s", series_id, exc)
        return pd.DataFrame()


def _load_world_bank_snapshot() -> Dict[str, pd.DataFrame]:
    output: Dict[str, pd.DataFrame] = {}
    country_path = ";".join(WORLD_BANK_COUNTRIES)

    for slug, (indicator, _) in WORLD_BANK_INDICATORS.items():
        url = f"{WORLD_BANK_API_BASE}/country/{country_path}/indicator/{indicator}"
        params = {"format": "json", "per_page": 200, "mrnev": 1}

        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()
            rows = _parse_world_bank_rows(data)
            output[slug] = pd.DataFrame(rows)
        except Exception as exc:
            logger.warning("Falha ao carregar World Bank %s: %s", indicator, exc)
            output[slug] = _load_world_bank_indicator_by_country(indicator)

    return output


def _load_world_bank_indicator_by_country(indicator: str) -> pd.DataFrame:
    rows = []
    for country in WORLD_BANK_COUNTRIES:
        url = f"{WORLD_BANK_API_BASE}/country/{country}/indicator/{indicator}"
        params = {"format": "json", "per_page": 20, "mrnev": 1}
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            rows.extend(_parse_world_bank_rows(response.json()))
        except Exception as exc:
            logger.warning("Falha World Bank %s/%s: %s", indicator, country, exc)
    return pd.DataFrame(rows)


def _parse_world_bank_rows(data) -> List[Dict]:
    rows = []
    if isinstance(data, list) and len(data) > 1:
        for item in data[1]:
            value = item.get("value")
            country = item.get("country", {}).get("value")
            year = item.get("date")
            if value is None or not country:
                continue
            rows.append({"country": country, "year": int(year), "value": float(value)})
    return rows


def _plot_time_series(
    frames: Dict[str, pd.DataFrame],
    labels: Dict[str, str],
    title: str,
    output_path: Path,
    source: str,
) -> ChartArtifact:
    plt = _get_pyplot()

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(12, 6.5))

    for series_id, frame in frames.items():
        ax.plot(frame["date"], frame["value"], linewidth=2.2, label=labels.get(series_id, series_id))

    ax.set_title(title, fontsize=16, fontweight="bold", loc="left")
    ax.set_xlabel("")
    ax.set_ylabel("")
    ax.legend(loc="best", frameon=True)
    ax.grid(alpha=0.28)
    _stamp_source(fig, source)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)

    status_lines = []
    for series_id, frame in frames.items():
        latest = frame.sort_values("date").iloc[-1]
        value = _format_value(latest["value"])
        date = latest["date"].strftime("%Y-%m-%d")
        status_lines.append(f"{labels.get(series_id, series_id)}: liberado ate {date}, ultimo valor {value}")

    return ChartArtifact(
        title=title,
        path=output_path,
        caption=f"{title}\nFonte: {source}",
        status_lines=status_lines,
    )


def _plot_country_bar(
    frame: pd.DataFrame,
    value_label: str,
    title: str,
    output_path: Path,
) -> ChartArtifact:
    plt = _get_pyplot()

    frame = frame.sort_values("value", ascending=False)
    year = int(frame["year"].max()) if not frame.empty else "-"

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(12, 6.5))
    colors = ["#0F766E" if value >= 0 else "#B91C1C" for value in frame["value"]]
    ax.bar(frame["country"], frame["value"], color=colors)
    ax.axhline(0, color="#333333", linewidth=1)
    ax.set_title(f"{title} - ultimo dado disponivel", fontsize=16, fontweight="bold", loc="left")
    ax.set_ylabel(value_label)
    ax.tick_params(axis="x", rotation=30)
    ax.grid(axis="y", alpha=0.28)
    _stamp_source(fig, f"World Bank, {year}")
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(output_path, dpi=160)
    plt.close(fig)

    latest_rows = frame.sort_values("value", ascending=False).head(3)
    status_lines = [f"{value_label}: liberado ate {year} no World Bank"]
    for _, row in latest_rows.iterrows():
        status_lines.append(f"{row['country']}: {_format_value(row['value'])}")

    return ChartArtifact(
        title=title,
        path=output_path,
        caption=f"{title}\nFonte: World Bank, {year}",
        status_lines=status_lines,
    )


def _stamp_source(fig, source: str) -> None:
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    fig.text(0.01, 0.01, f"Fonte: {source} | Gerado em {generated_at}", fontsize=8, color="#555555")


def _format_data_status(artifacts: List[ChartArtifact]) -> str:
    if not artifacts:
        return "Nenhum dado macro foi liberado/baixado nesta rodada."

    lines = ["Dados verificados e disponiveis:"]
    for artifact in artifacts:
        lines.append(f"- {artifact.title}")
        for status in artifact.status_lines[:4]:
            lines.append(f"  - {status}")
    return "\n".join(lines)


def _state_path(base_dir: Path) -> Path:
    return base_dir / "data" / "processed" / "global_macro_visual_state.json"


def _chart_signature(artifact: ChartArtifact) -> List[str]:
    return sorted(artifact.status_lines)


def _load_chart_state(base_dir: Path) -> Dict:
    path = _state_path(base_dir)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("Falha ao ler estado dos graficos: %s", exc)
        return {}


def _save_chart_state(base_dir: Path, artifacts: List[ChartArtifact]) -> None:
    path = _state_path(base_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "charts": {
            artifact.title: {
                "signature": _chart_signature(artifact),
                "path": str(artifact.path),
            }
            for artifact in artifacts
        },
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _detect_chart_updates(base_dir: Path, artifacts: List[ChartArtifact]) -> Dict:
    state = _load_chart_state(base_dir)
    previous = state.get("charts", {}) if state else {}
    updated_titles = []
    unchanged_titles = []

    for artifact in artifacts:
        current_signature = _chart_signature(artifact)
        previous_signature = previous.get(artifact.title, {}).get("signature")
        if previous_signature != current_signature:
            updated_titles.append(artifact.title)
        else:
            unchanged_titles.append(artifact.title)

    relevant_titles = _infer_relevant_unchanged_charts(unchanged_titles)
    return {
        "has_previous_state": bool(previous),
        "updated_titles": updated_titles,
        "unchanged_titles": unchanged_titles,
        "relevant_titles": relevant_titles,
    }


def _infer_relevant_unchanged_charts(unchanged_titles: List[str]) -> List[str]:
    """
    Mantem graficos sem dado novo apenas quando o mercado mexeu o suficiente
    para justificar usar o grafico como contexto da tese.
    """
    if not unchanged_titles:
        return []

    try:
        from apis.market_api import MarketDataClient

        snapshot = MarketDataClient().get_market_snapshot()
        quotes = snapshot.get("quotes", {})
        relevant = set()

        tnx = quotes.get("^TNX", {}).get("change_pct")
        oil = quotes.get("CL=F", {}).get("change_pct")
        brl = quotes.get("USDBRL=X", {}).get("change_pct")
        spx = quotes.get("^GSPC", {}).get("change_pct")

        if tnx is not None and abs(tnx) >= 2.0:
            relevant.update(["EUA: curva curta vs longa", "EUA: juros, inflacao e desemprego"])
        if oil is not None and abs(oil) >= 2.0:
            relevant.add("Commodities macro")
        if brl is not None and abs(brl) >= 1.0:
            relevant.update(["EUA: curva curta vs longa", "Commodities macro"])
        if spx is not None and abs(spx) >= 1.5:
            relevant.add("Global: Crescimento do PIB real (%)")

        return [title for title in unchanged_titles if title in relevant]
    except Exception as exc:
        logger.warning("Falha ao inferir graficos relevantes sem dado novo: %s", exc)
        return []


def _format_update_context(update_state: Dict) -> str:
    updated = update_state.get("updated_titles", [])
    relevant = update_state.get("relevant_titles", [])

    if not update_state.get("has_previous_state"):
        return "Controle de atualizacao: primeira rodada registrada; estes graficos viram a linha de base."

    lines = ["Controle de atualizacao:"]
    if updated:
        lines.append("Dados novos detectados:")
        lines.extend(f"- {title}" for title in updated)
    else:
        lines.append("Nenhum dado macro novo detectado frente a ultima rodada.")

    if relevant:
        lines.append("Graficos sem dado novo, mas relevantes para explicar o movimento atual:")
        lines.extend(f"- {title}" for title in relevant)
    return "\n".join(lines)


def _get_market_context() -> str:
    try:
        from apis.market_api import DEFAULT_ASSETS, MarketDataClient

        client = MarketDataClient()
        snapshot = client.get_market_snapshot()
        if snapshot.get("error"):
            return f"Mercado indisponivel: {snapshot['error']}"

        lines = ["Mercados observados agora:"]
        for ticker, meta in DEFAULT_ASSETS.items():
            quote = snapshot.get("quotes", {}).get(ticker, {})
            if "price" not in quote:
                continue
            change = quote.get("change_pct")
            change_text = f" ({change:+.2f}%)" if change is not None else ""
            lines.append(f"- {meta['label']}: {quote['price']}{change_text}")
        return "\n".join(lines)
    except Exception as exc:
        logger.warning("Falha ao coletar mercado para analise: %s", exc)
        return "Mercado indisponivel nesta rodada."


def _get_news_context() -> str:
    try:
        from apis.news_api import NewsCollector

        return NewsCollector().format_news_for_context(limit=6)
    except Exception as exc:
        logger.warning("Falha ao coletar noticias para analise: %s", exc)
        return "Noticias indisponiveis nesta rodada."


def _build_macro_analysis(data_status: str, market_context: str, news_context: str) -> str:
    llm_text = _build_llm_analysis(data_status, market_context, news_context)
    if llm_text:
        return llm_text

    return _build_rule_based_analysis(data_status, market_context, news_context)


def _build_llm_analysis(data_status: str, market_context: str, news_context: str) -> str:
    try:
        from utils.llm_client import MacroLLMClient

        llm = MacroLLMClient()
        if not llm.is_available():
            return ""

        question = (
            "Monte um relatorio curto para Telegram com: dados macro ja liberados, "
            "leitura dos graficos, analise do momento macro atual, impacto no Brasil "
            "e alertas para acompanhar. Seja claro para uma pessoa leiga, mas pense "
            "como macroeconomista senior. Se o controle de atualizacao disser que nao "
            "ha dado novo, deixe isso claro e nao trate grafico antigo como novidade. "
            "Nao invente numeros."
        )
        return llm.answer_question(
            question=question,
            sources=[],
            conversation=[],
            market_context=f"{data_status}\n\n{market_context}",
            news_context=news_context,
        )
    except Exception as exc:
        logger.warning("Falha ao gerar analise via LLM: %s", exc)
        return ""


def _build_rule_based_analysis(data_status: str, market_context: str, news_context: str) -> str:
    now = datetime.now(timezone.utc).strftime("%d/%m/%Y %H:%M UTC")
    lines = [
        f"Relatorio macro visual - {now}",
        "",
        "1. Dados liberados",
        data_status,
        "",
        "2. Leitura macro",
        "- O painel combina juros, inflacao, emprego, curva de juros, commodities, crescimento, inflacao global e divida publica.",
        "- Se juros longos sobem junto com commodities, o mercado costuma precificar mais inflacao ou premio de risco.",
        "- Se crescimento desacelera enquanto divida segue alta, bancos centrais e governos ficam com menos espaco de manobra.",
        "",
        "3. Mercado agora",
        market_context,
        "",
        "4. Noticias recentes usadas como contexto",
        news_context[:1200],
        "",
        "5. Impacto no Brasil",
        "- Juros globais altos tendem a pressionar moedas emergentes, inclusive o real.",
        "- Commodities fortes podem ajudar exportadores, mas tambem podem atrapalhar inflacao.",
        "- Se o risco fiscal global/local aumenta, a curva de juros brasileira tende a exigir premio maior.",
        "",
        "Vou enviar os graficos em seguida.",
    ]
    return "\n".join(lines)


def _format_value(value) -> str:
    try:
        number = float(value)
    except Exception:
        return str(value)
    if abs(number) >= 1000:
        return f"{number:,.0f}".replace(",", ".")
    return f"{number:.2f}"
