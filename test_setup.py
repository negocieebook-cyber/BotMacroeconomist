"""
Teste simples de instalacao do BotMacroeconomist.
Executa validacoes locais sem depender fortemente de internet.
"""

import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def test_imports():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 1: Validando importacoes")
    logger.info("=" * 60)

    try:
        import config
        from apis import FREDClient, IMFClient, WorldBankClient, OECDClient, BISClient
        from memory import ChromaDBManager, EmbeddingManager
        from scheduler import WeeklyScheduler, TaskManager
        from analysis import MacroeconomicAnalyzer, EconometricAnalyzer, RollingAnalyzer
        from utils import setup_logger, serialize_to_json
        from agents import MacroeconomistAgent

        logger.info("  OK: importacoes principais")
        return True
    except Exception as e:
        logger.error(f"  FALHOU: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_directories():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 2: Validando diretorios")
    logger.info("=" * 60)

    required_dirs = [
        "apis",
        "memory",
        "agents",
        "scheduler",
        "analysis",
        "utils",
    ]

    for dir_name in required_dirs:
        path = Path(dir_name)
        if path.exists():
            logger.info(f"  OK: {dir_name}/")
        else:
            logger.error(f"  FALHOU: {dir_name}/ nao encontrado")
            return False

    logger.info("  OK: estrutura basica presente")
    return True


def test_dependencies():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 3: Validando dependencias")
    logger.info("=" * 60)

    required_packages = {
        "requests": "requests",
        "pandas": "pandas",
        "numpy": "numpy",
        "chromadb": "chromadb",
        "dotenv": "dotenv",
        "apscheduler": "apscheduler",
        "sentence_transformers": "sentence_transformers",
        "statsmodels": "statsmodels",
        "sqlalchemy": "sqlalchemy",
    }

    all_ok = True
    for display_name, import_name in required_packages.items():
        try:
            __import__(import_name)
            logger.info(f"  OK: {display_name}")
        except ImportError:
            logger.error(f"  FALHOU: {display_name} nao instalado")
            all_ok = False

    return all_ok


def test_config():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 4: Validando configuracao")
    logger.info("=" * 60)

    try:
        import config

        logger.info(
            "  FRED_API_KEY: %s",
            "configurada" if config.FRED_API_KEY != "seu_fred_api_key_aqui" else "nao configurada",
        )
        logger.info(f"  CHROMA_DB_PATH: {config.CHROMA_DB_PATH}")
        logger.info(f"  LOG_LEVEL: {config.LOG_LEVEL}")
        logger.info(f"  REQUEST_TIMEOUT: {config.REQUEST_TIMEOUT}s")
        logger.info(f"  MAX_RETRIES: {config.MAX_RETRIES}")
        return True
    except Exception as e:
        logger.error(f"  FALHOU: {str(e)}")
        return False


def test_memory_init():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 5: Inicializando memoria")
    logger.info("=" * 60)

    try:
        from memory import ChromaDBManager

        db = ChromaDBManager()
        stats = db.get_collection_stats()
        logger.info(f"  OK: ChromaDB pronto com {stats.get('total_documents', 0)} documentos")
        return True
    except Exception as e:
        logger.error(f"  FALHOU: {str(e)}")
        import traceback

        traceback.print_exc()
        return False


def test_api_clients():
    logger.info("\n" + "=" * 60)
    logger.info("TESTE 6: Inicializando clientes de API")
    logger.info("=" * 60)

    try:
        from apis import FREDClient, IMFClient, WorldBankClient, OECDClient, BISClient

        FREDClient()
        IMFClient()
        WorldBankClient()
        OECDClient()
        BISClient()

        logger.info("  OK: clientes criados com sucesso")
        logger.info("  Observacao: este teste nao depende de internet")
        return True
    except Exception as e:
        logger.error(f"  FALHOU: {str(e)}")
        return False


def run_all_tests():
    logger.info("\n" + "=" * 80)
    logger.info("BotMacroeconomist - Teste de instalacao")
    logger.info("=" * 80)

    results = [
        ("Importacoes", test_imports()),
        ("Diretorios", test_directories()),
        ("Dependencias", test_dependencies()),
        ("Configuracao", test_config()),
        ("Memoria", test_memory_init()),
        ("APIs", test_api_clients()),
    ]

    logger.info("\n" + "=" * 80)
    logger.info("RESUMO DOS TESTES")
    logger.info("=" * 80)

    for test_name, result in results:
        logger.info(f"{test_name:20} {'PASSOU' if result else 'FALHOU'}")

    all_passed = all(result for _, result in results)

    logger.info("\n" + "=" * 80)
    if all_passed:
        logger.info("TODOS OS TESTES PASSARAM")
        logger.info("Use:")
        logger.info("  python main.py demo")
        logger.info("  python main.py")
    else:
        logger.error("ALGUNS TESTES FALHARAM")
        logger.info("Revise dependencias e configuracao do ambiente")
    logger.info("=" * 80 + "\n")

    return all_passed


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
