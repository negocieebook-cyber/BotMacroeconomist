"""
Configurações do Agente Macroeconomista
"""
import os
from dotenv import load_dotenv

load_dotenv()

# API KEYS (Gratuitas - Nenhuma chave necessária para FRED e World Bank)
FRED_API_KEY = os.getenv("FRED_API_KEY", "seu_fred_api_key_aqui")  # fred.stlouisfed.org/docs/api/api_key.html
IMF_API_BASE = "https://api.imf.org/external/sdmx/2.1"
WORLD_BANK_API_BASE = "https://api.worldbank.org/v2"
OECD_API_BASE = "https://stats.oecd.org/sdmx-json"
BIS_API_BASE = "https://stats.bis.org/statx/sdmx-json"

# OpenAI / OpenRouter (LLM opcional; embeddings seguem locais/OpenAI)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")
OPENAI_LLM_TEMPERATURE = float(os.getenv("OPENAI_LLM_TEMPERATURE", "0.2"))
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
OPENROUTER_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
OPENROUTER_MODEL = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
OPENROUTER_SITE_URL = os.getenv("OPENROUTER_SITE_URL", "")
OPENROUTER_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "BotMacroeconomist")

# X / social listening.
# Por padrao o projeto NAO depende da API do X. Sem token, a coleta fica
# desabilitada e o pipeline usa RSS, sites e insumos manuais.
X_COLLECTION_MODE = os.getenv("X_COLLECTION_MODE", "disabled").lower()
X_ALLOW_MOCK_FALLBACK = os.getenv("X_ALLOW_MOCK_FALLBACK", "False").lower() == "true"
X_CLIENT_ID = os.getenv("X_CLIENT_ID", "")
X_CLIENT_SECRET = os.getenv("X_CLIENT_SECRET", "")
X_BEARER_TOKEN = os.getenv("X_BEARER_TOKEN", "")
X_API_BASE = os.getenv("X_API_BASE", "https://api.x.com/2")
X_POST_FETCH_LIMIT = int(os.getenv("X_POST_FETCH_LIMIT", "5"))
X_REQUEST_TIMEOUT = int(os.getenv("X_REQUEST_TIMEOUT", "20"))

# Telegram (opcional)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
ENABLE_TELEGRAM_NOTIFICATIONS = os.getenv("ENABLE_TELEGRAM_NOTIFICATIONS", "False").lower() == "true"
DAILY_DIGEST_HOUR_UTC = int(os.getenv("DAILY_DIGEST_HOUR_UTC", "21"))
DAILY_DIGEST_MINUTE_UTC = int(os.getenv("DAILY_DIGEST_MINUTE_UTC", "0"))
DAILY_TECHNICAL_LEARNING_HOUR_UTC = int(os.getenv("DAILY_TECHNICAL_LEARNING_HOUR_UTC", "9"))
DAILY_TECHNICAL_LEARNING_MINUTE_UTC = int(os.getenv("DAILY_TECHNICAL_LEARNING_MINUTE_UTC", "0"))
DAILY_RESEARCH_HOUR_UTC = int(os.getenv("DAILY_RESEARCH_HOUR_UTC", "12"))
DAILY_RESEARCH_MINUTE_UTC = int(os.getenv("DAILY_RESEARCH_MINUTE_UTC", "0"))
DAILY_THESIS_HOUR_UTC = int(os.getenv("DAILY_THESIS_HOUR_UTC", "18"))
DAILY_THESIS_MINUTE_UTC = int(os.getenv("DAILY_THESIS_MINUTE_UTC", "0"))

# Briefing de Fechamento do Dia (22:00 BRT = 01:00 UTC)
END_OF_DAY_BRIEFING_HOUR_UTC = int(os.getenv("END_OF_DAY_BRIEFING_HOUR_UTC", "1"))
END_OF_DAY_BRIEFING_MINUTE_UTC = int(os.getenv("END_OF_DAY_BRIEFING_MINUTE_UTC", "0"))

# Coleta de noticias: 3x ao dia (09:00, 13:00, 18:00 BRT = 12:00, 16:00, 21:00 UTC)
NEWS_COLLECTION_HOURS_UTC = [12, 16, 21]
DAILY_THESIS_TOPIC = os.getenv(
    "DAILY_THESIS_TOPIC",
    "inflacao, juros reais, crescimento, fiscal e risco financeiro",
)
RESEARCH_FEED_LIMIT = int(os.getenv("RESEARCH_FEED_LIMIT", "5"))
DEFAULT_RESEARCH_FEEDS = [
    {
        "source_name": "IMF News",
        "feed_url": "https://www.imf.org/en/news/rss",
    },
    {
        "source_name": "ECB RSS",
        "feed_url": "https://www.ecb.europa.eu/rss/press.html",
    },
    {
        "source_name": "BIS Speeches",
        "feed_url": "https://www.bis.org/doclist/cbspeeches.rss",
    },
    {
        "source_name": "Federal Reserve News",
        "feed_url": "https://www.federalreserve.gov/feeds/press_all.xml",
    },
]

# ChromaDB Configurações
CHROMA_DB_PATH = "./data/chroma_db"
CHROMA_COLLECTION_NAME = "macroeconomic_data"
MAX_EMBEDDINGS_PER_BATCH = 100

# Configurações de Requisições
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
RETRY_DELAY = 5  # segundos

# Cronograma de Atualização (em horas UTC)
SCHEDULE = {
    "segunda": {
        "hour": 14,  # 14:00 UTC
        "apis": ["FRED", "IMF"],
        "focus": "Inflação e Política Monetária"
    },
    "terca": {
        "hour": 14,
        "apis": ["WORLD_BANK", "FRED"],
        "focus": "Crescimento Econômico"
    },
    "quarta": {
        "hour": 14,
        "apis": ["FRED", "WORLD_BANK"],
        "focus": "Mercado de Trabalho"
    },
    "quinta": {
        "hour": 14,
        "apis": ["IMF", "BIS"],
        "focus": "Comércio e Finanças Globais"
    },
    "sexta": {
        "hour": 14,
        "apis": ["IMF", "FRED"],
        "focus": "Previsões e Consensus"
    }
}

# Series FRED para Monitoramento
FRED_SERIES = {
    "CPI": "CPIAUCSL",
    "PCE": "PCEPI",
    "FEDFUNDS": "FEDFUNDS",
    "UNRATE": "UNRATE",
    "PAYEMS": "PAYEMS",
    "GDPC1": "GDPC1",
    "DGS10": "DGS10",
    "DEXUSEU": "DEXUSEU",
}

# Indicadores World Bank para Monitoramento
WORLDBANK_INDICATORS = {
    "GDP": "NY.GDP.MKTP.CD",
    "GDP_GROWTH": "NY.GDP.MKTP.KD.ZS",
    "GNI_PER_CAPITA": "GNI_PPP",
    "UNEMPLOYMENT": "SL.UEM.TOTL.ZS",
    "INFLATION": "FP.CPI.TOTL.ZG",
    "FDI": "BX.KLT.DINV.CD.WD",
}

# ============================================================================
# POSTGRESQL CONFIGURAÇÃO (Análises Profissionais)
# ============================================================================
# OPÇÃO 1: URL completa do Supabase (recomendado)
# OPÇÃO 2: Construir da credenciais individuais (PostgreSQL local)

_SUPABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL", "")

if _SUPABASE_URL:
    # Usando Supabase (completo)
    SQLALCHEMY_DATABASE_URL = _SUPABASE_URL
else:
    # Construindo PostgreSQL local
    POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_USER = os.getenv("POSTGRES_USER", "macroeconomist")
    POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "")
    POSTGRES_DB = os.getenv("POSTGRES_DB", "macroeconomic_data")
    
    SQLALCHEMY_DATABASE_URL = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

# ============================================================================
# ANÁLISE ECONOMÉTRICA CONFIGURAÇÃO
# ============================================================================
ARIMA_ORDER = (1, 1, 1)  # (p, d, q) - ajuste conforme necessário
GARCH_ORDER = (1, 1)     # (p, q)
CORRELATION_MIN_THRESHOLD = 0.3
GRANGER_CAUSALITY_LAG = 4  # trimestres
PROPHET_SEASONALITY = "monthly"

# Logging
LOG_LEVEL = "INFO"
LOG_FILE = "./logs/macroeconomist.log"

# Cache Configuration
CACHE_EXPIRY_HOURS = 6
CACHE_DIR = "./cache"
DATABASE_CACHE_MINUTES = 60
