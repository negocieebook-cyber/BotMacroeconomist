"""
Pacote de APIs para coleta de dados macroeconômicos
"""

from .fred_api import FREDClient, MacroeconomicMonitor
from .imf_api import IMFClient, BalanceOfPayments
from .worldbank_api import WorldBankClient
from .oecd_api import OECDClient
from .bis_api import BISClient
from .research_monitor import ResearchMonitor

__all__ = [
    "FREDClient",
    "MacroeconomicMonitor",
    "IMFClient",
    "BalanceOfPayments",
    "WorldBankClient",
    "OECDClient",
    "BISClient",
    "ResearchMonitor",
]
