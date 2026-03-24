from __future__ import annotations
import numpy as np
import pandas as pd


def simple_moving_average(series: pd.Series, window: int = 20) -> pd.Series:
    return series.rolling(window=window, min_periods=1).mean()


def exponential_moving_average(series: pd.Series, span: int = 20) -> pd.Series:
    return series.ewm(span=span, adjust=False).mean()


def bollinger_bands(
    series: pd.Series, window: int = 20, num_std: float = 2.0
) -> dict[str, pd.Series]:
    sma = series.rolling(window=window, min_periods=1).mean()
    std = series.rolling(window=window, min_periods=1).std().fillna(0)
    return {
        "middle": sma,
        "upper": sma + num_std * std,
        "lower": sma - num_std * std,
    }


def rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = (-delta).where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=1).mean()
    avg_loss = loss.rolling(window=period, min_periods=1).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    result = 100 - (100 / (1 + rs))
    result = result.where(avg_loss > 0, np.where(avg_gain > 0, 100.0, 50.0))
    return result


def macd(
    series: pd.Series,
    fast: int = 12,
    slow: int = 26,
    signal: int = 9,
) -> dict[str, pd.Series]:
    ema_fast = series.ewm(span=fast, adjust=False).mean()
    ema_slow = series.ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal, adjust=False).mean()
    histogram = macd_line - signal_line
    return {"macd": macd_line, "signal": signal_line, "histogram": histogram}


def rolling_volatility(series: pd.Series, window: int = 20) -> pd.Series:
    returns = series.pct_change()
    return returns.rolling(window=window, min_periods=2).std() * np.sqrt(252)


def drawdown(series: pd.Series) -> pd.Series:
    cummax = series.cummax()
    dd = (series - cummax) / cummax
    return dd


def abnormal_volume(volume: pd.Series, window: int = 20, threshold: float = 2.0) -> pd.Series:
    rolling_mean = volume.rolling(window=window, min_periods=1).mean()
    rolling_std = volume.rolling(window=window, min_periods=1).std().fillna(1)
    z_scores = (volume - rolling_mean) / rolling_std.replace(0, 1)
    return (z_scores.abs() > threshold).astype(int)


def compute_indicator(
    df: pd.DataFrame,
    col: str,
    indicator_type: str,
    params: dict | None = None,
    volume_col: str | None = None,
) -> dict[str, list]:
    params = params or {}
    s = df[col].dropna() if col in df.columns else pd.Series(dtype=float)

    handlers = {
        "sma": lambda: {"sma": simple_moving_average(s, params.get("window", 20))},
        "ema": lambda: {"ema": exponential_moving_average(s, params.get("span", 20))},
        "bollinger": lambda: bollinger_bands(s, params.get("window", 20), params.get("num_std", 2.0)),
        "rsi": lambda: {"rsi": rsi(s, params.get("period", 14))},
        "macd": lambda: macd(s, params.get("fast", 12), params.get("slow", 26), params.get("signal", 9)),
        "volatility": lambda: {"volatility": rolling_volatility(s, params.get("window", 20))},
        "drawdown": lambda: {"drawdown": drawdown(s)},
        "abnormal_volume": lambda: {
            "abnormal_volume": abnormal_volume(
                df[volume_col] if volume_col and volume_col in df.columns else pd.Series(dtype=float),
                params.get("window", 20),
                params.get("threshold", 2.0),
            )
        },
    }

    fn = handlers.get(indicator_type)
    if fn is None:
        return {}

    result_series = fn()
    out: dict[str, list] = {}
    for k, v in result_series.items():
        vals = v.reindex(df.index)
        out[k] = [None if pd.isna(x) else round(float(x), 6) for x in vals]
    return out
