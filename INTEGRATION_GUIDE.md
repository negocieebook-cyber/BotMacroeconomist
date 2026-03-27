"""
Guia de Integração: Conectando PostgreSQL + Econometria ao Agent Principal
Este arquivo mostra EXATAMENTE como modificar agents/macroeconomist.py
"""

# ============================================================================
# PASSO 1: ADICIONAR IMPORTS NO TOPO DE agents/macroeconomist.py
# ============================================================================
"""
Adicionar essas linhas após os imports existentes:

from database.postgres_manager import PostgreSQLManager, EconomicIndicator
from analysis.econometrics import EconometricAnalyzer, RollingAnalyzer
"""


# ============================================================================
# PASSO 2: MODIFICAR __init__ DA CLASSE MacroeconomistAgent
# ============================================================================
"""
No método __init__, adicionar estas linhas após a inicialização do ChromaDB:

    def __init__(self):
        # ... código existente de ChromaDB ...
        
        # NOVA INICIALIZAÇÃO: PostgreSQL + Econometria
        logger.info("Inicializando PostgreSQL Manager...")
        self.db = PostgreSQLManager()
        
        logger.info("Inicializando Econometric Analyzer...")
        self.econometrics = EconometricAnalyzer()
        self.rolling_analyzer = RollingAnalyzer()
        
        logger.info("✓ PostgreSQL e Econometria inicializados com sucesso")
"""


# ============================================================================
# PASSO 3: MODIFICAR MÉTODOS DE COLETA DE DADOS
# ============================================================================
"""
Cada método de coleta deve TAMBÉM salvar em PostgreSQL. Exemplo:

def collect_fred_data():
    # Código existente...
    cpi_data = fred.get_series('CPIAUCSL', limit=100)
    unemployment = fred.get_series('UNRATE', limit=100)
    
    # NOVO: Salvar em PostgreSQL
    if not cpi_data.empty:
        inserted = self.db.insert_data(
            df=cpi_data,
            country_code="US",
            indicator_code="CPIAUCSL",
            indicator_name="Consumer Price Index",
            api_source="FRED"
        )
        logger.info(f"✓ {inserted} registros CPI salvos em PostgreSQL")
    
    if not unemployment.empty:
        inserted = self.db.insert_data(
            df=unemployment,
            country_code="US",
            indicator_code="UNRATE",
            indicator_name="Unemployment Rate",
            api_source="FRED"
        )
        logger.info(f"✓ {inserted} registros Desemprego salvos em PostgreSQL")
    
    # Resto do código existente...
"""


# ============================================================================
# PASSO 4: ADICIONAR NOVOS MÉTODOS DE ANÁLISE PROFISSIONAL
# ============================================================================
"""
Adicionar esses métodos à classe MacroeconomistAgent:

def analyze_inflation_unemployment_causality(self):
    '''Causalidade Granger: Inflação causa desemprego?'''
    from apis.fred_api import FREDClient
    fred = FREDClient()
    
    inflation = fred.get_series('CPIAUCSL', limit=60)
    unemployment = fred.get_series('UNRATE', limit=60)
    
    if not inflation.empty and not unemployment.empty:
        # Usar dados que já estão em PostgreSQL
        inflation_changes = inflation['value'].pct_change() * 100
        
        result = self.econometrics.granger_causality_test(
            unemployment['value'], 
            inflation_changes,
            max_lag=4
        )
        
        insight = f"Causalidade Granger (Inflação→Desemprego): {result['causes']}"
        self.memory.store_analysis_result(insight, result)
        return result


def detect_volatility_changes(self):
    '''Detectar mudanças de volatilidade na economia'''
    from apis.fred_api import FREDClient
    fred = FREDClient()
    
    inflation = fred.get_series('CPIAUCSL', limit=120)
    if not inflation.empty:
        returns = inflation['value'].pct_change() * 100
        
        result = self.econometrics.garch_analysis(returns)
        
        insight = f"Volatilidade atual: {result['current_volatility']:.2f}%"
        self.memory.store_analysis_result(insight, result)
        return result


def forecast_gdp_next_quarters(self):
    '''Prever PIB para próximos 4 trimestres'''
    from apis.fred_api import FREDClient
    fred = FREDClient()
    
    gdp = fred.get_series('GDPC1', limit=60)
    if not gdp.empty:
        result = self.econometrics.arima_forecast(gdp['value'], periods=4)
        
        forecasts = result['forecast']
        insight = f"Previsão PIB próx. trimestre: {forecasts[0]:,.2f}"
        self.memory.store_analysis_result(insight, result)
        return result


def analyze_economic_indicators_correlation(self):
    '''Correlação entre múltiplos indicadores econômicos'''
    # Obter dados já coletados de PostgreSQL
    correlation_data = self.db.get_correlation_data("US", start_date="2020-01-01")
    
    if not correlation_data.empty:
        result = self.econometrics.correlation_matrix(correlation_data)
        
        insight = f"Principais correlações: {result.get('significant_correlations', {})}"
        self.memory.store_analysis_result(insight, result)
        return result


def detect_economic_regime_changes(self):
    '''Detectar quebras estruturais (mudanças de regime)'''
    from apis.fred_api import FREDClient
    fred = FREDClient()
    
    unemployment = fred.get_series('UNRATE', limit=120)
    if not unemployment.empty:
        result = self.rolling_analyzer.structural_break_detection(unemployment['value'])
        
        if result['breaks']:
            insight = f"Quebras estruturais detectadas em: {result['breaks']}"
            self.memory.store_analysis_result(insight, result)
        return result
"""


# ============================================================================
# PASSO 5: ADICIONAR À AGENDA DE TAREFAS SEMANAIS
# ============================================================================
"""
Em scheduler/weekly_schedule.py, adicionar essas análises à agenda:

def setup_professional_analysis_schedule(agent):
    '''Agenda análises profissionais junto com coleta de dados'''
    
    # Análises diárias
    schedule.every().monday.at("14:00").do(agent.analyze_inflation_unemployment_causality)
    schedule.every().wednesday.at("16:00").do(agent.detect_volatility_changes)
    schedule.every().friday.at("09:00").do(agent.forecast_gdp_next_quarters)
    
    # Análises semanais
    schedule.every().sunday.at("20:00").do(agent.analyze_economic_indicators_correlation)
    schedule.every().sunday.at("21:00").do(agent.detect_economic_regime_changes)
    
    logger.info("✓ Agenda de análise profissional configurada")
"""


# ============================================================================
# PASSO 6: VARIÁVEIS DE AMBIENTE NECESSÁRIAS (.env)
# ============================================================================
"""
Adicionar ao arquivo .env da aplicação:

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_USER=macroeconomist
POSTGRES_PASSWORD=seu_password_aqui
POSTGRES_DB=macroeconomic_data

# Ou use URL completa:
SQLALCHEMY_DATABASE_URL=postgresql://macroeconomist:senha@localhost:5432/macroeconomic_data
"""


# ============================================================================
# PASSO 7: INSTALAR DEPENDÊNCIAS NECESSÁRIAS
# ============================================================================
"""
No terminal, executar:

pip install -r requirements.txt

Ou, para instalar apenas as novas dependências:

pip install statsmodels==0.14.0 scipy==1.11.4 arch==6.2.0 \\
    prophet==1.1.5 psycopg2-binary==2.9.9 sqlalchemy==2.0.23 \\
    plotly==5.18.0 matplotlib==3.8.2
"""


# ============================================================================
# PASSO 8: INICIALIZAR BANCO DE DADOS POSTGRESQL
# ============================================================================
"""
Criar script: setup_postgresql.py

from database.postgres_manager import PostgreSQLManager
from config import SQLALCHEMY_DATABASE_URL

if __name__ == '__main__':
    # Isto cria tabelas automaticamente
    db = PostgreSQLManager()
    print("✓ Banco de dados PostgreSQL inicializado")
    print(f"  URL: {SQLALCHEMY_DATABASE_URL}")

Executar:
python setup_postgresql.py
"""


# ============================================================================
# PASSO 9: VALIDAR INTEGRAÇÃO
# ============================================================================
"""
Para testar se tudo está funcionando:

python professional_examples.py

Ou executar no main.py:
python main.py demo
"""


# ============================================================================
# RESUMO DE MODIFICAÇÕES
# ============================================================================
"""
ARQUIVO: agents/macroeconomist.py
========================================

1. IMPORTS (adicionar no topo):
   - from database.postgres_manager import PostgreSQLManager
   - from analysis.econometrics import EconometricAnalyzer, RollingAnalyzer

2. __init__ (adicionar após ChromaDB):
   - self.db = PostgreSQLManager()
   - self.econometrics = EconometricAnalyzer()
   - self.rolling_analyzer = RollingAnalyzer()

3. collect_fred_data() (adicionar após cada coleta):
   - self.db.insert_data(df, country, indicator, name, source)

4. collect_imf_data() (adicionar após cada coleta):
   - self.db.insert_data(...)

5. collect_worldbank_data() (adicionar após cada coleta):
   - self.db.insert_data(...)

6. NOVOS MÉTODOS (adicionar à classe):
   - analyze_inflation_unemployment_causality()
   - detect_volatility_changes()
   - forecast_gdp_next_quarters()
   - analyze_economic_indicators_correlation()
   - detect_economic_regime_changes()

ARQUIVO: scheduler/weekly_schedule.py
========================================

1. Atualizar setup_schedule() para incluir:
   - agent.analyze_inflation_unemployment_causality()
   - agent.detect_volatility_changes()
   - agent.forecast_gdp_next_quarters()
   - agent.analyze_economic_indicators_correlation()
   - agent.detect_economic_regime_changes()

ARQUIVO: .env
========================================

1. Adicionar variáveis PostgreSQL:
   - POSTGRES_HOST=localhost
   - POSTGRES_PORT=5432
   - POSTGRES_USER=macroeconomist
   - POSTGRES_PASSWORD=***
   - POSTGRES_DB=macroeconomic_data

ORDEM DE EXECUÇÃO
========================================

1. pip install -r requirements.txt
2. python setup_postgresql.py (criar tabelas)
3. Modificar agents/macroeconomist.py (adicionar imports + métodos)
4. python professional_examples.py (testar)
5. python main.py (executar agent completo)
"""
