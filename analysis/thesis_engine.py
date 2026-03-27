"""
Motor simples para montar teses macro com evidencias e citacoes.
"""

from datetime import datetime
from typing import Dict, List


class ThesisEngine:
    """Organiza uma tese macroeconomica a partir de documentos e fontes."""

    def build_thesis(self, topic: str, memory_results: List[Dict], source_results: List[Dict]) -> Dict:
        evidence = self._build_evidence(memory_results, source_results)
        thesis_text = self._build_thesis_text(topic, evidence)
        risks = self._build_risks(topic, evidence)
        citations = self._build_citations(source_results, memory_results)

        return {
            "topic": topic,
            "timestamp": datetime.utcnow().isoformat(),
            "thesis": thesis_text,
            "evidence": evidence,
            "risks": risks,
            "citations": citations,
            "source_count": len(source_results),
            "memory_count": len(memory_results),
        }

    def _build_evidence(self, memory_results: List[Dict], source_results: List[Dict]) -> List[str]:
        evidence: List[str] = []

        for result in memory_results[:3]:
            meta = result.get("metadata", {}) or {}
            focus = meta.get("focus_area") or meta.get("title") or "Memoria"
            evidence.append(
                f"Memoria tecnica relevante em {focus.lower()} reforca o contexto do tema."
            )

        for result in source_results[:3]:
            meta = result.get("metadata", {}) or {}
            source_name = meta.get("source_name") or meta.get("api") or "fonte"
            title = meta.get("title") or "documento sem titulo"
            evidence.append(
                f"Fonte recente de {source_name} destaca: {title}."
            )

        if not evidence:
            evidence.append(
                "Ainda nao ha evidencias suficientes na memoria para sustentar uma tese robusta."
            )

        return evidence

    def _build_thesis_text(self, topic: str, evidence: List[str]) -> str:
        if not evidence:
            return (
                f"A tese para {topic} ainda esta fraca porque faltam dados e fontes recentes."
            )

        if len(evidence) >= 3:
            return (
                f"Tese para {topic}: os sinais tecnicos e as fontes recentes apontam para um "
                "cenario que merece monitoramento ativo, com maior confianca do que uma leitura isolada."
            )

        return (
            f"Tese para {topic}: ja existe uma direcao analitica inicial, mas a confianca ainda "
            "depende de mais confirmacoes."
        )

    def _build_risks(self, topic: str, evidence: List[str]) -> List[str]:
        risks = [
            "Dados macro podem ser revisados e alterar a leitura.",
            "Sinais de mercado e textos narrativos podem divergir no curto prazo.",
        ]

        if len(evidence) < 3:
            risks.append(
                f"O tema {topic} ainda tem cobertura insuficiente em fontes recentes."
            )

        return risks

    def _build_citations(self, source_results: List[Dict], memory_results: List[Dict]) -> List[Dict]:
        citations: List[Dict] = []

        for result in source_results[:5]:
            meta = result.get("metadata", {}) or {}
            citations.append(
                {
                    "id": result.get("id"),
                    "title": meta.get("title", "Sem titulo"),
                    "source": meta.get("source_name", meta.get("api", "fonte")),
                    "url": meta.get("url", ""),
                    "published_at": meta.get("published_at", meta.get("timestamp", "")),
                    "type": meta.get("type", "source_article"),
                }
            )

        if citations:
            return citations

        for result in memory_results[:3]:
            meta = result.get("metadata", {}) or {}
            citations.append(
                {
                    "id": result.get("id"),
                    "title": meta.get("title", meta.get("focus_area", "Memoria tecnica")),
                    "source": meta.get("api", "memory"),
                    "url": "",
                    "published_at": meta.get("timestamp", ""),
                    "type": meta.get("type", "memory"),
                }
            )

        return citations
