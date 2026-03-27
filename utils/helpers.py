"""
Funções auxiliares
"""
import json
from typing import Any, Dict, List
from datetime import datetime
import pandas as pd


def serialize_to_json(obj: Any, indent: int = 2) -> str:
    """
    Serializa objeto para JSON com tratamento de tipos especiais
    
    Args:
        obj: Objeto a serializar
        indent: Indentação JSON
        
    Returns:
        String JSON
    """
    def default_handler(o):
        if isinstance(o, (datetime, pd.Timestamp)):
            return o.isoformat()
        elif isinstance(o, pd.DataFrame):
            return o.to_dict()
        elif hasattr(o, '__dict__'):
            return o.__dict__
        return str(o)
    
    return json.dumps(obj, indent=indent, default=default_handler)


def format_number(value: float, decimals: int = 2, prefix: str = "") -> str:
    """
    Formata número com separadores e prefixo
    
    Args:
        value: Número a formatar
        decimals: Número de casas decimais
        prefix: Prefixo (ex: "$", "€")
        
    Returns:
        String formatada
    """
    if value is None:
        return "N/A"
    
    formatted = f"{value:,.{decimals}f}"
    return f"{prefix}{formatted}"


def percent_change(old: float, new: float) -> float:
    """Calcula variação percentual"""
    if old == 0:
        return 0.0
    return ((new - old) / abs(old)) * 100


def moving_average(data: List[float], window: int = 3) -> List[float]:
    """Calcula média móvel"""
    if len(data) < window:
        return data
    
    ma = []
    for i in range(len(data) - window + 1):
        avg = sum(data[i:i+window]) / window
        ma.append(avg)
    
    return ma


def find_outliers(data: List[float], std_threshold: float = 2.0) -> Dict:
    """
    Encontra outliers usando desvio padrão
    
    Args:
        data: Lista de valores
        std_threshold: Número de desvios padrão para considerar outlier
        
    Returns:
        Dicionário com índices e valores dos outliers
    """
    if len(data) < 2:
        return {"outliers": []}
    
    import statistics
    
    mean = statistics.mean(data)
    stdev = statistics.stdev(data)
    
    outliers = []
    for idx, value in enumerate(data):
        if abs(value - mean) > std_threshold * stdev:
            outliers.append({
                "index": idx,
                "value": value,
                "deviation": (value - mean) / stdev if stdev != 0 else 0
            })
    
    return {"outliers": outliers, "mean": mean, "stdev": stdev}


def merge_dataframes(dfs: Dict[str, pd.DataFrame], on: str = "date") -> pd.DataFrame:
    """
    Merge múltiplos DataFrames
    
    Args:
        dfs: Dicionário de DataFrames
        on: Coluna para merge
        
    Returns:
        DataFrame merged
    """
    if not dfs:
        return pd.DataFrame()
    
    result = None
    for name, df in dfs.items():
        if result is None:
            result = df.copy()
            result.columns = [f"{name}_{col}" if col != on else col for col in result.columns]
        else:
            df_renamed = df.copy()
            df_renamed.columns = [f"{name}_{col}" if col != on else col for col in df_renamed.columns]
            result = result.merge(df_renamed, on=on, how="outer")
    
    return result


class DataCache:
    """Cache simples em memória com expiração"""
    
    def __init__(self, ttl_seconds: int = 3600):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def set(self, key: str, value: Any) -> None:
        """Armazena valor em cache"""
        self.cache[key] = {
            "value": value,
            "timestamp": datetime.now()
        }
    
    def get(self, key: str) -> Any:
        """Obtém valor do cache se válido"""
        if key not in self.cache:
            return None
        
        entry = self.cache[key]
        age = (datetime.now() - entry["timestamp"]).total_seconds()
        
        if age > self.ttl:
            del self.cache[key]
            return None
        
        return entry["value"]
    
    def clear(self) -> None:
        """Limpa todo o cache"""
        self.cache.clear()
