"""
Análise de dados macroeconômicos
"""
import logging
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class MacroeconomicAnalyzer:
    """Analisa dados macroeconômicos para gerar insights"""
    
    def __init__(self):
        pass
    
    def analyze_trends(self, df: pd.DataFrame, column: str = "value", window: int = 3) -> Dict:
        """
        Analisa tendências em uma série temporal
        
        Args:
            df: DataFrame com dados (deve ter coluna de date)
            column: Coluna a analisar
            window: Janela para média móvel
            
        Returns:
            Dicionário com análise de tendência
        """
        if df.empty or column not in df.columns:
            return {}
        
        try:
            values = df[column].dropna().values.tolist()
            
            if len(values) < window:
                return {"error": "Dados insuficientes"}
            
            # Calcular mudança
            latest = values[-1]
            previous = values[-window] if len(values) >= window else values[0]
            change = ((latest - previous) / abs(previous)) * 100 if previous != 0 else 0
            
            # Calcular volatilidade
            volatility = statistics.stdev(values) if len(values) > 1 else 0
            
            # Tendência simples
            first_half = statistics.mean(values[:len(values)//2])
            second_half = statistics.mean(values[len(values)//2:])
            trend = "Crescente" if second_half > first_half else "Decrescente"
            
            return {
                "latest_value": latest,
                "change_pct": round(change, 2),
                "volatility": round(volatility, 2),
                "trend": trend,
                "mean": round(statistics.mean(values), 2),
                "median": round(statistics.median(values), 2),
                "min": min(values),
                "max": max(values),
                "data_points": len(values)
            }
        
        except Exception as e:
            logger.error(f"Erro na análise de tendência: {str(e)}")
            return {}
    
    def correlate_indicators(self, dfs: Dict[str, pd.DataFrame], 
                            column: str = "value") -> Dict[Tuple[str, str], float]:
        """
        Calcula correlação entre múltiplos indicadores
        
        Args:
            dfs: Dicionário de DataFrames com indicadores
            column: Coluna a correlacionar
            
        Returns:
            Dicionário com correlações entre pares
        """
        correlations = {}
        
        try:
            indicators = list(dfs.keys())
            
            for i, ind1 in enumerate(indicators):
                for ind2 in indicators[i+1:]:
                    df1 = dfs[ind1]
                    df2 = dfs[ind2]
                    
                    if df1.empty or df2.empty or column not in df1.columns:
                        continue
                    
                    # Merge nos índices comuns
                    merged = df1[[column]].dropna().join(
                        df2[[column]].dropna(),
                        how="inner",
                        rsuffix="_2"
                    )
                    
                    if len(merged) > 1:
                        corr = merged.iloc[:, 0].corr(merged.iloc[:, 1])
                        correlations[(ind1, ind2)] = round(corr, 3)
            
            return correlations
        
        except Exception as e:
            logger.error(f"Erro na correlação: {str(e)}")
            return {}
    
    def detect_anomalies(self, df: pd.DataFrame, column: str = "value",
                        std_threshold: float = 2.0) -> List[Dict]:
        """
        Detecta anomalias em série temporal
        
        Args:
            df: DataFrame com dados
            column: Coluna a analisar
            std_threshold: Número de desvios padrão para considerar anomalia
            
        Returns:
            Lista de anomalias detectadas
        """
        if df.empty or column not in df.columns:
            return []
        
        try:
            values = df[column].dropna().values
            
            if len(values) < 3:
                return []
            
            mean = statistics.mean(values)
            stdev = statistics.stdev(values)
            
            anomalies = []
            
            for idx, (_, row) in enumerate(df.iterrows()):
                if column in row and pd.notna(row[column]):
                    value = row[column]
                    zscore = abs((value - mean) / stdev) if stdev != 0 else 0
                    
                    if zscore > std_threshold:
                        anomalies.append({
                            "date": row.get("date", row.name),
                            "value": value,
                            "zscore": round(zscore, 2),
                            "deviation": round((value - mean) / stdev, 2) if stdev != 0 else 0,
                            "severity": "HIGH" if zscore > 3 else "MEDIUM"
                        })
            
            return anomalies
        
        except Exception as e:
            logger.error(f"Erro na detecção de anomalias: {str(e)}")
            return []
    
    def forecast_simple(self, df: pd.DataFrame, column: str = "value",
                       periods: int = 3, method: str = "linear") -> List[Dict]:
        """
        Faz previsão simples para próximos períodos
        
        Args:
            df: DataFrame com dados históricos
            column: Coluna a prever
            periods: Número de períodos a prever
            method: Método de previsão ('linear', 'exponential')
            
        Returns:
            Lista com previsões
        """
        if df.empty or column not in df.columns:
            return []
        
        try:
            values = df[column].dropna().values.tolist()
            
            if len(values) < 2:
                return []
            
            last_date = df[df[column].notna()].index[-1] if "date" not in df.columns else df["date"].max()
            
            forecasts = []
            
            if method == "linear":
                # Regressão linear simples
                x = list(range(len(values)))
                x_mean = statistics.mean(x)
                y_mean = statistics.mean(values)
                
                numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(len(values)))
                denominator = sum((xi - x_mean) ** 2 for xi in x)
                
                slope = numerator / denominator if denominator != 0 else 0
                intercept = y_mean - slope * x_mean
                
                for i in range(1, periods + 1):
                    x_next = len(values) + i - 1
                    y_pred = slope * x_next + intercept
                    
                    forecasts.append({
                        "period": i,
                        "forecast": round(y_pred, 2),
                        "method": "linear",
                        "confidence": "low"
                    })
            
            elif method == "exponential":
                # Média exponencial simples
                alpha = 0.3
                level = values[-1]
                
                for i in range(1, periods + 1):
                    forecasts.append({
                        "period": i,
                        "forecast": round(level, 2),
                        "method": "exponential",
                        "confidence": "low"
                    })
            
            return forecasts
        
        except Exception as e:
            logger.error(f"Erro na previsão: {str(e)}")
            return []
    
    def compare_indicators(self, baseline_df: pd.DataFrame,
                          comparison_dfs: Dict[str, pd.DataFrame],
                          column: str = "value") -> Dict:
        """
        Compara um indicador com outros
        
        Args:
            baseline_df: DataFrame de referência
            comparison_dfs: Dicionário com DataFrames para comparação
            column: Coluna a comparar
            
        Returns:
            Dicionário com comparações
        """
        if baseline_df.empty or column not in baseline_df.columns:
            return {}
        
        baseline_values = baseline_df[column].dropna().values
        baseline_mean = statistics.mean(baseline_values) if baseline_values.size > 0 else 0
        baseline_latest = baseline_values[-1] if baseline_values.size > 0 else None
        
        comparisons = {
            "baseline_mean": round(baseline_mean, 2),
            "baseline_latest": baseline_latest,
            "comparisons": {}
        }
        
        try:
            for name, df in comparison_dfs.items():
                if df.empty or column not in df.columns:
                    continue
                
                comp_values = df[column].dropna().values
                comp_mean = statistics.mean(comp_values) if comp_values.size > 0 else 0
                comp_latest = comp_values[-1] if comp_values.size > 0 else None
                
                diff_mean = ((comp_mean - baseline_mean) / abs(baseline_mean)) * 100 if baseline_mean != 0 else 0
                
                comparisons["comparisons"][name] = {
                    "mean": round(comp_mean, 2),
                    "latest": comp_latest,
                    "diff_vs_baseline_pct": round(diff_mean, 2),
                    "is_higher": comp_mean > baseline_mean
                }
            
            return comparisons
        
        except Exception as e:
            logger.error(f"Erro na comparação: {str(e)}")
            return comparisons
