"""Generate sample datasets for NATASHA testing."""
import numpy as np
import pandas as pd
from pathlib import Path

OUT = Path(__file__).parent
np.random.seed(42)


def stock_ohlcv():
    """Simulated stock OHLCV data (252 trading days)."""
    dates = pd.bdate_range("2024-01-02", periods=252)
    close = 100 * np.exp(np.cumsum(np.random.normal(0.0003, 0.015, 252)))

    high = close * (1 + np.abs(np.random.normal(0, 0.008, 252)))
    low = close * (1 - np.abs(np.random.normal(0, 0.008, 252)))
    open_price = low + (high - low) * np.random.uniform(0.2, 0.8, 252)
    volume = np.random.lognormal(mean=15, sigma=0.5, size=252).astype(int)

    # Inject a spike and a drop
    close[120] *= 1.08
    high[120] = close[120] * 1.01
    volume[120] *= 4
    close[200] *= 0.92
    low[200] = close[200] * 0.99
    volume[200] *= 5

    df = pd.DataFrame({
        "date": dates,
        "open": np.round(open_price, 2),
        "high": np.round(high, 2),
        "low": np.round(low, 2),
        "close": np.round(close, 2),
        "volume": volume,
    })
    df.to_csv(OUT / "stock_ohlcv.csv", index=False)
    print(f"Created stock_ohlcv.csv ({len(df)} rows)")


def macro_timeseries():
    """Monthly macroeconomic indicators (10 years)."""
    dates = pd.date_range("2015-01-01", periods=120, freq="MS")
    gdp = 18000 + np.cumsum(np.random.normal(50, 30, 120))
    cpi = 240 + np.cumsum(np.random.normal(0.2, 0.3, 120))
    unemployment = np.clip(5.0 + np.cumsum(np.random.normal(0, 0.1, 120)), 2.5, 12)
    fed_rate = np.clip(2.0 + np.cumsum(np.random.normal(0.01, 0.1, 120)), 0, 8)

    df = pd.DataFrame({
        "date": dates,
        "gdp_billions": np.round(gdp, 1),
        "cpi_index": np.round(cpi, 1),
        "unemployment_rate": np.round(unemployment, 1),
        "fed_funds_rate": np.round(fed_rate, 2),
    })
    df.to_csv(OUT / "macro_monthly.csv", index=False)
    print(f"Created macro_monthly.csv ({len(df)} rows)")


def business_kpi():
    """Daily business KPI data (1 year)."""
    dates = pd.date_range("2024-01-01", periods=365)
    base_revenue = 5000 + 2000 * np.sin(np.linspace(0, 4 * np.pi, 365))
    revenue = base_revenue + np.random.normal(0, 500, 365)
    users = np.clip(1000 + np.cumsum(np.random.normal(5, 10, 365)), 500, None).astype(int)
    conversion = np.clip(0.03 + np.random.normal(0, 0.005, 365), 0.01, 0.08)

    df = pd.DataFrame({
        "date": dates,
        "revenue": np.round(revenue, 2),
        "active_users": users,
        "conversion_rate": np.round(conversion, 4),
    })
    df.to_csv(OUT / "business_kpi.csv", index=False)
    print(f"Created business_kpi.csv ({len(df)} rows)")


def messy_dataset():
    """Intentionally messy dataset for robustness testing."""
    n = 150
    dates = pd.date_range("2023-06-01", periods=n)
    dates_str = [d.strftime("%m/%d/%Y") if i % 3 == 0
                 else d.strftime("%Y-%m-%d") if i % 3 == 1
                 else d.strftime("%d %b %Y")
                 for i, d in enumerate(dates)]

    values = 50 + np.cumsum(np.random.normal(0, 1, n))
    values[10] = np.nan
    values[25] = np.nan
    values[50] = np.nan

    category = np.random.choice(["A", "B", "A", "A"], n)
    volume = np.random.randint(100, 10000, n).astype(float)
    volume[15] = np.nan
    volume[45] = np.nan

    df = pd.DataFrame({
        "  Date  ": dates_str,
        "Price (USD)": np.round(values, 2),
        "Volume Traded": volume,
        "Category": category,
        "empty_col": [None] * n,
    })
    # Add a duplicate date
    dup = df.iloc[30:31].copy()
    df = pd.concat([df, dup], ignore_index=True)

    df.to_csv(OUT / "messy_data.csv", index=False)
    print(f"Created messy_data.csv ({len(df)} rows)")


if __name__ == "__main__":
    stock_ohlcv()
    macro_timeseries()
    business_kpi()
    messy_dataset()
    print("All sample datasets generated.")
