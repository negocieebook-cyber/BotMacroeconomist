"""
Integração com BIS Data Portal API (Bank for International Settlements)
https://www.bis.org/
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from config import BIS_API_BASE, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from datetime import datetime

logger = logging.getLogger(__name__)

class BISClient:
    """Cliente para acesso à API BIS Data Portal"""
    
    BASE_URL = "https://stats.bis.org/statx/sdmx-json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_global_credit(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dados de crédito global
        
        Dataset: TOTAL CREDIT TO PRIVATE NON-FINANCIAL SECTOR
        Inclui: Crédito bancário + crédito de mercado
        
        Args:
            countries: Lista de códigos BIS (US, BR, CN, etc)
            
        Returns:
            DataFrame com dados de crédito
        """
        dataset = "DF_CBT01"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Dados de crédito global obtidos do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar crédito global: {str(e)}")
            return pd.DataFrame()
    
    def get_credit_to_households(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém crédito para pessoas físicas"""
        dataset = "CBSPF"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Crédito para famílias obtido do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar crédito para famílias: {str(e)}")
            return pd.DataFrame()
    
    def get_credit_to_businesses(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém crédito para empresas"""
        dataset = "CBSPNF"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Crédito para empresas obtido do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar crédito para empresas: {str(e)}")
            return pd.DataFrame()
    
    def get_derivatives_markets(self) -> pd.DataFrame:
        """
        Obtém dados de mercados de derivativos
        
        Inclui: OTC derivatives, FX, juros, commodities
        """
        dataset = "DSRX"
        
        try:
            df = self._get_dataset(dataset)
            logger.info("✓ Dados de derivativos obtidos do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar dados de derivativos: {str(e)}")
            return pd.DataFrame()
    
    def get_property_prices(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém índices de preços imobiliários
        """
        dataset = "DSR"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Preços imobiliários obtidos do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar preços imobiliários: {str(e)}")
            return pd.DataFrame()
    
    def get_banking_locational(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dados de banking locacional
        
        Repositório de informações sobre bancos internacionais
        """
        dataset = "HLINKX"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Banking locacional obtido do BIS")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar banking locacional: {str(e)}")
            return pd.DataFrame()
    
    def _get_dataset(self, dataset_id: str, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dataset genérico do BIS
        
        Args:
            dataset_id: ID do dataset (DF_CBT01, DSRX, etc)
            countries: Lista de códigos de país
            
        Returns:
            DataFrame com os dados
        """
        url = f"{self.BASE_URL}/data/{dataset_id}"
        
        params = {
            "startTime": "2019-01",
            "format": "json",
            "detail": "full"
        }
        
        try:
            response = self._make_request(url, params)
            data = response.json()
            
            return self._parse_bis_response(data, dataset_id)
            
        except Exception as e:
            logger.warning(f"Não foi possível obter {dataset_id}: {str(e)}")
            return pd.DataFrame()
    
    def _parse_bis_response(self, data: Dict, dataset: str) -> pd.DataFrame:
        """Parse resposta BIS para DataFrame"""
        records = []
        
        try:
            if "data" not in data or "observations" not in data["data"]:
                return pd.DataFrame()
            
            observations = data["data"]["observations"]
            
            for obs_key, obs_values in observations.items():
                for idx, value in enumerate(obs_values):
                    if value is not None:
                        records.append({
                            "dataset": dataset,
                            "obs_key": obs_key,
                            "value": value,
                            "period_idx": idx,
                            "source": "BIS",
                            "timestamp": datetime.now().isoformat()
                        })
            
            if records:
                return pd.DataFrame(records)
        except Exception as e:
            logger.error(f"Erro ao parsear resposta BIS: {str(e)}")
        
        return pd.DataFrame()
    
    def _make_request(self, url: str, params: Dict = None, retries: int = 0):
        """Faz requisição com retry automático"""
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                logger.warning(f"Erro BIS, tentando novamente... ({retries + 1}/{MAX_RETRIES})")
                import time
                time.sleep(RETRY_DELAY)
                return self._make_request(url, params, retries + 1)
            else:
                raise
