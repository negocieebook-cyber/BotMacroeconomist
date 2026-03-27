"""
Exemplo de uso do Agente Macroeconomista
"""
from agents.macroeconomist import MacroeconomistAgent
from utils import setup_logger
import logging

# Configurar logging
logger = setup_logger("INFO", "./logs/example.log")


def example_1_basic_usage():
    """Exemplo 1: Uso básico do agente"""
    logger.info("\n" + "="*60)
    logger.info("EXEMPLO 1: Uso Básico")
    logger.info("="*60)
    
    # Inicializar agente sem scheduler
    agent = MacroeconomistAgent(enable_scheduler=False)
    
    # Coletar dados de inflação
    logger.info("\nColetando dados de inflação...")
    inflation_data = agent.monday_inflation_policy()
    
    # Exibir resultados
    for api, data in inflation_data.items():
        logger.info(f"  {api}: {type(data).__name__}")
    
    agent.shutdown()


def example_2_search_memory():
    """Exemplo 2: Buscar na memória"""
    logger.info("\n" + "="*60)
    logger.info("EXEMPLO 2: Busca Semântica na Memória")
    logger.info("="*60)
    
    agent = MacroeconomistAgent(enable_scheduler=False)
    
    # Coletar alguns dados primeiro
    logger.info("\nColetando dados iniciais...")
    agent.monday_inflation_policy()
    
    # Buscar na memória
    logger.info("\nBuscando: 'taxa de desemprego por país'")
    results = agent.search_knowledge("taxa de desemprego por país", n_results=5)
    
    logger.info(f"Encontrados {results['results_count']} resultados:")
    for i, result in enumerate(results['results'], 1):
        logger.info(f"  {i}. {result['api']} | Score: {1-result['distance']:.3f}")
    
    agent.shutdown()


def example_3_analyze_indicator():
    """Exemplo 3: Analisar indicador específico"""
    logger.info("\n" + "="*60)
    logger.info("EXEMPLO 3: Análise de Indicador")
    logger.info("="*60)
    
    agent = MacroeconomistAgent(enable_scheduler=False)
    
    # Coletar dados
    logger.info("\nColetando dados de crescimento econômico...")
    agent.tuesday_economic_growth()
    
    # Analisar
    logger.info("\nAnalisando indicador: PIB Global")
    analysis = agent.analyze_indicator("GDP")
    
    logger.info(f"Indicador: {analysis['indicator']}")
    logger.info(f"Dados históricos: {len(analysis['historical_data'].get('results', []))} pontos")
    logger.info(f"Insights: {', '.join(analysis['insights'])}")
    
    agent.shutdown()


def example_4_get_status():
    """Exemplo 4: Obter status do agente"""
    logger.info("\n" + "="*60)
    logger.info("EXEMPLO 4: Status do Agente")
    logger.info("="*60)
    
    agent = MacroeconomistAgent(enable_scheduler=False)
    
    # Obter status
    status = agent.get_agent_status()
    
    logger.info(f"\n📊 Status:")
    logger.info(f"  Memória: {status['memory']['total_documents']} documentos")
    logger.info(f"  Timestamp: {status['timestamp']}")
    
    logger.info(f"\n🌐 Conexões com APIs:")
    for api, available in status['system'].items():
        status_str = "✅ Disponível" if available else "❌ Indisponível"
        logger.info(f"  {api}: {status_str}")
    
    agent.shutdown()


if __name__ == "__main__":
    # Executar exemplos
    example_1_basic_usage()
    example_2_search_memory()
    example_3_analyze_indicator()
    example_4_get_status()
    
    logger.info("\n✅ Todos os exemplos executados com sucesso!")
