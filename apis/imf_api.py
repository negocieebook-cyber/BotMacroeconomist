"""
Integração com IMF SDMX API (International Monetary Fund)
https://www.imf.org/external/datamapper/api/v1
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from config import IMF_API_BASE, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from datetime import datetime

logger = logging.getLogger(__name__)

class IMFClient:
    """Cliente para acesso à API IMF SDMX"""
    
    BASE_URL = "https://www.imf.org/external/datamapper/api/v1"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_world_economic_outlook(self, indicator: str, 
                                   countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dados do World Economic Outlook (WEO)
        
        Indicadores populares:
        - NGDPD: Nominal GDP (USD Billions)
        - NGDPDPC: GDP per Capita (USD)
        - PPPGDP: PPP GDP (USD Billions)
        - PPIPC: PPP GDP per Capita
        - FLUR: Unemployment Rate (%)
        - PCPIPCH: Inflation Rate (%)
        
        Args:
            indicator: Código do indicador
            countries: Lista de códigos de países (BR, US, CN, etc)
            
        Returns:
            DataFrame com dados do WEO
        """
        url = f"{self.BASE_URL}/MetadataStructure/indicator/{indicator}"
        
        try:
            response = self._make_request(url)
            data = response.json()
            
            if countries:
                country_filter = "/".join(countries)
                url = f"{self.BASE_URL}/MetadataStructure/indicator/{indicator}/{country_filter}"
                response = self._make_request(url)
                data = response.json()
            
            return self._parse_weo_response(data, indicator)
            
        except Exception as e:
            logger.error(f"Erro ao buscar WEO {indicator}: {str(e)}")
            return pd.DataFrame()
    
    def get_global_inflation(self) -> Dict:
        """Obtém dados globais de inflação"""
        try:
            url = f"{self.BASE_URL}/MetadataStructure/indicator/PCPIPCH"
            response = self._make_request(url)
            data = response.json()
            logger.info("✓ Dados de inflação global obtidos do IMF")
            return data if data else {}
        except Exception as e:
            logger.error(f"Erro ao buscar inflação global: {str(e)}")
            return {}
    
    def get_global_growth(self) -> Dict:
        """Obtém dados globais de crescimento (PIB)"""
        try:
            url = f"{self.BASE_URL}/MetadataStructure/indicator/NGDPD"
            response = self._make_request(url)
            data = response.json()
            logger.info("✓ Dados de crescimento global obtidos do IMF")
            return data if data else {}
        except Exception as e:
            logger.error(f"Erro ao buscar crescimento global: {str(e)}")
            return {}
    
    def get_unemployment_global(self) -> Dict:
        """Obtém dados globais de desemprego"""
        try:
            url = f"{self.BASE_URL}/MetadataStructure/indicator/FLUR"
            response = self._make_request(url)
            data = response.json()
            logger.info("✓ Dados de desemprego global obtidos do IMF")
            return data if data else {}
        except Exception as e:
            logger.error(f"Erro ao buscar desemprego global: {str(e)}")
            return {}
    
    def _parse_weo_response(self, data: Dict, indicator: str) -> pd.DataFrame:
        """Parse resposta WEO para DataFrame"""
        if not data or "data" not in data:
            return pd.DataFrame()
        
        records = []
        for country_code, country_data in data.get("data", {}).items():
            if isinstance(country_data, dict):
                for year, value in country_data.items():
                    try:
                        records.append({
                            "country": country_code,
                            "year": int(year),
                            "value": float(value),
                            "indicator": indicator,
                            "source": "IMF",
                            "timestamp": datetime.now().isoformat()
                        })
                    except (ValueError, TypeError):
                        continue
        
        if records:
            df = pd.DataFrame(records)
            return df.sort_values(["country", "year"])
        
        return pd.DataFrame()
    
    def _make_request(self, url: str, retries: int = 0):
        """Faz requisição com retry automático"""
        try:
            response = self.session.get(url, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                logger.warning(f"Erro IMF, tentando novamente... ({retries + 1}/{MAX_RETRIES})")
                import time
                time.sleep(RETRY_DELAY)
                return self._make_request(url, retries + 1)
            else:
                raise


class BalanceOfPayments:
    """Análise de Balanço de Pagamentos"""
    
    def __init__(self):
        self.client = IMFClient()
    
    def get_current_account(self, countries: Optional[List[str]] = None) -> Dict:
        """Obtém dados de conta corrente"""
        logger.info("Buscando dados de conta corrente...")
        return self.client.get_world_economic_outlook("BXNPGDPD", countries)
    
    def get_fdi(self, countries: Optional[List[str]] = None) -> Dict:
        """Obtém dados de Investimento Direto Estrangeiro"""
        logger.info("Buscando dados de FDI...")
        return self.client.get_world_economic_outlook("BXDPGDPD", countries)
