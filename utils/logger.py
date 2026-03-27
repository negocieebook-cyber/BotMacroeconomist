"""
Configuração de logging
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

def setup_logger(level: str = "INFO", log_file: str = "./logs/macroeconomist.log") -> logging.Logger:
    """
    Configura o sistema de logging
    
    Args:
        level: Nível de logging (DEBUG, INFO, WARNING, ERROR)
        log_file: Caminho do arquivo de log
        
    Returns:
        Logger configurado
    """
    # Criar diretório de logs se não existir
    os.makedirs(os.path.dirname(log_file) or "logs", exist_ok=True)
    
    # Configurar logger root
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, level.upper()))
    logger.handlers.clear()

    # Formato de log
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # Handler para console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Handler para arquivo com rotação
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10*1024*1024,  # 10MB
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setLevel(getattr(logging, level.upper()))
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    return logger
