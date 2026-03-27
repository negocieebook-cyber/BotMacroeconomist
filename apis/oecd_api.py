"""
Integração com OECD SDMX API
https://stats.oecd.org/
"""
import requests
import pandas as pd
from typing import Dict, List, Optional
import logging
from config import OECD_API_BASE, REQUEST_TIMEOUT, MAX_RETRIES, RETRY_DELAY
from datetime import datetime

logger = logging.getLogger(__name__)

class OECDClient:
    """Cliente para acesso à API OECD SDMX"""
    
    BASE_URL = "https://stats.oecd.org/sdmx-json"
    
    def __init__(self):
        self.session = requests.Session()
    
    def get_leading_indicators(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém Índices Antecedentes (Leading Indicators)
        
        Args:
            countries: Lista de códigos OECD (AUS, AUT, BEL, CAN, etc)
            
        Returns:
            DataFrame com índices antecedentes
        """
        dataset = "CLI"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Índices antecedentes obtidos do OECD")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar índices antecedentes: {str(e)}")
            return pd.DataFrame()
    
    def get_coincident_indicators(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém Índices Coincidentes (Coincident Indicators)"""
        dataset = "CCI"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Índices coincidentes obtidos do OECD")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar índices coincidentes: {str(e)}")
            return pd.DataFrame()
    
    def get_productivity(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dados de produtividade
        
        Dataset: PDB_LV (OECD Productivity Database)
        """
        dataset = "PDB_LV"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Dados de produtividade obtidos do OECD")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar produtividade: {str(e)}")
            return pd.DataFrame()
    
    def get_labour_force(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém dados de força de trabalho"""
        dataset = "MEILF"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Dados de força de trabalho obtidos do OECD")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar força de trabalho: {str(e)}")
            return pd.DataFrame()
    
    def get_consumer_confidence(self, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """Obtém índice de confiança do consumidor"""
        dataset = "BTS_CCI"
        
        try:
            df = self._get_dataset(dataset, countries)
            logger.info("✓ Confiança do consumidor obtida do OECD")
            return df
        except Exception as e:
            logger.error(f"Erro ao buscar confiança do consumidor: {str(e)}")
            return pd.DataFrame()
    
    def _get_dataset(self, dataset_id: str, countries: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Obtém dataset genérico do OECD
        
        Args:
            dataset_id: ID do dataset (CLI, CCI, PDB_LV, etc)
            countries: Lista de códigos de país
            
        Returns:
            DataFrame com os dados
        """
        # Construir dimensões
        location = ";".join(countries) if countries else "OECD"
        frequency = "M"  # Mensal
        
        url = f"{self.BASE_URL}/data/{dataset_id}/{location}.{frequency}"
        
        params = {
            "startTime": "2020-01",
            "format": "json",
            "detail": "full"
        }
        
        try:
            response = self._make_request(url, params)
            data = response.json()
            
            return self._parse_oecd_response(data, dataset_id)
            
        except Exception as e:
            logger.warning(f"Não foi possível obter {dataset_id}: {str(e)}")
            return pd.DataFrame()
    
    def _parse_oecd_response(self, data: Dict, dataset: str) -> pd.DataFrame:
        """Parse resposta OECD para DataFrame"""
        records = []
        
        try:
            if "data" not in data or "observations" not in data["data"]:
                return pd.DataFrame()
            
            observations = data["data"]["observations"]
            dimensions = data["data"]["dimension"]
            
            for obs_key, obs_values in observations.items():
                parts = obs_key.split(":")
                if len(parts) >= 2:
                    for idx, value in enumerate(obs_values):
                        if value is not None:
                            records.append({
                                "dataset": dataset,
                                "indicator": obs_key,
                                "value": value,
                                "obs_index": idx,
                                "source": "OECD",
                                "timestamp": datetime.now().isoformat()
                            })
            
            if records:
                return pd.DataFrame(records)
        except Exception as e:
            logger.error(f"Erro ao parsear resposta OECD: {str(e)}")
        
        return pd.DataFrame()
    
    def _make_request(self, url: str, params: Dict = None, retries: int = 0):
        """Faz requisição com retry automático"""
        try:
            response = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
            response.raise_for_status()
            return response
        except requests.exceptions.RequestException as e:
            if retries < MAX_RETRIES:
                logger.warning(f"Erro OECD, tentando novamente... ({retries + 1}/{MAX_RETRIES})")
                import time
                time.sleep(RETRY_DELAY)
                return self._make_request(url, params, retries + 1)
            else:
                raise
