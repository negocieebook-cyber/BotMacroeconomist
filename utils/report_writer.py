"""
Geracao de relatorios em texto com tom de analista macro.
"""

from datetime import datetime
import os
from typing import Dict, List, Optional, Tuple

import pandas as pd

from .theory_library import select_relevant_theory_sections


def _safe_float(value) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def _extract_nested_value(data: Dict, *keys) -> Optional[float]:
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return None
        current = current[key]

    if isinstance(current, dict) and "value" in current:
        return _safe_float(current.get("value"))

    return _safe_float(current)


def _describe_value(value) -> str:
    if isinstance(value, pd.DataFrame):
        if value.empty:
            return "Sem dados retornados."

        columns = ", ".join(map(str, value.columns[:6]))
        return (
            f"DataFrame com {len(value)} linha(s) e {len(value.columns)} coluna(s). "
            f"Colunas principais: {columns}."
        )

    if isinstance(value, dict):
        if not value:
            return "Dicionario vazio."

        keys = list(value.keys())[:8]
        return f"Dicionario com chaves: {', '.join(map(str, keys))}."

    if isinstance(value, list):
        return f"Lista com {len(value)} item(ns)."

    if value is None:
        return "Sem valor."

    text = str(value)
    if len(text) > 220:
        text = text[:220] + "..."
    return text


def _top_country_snapshot(df: pd.DataFrame, label: str, top_n: int = 3) -> List[str]:
    if not isinstance(df, pd.DataFrame) or df.empty or "value" not in df.columns:
        return [f"- {label}: sem dados suficientes para ranking."]

    working = df.copy()
    sort_columns = [col for col in ["year", "date"] if col in working.columns]
    if sort_columns:
        working = working.sort_values(sort_columns)

    group_col = "country_name" if "country_name" in working.columns else None
    if group_col:
        latest = working.groupby(group_col, as_index=False).tail(1)
    else:
        latest = working.tail(top_n)

    latest = latest.dropna(subset=["value"]).sort_values("value", ascending=False).head(top_n)
    if latest.empty:
        return [f"- {label}: sem observacoes validas."]

    lines = [f"- {label}:"]
    for _, row in latest.iterrows():
        country = row.get("country_name") or row.get("country_code") or "N/A"
        year = row.get("year", row.get("date", "atual"))
        value = row.get("value")
        lines.append(f"  {country}: {value:,.2f} ({year})")
    return lines


def _inflation_view(collected_blocks: Dict[str, Dict]) -> Tuple[List[str], List[str]]:
    analysis = []
    observations = []

    monday = collected_blocks.get("inflacao_politica", {})
    cpi = _extract_nested_value(monday, "fred", "CPI")
    pce = _extract_nested_value(monday, "fred", "PCE")
    fed_funds = _extract_nested_value(monday, "fed_policy", "FED_FUNDS")
    dgs10 = _extract_nested_value(monday, "fed_policy", "DGS10")

    if cpi is not None:
        observations.append(f"- CPI mais recente: {cpi:.2f}")
    if pce is not None:
        observations.append(f"- PCE mais recente: {pce:.2f}")
    if fed_funds is not None:
        observations.append(f"- Fed Funds: {fed_funds:.2f}")
    if dgs10 is not None:
        observations.append(f"- Treasury 10 anos: {dgs10:.2f}")

    if fed_funds is not None and fed_funds >= 4.5:
        analysis.append(
            "A politica monetaria parece claramente restritiva, o que sugere foco do Fed em conter inflacao."
        )
    elif fed_funds is not None and fed_funds >= 2.0:
        analysis.append(
            "Os juros ainda indicam aperto moderado, sem um sinal claro de politica frouxa."
        )
    elif fed_funds is not None:
        analysis.append(
            "Os juros estao em nivel relativamente baixo, o que tende a aliviar condicoes financeiras."
        )

    if cpi is not None and pce is not None:
        if cpi > pce:
            analysis.append(
                "O CPI acima do PCE pode indicar pressao mais visivel para o consumidor final do que para a medida preferida do Fed."
            )
        elif pce > cpi:
            analysis.append(
                "O PCE acima do CPI sugere que a inflacao subjacente merece atencao adicional."
            )

    if not analysis:
        analysis.append("Ainda nao ha informacao suficiente para uma leitura mais firme de inflacao e juros.")

    return analysis, observations


def _growth_view(collected_blocks: Dict[str, Dict]) -> Tuple[List[str], List[str]]:
    analysis = []
    observations = []

    growth = collected_blocks.get("crescimento", {})
    gdp_growth = growth.get("gdp_growth")
    gdp_nominal = growth.get("gdp_nominal")
    real_gdp = _extract_nested_value(growth, "gdp_forecast", "REAL_GDP")

    if real_gdp is not None:
        observations.append(f"- GDP real dos EUA (ultima leitura): {real_gdp:,.2f}")

    if isinstance(gdp_growth, pd.DataFrame):
        observations.extend(_top_country_snapshot(gdp_growth, "Maiores taxas recentes de crescimento do PIB"))
        if not gdp_growth.empty and "value" in gdp_growth.columns:
            median_growth = _safe_float(gdp_growth["value"].median())
            if median_growth is not None:
                observations.append(f"- Mediana de crescimento global capturado: {median_growth:.2f}%")
                if median_growth > 3:
                    analysis.append(
                        "A mediana de crescimento sugere ambiente global relativamente resiliente."
                    )
                elif median_growth > 1:
                    analysis.append(
                        "O crescimento agregado parece positivo, mas sem grande folga."
                    )
                else:
                    analysis.append(
                        "A leitura de crescimento sugere economia global mais fraca ou heterogenea."
                    )

    if isinstance(gdp_nominal, pd.DataFrame):
        observations.extend(_top_country_snapshot(gdp_nominal, "Maiores PIBs nominais recentes"))

    if not analysis:
        analysis.append("Ainda nao ha base suficiente para uma leitura mais forte de crescimento.")

    return analysis, observations


def _market_takeaways(collected_blocks: Dict[str, Dict], status: Dict) -> List[str]:
    takeaways = []
    inflation_analysis, _ = _inflation_view(collected_blocks)
    growth_analysis, _ = _growth_view(collected_blocks)

    if inflation_analysis:
        takeaways.append(f"Inflacao/Juros: {inflation_analysis[0]}")
    if growth_analysis:
        takeaways.append(f"Crescimento: {growth_analysis[0]}")

    memory_docs = status.get("memory", {}).get("total_documents", 0)
    if memory_docs >= 10:
        takeaways.append(
            "Base historica ja comeca a ficar util para comparacoes mais consistentes."
        )
    else:
        takeaways.append(
            "A memoria ainda esta no inicio; quanto mais rodadas, melhor a capacidade de comparar ciclos."
        )

    return takeaways


def build_telegram_market_brief(collected_blocks: Dict[str, Dict], status: Dict) -> str:
    inflation_analysis, inflation_obs = _inflation_view(collected_blocks)
    growth_analysis, growth_obs = _growth_view(collected_blocks)
    takeaways = _market_takeaways(collected_blocks, status)
    memory_docs = status.get("memory", {}).get("total_documents", 0)
    task_stats = status.get("task_stats", {})

    lines = [
        "Resumo macro do bot",
        "",
        "O que estou vendo no mercado:",
    ]

    for item in takeaways:
        lines.append(f"- {item}")

    lines.extend(
        [
            "",
            "Como estou pensando:",
        ]
    )

    if inflation_analysis:
        lines.append(f"- Inflacao/Juros: {inflation_analysis[0]}")
        if len(inflation_analysis) > 1:
            lines.append(f"- Leitura complementar: {inflation_analysis[1]}")

    if growth_analysis:
        lines.append(f"- Crescimento: {growth_analysis[0]}")

    lines.extend(
        [
            "",
            "O que estou aprendendo:",
            (
                "- Estou acumulando historico para comparar as novas leituras "
                "com coletas anteriores e reduzir conclusoes baseadas em um dado isolado."
            ),
            (
                "- Estou conectando os dados com a biblioteca teorica para interpretar "
                "inflacao, juros e crescimento com mais criterio macroeconomico."
            ),
            "",
            "Pontos observados agora:",
        ]
    )

    for item in inflation_obs[:4]:
        lines.append(item)
    for item in growth_obs[:4]:
        lines.append(item)

    lines.extend(
        [
            "",
            "Saude do agente:",
            f"- Documentos na memoria: {memory_docs}",
            f"- Execucoes: {task_stats.get('total_executions', 0)}",
            f"- Sucessos: {task_stats.get('successful', 0)}",
            f"- Falhas: {task_stats.get('failed', 0)}",
        ]
    )

    return "\n".join(lines)


def build_daily_learning_digest(snapshot: Dict) -> str:
    """Monta um resumo diario do que entrou na memoria do agente."""
    date = snapshot.get("date", "-")
    documents = snapshot.get("documents", [])
    memory = snapshot.get("memory", {})

    lines = [
        f"Aprendizados do dia {date}",
        f"Novos itens na memoria hoje: {len(documents)}",
        f"Documentos totais na memoria: {memory.get('total_documents', 0)}",
        "",
    ]

    if not documents:
        lines.append("Nenhum novo aprendizado foi salvo hoje.")
        return "\n".join(lines)

    for index, item in enumerate(documents, 1):
        metadata = item.get("metadata", {})
        lines.extend(
            [
                f"{index}. {metadata.get('focus_area', 'Sem foco definido')}",
                f"API: {metadata.get('api', 'desconhecida')}",
                f"Horario: {metadata.get('timestamp', '-')}",
                f"Resumo: {item.get('preview', '')}",
                "",
            ]
        )

    return "\n".join(lines).strip()


def build_market_report(collected_blocks: Dict[str, Dict], status: Dict) -> str:
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    memory = status.get("memory", {})
    task_stats = status.get("task_stats", {})
    system = status.get("system", {})

    inflation_analysis, inflation_obs = _inflation_view(collected_blocks)
    growth_analysis, growth_obs = _growth_view(collected_blocks)
    takeaways = _market_takeaways(collected_blocks, status)
    theory_sections = select_relevant_theory_sections(collected_blocks)

    lines: List[str] = [
        "RELATORIO MACROECONOMICO DO AGENTE",
        f"Gerado em: {timestamp}",
        "",
        "1. Resumo executivo",
    ]

    for takeaway in takeaways:
        lines.append(f"- {takeaway}")

    lines.extend(
        [
            "",
            "2. Leitura de inflacao e juros",
        ]
    )
    for item in inflation_analysis:
        lines.append(f"- {item}")
    if inflation_obs:
        lines.append("Dados observados:")
        lines.extend(inflation_obs)

    lines.extend(
        [
            "",
            "3. Leitura de crescimento",
        ]
    )
    for item in growth_analysis:
        lines.append(f"- {item}")
    if growth_obs:
        lines.append("Dados observados:")
        lines.extend(growth_obs)

    lines.extend(
        [
            "",
            "4. O que o agente esta aprendendo",
            (
                "O agente esta acumulando blocos de inflacao, juros, crescimento e atividade "
                "em memoria. Isso permite recuperar contexto historico e refinar a leitura do mercado ao longo do tempo."
            ),
            (
                "Quanto mais coletas forem executadas, mais facil fica separar ruido de tendencia e comparar o momento atual com leituras anteriores."
            ),
            "",
            "5. Base teorica usada",
        ]
    )

    if theory_sections:
        for section in theory_sections:
            lines.append(section)
            lines.append("")
    else:
        lines.append("Nenhuma secao teorica foi vinculada a esta coleta.")
        lines.append("")

    lines.append("6. Mapa da coleta atual")

    if not collected_blocks:
        lines.append("- Nenhuma coleta foi executada ainda.")
    else:
        for block_name, block_data in collected_blocks.items():
            lines.append(f"- Bloco {block_name}:")
            if not block_data:
                lines.append("  Nenhum dado retornado neste bloco.")
                continue
            for key, value in block_data.items():
                lines.append(f"  {key}: {_describe_value(value)}")

    lines.extend(
        [
            "",
            "7. Saude do agente",
            f"- Documentos na memoria: {memory.get('total_documents', 0)}",
            f"- Execucoes registradas: {task_stats.get('total_executions', 0)}",
            f"- Sucessos: {task_stats.get('successful', 0)}",
            f"- Falhas: {task_stats.get('failed', 0)}",
            f"- FRED pronto: {'sim' if system.get('fred_available') else 'nao'}",
            f"- IMF pronto: {'sim' if system.get('imf_available') else 'nao'}",
            f"- World Bank pronto: {'sim' if system.get('worldbank_available') else 'nao'}",
            f"- OECD pronto: {'sim' if system.get('oecd_available') else 'nao'}",
            f"- BIS pronto: {'sim' if system.get('bis_available') else 'nao'}",
            "",
            "8. Proximo passo sugerido",
            (
                "Rode o relatorio com frequencia para aumentar o historico. "
                "Depois disso, vale adicionar um resumo de trabalho, comercio e risco financeiro para fechar a visao macro."
            ),
            "",
        ]
    )

    return "\n".join(lines)


def save_report(report_text: str, directory: str = "./reports") -> str:
    directory = os.path.normpath(directory)
    os.makedirs(directory, exist_ok=True)
    filename = datetime.utcnow().strftime("market_report_%Y%m%d_%H%M%S.txt")
    path = os.path.join(directory, filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(report_text)

    return path
