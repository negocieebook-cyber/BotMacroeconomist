"""
Integração com FRED API (Federal Reserve Economic Data)
https://fred.stlouisfed.org/
"""
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging
from config import FRED_API_KEY, FRED_SERIES, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY

logger = logging.getLogger(__name__)

class FREDClient:
    """Cliente para acesso à API FRED"""
    
    BASE_URL = "https://api.stlouisfed.org/fred"
    
    def __init__(self, api_key: str = FRED_API_KEY):
        self.api_key = api_key
        self.session = requests.Session()
    
    def get_series(self, series_id: str, limit: int = 1000, 
                   start_date: Optional[str] = None) -> pd.DataFrame:
        """
        Obtém dados históricos de uma série FRED
        
        Args:
            series_id: ID da série (ex: 'CPIAUCSL')
            limit: Número máximo de observações
            start_date: Data inicial (YYYY-MM-DD)
            
        Returns:
            DataFrame com os dados da série
        """
        url = f"{self.BASE_URL}/series/observations"
        params = {
            "series_id": series_id,
            "api_key": self.api_key,
            "file_type": "json",
            "limit": limit
        }
        
        if start_date:
            params["observation_start"] = start_date
        
        try:
            response = self._make_request(url, params)
            data = response.json()
            
            if "observations" in data:
                df = pd.DataFrame(data["observations"])
                df["date"] = pd.to_datetime(df["date"])
                df["value"] = pd.to_numeric(df["value"], errors="coerce")
                df = df.dropna(subset=["value"])
                return df.sort_values("date")
            else:
                logger.warning(f"Nenhum dado encontrado para série: {series_id}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Erro ao buscar série {series_id}: {str(e)}")
            return pd.DataFrame()
    
    def get_multiple_series(self, series_ids: List[str], 
                          days_back: int = 365) -> Dict[str, pd.DataFrame]:
        """
        Obtém múltiplas séries em paralelo
        
        Args:
            series_ids: Lista de IDs de séries
            days_back: Quantos dias para trás
            
        Returns:
            Dicionário com DataFrames de cada série
        """
        start_date = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%d")
        results = {}
        
        for series_id in series_ids:
            results[series_id] = self.get_series(series_id, start_date=start_date)
            logger.info(f"✓ Obtida série {series_id}")
        
        return results
    
    def get_latest_release(self, series_id: str) -> Dict:
        """
        Obtém o valor mais recente de uma série
        
        Args:
            series_id: ID da série
            
        Returns:
            Dicionário com valor, data e metadados
        """
        df = self.get_series(series_id, limit=1)
        
        if df.empty:
            return {}
        
        latest = df.iloc[-1]
        return {
            "series_id": series_id,
            "value": latest["value"],
            "date": latest["date"].strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat()
        }
    
    def get_series_metadata(self, series_id: str) -> Dict:
        """
        Obtém metadados de uma série
        
        Args:
            series_id: ID da série
            
        Returns:
            Dicionário com metadatos
        """
        url = f"{self.BASE_URL}/series/{series_id}"
        params = {"api_key": self.api_key, "file_type": "json"}
        
        try:
            response = self._make_request(url, params)
            data = response.json()
            
            if "seriess" in data and len(data["seriess"]) > 0:
                series = data["seriess"][0]
                return {
                    "id": series["id"],
                    "title": series["title"],
                    "units": series.get("units", "N/A"),
                    "frequency": series.get("frequency", "N/A"),
                    "notes": series.get("notes", ""),
                    "last_updated": series.get("last_updated", "N/A")
                }
        except Exception as e:
            logger.error(f"Erro ao buscar metadados de {series_id}: {str(e)}")
        
        return {}
    
    def _make_request(self, url: str, params: Dict, retries: int = 0):
        """
        Faz requisição com retry automático
        """
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                logger.warning(f"Erro na requisição, tentando novamente... ({retries + 1}/{MAX_RETRIES})")
                import time
                time.sleep(RETRY_DELAY)
                return self._make_request(url, params, retries + 1)
            else:
                raise


class MacroeconomicMonitor:
    """Monitor de indicadores macroeconômicos via FRED"""
    
    def __init__(self):
        self.client = FREDClient()
    
    def get_inflation_metrics(self) -> Dict:
        """Obtém métricas de inflação"""
        return {
            "CPI": self.client.get_latest_release("CPIAUCSL"),
            "PCE": self.client.get_latest_release("PCEPI"),
        }
    
    def get_fed_policy(self) -> Dict:
        """Obtém dados de política monetária"""
        return {
            "FED_FUNDS": self.client.get_latest_release("FEDFUNDS"),
            "DGS10": self.client.get_latest_release("DGS10"),  # 10-year yield
        }
    
    def get_labor_market(self) -> Dict:
        """Obtém dados do mercado de trabalho"""
        return {
            "UNEMPLOYMENT_RATE": self.client.get_latest_release("UNRATE"),
            "NONFARM_PAYROLLS": self.client.get_latest_release("PAYEMS"),
        }
    
    def get_gdp_forecast(self) -> Dict:
        """Obtém forecast de PIB (GDPNow)"""
        return {
            "REAL_GDP": self.client.get_latest_release("GDPC1"),
        }
    
    def get_all_indicators(self) -> Dict:
        """Obtém todos os indicadores críticos"""
        return {
            "inflacao": self.get_inflation_metrics(),
            "politica_monetaria": self.get_fed_policy(),
            "mercado_trabalho": self.get_labor_market(),
            "gdp": self.get_gdp_forecast(),
        }
