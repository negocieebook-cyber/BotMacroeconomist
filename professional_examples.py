"""
Exemplos de Uso: PostgreSQL + Análise Econométrica Profissional
Demonstra como usar o novo sistema para análises reais
"""
import logging
import pandas as pd
from datetime import datetime, timedelta

# Imports do novo sistema
from database.postgres_manager import PostgreSQLManager
from analysis.econometrics import EconometricAnalyzer, RollingAnalyzer
from apis.fred_api import FREDClient
from utils.logger import setup_logger

# Configurar logging
logger = setup_logger("INFO", "./logs/professional_analysis.log")


def example_1_store_data_postgresql():
    """Exemplo 1: Coleta dados via API e armazena em PostgreSQL"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 1: Coleta de Dados via API → PostgreSQL")
    logger.info("="*80)
    
    # Inicializar cliente FRED e PostgreSQL
    fred = FREDClient()
    db = PostgreSQLManager()
    
    # Coletar dados de inflação (CPI)
    logger.info("\n  → Coletando CPI (Consumer Price Index)...")
    cpi_data = fred.get_series('CPIAUCSL', limit=100)
    
    if not cpi_data.empty:
        # Armazenar em PostgreSQL
        inserted = db.insert_data(
            df=cpi_data,
            country_code="US",
            indicator_code="CPIAUCSL",
            indicator_name="Consumer Price Index",
            api_source="FRED"
        )
        logger.info(f"  ✓ {inserted} registros armazenados em PostgreSQL")
    
    # Coletar dados de desemprego
    logger.info("\n  → Coletando Taxa de Desemprego (UNRATE)...")
    unemployment_data = fred.get_series('UNRATE', limit=100)
    
    if not unemployment_data.empty:
        inserted = db.insert_data(
            df=unemployment_data,
            country_code="US",
            indicator_code="UNRATE",
            indicator_name="Unemployment Rate",
            api_source="FRED"
        )
        logger.info(f"  ✓ {inserted} registros armazenados em PostgreSQL")
    
    # Exibir informações do banco
    db_info = db.get_database_info()
    logger.info(f"\n  📊 Status do Banco de Dados:")
    logger.info(f"     Total de registros: {db_info.get('total_records', 0)}")
    logger.info(f"     Indicadores únicos: {db_info.get('unique_indicators', 0)}")
    logger.info(f"     Países: {db_info.get('unique_countries', 0)}")


def example_2_test_stationarity():
    """Exemplo 2: Testar estacionaridade com ADF"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 2: Teste de Estacionaridade (ADF)")
    logger.info("="*80)
    
    fred = FREDClient()
    analyzer = EconometricAnalyzer()
    
    # Coletar dados
    logger.info("\n  → Coletando dados...")
    inflation_data = fred.get_series('CPIAUCSL', limit=60)
    
    if not inflation_data.empty:
        # Testar estacionaridade
        result = analyzer.adf_test(inflation_data['value'], title="CPI - Consumer Price Index")
        
        logger.info(f"\n  📊 Resultado do Teste ADF:")
        logger.info(f"     Estatística: {result.get('test_statistic', 'N/A'):.4f}")
        logger.info(f"     P-value: {result.get('p_value', 'N/A'):.4f}")
        logger.info(f"     Estacionária: {result.get('is_stationary', False)}")
        logger.info(f"     ➜ {result.get('interpretation', '')}")


def example_3_granger_causality():
    """Exemplo 3: Testar causalidade Granger"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 3: Causalidade Granger (Inflação → Desemprego?)")
    logger.info("="*80)
    
    fred = FREDClient()
    analyzer = EconometricAnalyzer()
    
    # Coletar dados
    logger.info("\n  → Coletando séries...")
    inflation = fred.get_series('CPIAUCSL', limit=60)
    unemployment = fred.get_series('UNRATE', limit=60)
    
    if not inflation.empty and not unemployment.empty:
        # Calcular variações (mais apropriado)
        inflation_change = inflation['value'].pct_change() * 100
        unemployment_rate = unemployment['value']
        
        # Testar causalidade
        result = analyzer.granger_causality_test(unemployment_rate, inflation_change, max_lag=4)
        
        logger.info(f"\n  🔗 Resultado Causalidade Granger:")
        logger.info(f"     Inflação causa desemprego? {result.get('causes', False)}")
        logger.info(f"     P-value: {result.get('p_value', 'N/A'):.4f}")
        logger.info(f"     Melhor lag: {result.get('best_lag', 'N/A')}")
        logger.info(f"     ➜ {result.get('interpretation', '')}")


def example_4_correlation_analysis():
    """Exemplo 4: Matriz de correlação entre indicadores"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 4: Análise de Correlação Múltipla")
    logger.info("="*80)
    
    db = PostgreSQLManager()
    analyzer = EconometricAnalyzer()
    
    # Obter dados de correlação
    logger.info("\n  → Obtendo dados para correlação...")
    correlation_data = db.get_correlation_data("US", start_date="2020-01-01")
    
    if not correlation_data.empty:
        # Análise de correlação
        result = analyzer.correlation_matrix(correlation_data)
        
        logger.info(f"\n  📊 Correlações Significativas (>0.3):")
        for pair, corr_value in result.get('significant_correlations', {}).items():
            logger.info(f"     {pair}: {corr_value:.3f}")
        
        logger.info(f"\n  🔝 Top 5 Correlações Mais Fortes:")
        for pair, corr_value in result.get('strongest', [])[:5]:
            logger.info(f"     {pair}: {corr_value:.3f}")


def example_5_volatility_analysis():
    """Exemplo 5: Análise de volatilidade com GARCH"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 5: Análise de Volatilidade (GARCH)")
    logger.info("="*80)
    
    fred = FREDClient()
    analyzer = EconometricAnalyzer()
    
    # Coletar dados de inflação
    logger.info("\n  → Coletando dados de inflação...")
    inflation = fred.get_series('CPIAUCSL', limit=120)
    
    if not inflation.empty:
        # Calcular retornos (mudanças %)
        returns = inflation['value'].pct_change() * 100
        
        # Análise GARCH
        result = analyzer.garch_analysis(returns)
        
        logger.info(f"\n  📈 Análise GARCH de Volatilidade:")
        logger.info(f"     Volatilidade atual: {result.get('current_volatility', 'N/A'):.4f}%")
        logger.info(f"     Volatilidade média: {result.get('volatility_mean', 'N/A'):.4f}%")
        logger.info(f"     Volatilidade máxima: {result.get('volatility_max', 'N/A'):.4f}%")
        
        forecast = result.get('forecast_volatility', [])
        if forecast:
            logger.info(f"\n  🔮 Previsão Volatilidade Próximos 5 Períodos:")
            for i, vol in enumerate(forecast, 1):
                logger.info(f"     T+{i}: {vol:.4f}%")


def example_6_arima_forecast():
    """Exemplo 6: Previsão com ARIMA"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 6: Previsão ARIMA (Próximos 4 trimestres)")
    logger.info("="*80)
    
    fred = FREDClient()
    analyzer = EconometricAnalyzer()
    
    # Coletar dados de PIB
    logger.info("\n  → Coletando dados de PIB real...")
    gdp = fred.get_series('GDPC1', limit=60)
    
    if not gdp.empty:
        # Previsão ARIMA
        result = analyzer.arima_forecast(gdp['value'], periods=4)
        
        logger.info(f"\n  🔮 Previsão ARIMA (Ordem: {result.get('order', 'N/A')}):")
        forecasts = result.get('forecast', [])
        lower = result.get('lower_bound', [])
        upper = result.get('upper_bound', [])
        
        for i, (forecast, low, high) in enumerate(zip(forecasts, lower, upper), 1):
            logger.info(f"     T+{i}: {forecast:,.2f} (IC 95%: {low:,.2f} - {high:,.2f})")
        
        logger.info(f"\n     RMSE: {result.get('rmse', 'N/A'):.2f}")
        logger.info(f"     AIC: {result.get('aic', 'N/A'):.2f}")


def example_7_elasticity():
    """Exemplo 7: Análise de elasticidade"""
    logger.info("\n" + "="*80)
    logger.info("EXEMPLO 7: Elasticidade (Inclinação da Relação)")
    logger.info("="*80)
    
    fred = FREDClient()
    analyzer = EconometricAnalyzer()
    
    # Coletar dados
    logger.info("\n  → Coletando dados...")
    inflation = fred.get_series('CPIAUCSL', limit=60)
    unemployment = fred.get_series('UNRATE', limit=60)
    
    if not inflation.empty and not unemployment.empty:
        # Análise de elasticidade
        result = analyzer.elasticity_analysis(unemployment['value'], inflation['value'])
        
        logger.info(f"\n  📊 Elasticidade Desemprego-Inflação:")
        logger.info(f"     Elasticidade: {result.get('elasticity', 'N/A'):.4f}")
        logger.info(f"     R²: {result.get('r_squared', 'N/A'):.4f}")
        logger.info(f"     Significante: {result.get('significant', False)}")
        logger.info(f"     ➜ {result.get('interpretation', '')}")


def run_all_professional_examples():
    """Executa todos os exemplos profissionais"""
    logger.info("\n" + "╔" + "="*78 + "╗")
    logger.info("║" + " "*15 + "🎓 EXEMPLOS DE ANÁLISE ECONOMÉTRICA PROFISSIONAL" + " "*15 + "║")
    logger.info("╚" + "="*78 + "╝")
    
    try:
        example_1_store_data_postgresql()
        example_2_test_stationarity()
        example_3_granger_causality()
        example_4_correlation_analysis()
        example_5_volatility_analysis()
        example_6_arima_forecast()
        example_7_elasticity()
        
        logger.info("\n" + "="*80)
        logger.info("✅ TODOS OS EXEMPLOS EXECUTADOS COM SUCESSO!")
        logger.info("="*80 + "\n")
    
    except Exception as e:
        logger.error(f"\n❌ Erro durante execução: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_professional_examples()
