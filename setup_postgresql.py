#!/usr/bin/env python3
"""
Setup PostgreSQL para Macroeconomist Bot
Script que inicializa o banco de dados com todas as tabelas necessárias
"""

import os
import sys
import logging
from pathlib import Path

# Adicionar projeto ao path
sys.path.insert(0, str(Path(__file__).parent))

from database.postgres_manager import PostgreSQLManager, EconomicIndicator
from config import SQLALCHEMY_DATABASE_URL
from utils.logger import setup_logger

logger = setup_logger("INFO", "./logs/setup.log")


def print_header(text: str, width: int = 80):
    """Imprimir header formatado"""
    print("\n" + "╔" + "="*(width-2) + "╗")
    print("║" + text.center(width-2) + "║")
    print("╚" + "="*(width-2) + "╝\n")


def check_postgresql_connection():
    """Verificar conexão com PostgreSQL"""
    logger.info("Verificando conexão com PostgreSQL...")
    print("  ⏳ Testando conexão PostgreSQL...", end=" ")
    
    try:
        db = PostgreSQLManager()
        
        # Tentar executar query simples
        result = db.raw_sql_query("SELECT 1 as test")
        
        if not result.empty:
            print("✓ SUCESSO\n")
            logger.info("✓ Conexão PostgreSQL estabelecida com sucesso")
            return True, db
        else:
            print("✗ FALHOU\n")
            logger.error("PostgreSQL respondeu mas query de teste falhou")
            return False, None
    
    except Exception as e:
        print(f"✗ ERRO: {str(e)}\n")
        logger.error(f"Erro ao conectar PostgreSQL: {str(e)}")
        return False, None


def initialize_database(db: PostgreSQLManager):
    """Inicializar banco de dados com tabelas"""
    logger.info("Inicializando banco de dados...")
    print("  ⏳ Criando tabelas...", end=" ")
    
    try:
        # PostgreSQLManager cria tabelas automaticamente no __init__
        # Verificar que a tabela foi criada
        result = db.raw_sql_query(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_name = 'economic_indicators'
            """
        )
        
        if not result.empty:
            print("✓ SUCESSO\n")
            logger.info("✓ Tabelas do banco de dados criadas com sucesso")
            return True
        else:
            print("✗ FALHOU - Tabela não foi criada\n")
            logger.error("Tabela economic_indicators não foi criada")
            return False
    
    except Exception as e:
        print(f"✗ ERRO: {str(e)}\n")
        logger.error(f"Erro ao criar tabelas: {str(e)}")
        return False


def verify_database_structure(db: PostgreSQLManager):
    """Verificar estrutura do banco de dados"""
    logger.info("Verificando estrutura do banco de dados...")
    print("  ⏳ Analisando tabelas e índices...", end=" ")
    
    try:
        # Verificar tabelas
        tables = db.raw_sql_query(
            """
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public'
            """
        )
        
        # Verificar índices
        indexes = db.raw_sql_query(
            """
            SELECT indexname FROM pg_indexes 
            WHERE schemaname = 'public'
            """
        )
        
        if not tables.empty:
            print("✓ SUCESSO\n")
            logger.info(f"✓ Banco de dados contém {len(tables)} tabelas")
            
            print("  📊 Estrutura do Banco:")
            for table in tables['table_name'].tolist():
                print(f"     • {table}")
            
            print(f"\n  🔑 Índices criados: {len(indexes)}")
            for idx in indexes['indexname'].tolist()[:5]:  # Mostrar primeiros 5
                print(f"     • {idx}")
            if len(indexes) > 5:
                print(f"     ... e mais {len(indexes)-5} índices")
            
            return True
        else:
            print("✗ FALHOU - Nenhuma tabela encontrada\n")
            logger.error("Nenhuma tabela foi criada no banco de dados")
            return False
    
    except Exception as e:
        print(f"✗ ERRO: {str(e)}\n")
        logger.error(f"Erro ao verificar estrutura: {str(e)}")
        return False


def get_database_stats(db: PostgreSQLManager):
    """Obter estatísticas do banco de dados"""
    print("  📈 Estatísticas do Banco:")
    
    try:
        # Total de registros
        result = db.raw_sql_query("SELECT COUNT(*) as count FROM economic_indicators")
        total_records = result['count'].iloc[0] if not result.empty else 0
        print(f"     • Total de registros: {total_records}")
        
        # Indicadores únicos
        result = db.raw_sql_query(
            "SELECT COUNT(DISTINCT indicator_code) as count FROM economic_indicators"
        )
        unique_indicators = result['count'].iloc[0] if not result.empty else 0
        print(f"     • Indicadores únicos: {unique_indicators}")
        
        # Países únicos
        result = db.raw_sql_query(
            "SELECT COUNT(DISTINCT country_code) as count FROM economic_indicators"
        )
        unique_countries = result['count'].iloc[0] if not result.empty else 0
        print(f"     • Países únicos: {unique_countries}")
        
        # Fontes de dados
        result = db.raw_sql_query(
            "SELECT DISTINCT api_source FROM economic_indicators ORDER BY api_source"
        )
        sources = result['api_source'].tolist() if not result.empty else []
        print(f"     • Fontes de dados: {', '.join(sources) if sources else 'Nenhuma'}")
        
    except Exception as e:
        logger.error(f"Erro ao obter estatísticas: {str(e)}")
        print(f"     ⚠️  Erro ao obter estatísticas: {str(e)}")


def display_environment_info():
    """Mostrar informações de ambiente"""
    print("  🔧 Configuração do Ambiente:")
    
    db_url = SQLALCHEMY_DATABASE_URL
    # Ocultar senha na exibição
    display_url = db_url.replace(
        db_url[db_url.find(":")+1:db_url.find("@")],
        "***"
    ) if "@" in db_url else db_url
    
    print(f"     • Database URL: {display_url}")
    print(f"     • Python: {sys.version.split()[0]}")
    print(f"     • Pandas: importado com sucesso")
    print(f"     • SQLAlchemy: importado com sucesso")


def display_next_steps():
    """Mostrar próximos passos"""
    print("\n" + "="*80)
    print("✅ PRÓXIMOS PASSOS:")
    print("="*80)
    print("""
1. INSTALAR DEPENDÊNCIAS (se ainda não fez):
   pip install -r requirements.txt

2. CONFIGURAR AGENTE PRINCIPAL:
   • Consulte: INTEGRATION_GUIDE.md
   • Abra: agents/macroeconomist.py
   • Adicione imports e inicializações PostgreSQL

3. TESTAR INTEGRAÇÃO:
   python professional_examples.py

4. EXECUTAR AGENTE:
   python main.py

5. MONITORAR LOGS:
   tail -f logs/setup.log
   tail -f logs/bot.log
    """)


def main():
    """Executar setup completo"""
    print_header("🚀 SETUP PostgreSQL - Macroeconomist Bot", 80)
    
    logger.info("="*80)
    logger.info("Iniciando setup PostgreSQL")
    logger.info("="*80)
    
    display_environment_info()
    
    # Testar conexão
    print("\n" + "-"*80)
    print("PASSO 1: VERIFICAR CONEXÃO")
    print("-"*80 + "\n")
    success, db = check_postgresql_connection()
    
    if not success:
        print("\n❌ ERRO: Não foi possível conectar ao PostgreSQL")
        print("\n   Solução:")
        print("   1. Certifique-se de que PostgreSQL está rodando")
        print("   2. Verifique as credenciais em .env")
        print("   3. Verifique POSTGRES_HOST e POSTGRES_PORT")
        print("\n   Comando para rodar PostgreSQL (Docker):")
        print("   docker run --name postgres -e POSTGRES_PASSWORD=password \\")
        print("      -p 5432:5432 -d postgres:15")
        logger.error("Setup falhou: Não foi possível conectar ao PostgreSQL")
        return False
    
    # Inicializar banco
    print("-"*80)
    print("PASSO 2: CRIAR TABELAS")
    print("-"*80 + "\n")
    if not initialize_database(db):
        logger.error("Setup falhou: Erro ao criar tabelas")
        return False
    
    # Verificar estrutura
    print("-"*80)
    print("PASSO 3: VERIFICAR ESTRUTURA")
    print("-"*80 + "\n")
    if not verify_database_structure(db):
        logger.error("Setup falhou: Erro ao verificar estrutura")
        return False
    
    # Exibir estatísticas
    print("\n" + "-"*80)
    print("PASSO 4: ESTATÍSTICAS")
    print("-"*80 + "\n")
    get_database_stats(db)
    
    # Sucesso!
    print("\n" + "="*80)
    print_header("✅ SETUP COMPLETO COM SUCESSO!", 80)
    
    logger.info("="*80)
    logger.info("Setup PostgreSQL concluído com sucesso")
    logger.info("="*80)
    
    # Próximos passos
    display_next_steps()
    
    return True


if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup interrompido pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro inesperado: {str(e)}")
        logger.error(f"Erro inesperado durante setup: {str(e)}", exc_info=True)
        sys.exit(1)
