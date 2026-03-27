"""
Pacote de banco de dados e persistência
"""

from .postgres_manager import PostgreSQLManager, EconomicIndicator

__all__ = [
    "PostgreSQLManager",
    "EconomicIndicator",
]
