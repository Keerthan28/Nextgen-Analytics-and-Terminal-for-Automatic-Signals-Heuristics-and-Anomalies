from __future__ import annotations
import io
import re
import hashlib
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
from dateutil import parser as date_parser

from app.models.schemas import (
    ColumnMapping, ColumnRole, DatasetSchema, DatasetType,
)

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

_datasets: dict[str, pd.DataFrame] = {}
_schemas: dict[str, DatasetSchema] = {}


def _generate_id(filename: str, content_bytes: bytes) -> str:
    h = hashlib.sha256(content_bytes[:4096] + filename.encode()).hexdigest()[:12]
    return h


def load_file(filename: str, content: bytes) -> tuple[str, pd.DataFrame]:
    dataset_id = _generate_id(filename, content)
    buf = io.BytesIO(content)

    if filename.lower().endswith((".xlsx", ".xls")):
        df = pd.read_excel(buf, engine="openpyxl")
    else:
        for enc in ("utf-8", "latin-1", "cp1252"):
            try:
                buf.seek(0)
                df = pd.read_csv(buf, encoding=enc)
                break
            except (UnicodeDecodeError, pd.errors.ParserError):
                continue
        else:
            raise ValueError(f"Unable to parse {filename}")

    df = _normalize_columns(df)
    _datasets[dataset_id] = df
    return dataset_id, df


def get_dataset(dataset_id: str) -> Optional[pd.DataFrame]:
    return _datasets.get(dataset_id)


def get_schema(dataset_id: str) -> Optional[DatasetSchema]:
    return _schemas.get(dataset_id)


def set_schema(dataset_id: str, schema: DatasetSchema):
    _schemas[dataset_id] = schema


def _normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    rename_map = {}
    for col in df.columns:
        clean = re.sub(r"[^\w]+", "_", str(col).strip()).strip("_").lower()
        rename_map[col] = clean
    df = df.rename(columns=rename_map)
    df = df.loc[:, ~df.columns.duplicated()]
    return df


# ---------------------------------------------------------------------------
# Schema detection
# ---------------------------------------------------------------------------

GEO_KEYWORDS = ("lat", "lon", "latitude", "longitude", "lat_long", "zip_code", "zip")
ID_KEYWORDS = ("id", "customer_id", "user_id", "account", "key", "index")
IGNORE_KEYWORDS = ("count",)

def detect_schema(df: pd.DataFrame) -> DatasetSchema:
    mappings: list[ColumnMapping] = []
    datetime_col = None
    value_cols: list[str] = []
    category_cols: list[str] = []
    volume_col = None
    ohlc_found = {"open": False, "high": False, "low": False, "close": False}

    for col in df.columns:
        role = _infer_role(df[col], col, ohlc_found, len(df))
        mappings.append(ColumnMapping(column_name=col, role=role))

        if role == ColumnRole.DATETIME and datetime_col is None:
            datetime_col = col
        elif role in (ColumnRole.CLOSE, ColumnRole.VALUE):
            value_cols.append(col)
        elif role == ColumnRole.VOLUME:
            volume_col = col
        elif role == ColumnRole.CATEGORY:
            category_cols.append(col)

    has_ohlc = all(ohlc_found.values())

    if not value_cols:
        for m in mappings:
            if m.role == ColumnRole.IGNORE and pd.api.types.is_numeric_dtype(df[m.column_name]):
                value_cols.append(m.column_name)
                m.role = ColumnRole.VALUE

    dataset_type = _classify_dataset(df, datetime_col, value_cols, category_cols, has_ohlc)

    target_col = _detect_target(df, category_cols, value_cols)

    return DatasetSchema(
        columns=mappings,
        row_count=len(df),
        dataset_type=dataset_type,
        datetime_column=datetime_col,
        value_columns=value_cols,
        category_columns=category_cols,
        volume_column=volume_col,
        target_column=target_col,
        has_ohlc=has_ohlc,
    )


def _classify_dataset(
    df: pd.DataFrame,
    datetime_col: str | None,
    value_cols: list[str],
    category_cols: list[str],
    has_ohlc: bool,
) -> DatasetType:
    if has_ohlc and datetime_col:
        return DatasetType.TIMESERIES

    if datetime_col:
        dt_series = pd.to_datetime(df[datetime_col], errors="coerce").dropna()
        if len(dt_series) > 10:
            nunique_ratio = dt_series.nunique() / len(dt_series)
            if nunique_ratio > 0.5:
                return DatasetType.TIMESERIES

    if len(category_cols) >= 3 and not datetime_col:
        return DatasetType.TABULAR

    if len(category_cols) >= 2 and len(value_cols) >= 2 and not datetime_col:
        return DatasetType.TABULAR

    if not datetime_col and len(value_cols) >= 1:
        return DatasetType.TABULAR

    return DatasetType.TIMESERIES if datetime_col else DatasetType.TABULAR


def _detect_target(df: pd.DataFrame, cat_cols: list[str], val_cols: list[str]) -> str | None:
    target_keywords = (
        "target", "label", "churn", "class", "outcome", "status",
        "default", "fraud", "spam", "result", "flag",
    )
    for col in cat_cols:
        if any(kw in col.lower() for kw in target_keywords):
            if df[col].nunique() <= 10:
                return col
    for col in val_cols:
        if any(kw in col.lower() for kw in target_keywords):
            if df[col].nunique() <= 10:
                return col
    return None


def _infer_role(series: pd.Series, col_name: str, ohlc_found: dict, n_rows: int) -> ColumnRole:
    name = col_name.lower()

    if any(name == kw or name.endswith("_" + kw) for kw in IGNORE_KEYWORDS):
        if pd.api.types.is_numeric_dtype(series) and series.nunique() <= 1:
            return ColumnRole.IGNORE

    if any(name == kw or name.endswith("_" + kw) for kw in ID_KEYWORDS):
        return ColumnRole.IDENTIFIER

    if any(kw in name for kw in GEO_KEYWORDS):
        return ColumnRole.GEO

    date_keywords = ("date", "time", "timestamp", "datetime", "dt", "period")
    if any(k in name for k in date_keywords):
        if _is_datetime_series(series):
            return ColumnRole.DATETIME

    if _is_datetime_series(series):
        return ColumnRole.DATETIME

    if name in ("open", "open_price") and not ohlc_found["open"]:
        ohlc_found["open"] = True
        return ColumnRole.OPEN
    if name in ("high", "high_price") and not ohlc_found["high"]:
        ohlc_found["high"] = True
        return ColumnRole.HIGH
    if name in ("low", "low_price") and not ohlc_found["low"]:
        ohlc_found["low"] = True
        return ColumnRole.LOW
    if name in ("close", "close_price", "adj_close", "adj close", "adjusted_close") and not ohlc_found["close"]:
        ohlc_found["close"] = True
        return ColumnRole.CLOSE

    vol_keywords = ("volume", "vol", "qty", "quantity", "shares")
    if any(k == name or name.startswith(k) for k in vol_keywords):
        return ColumnRole.VOLUME

    if pd.api.types.is_numeric_dtype(series):
        nunique = series.nunique()
        if nunique <= 2 and n_rows > 20:
            return ColumnRole.CATEGORY
        price_keywords = ("price", "value", "amount", "rate", "index", "level", "return", "pnl")
        if any(k in name for k in price_keywords):
            return ColumnRole.VALUE
        return ColumnRole.VALUE

    if series.dtype == object:
        nunique_ratio = series.nunique() / max(n_rows, 1)
        if nunique_ratio > 0.8:
            return ColumnRole.IDENTIFIER
        if nunique_ratio < 0.3:
            return ColumnRole.CATEGORY

    return ColumnRole.IGNORE


def _is_datetime_series(series: pd.Series, sample_size: int = 20) -> bool:
    if pd.api.types.is_datetime64_any_dtype(series):
        return True
    if not series.dtype == object:
        return False
    sample = series.dropna().head(sample_size)
    if len(sample) == 0:
        return False
    parsed = 0
    for val in sample:
        try:
            date_parser.parse(str(val), fuzzy=False)
            parsed += 1
        except (ValueError, OverflowError, TypeError):
            pass
    return parsed / len(sample) > 0.7


# ---------------------------------------------------------------------------
# Time-series chart data (existing)
# ---------------------------------------------------------------------------

def prepare_chart_data(
    df: pd.DataFrame,
    schema: DatasetSchema,
    series_cols: list[str] | None = None,
    timeframe: str | None = None,
) -> dict:
    result: dict = {}

    if schema.datetime_column:
        dt_col = schema.datetime_column
        df = df.copy()
        df[dt_col] = pd.to_datetime(df[dt_col], errors="coerce")
        df = df.dropna(subset=[dt_col]).sort_values(dt_col)

        if timeframe:
            df = _apply_timeframe(df, dt_col, timeframe)

        result["x"] = df[dt_col].dt.strftime("%Y-%m-%dT%H:%M:%S").tolist()
        result["date_range"] = {
            "start": str(df[dt_col].min()),
            "end": str(df[dt_col].max()),
        }
    else:
        result["x"] = list(range(len(df)))

    cols = series_cols or schema.value_columns
    result["series"] = {}
    for col in cols:
        if col in df.columns:
            result["series"][col] = df[col].where(df[col].notna(), None).tolist()

    if schema.has_ohlc:
        ohlc_map = {}
        for m in schema.columns:
            if m.role in (ColumnRole.OPEN, ColumnRole.HIGH, ColumnRole.LOW, ColumnRole.CLOSE):
                ohlc_map[m.role.value] = df[m.column_name].where(df[m.column_name].notna(), None).tolist()
        result["ohlc"] = ohlc_map

    if schema.volume_column and schema.volume_column in df.columns:
        result["volume"] = df[schema.volume_column].where(df[schema.volume_column].notna(), None).tolist()

    return result


def _apply_timeframe(df: pd.DataFrame, dt_col: str, timeframe: str) -> pd.DataFrame:
    now = df[dt_col].max()
    mapping = {
        "1D": pd.Timedelta(days=1),
        "5D": pd.Timedelta(days=5),
        "1M": pd.DateOffset(months=1),
        "3M": pd.DateOffset(months=3),
        "6M": pd.DateOffset(months=6),
        "1Y": pd.DateOffset(years=1),
        "YTD": None,
        "MAX": None,
    }
    if timeframe == "YTD":
        start = pd.Timestamp(year=now.year, month=1, day=1)
        return df[df[dt_col] >= start]
    offset = mapping.get(timeframe)
    if offset is None:
        return df
    return df[df[dt_col] >= now - offset]


# ---------------------------------------------------------------------------
# Tabular chart data (new)
# ---------------------------------------------------------------------------

def prepare_tabular_chart(
    df: pd.DataFrame,
    schema: DatasetSchema,
    chart_type: str,
    x_col: str | None = None,
    y_col: str | None = None,
    color_col: str | None = None,
    agg: str = "count",
) -> dict:
    if chart_type == "histogram":
        return _build_histogram(df, x_col or (schema.value_columns[0] if schema.value_columns else None), color_col)
    elif chart_type == "bar":
        return _build_bar(df, x_col, y_col, color_col, agg)
    elif chart_type == "scatter":
        return _build_scatter(df, x_col, y_col, color_col)
    elif chart_type == "box":
        return _build_box(df, x_col, y_col)
    elif chart_type == "heatmap":
        return _build_heatmap(df, schema)
    elif chart_type == "pie":
        return _build_pie(df, x_col)
    else:
        return _build_histogram(df, x_col, color_col)


def _build_histogram(df: pd.DataFrame, col: str | None, color_col: str | None) -> dict:
    if not col or col not in df.columns:
        return {"traces": [], "layout": {"title": "No column selected"}}

    traces = []
    if color_col and color_col in df.columns:
        for val in df[color_col].dropna().unique()[:10]:
            subset = df[df[color_col] == val][col].dropna()
            traces.append({
                "type": "histogram",
                "x": subset.tolist(),
                "name": _trunc(str(val), 22),
                "opacity": 0.7,
            })
    else:
        traces.append({
            "type": "histogram",
            "x": df[col].dropna().tolist(),
            "name": col,
            "opacity": 0.8,
        })

    return {
        "traces": traces,
        "layout": {
            "title": f"Distribution of {col}",
            "xaxis_title": col,
            "yaxis_title": "Count",
            "barmode": "overlay" if color_col else "relative",
        },
    }


def _build_bar(df: pd.DataFrame, x_col: str | None, y_col: str | None,
               color_col: str | None, agg: str) -> dict:
    if not x_col or x_col not in df.columns:
        return {"traces": [], "layout": {"title": "No column selected"}}

    if y_col and y_col in df.columns:
        if color_col and color_col in df.columns:
            pivot = df.groupby([x_col, color_col])[y_col].agg(agg).reset_index()
            traces = []
            for cv in pivot[color_col].unique()[:10]:
                sub = pivot[pivot[color_col] == cv]
                traces.append({
                    "type": "bar",
                    "x": [_trunc(v) for v in sub[x_col].astype(str)],
                    "y": [_safe_float(v) for v in sub[y_col]],
                    "name": _trunc(str(cv), 22),
                })
        else:
            grouped = df.groupby(x_col)[y_col].agg(agg).reset_index()
            traces = [{
                "type": "bar",
                "x": [_trunc(v) for v in grouped[x_col].astype(str)],
                "y": [_safe_float(v) for v in grouped[y_col]],
                "name": f"{agg}({y_col})",
            }]
    else:
        counts = df[x_col].value_counts().head(20)
        traces = [{
            "type": "bar",
            "x": [_trunc(v) for v in counts.index.astype(str)],
            "y": counts.values.tolist(),
            "name": "Count",
        }]

    return {
        "traces": traces,
        "layout": {
            "title": f"{x_col}" + (f" by {y_col}" if y_col else " — counts"),
            "xaxis_title": x_col,
            "yaxis_title": y_col or "Count",
            "barmode": "group" if color_col else "relative",
        },
    }


def _build_scatter(df: pd.DataFrame, x_col: str | None, y_col: str | None,
                   color_col: str | None) -> dict:
    if not x_col or not y_col or x_col not in df.columns or y_col not in df.columns:
        return {"traces": [], "layout": {"title": "Select x and y columns"}}

    sample = df[[x_col, y_col]].copy()
    if color_col and color_col in df.columns:
        sample[color_col] = df[color_col]
    sample = sample.dropna(subset=[x_col, y_col])
    if len(sample) > 5000:
        sample = sample.sample(5000, random_state=42)

    traces = []
    if color_col and color_col in sample.columns:
        for val in sample[color_col].unique()[:10]:
            sub = sample[sample[color_col] == val]
            traces.append({
                "type": "scatter",
                "mode": "markers",
                "x": [_safe_float(v) for v in sub[x_col]],
                "y": [_safe_float(v) for v in sub[y_col]],
                "name": str(val),
                "marker": {"size": 4, "opacity": 0.6},
            })
    else:
        traces.append({
            "type": "scatter",
            "mode": "markers",
            "x": [_safe_float(v) for v in sample[x_col]],
            "y": [_safe_float(v) for v in sample[y_col]],
            "name": f"{x_col} vs {y_col}",
            "marker": {"size": 4, "opacity": 0.5},
        })

    return {
        "traces": traces,
        "layout": {
            "title": f"{x_col} vs {y_col}",
            "xaxis_title": x_col,
            "yaxis_title": y_col,
        },
    }


def _build_box(df: pd.DataFrame, x_col: str | None, y_col: str | None) -> dict:
    if not y_col or y_col not in df.columns:
        return {"traces": [], "layout": {"title": "Select a numeric column"}}

    traces = []
    if x_col and x_col in df.columns:
        for val in df[x_col].dropna().unique()[:15]:
            sub = df[df[x_col] == val][y_col].dropna()
            traces.append({
                "type": "box",
                "y": sub.tolist(),
                "name": _trunc(str(val), 22),
            })
    else:
        traces.append({
            "type": "box",
            "y": df[y_col].dropna().tolist(),
            "name": y_col,
        })

    return {
        "traces": traces,
        "layout": {
            "title": f"Distribution of {y_col}" + (f" by {x_col}" if x_col else ""),
            "yaxis_title": y_col,
        },
    }


def _build_heatmap(df: pd.DataFrame, schema: DatasetSchema) -> dict:
    num_cols = [c for c in schema.value_columns if c in df.columns][:15]
    if len(num_cols) < 2:
        return {"traces": [], "layout": {"title": "Need at least 2 numeric columns"}}

    corr = df[num_cols].corr()
    return {
        "traces": [{
            "type": "heatmap",
            "z": corr.values.round(3).tolist(),
            "x": [_trunc(c, 16) for c in corr.columns],
            "y": [_trunc(c, 16) for c in corr.index],
            "colorscale": [
                [0, "#f85149"], [0.5, "#0d1117"], [1, "#3fb950"]
            ],
            "zmin": -1,
            "zmax": 1,
        }],
        "layout": {
            "title": "Correlation Matrix",
            "height": max(400, len(num_cols) * 30 + 100),
        },
    }


def _build_pie(df: pd.DataFrame, col: str | None) -> dict:
    if not col or col not in df.columns:
        return {"traces": [], "layout": {"title": "Select a column"}}

    counts = df[col].value_counts().head(12)
    return {
        "traces": [{
            "type": "pie",
            "labels": [_trunc(v, 22) for v in counts.index.astype(str)],
            "values": counts.values.tolist(),
            "hole": 0.4,
            "textinfo": "label+percent",
        }],
        "layout": {"title": f"Distribution of {col}"},
    }


def _trunc(text: str, max_len: int = 18) -> str:
    """Truncate long tick labels with ellipsis to prevent axis overflow."""
    s = str(text)
    return s[:max_len - 1] + "…" if len(s) > max_len else s


def _safe_float(v):
    try:
        f = float(v)
        return None if np.isnan(f) else round(f, 4)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Tabular profiling
# ---------------------------------------------------------------------------

def build_tabular_profile(df: pd.DataFrame, schema: DatasetSchema) -> dict:
    profile: dict = {
        "numeric_summary": {},
        "category_summary": {},
        "correlations": {},
        "target_breakdown": None,
        "suggested_charts": [],
    }

    for col in schema.value_columns[:15]:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        profile["numeric_summary"][col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 4) if len(s) else None,
            "std": round(float(s.std()), 4) if len(s) > 1 else None,
            "min": round(float(s.min()), 4) if len(s) else None,
            "q25": round(float(s.quantile(0.25)), 4) if len(s) else None,
            "median": round(float(s.median()), 4) if len(s) else None,
            "q75": round(float(s.quantile(0.75)), 4) if len(s) else None,
            "max": round(float(s.max()), 4) if len(s) else None,
            "missing": int(df[col].isna().sum()),
            "nunique": int(s.nunique()),
        }

    for col in schema.category_columns[:15]:
        if col not in df.columns:
            continue
        vc = df[col].value_counts().head(10)
        profile["category_summary"][col] = {
            "nunique": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in vc.items()},
            "missing": int(df[col].isna().sum()),
        }

    num_cols = [c for c in schema.value_columns if c in df.columns][:15]
    if len(num_cols) >= 2:
        corr = df[num_cols].corr()
        top_corr = []
        for i in range(len(num_cols)):
            for j in range(i + 1, len(num_cols)):
                r = corr.iloc[i, j]
                if not np.isnan(r):
                    top_corr.append({
                        "col_a": num_cols[i],
                        "col_b": num_cols[j],
                        "r": round(float(r), 4),
                    })
        top_corr.sort(key=lambda x: abs(x["r"]), reverse=True)
        profile["correlations"] = top_corr[:20]

    if schema.target_column and schema.target_column in df.columns:
        tc = schema.target_column
        breakdown: dict = {"column": tc}
        vc = df[tc].value_counts()
        breakdown["distribution"] = {str(k): int(v) for k, v in vc.items()}
        breakdown["rates"] = {str(k): round(v / len(df) * 100, 2) for k, v in vc.items()}
        profile["target_breakdown"] = breakdown

    profile["suggested_charts"] = _suggest_charts(schema, profile)

    return profile


def _suggest_charts(schema: DatasetSchema, profile: dict) -> list[dict]:
    suggestions = []

    if schema.target_column:
        tc = schema.target_column
        suggestions.append({
            "title": f"{tc} Distribution",
            "chart_type": "pie",
            "x_col": tc,
            "description": f"Breakdown of {tc} values",
        })

        for cat in schema.category_columns[:5]:
            if cat == tc:
                continue
            suggestions.append({
                "title": f"{tc} by {cat}",
                "chart_type": "bar",
                "x_col": cat,
                "y_col": None,
                "color_col": tc,
                "description": f"Compare {tc} across {cat}",
            })

        for num in schema.value_columns[:5]:
            suggestions.append({
                "title": f"{num} by {tc}",
                "chart_type": "box",
                "x_col": tc,
                "y_col": num,
                "description": f"Distribution of {num} split by {tc}",
            })

    for num in schema.value_columns[:3]:
        suggestions.append({
            "title": f"{num} Distribution",
            "chart_type": "histogram",
            "x_col": num,
            "color_col": schema.target_column,
            "description": f"Histogram of {num}",
        })

    if len(schema.value_columns) >= 2:
        suggestions.append({
            "title": "Correlation Matrix",
            "chart_type": "heatmap",
            "description": "Correlations between all numeric columns",
        })

    corrs = profile.get("correlations", [])
    if corrs:
        top = corrs[0]
        suggestions.append({
            "title": f"{top['col_a']} vs {top['col_b']} (r={top['r']})",
            "chart_type": "scatter",
            "x_col": top["col_a"],
            "y_col": top["col_b"],
            "color_col": schema.target_column,
            "description": "Strongest correlation pair",
        })

    return suggestions[:12]


# ---------------------------------------------------------------------------
# Stats (works for both modes)
# ---------------------------------------------------------------------------

def compute_stats(df: pd.DataFrame, schema: DatasetSchema) -> dict:
    stats: dict = {}
    for col in schema.value_columns:
        if col not in df.columns:
            continue
        s = df[col].dropna()
        stats[col] = {
            "count": int(s.count()),
            "mean": round(float(s.mean()), 4) if len(s) else None,
            "std": round(float(s.std()), 4) if len(s) > 1 else None,
            "min": round(float(s.min()), 4) if len(s) else None,
            "max": round(float(s.max()), 4) if len(s) else None,
            "median": round(float(s.median()), 4) if len(s) else None,
            "missing": int(df[col].isna().sum()),
        }
    return stats
