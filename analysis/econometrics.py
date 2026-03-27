"""
Analise econometrica simplificada e robusta para o projeto.
"""

import logging
from typing import Dict, Tuple

import numpy as np
import pandas as pd
from scipy.stats import linregress
from statsmodels.tsa.api import VAR
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller, coint, grangercausalitytests

import config

try:
    from arch import arch_model
    ARCH_AVAILABLE = True
except ImportError:
    ARCH_AVAILABLE = False

logger = logging.getLogger(__name__)


class EconometricAnalyzer:
    """Conjunto enxuto de funcoes econometricas."""

    def __init__(self):
        self.arima_order = config.ARIMA_ORDER
        self.garch_order = config.GARCH_ORDER
        self.correlation_threshold = config.CORRELATION_MIN_THRESHOLD
        self.granger_lag = config.GRANGER_CAUSALITY_LAG

    def adf_test(self, series: pd.Series, title: str = "") -> Dict:
        try:
            series_clean = pd.Series(series).dropna()
            if len(series_clean) < 10:
                return {"error": "Dados insuficientes"}

            result = adfuller(series_clean, autolag="AIC")
            p_value = float(result[1])

            return {
                "title": title,
                "test_statistic": float(result[0]),
                "p_value": p_value,
                "critical_values": {
                    "1%": float(result[4]["1%"]),
                    "5%": float(result[4]["5%"]),
                    "10%": float(result[4]["10%"]),
                },
                "is_stationary": p_value < 0.05,
                "interpretation": (
                    "Serie estacionaria"
                    if p_value < 0.05
                    else "Serie nao estacionaria"
                ),
            }
        except Exception as e:
            logger.error(f"Erro no teste ADF: {str(e)}")
            return {"error": str(e)}

    def granger_causality_test(
        self,
        dependent: pd.Series,
        independent: pd.Series,
        max_lag: int = None,
    ) -> Dict:
        try:
            max_lag = max_lag or self.granger_lag
            data = pd.concat([dependent, independent], axis=1).dropna()
            data.columns = ["dependent", "independent"]

            if len(data) < max_lag + 10:
                return {"error": "Dados insuficientes para teste"}

            results = grangercausalitytests(data, max_lag=max_lag, verbose=False)
            p_values = [float(results[lag][0]["ssr_ftest"][1]) for lag in range(1, max_lag + 1)]
            best_lag = int(np.argmin(p_values) + 1)
            min_pvalue = p_values[best_lag - 1]

            return {
                "causes": min_pvalue < 0.05,
                "p_value": min_pvalue,
                "best_lag": best_lag,
                "interpretation": (
                    f"Ha indicio de causalidade Granger no lag {best_lag}"
                    if min_pvalue < 0.05
                    else "Nao ha evidencia de causalidade"
                ),
            }
        except Exception as e:
            logger.error(f"Erro no teste Granger: {str(e)}")
            return {"error": str(e)}

    def rolling_correlation(
        self,
        series1: pd.Series,
        series2: pd.Series,
        window: int = 12,
    ) -> pd.DataFrame:
        try:
            data = pd.concat([series1, series2], axis=1).dropna()
            data.columns = ["x", "y"]
            rolling_corr = data["x"].rolling(window=window).corr(data["y"])
            return pd.DataFrame(
                {
                    "date": data.index,
                    "rolling_correlation": rolling_corr.values,
                    "window": window,
                }
            )
        except Exception as e:
            logger.error(f"Erro na correlacao movel: {str(e)}")
            return pd.DataFrame()

    def correlation_matrix(self, df: pd.DataFrame) -> Dict:
        try:
            corr = df.corr(numeric_only=True)
            significant = {}

            for col1 in corr.columns:
                for col2 in corr.columns:
                    if col1 < col2:
                        corr_value = corr.loc[col1, col2]
                        if pd.notna(corr_value) and abs(corr_value) > self.correlation_threshold:
                            significant[f"{col1} <-> {col2}"] = float(corr_value)

            strongest = sorted(
                significant.items(),
                key=lambda item: abs(item[1]),
                reverse=True,
            )[:5]

            return {
                "correlation_matrix": corr.to_dict(),
                "significant_correlations": significant,
                "strongest": strongest,
            }
        except Exception as e:
            logger.error(f"Erro na matriz de correlacao: {str(e)}")
            return {"error": str(e)}

    def garch_analysis(self, returns: pd.Series) -> Dict:
        try:
            if not ARCH_AVAILABLE:
                return {"error": "Pacote 'arch' nao esta disponivel"}

            returns_clean = pd.Series(returns).dropna()
            if len(returns_clean) < 20:
                return {"error": "Dados insuficientes"}

            model = arch_model(
                returns_clean,
                vol="Garch",
                p=self.garch_order[0],
                q=self.garch_order[1],
            )
            results = model.fit(disp="off")
            forecast = results.forecast(horizon=5)
            variance_forecast = forecast.variance.values[-1]

            return {
                "current_volatility": float(results.conditional_volatility.iloc[-1]),
                "volatility_mean": float(results.conditional_volatility.mean()),
                "volatility_max": float(results.conditional_volatility.max()),
                "forecast_volatility": [float(v) for v in variance_forecast],
                "garch_params": {
                    "alpha": float(results.params.get("alpha[1]", 0.0)),
                    "beta": float(results.params.get("beta[1]", 0.0)),
                },
            }
        except Exception as e:
            logger.error(f"Erro na analise GARCH: {str(e)}")
            return {"error": str(e)}

    def arima_forecast(
        self,
        series: pd.Series,
        periods: int = 4,
        order: Tuple = None,
    ) -> Dict:
        try:
            order = order or self.arima_order
            series_clean = pd.Series(series).dropna()

            if len(series_clean) < 20:
                return {"error": "Dados insuficientes para ARIMA"}

            model = ARIMA(series_clean, order=order)
            results = model.fit()
            forecast = results.get_forecast(steps=periods)
            conf_int = forecast.conf_int()

            return {
                "forecast": [float(v) for v in forecast.predicted_mean],
                "lower_bound": [float(v) for v in conf_int.iloc[:, 0]],
                "upper_bound": [float(v) for v in conf_int.iloc[:, 1]],
                "rmse": float(np.sqrt(np.mean(results.resid**2))),
                "aic": float(results.aic),
                "order": order,
            }
        except Exception as e:
            logger.error(f"Erro na previsao ARIMA: {str(e)}")
            return {"error": str(e)}

    def var_model(self, df: pd.DataFrame, lag: int = 1) -> Dict:
        try:
            df_clean = df.dropna()
            if len(df_clean) < lag + 10:
                return {"error": "Dados insuficientes"}

            model = VAR(df_clean)
            results = model.fit(lag)
            return {
                "aic": float(results.aic),
                "bic": float(results.bic),
                "lag": lag,
                "covariance": results.sigma_u.tolist() if hasattr(results, "sigma_u") else None,
                "summary": str(results.summary()),
            }
        except Exception as e:
            logger.error(f"Erro no modelo VAR: {str(e)}")
            return {"error": str(e)}

    def cointegration_test(self, series1: pd.Series, series2: pd.Series) -> Dict:
        try:
            data = pd.concat([series1, series2], axis=1).dropna()
            if len(data) < 20:
                return {"error": "Dados insuficientes"}

            stat, p_value, _ = coint(data.iloc[:, 0], data.iloc[:, 1])
            return {
                "cointegrated": float(p_value) < 0.05,
                "p_value": float(p_value),
                "hedge_ratio": float(stat),
                "interpretation": (
                    "Series cointegradas"
                    if float(p_value) < 0.05
                    else "Nao ha cointegracao"
                ),
            }
        except Exception as e:
            logger.error(f"Erro no teste de cointegracao: {str(e)}")
            return {"error": str(e)}

    def elasticity_analysis(self, dependent: pd.Series, independent: pd.Series) -> Dict:
        try:
            data = pd.concat([dependent, independent], axis=1).dropna()
            data.columns = ["y", "x"]
            log_data = np.log(data.abs() + 1)

            slope, _, r_value, p_value, _ = linregress(log_data["x"], log_data["y"])
            return {
                "elasticity": float(slope),
                "r_squared": float(r_value**2),
                "p_value": float(p_value),
                "significant": float(p_value) < 0.05,
                "interpretation": f"1% de mudanca em X -> {slope:.2f}% em Y",
            }
        except Exception as e:
            logger.error(f"Erro na analise de elasticidade: {str(e)}")
            return {"error": str(e)}

    def trend_decomposition(self, series: pd.Series, period: int = 12) -> Dict:
        try:
            from statsmodels.tsa.seasonal import seasonal_decompose

            series_clean = pd.Series(series).dropna()
            if len(series_clean) < 2 * period:
                return {"error": "Dados insuficientes para decomposicao"}

            decomposition = seasonal_decompose(series_clean, model="additive", period=period)
            return {
                "trend": decomposition.trend.dropna().tolist(),
                "seasonal": decomposition.seasonal.dropna().tolist(),
                "residual": decomposition.resid.dropna().tolist(),
                "original": series_clean.tolist(),
            }
        except Exception as e:
            logger.error(f"Erro na decomposicao: {str(e)}")
            return {"error": str(e)}


class RollingAnalyzer:
    """Analises com janelas moveis."""

    @staticmethod
    def structural_break_detection(series: pd.Series, window: int = 24) -> Dict:
        try:
            series_clean = pd.Series(series).dropna()
            if len(series_clean) < 2 * window:
                return {"error": "Dados insuficientes"}

            rolling_mean = series_clean.rolling(window=window).mean()
            rolling_std = series_clean.rolling(window=window).std()

            breaks = []
            for i in range(window, len(series_clean)):
                std_value = rolling_std.iloc[i]
                if pd.isna(std_value) or std_value == 0:
                    continue

                if abs(series_clean.iloc[i] - rolling_mean.iloc[i]) > 2 * std_value:
                    breaks.append(i)

            return {
                "structural_breaks": breaks,
                "break_dates": [str(series_clean.index[b]) for b in breaks],
                "count": len(breaks),
            }
        except Exception as e:
            logger.error(f"Erro na deteccao de ruptura: {str(e)}")
            return {"error": str(e)}
