"""
Integração com World Bank API
https://data.worldbank.org/
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from config import WORLD_BANK_API_BASE, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY, WORLDBANK_INDICATORS
from datetime import datetime

logger = logging.getLogger(__name__)

class WorldBankClient:
    """Cliente para acesso à API World Bank"""
    
    def __init__(self):
        self.session = requests.Session()
        self.base_url = WORLD_BANK_API_BASE
    
    def get_indicator(self, indicator_code: str, 
                     countries: Optional[List[str]] = None,
                     date: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém dados de um indicador do World Bank
        
        Indicadores populares:
        - NY.GDP.MKTP.CD: GDP (current US$)
        - NY.GDP.MKTP.KD.ZS: GDP growth (annual %)
        - NY.GNP.PCAP.PP.CD: GNI per Capita (PPP)
        - SL.UEM.TOTL.ZS: Unemployment (% de força de trabalho)
        - FP.CPI.TOTL.ZG: Inflação, índice de preços ao consumidor
        - BX.KLT.DINV.CD.WD: Foreign Direct Investment
        
        Args:
            indicator_code: Código do indicador
            countries: Lista de códigos ISO do país
            date: Ano ou período (ex: "2023" ou "2020:2023")
            
        Returns:
            DataFrame com os dados
        """
        url = f"{self.base_url}/country/all/indicator/{indicator_code}"
        
        params = {
            "format": "json",
            "per_page": 500,
            "mrnev": 1  # Most recent non-empty value
        }
        
        if countries:
            country_codes = ";".join(countries)
            url = f"{self.base_url}/country/{country_codes}/indicator/{indicator_code}"
        
        if date:
            params["date"] = date
        
        try:
            response = self._make_request(url, params)
            data = response.json()
            
            if isinstance(data, list) and len(data) > 1:
                return self._parse_wb_response(data[1], indicator_code)
            else:
                logger.warning(f"Nenhum dado encontrado para indicador: {indicator_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Erro ao buscar indicador {indicator_code}: {str(e)}")
            return pd.DataFrame()
    
    def get_gdp_all_countries(self, year: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém PIB de todos os países
        
        Args:
            year: Ano específico (opcional)
            
        Returns:
            DataFrame com GDP de todos os países
        """
        logger.info("Buscando GDP de todos os países...")
        return self.get_indicator("NY.GDP.MKTP.CD", date=year)
    
    def get_gdp_growth_all(self, year: Optional[str] = None) -> pd.DataFrame:
        """Obtém crescimento de PIB de todos os países"""
        logger.info("Buscando crescimento de PIB...")
        return self.get_indicator("NY.GDP.MKTP.KD.ZS", date=year)
    
    def get_unemployment_rate(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém taxa de desemprego"""
        logger.info("Buscando taxa de desemprego...")
        return self.get_indicator("SL.UEM.TOTL.ZS", countries=countries)
    
    def get_inflation_rate(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém taxa de inflação"""
        logger.info("Buscando taxa de inflação...")
        return self.get_indicator("FP.CPI.TOTL.ZG", countries=countries)
    
    def get_fdi(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém Investimento Direto Estrangeiro"""
        logger.info("Buscando dados de FDI...")
        return self.get_indicator("BX.KLT.DINV.CD.WD", countries=countries)
    
    def get_multiple_indicators(self, countries: List[str] = None) -> Dict[str, pd.DataFrame]:
        """
        Obtém múltiplos indicadores
        
        Args:
            countries: Lista de códigos ISO (BR, US, CN, etc)
            
        Returns:
            Dicionário com DataFrames para cada indicador
        """
        results = {}
        
        for name, code in WORLDBANK_INDICATORS.items():
            results[name] = self.get_indicator(code, countries=countries)
            logger.info(f"✓ Obtido indicador {name}")
        
        return results
    
    def _parse_wb_response(self, data: List, indicator: str) -> pd.DataFrame:
        """Parse resposta World Bank para DataFrame"""
        records = []
        
        for country_data in data:
            if isinstance(country_data, dict):
                country_code = country_data.get("countryiso3code", "")
                country_name = country_data.get("country", {}).get("value", "")
                
                for year, value in country_data.items():
                    if year not in ["countryiso3code", "country", "indicator"] and value is not None:
                        try:
                            records.append({
                                "country_code": country_code,
                                "country_name": country_name,
                                "year": int(year),
                                "value": float(value),
                                "indicator": indicator,
                                "source": "World Bank",
                                "timestamp": datetime.now().isoformat()
                            })
                        except (ValueError, TypeError):
                            continue
        
        if records:
            df = pd.DataFrame(records)
            return df.sort_values(["country_code", "year"])
        
        return pd.DataFrame()
    
    def _make_request(self, url: str, params: Dict = None, retries: int = 0):
        """Faz requisição com retry automático"""
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                logger.warning(f"Erro WB, tentando novamente... ({retries + 1}/{MAX_RETRIES})")
                import time
                time.sleep(RETRY_DELAY)
                return self._make_request(url, params, retries + 1)
            else:
                raise
