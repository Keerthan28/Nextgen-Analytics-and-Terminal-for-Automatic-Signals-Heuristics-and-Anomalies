from __future__ import annotations
import numpy as np
import pandas as pd

from app.models.schemas import DatasetSchema, InsightItem, InsightReport, ColumnRole
from app.services.indicators import (
    rsi,
    rolling_volatility,
    simple_moving_average,
    drawdown,
)


def generate_insights(
    df: pd.DataFrame, schema: DatasetSchema, dataset_id: str, max_findings: int = 5
) -> InsightReport:
    findings: list[InsightItem] = []

    primary_col = _get_primary_value_col(schema)
    if primary_col is None or primary_col not in df.columns:
        return InsightReport(
            dataset_id=dataset_id,
            top_findings=[],
            summary="No numeric series found for analysis.",
        )

    series = df[primary_col].dropna()
    if len(series) < 5:
        return InsightReport(
            dataset_id=dataset_id,
            top_findings=[],
            summary="Not enough data points for meaningful analysis.",
        )

    dt_col = schema.datetime_column
    has_dates = dt_col is not None and dt_col in df.columns

    findings.extend(_return_insights(series, primary_col))
    findings.extend(_spike_drop_detection(series, df, primary_col, dt_col))
    findings.extend(_ma_crossover(series, df, primary_col, dt_col))
    findings.extend(_rsi_insights(series, primary_col))
    findings.extend(_volatility_insights(series, primary_col))
    findings.extend(_drawdown_insights(series, primary_col))

    if schema.volume_column and schema.volume_column in df.columns:
        findings.extend(_volume_insights(df[schema.volume_column]))

    findings.sort(key=lambda f: _severity_rank(f.severity), reverse=True)
    top = findings[:max_findings]

    summary_parts = [f.title for f in top]
    summary = "Key findings: " + "; ".join(summary_parts) if summary_parts else "No significant findings."

    return InsightReport(dataset_id=dataset_id, top_findings=top, summary=summary)


def _get_primary_value_col(schema: DatasetSchema) -> str | None:
    for m in schema.columns:
        if m.role == ColumnRole.CLOSE:
            return m.column_name
    return schema.value_columns[0] if schema.value_columns else None


def _severity_rank(sev: str) -> int:
    return {"critical": 4, "warning": 3, "info": 2, "neutral": 1}.get(sev, 0)


def _return_insights(series: pd.Series, col: str) -> list[InsightItem]:
    items = []
    for window, label in [(5, "5-period"), (20, "20-period"), (60, "60-period")]:
        if len(series) < window + 1:
            continue
        ret = (series.iloc[-1] / series.iloc[-window] - 1) * 100
        direction = "gained" if ret > 0 else "lost"
        sev = "warning" if abs(ret) > 10 else "info"
        items.append(InsightItem(
            title=f"{label} return: {ret:+.2f}%",
            description=f"{col} has {direction} {abs(ret):.2f}% over the last {window} periods.",
            severity=sev,
            metric="return",
            value=round(ret, 4),
            rule=f"pct_return_window_{window}",
        ))
    return items


def _spike_drop_detection(
    series: pd.Series, df: pd.DataFrame, col: str, dt_col: str | None
) -> list[InsightItem]:
    items = []
    pct = series.pct_change() * 100
    z = (pct - pct.mean()) / pct.std() if pct.std() > 0 else pct * 0

    spikes = z[z > 2.5]
    drops = z[z < -2.5]

    if len(spikes) > 0:
        idx = spikes.idxmax()
        ts = _get_timestamp(df, dt_col, idx)
        items.append(InsightItem(
            title=f"Largest spike detected: {pct.loc[idx]:+.2f}%",
            description=f"Abnormal upward move at index {idx}" + (f" ({ts})" if ts else ""),
            severity="warning",
            metric="spike_z",
            value=round(float(z.loc[idx]), 4),
            rule="z_score_spike_gt_2.5",
            timestamp=ts,
        ))

    if len(drops) > 0:
        idx = drops.idxmin()
        ts = _get_timestamp(df, dt_col, idx)
        items.append(InsightItem(
            title=f"Largest drop detected: {pct.loc[idx]:+.2f}%",
            description=f"Abnormal downward move at index {idx}" + (f" ({ts})" if ts else ""),
            severity="critical",
            metric="drop_z",
            value=round(float(z.loc[idx]), 4),
            rule="z_score_drop_lt_-2.5",
            timestamp=ts,
        ))

    return items


def _ma_crossover(
    series: pd.Series, df: pd.DataFrame, col: str, dt_col: str | None
) -> list[InsightItem]:
    items = []
    if len(series) < 50:
        return items

    sma20 = simple_moving_average(series, 20)
    sma50 = simple_moving_average(series, 50)
    cross = sma20 - sma50
    cross_sign = np.sign(cross)
    changes = cross_sign.diff().dropna()

    golden = changes[changes > 0]
    death = changes[changes < 0]

    if len(golden) > 0:
        idx = golden.index[-1]
        ts = _get_timestamp(df, dt_col, idx)
        items.append(InsightItem(
            title="Golden cross (SMA20 > SMA50)",
            description=f"Short-term MA crossed above long-term MA" + (f" on {ts}" if ts else ""),
            severity="info",
            rule="ma_crossover_golden",
            timestamp=ts,
        ))

    if len(death) > 0:
        idx = death.index[-1]
        ts = _get_timestamp(df, dt_col, idx)
        items.append(InsightItem(
            title="Death cross (SMA20 < SMA50)",
            description=f"Short-term MA crossed below long-term MA" + (f" on {ts}" if ts else ""),
            severity="warning",
            rule="ma_crossover_death",
            timestamp=ts,
        ))

    return items


def _rsi_insights(series: pd.Series, col: str) -> list[InsightItem]:
    items = []
    if len(series) < 15:
        return items
    r = rsi(series, 14)
    last_rsi = r.iloc[-1]
    if pd.isna(last_rsi):
        return items

    if last_rsi > 70:
        items.append(InsightItem(
            title=f"RSI overbought ({last_rsi:.1f})",
            description=f"{col} RSI(14) is above 70, indicating potentially overbought conditions.",
            severity="warning",
            metric="rsi",
            value=round(float(last_rsi), 2),
            rule="rsi_overbought_gt_70",
        ))
    elif last_rsi < 30:
        items.append(InsightItem(
            title=f"RSI oversold ({last_rsi:.1f})",
            description=f"{col} RSI(14) is below 30, indicating potentially oversold conditions.",
            severity="warning",
            metric="rsi",
            value=round(float(last_rsi), 2),
            rule="rsi_oversold_lt_30",
        ))
    return items


def _volatility_insights(series: pd.Series, col: str) -> list[InsightItem]:
    items = []
    if len(series) < 25:
        return items
    vol = rolling_volatility(series, 20)
    recent = vol.iloc[-5:].mean()
    overall = vol.mean()
    if pd.isna(recent) or pd.isna(overall) or overall == 0:
        return items

    ratio = recent / overall
    if ratio > 1.5:
        items.append(InsightItem(
            title=f"Elevated volatility ({ratio:.1f}x average)",
            description=f"Recent 5-period volatility is {ratio:.1f}x the historical average for {col}.",
            severity="warning",
            metric="vol_ratio",
            value=round(float(ratio), 4),
            rule="volatility_ratio_gt_1.5",
        ))
    return items


def _drawdown_insights(series: pd.Series, col: str) -> list[InsightItem]:
    items = []
    dd = drawdown(series)
    max_dd = dd.min()
    if pd.isna(max_dd):
        return items

    items.append(InsightItem(
        title=f"Max drawdown: {max_dd * 100:.2f}%",
        description=f"The maximum peak-to-trough decline for {col} is {max_dd * 100:.2f}%.",
        severity="critical" if max_dd < -0.20 else "info",
        metric="max_drawdown",
        value=round(float(max_dd), 6),
        rule="max_drawdown",
    ))
    return items


def _volume_insights(vol_series: pd.Series) -> list[InsightItem]:
    items = []
    if len(vol_series) < 20:
        return items
    recent_avg = vol_series.iloc[-5:].mean()
    overall_avg = vol_series.mean()
    if overall_avg == 0 or pd.isna(recent_avg):
        return items
    ratio = recent_avg / overall_avg
    if ratio > 2.0:
        items.append(InsightItem(
            title=f"Volume surge ({ratio:.1f}x average)",
            description=f"Recent volume is {ratio:.1f}x the historical average.",
            severity="warning",
            metric="volume_ratio",
            value=round(float(ratio), 4),
            rule="abnormal_volume_ratio_gt_2",
        ))
    return items


def _get_timestamp(df: pd.DataFrame, dt_col: str | None, idx) -> str | None:
    if dt_col is None or dt_col not in df.columns:
        return None
    try:
        val = df.loc[idx, dt_col]
        return str(val)
    except (KeyError, IndexError):
        return None
