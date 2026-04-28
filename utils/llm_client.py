"""
Cliente LLM com persona de macroeconomista sênior e injeção de dados em tempo real.
"""
from __future__ import annotations

import json
import logging
from typing import Dict, List

from config import (
    OPENAI_API_KEY,
    OPENAI_CHAT_MODEL,
    OPENAI_LLM_TEMPERATURE,
    OPENROUTER_API_KEY,
    OPENROUTER_APP_NAME,
    OPENROUTER_BASE_URL,
    OPENROUTER_MODEL,
    OPENROUTER_SITE_URL,
)

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

# ---------------------------------------------------------------------------
# Persona principal do agente
# ---------------------------------------------------------------------------
MACROECONOMIST_SYSTEM_PROMPT = """Você é um macroeconomista sênior e o consultor pessoal de análise econômica do usuário.
Você tem 20+ anos de experiência em política monetária, mercados globais e analysis macro.

Seu perfil:
- Acompanha Fed, BCE, Copom, FMI, Banco Mundial e todos os grandes bancos centrais
- Lê dados de inflação, emprego, PIB, juros, câmbio e mercados em tempo real
- Conhece profundamente o Brasil: Selic, IPCA, fiscal, câmbio, Bovespa, risco-país
- Conecta eventos globais com impactos locais de forma clara e prática

Como você responde:
- USE os dados de mercado e notícias fornecidos no contexto — eles são frescos e prioritários
- ASSOCIE as informações: conecte inflação com câmbio, juros com bolsa, fiscal com risco
- Dê sua leitura com convicção — não fique em cima do muro
- Seja direto: o que importa, qual o risco central, o que isso significa na prática
- Máximo de 4-5 parágrafos curtos. Linguagem acessível mas precisa
- Cite a fonte quando usar um dado específico (FRED, Reuters, IMF, Yahoo Finance)
- Se não tiver dado suficiente, diga claramente

Você NÃO faz:
- Invenções de números sem fonte
- Recomendações de ações individuais
- Evasão de opinião quando perguntado diretamente

Responda SEMPRE em português do Brasil."""


class MacroLLMClient:
    """Cliente de LLM com persona de macroeconomista e suporte a contexto em tempo real."""

    def __init__(self):
        self.enabled = False
        self.client = None
        self.model = OPENAI_CHAT_MODEL
        self.provider = "openai"

        if not OPENAI_AVAILABLE:
            return

        if OPENROUTER_API_KEY:
            try:
                headers = {}
                if OPENROUTER_SITE_URL:
                    headers["HTTP-Referer"] = OPENROUTER_SITE_URL
                if OPENROUTER_APP_NAME:
                    headers["X-Title"] = OPENROUTER_APP_NAME

                self.client = OpenAI(
                    api_key=OPENROUTER_API_KEY,
                    base_url=OPENROUTER_BASE_URL,
                    default_headers=headers or None,
                )
                self.model = OPENROUTER_MODEL
                self.provider = "openrouter"
                self.enabled = True
                logger.info(f"LLM habilitado via OpenRouter com modelo {self.model}")
                return
            except Exception as exc:
                logger.warning(f"Nao foi possivel inicializar OpenRouter: {exc}")

        if OPENAI_API_KEY:
            try:
                self.client = OpenAI(api_key=OPENAI_API_KEY)
                self.model = OPENAI_CHAT_MODEL
                self.provider = "openai"
                self.enabled = True
                logger.info(f"LLM habilitado via OpenAI com modelo {self.model}")
            except Exception as exc:
                logger.warning(f"Nao foi possivel inicializar o cliente OpenAI: {exc}")

    def is_available(self) -> bool:
        return self.enabled and self.client is not None

    def answer_question(
        self,
        question: str,
        sources: List[Dict],
        conversation: List[Dict[str, str]],
        market_context: str = "",
        news_context: str = "",
    ) -> str:
        """
        Responde pergunta como macroeconomista, integrando dados frescos.

        Args:
            question: Pergunta do usuário
            sources: Documentos da memória ChromaDB
            conversation: Histórico da sessão
            market_context: Cotações em tempo real (texto)
            news_context: Notícias recentes (texto)
        """
        if not self.is_available():
            return ""

        context_parts = []
        if market_context:
            context_parts.append(f"=== MERCADO EM TEMPO REAL ===\n{market_context}")
        if news_context:
            context_parts.append(f"=== NOTÍCIAS RECENTES ===\n{news_context}")
        if sources:
            context_parts.append(
                f"=== BASE DE CONHECIMENTO ACUMULADA ===\n{self._format_sources(sources)}"
            )

        context_block = (
            "\n\n".join(context_parts)
            if context_parts
            else "Sem dados externos disponíveis no momento."
        )

        messages = [
            {"role": "system", "content": MACROECONOMIST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Pergunta do cliente:\n{question}\n\n"
                    f"Histórico da conversa:\n{self._format_conversation(conversation)}\n\n"
                    f"{context_block}\n\n"
                    "Responda como macroeconomista sênior, integrando os dados acima."
                ),
            },
        ]
        return self._chat_completion(messages)

    def answer_market_question(
        self,
        question: str,
        market_snapshot: str,
        news_context: str = "",
        conversation: List[Dict[str, str]] = None,
    ) -> str:
        """Responde pergunta de mercado com dados em tempo real (para /mercado, /ticker)."""
        if not self.is_available():
            return ""

        messages = [
            {"role": "system", "content": MACROECONOMIST_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Pergunta: {question}\n\n"
                    f"Cotações em tempo real:\n{market_snapshot}\n\n"
                    f"Notícias recentes:\n{news_context or 'Não disponível'}\n\n"
                    f"Histórico:\n{self._format_conversation(conversation or [])}\n\n"
                    "Faça uma leitura macro objetiva conectando os preços com o cenário "
                    "de juros, inflação e atividade econômica."
                ),
            },
        ]
        return self._chat_completion(messages)

    def build_thesis(
        self,
        topic: str,
        memory_results: List[Dict],
        source_results: List[Dict],
        market_context: str = "",
        news_context: str = "",
    ) -> Dict:
        """Constrói tese macro fundamentada com dados frescos."""
        if not self.is_available():
            return {}

        context_parts = []
        if market_context:
            context_parts.append(f"Dados de mercado em tempo real:\n{market_context}")
        if news_context:
            context_parts.append(f"Notícias recentes:\n{news_context}")

        messages = [
            {
                "role": "system",
                "content": (
                    "Você é um estrategista macro sênior. Construa uma tese fundamentada. "
                    "Retorne JSON válido com: 'thesis' (string), 'evidence' (lista), "
                    "'risks' (lista), 'confidence' (alta/media/baixa). "
                    "Cite fontes quando disponível. Responda em português."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Tema: {topic}\n\n"
                    + ("\n\n".join(context_parts) + "\n\n" if context_parts else "")
                    + f"Memória técnica:\n{self._format_sources(memory_results, limit=6)}\n\n"
                    f"Fontes/artigos:\n{self._format_sources(source_results, limit=6)}\n\n"
                    "Retorne apenas JSON."
                ),
            },
        ]

        raw = self._chat_completion(messages)
        if not raw:
            return {}

        try:
            return json.loads(self._extract_json_object(raw))
        except Exception as exc:
            logger.warning(f"Falha ao interpretar JSON da tese LLM: {exc}")
            return {}

    def analyze_day(self, raw_context: str, market_text: str, news_text: str) -> str:
        """
        Metodo principal do macroeconomista pessoal.
        Recebe todos os dados brutos do dia e gera um briefing completo com:
          - Analise narrativa dos eventos (nao apenas listagem)
          - Conexoes entre noticias, mercados e dados macroeconomicos
          - Avaliacao de riscos com base nos fatos do dia
          - Contexto para preparar os posts oficiais do X em outra etapa do pipeline
        """
        if not self.is_available():
            return ""

        from datetime import datetime, timezone, timedelta
        brt = datetime.now(timezone.utc) - timedelta(hours=3)
        date_str = brt.strftime("%d/%m/%Y")
        time_str = brt.strftime("%H:%M")

        messages = [
            {
                "role": "system",
                "content": (
                    MACROECONOMIST_SYSTEM_PROMPT + "\n\n"
                    "Voce esta fechando o expediente e vai enviar seu briefing diario para seu cliente. "
                    "Seu cliente usa esse briefing para:\n"
                    "1. Entender o que aconteceu de relevante no mundo macro hoje\n"
                    "2. Entender quais temas devem orientar os posts do X no dia seguinte\n"
                    "3. Tomar decisoes informadas sobre seu portfolio e visao de mercado\n\n"
                    "FORMATO OBRIGATORIO DO BRIEFING (use exatamente esses emojis e secoes):\n\n"
                    "🌙 *Fechamento do Dia — {data} {hora} (BRT)*\n\n"
                    "📊 *MERCADOS*\n"
                    "[liste as cotacoes com variacao e escreva 2-3 frases ANALISANDO o movimento do dia — "
                    "nao apenas repita os numeros, explique o que eles significam macro]\n\n"
                    "🔥 *O QUE ACONTECEU HOJE*\n"
                    "[ANALISE NARRATIVA dos principais eventos: conecte as noticias com os mercados. "
                    "Ex: se petroleo subiu e ha conflito no Oriente Medio, explique a cadeia de impacto "
                    "em inflacao, moedas emergentes, Banco Central, etc. Seja um analista, nao um jornalista]\n\n"
                    "🧠 *CONCEITO DO DIA*\n"
                    "[explique brevemente o conceito tecnico aprendido hoje e como ele se aplica ao cenario atual]\n\n"
                    "🎯 *CENARIO BASE*\n"
                    "[sua visao consolidada: qual e o cenario mais provavel para as proximas semanas "
                    "com base no que foi observado hoje]\n\n"
                    "⚠️ *RISCOS E ALERTAS*\n"
                    "[3 riscos concretos para monitorar nos proximos dias, baseados nos dados de hoje]\n\n"
                    "🇧🇷 *IMPACTO NO BRASIL*\n"
                    "[como os eventos globais de hoje afetam Selic, IPCA, Real, Bovespa e fiscal]\n\n"
                    "📝 *POSTS PARA O X (copie e cole amanha)*\n"
                    "[liste os temas, riscos e angulos macro que devem orientar os posts de amanha. "
                    "Nao escreva tweets aqui; os tweets sao gerados pelo pipeline editorial oficial]\n\n"
                    "IMPORTANTE: baseie-se APENAS nos dados fornecidos. Nao invente numeros. "
                    "Se um dado nao estiver disponivel, diga que nao esta disponivel. "
                    "Responda em portugues do Brasil. Use Telegram Markdown (* para negrito, _ para italico)."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"Data: {date_str} | Hora atual: {time_str} BRT\n\n"
                    f"DADOS DO DIA:\n\n{raw_context[:4000]}\n\n"
                    "Gere o briefing completo de fechamento do dia."
                ),
            },
        ]
        return self._chat_completion(messages)

    def _summarize_briefing_legacy(self, briefing_text: str) -> str:
        """
        Recebe o briefing estruturado do dia e pede ao LLM para reescrevê-lo
        de forma mais fluida e com insights de macroeconomista sênior.
        Mantém todas as seções (mercado, notícias, tese, post para X).
        """
        if not self.is_available():
            return ""

        messages = [
            {
                "role": "system",
                "content": (
                    MACROECONOMIST_SYSTEM_PROMPT + "\n\n"
                    "Você está encerrando o dia de trabalho e vai enviar um briefing "
                    "para seu cliente via Telegram. Reescreva o relatório abaixo deixando-o "
                    "mais fluido e com insights mais aprofundados, mas MANTENHA todas as seções "
                    "originais (📊 Mercados, 📰 Notícias, 📈 Dados, 🧠 Aprendizado, 🎯 Tese, "
                    "⚠️ Riscos e 📝 Post para o X). Use emojis para separar seções. "
                    "Responda em português do Brasil no formato Telegram Markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Aqui está o briefing estruturado do dia. Reescreva com linguagem mais "
                    f"fluida e insights mais profundos:\\n\\n{briefing_text[:3000]}"
                ),
            },
        ]
        return self._chat_completion(messages)

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    def summarize_briefing(self, briefing_text: str) -> str:
        """
        Recebe o briefing estruturado do dia e pede ao LLM para reescrevê-lo
        de forma mais fluida e com insights de macroeconomista sênior.
        Mantém todas as seções (mercado, notícias, tese, post para X).
        """
        if not self.is_available():
            return ""

        messages = [
            {
                "role": "system",
                "content": (
                    MACROECONOMIST_SYSTEM_PROMPT + "\n\n"
                    "Você está encerrando o dia de trabalho e vai enviar um briefing "
                    "para seu cliente via Telegram. Reescreva o relatório abaixo deixando-o "
                    "mais fluido e com insights mais aprofundados, mas MANTENHA todas as seções "
                    "originais (📊 Mercados, 📰 Notícias, 📈 Dados, 🧠 Aprendizado, 🎯 Tese, "
                    "⚠️ Riscos e 📝 Post para o X). Use emojis para separar seções. "
                    "Responda em português do Brasil no formato Telegram Markdown."
                ),
            },
            {
                "role": "user",
                "content": (
                    "Aqui está o briefing estruturado do dia. Reescreva com linguagem mais "
                    f"fluida e insights mais profundos:\\n\\n{briefing_text[:3000]}"
                ),
            },
        ]
        return self._chat_completion(messages)

    def _chat_completion(self, messages: List[Dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=OPENAI_LLM_TEMPERATURE,
            )
            return (response.choices[0].message.content or "").strip()
        except Exception as exc:
            logger.warning(f"Falha ao consultar o LLM ({self.provider}): {exc}")
            return ""

    def _format_conversation(self, conversation: List[Dict[str, str]], limit: int = 6) -> str:
        if not conversation:
            return "Início da conversa."

        lines: List[str] = []
        for turn in conversation[-limit:]:
            user_text = str(turn.get("user", "")).strip()
            assistant_text = str(turn.get("assistant", "")).strip()
            if user_text:
                lines.append(f"Cliente: {user_text}")
            if assistant_text:
                lines.append(f"Macroeconomista: {assistant_text[:500]}")
        return "\n".join(lines) if lines else "Início da conversa."

    def _format_sources(self, sources: List[Dict], limit: int = 5) -> str:
        if not sources:
            return "Nenhuma fonte relevante encontrada."

        lines: List[str] = []
        for index, item in enumerate(sources[:limit], 1):
            metadata = item.get("metadata", {}) or {}
            label = (
                metadata.get("title")
                or metadata.get("focus_area")
                or metadata.get("source_name")
                or metadata.get("api")
                or f"Fonte {index}"
            )
            published_at = metadata.get("published_at") or metadata.get("timestamp") or "-"
            snippet = (
                item.get("snippet")
                or self._extract_relevant_text(item.get("document", ""))
                or "Sem trecho textual."
            )
            lines.append(f"[{index}] {label} | {published_at}\n{snippet}")
        return "\n\n".join(lines)

    def _extract_relevant_text(self, text: str, max_chars: int = 500) -> str:
        compact = " ".join(str(text or "").split()).strip()
        return compact[:max_chars] + ("..." if len(compact) > max_chars else "")

    def _extract_json_object(self, text: str) -> str:
        raw = text.strip()
        if raw.startswith("{") and raw.endswith("}"):
            return raw

        start = raw.find("{")
        end = raw.rfind("}")
        if start >= 0 and end > start:
            return raw[start : end + 1]
        return raw
