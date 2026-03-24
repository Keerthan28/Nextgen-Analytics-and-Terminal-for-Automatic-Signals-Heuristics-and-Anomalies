import io
import pytest
import numpy as np
import pandas as pd

from app.services.data_processor import (
    load_file,
    detect_schema,
    _normalize_columns,
    _is_datetime_series,
    prepare_chart_data,
    compute_stats,
)
from app.models.schemas import ColumnRole


class TestNormalizeColumns:
    def test_strips_and_lowercases(self):
        df = pd.DataFrame({"  Date  ": [1], "Price (USD)": [2], "Volume Traded": [3]})
        result = _normalize_columns(df)
        assert list(result.columns) == ["date", "price_usd", "volume_traded"]

    def test_deduplicates(self):
        df = pd.DataFrame([[1, 2]], columns=["a", "a"])
        result = _normalize_columns(df)
        assert len(result.columns) == len(set(result.columns))


class TestDatetimeDetection:
    def test_iso_dates(self):
        s = pd.Series(["2024-01-01", "2024-01-02", "2024-01-03"])
        assert _is_datetime_series(s) is True

    def test_us_format(self):
        s = pd.Series(["01/15/2024", "02/20/2024", "03/10/2024"])
        assert _is_datetime_series(s) is True

    def test_verbose_dates(self):
        s = pd.Series(["15 Jan 2024", "20 Feb 2024", "10 Mar 2024"])
        assert _is_datetime_series(s) is True

    def test_numeric_not_datetime(self):
        s = pd.Series([100, 200, 300])
        assert _is_datetime_series(s) is False

    def test_random_strings_not_datetime(self):
        s = pd.Series(["foo", "bar", "baz", "qux", "hello"])
        assert _is_datetime_series(s) is False

    def test_already_datetime_dtype(self):
        s = pd.to_datetime(pd.Series(["2024-01-01", "2024-01-02"]))
        assert _is_datetime_series(s) is True

    def test_empty_series(self):
        s = pd.Series(dtype=object)
        assert _is_datetime_series(s) is False


class TestSchemaDetection:
    def test_ohlcv_schema(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "open": [1, 2, 3, 4, 5],
            "high": [2, 3, 4, 5, 6],
            "low": [0.5, 1, 2, 3, 4],
            "close": [1.5, 2.5, 3.5, 4.5, 5.5],
            "volume": [100, 200, 300, 400, 500],
        })
        schema = detect_schema(df)
        assert schema.has_ohlc is True
        assert schema.datetime_column == "date"
        assert schema.volume_column == "volume"
        assert "close" in schema.value_columns

    def test_simple_timeseries(self):
        df = pd.DataFrame({
            "timestamp": ["2024-01-01", "2024-01-02", "2024-01-03"],
            "price": [10.5, 11.0, 10.8],
        })
        schema = detect_schema(df)
        assert schema.datetime_column == "timestamp"
        assert "price" in schema.value_columns
        assert schema.has_ohlc is False

    def test_no_date_column(self):
        df = pd.DataFrame({
            "metric_a": [1, 2, 3],
            "metric_b": [4, 5, 6],
        })
        schema = detect_schema(df)
        assert schema.datetime_column is None
        assert len(schema.value_columns) >= 1

    def test_category_detection(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=100),
            "value": np.random.randn(100),
            "sector": ["Tech"] * 100,
        })
        schema = detect_schema(df)
        sector_col = [m for m in schema.columns if m.column_name == "sector"]
        assert len(sector_col) == 1
        assert sector_col[0].role == ColumnRole.CATEGORY


class TestPrepareChartData:
    def test_basic_output(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=5),
            "close": [10, 11, 12, 11, 13],
        })
        schema = detect_schema(df)
        result = prepare_chart_data(df, schema)
        assert "x" in result
        assert "series" in result
        assert len(result["x"]) == 5

    def test_timeframe_filter(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=365),
            "close": np.random.randn(365).cumsum() + 100,
        })
        schema = detect_schema(df)
        result = prepare_chart_data(df, schema, timeframe="1M")
        assert len(result["x"]) < 365


class TestComputeStats:
    def test_stat_keys(self):
        df = pd.DataFrame({
            "date": pd.date_range("2024-01-01", periods=10),
            "price": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10],
        })
        schema = detect_schema(df)
        stats = compute_stats(df, schema)
        assert "price" in stats
        assert "mean" in stats["price"]
        assert stats["price"]["mean"] == 5.5

    def test_handles_missing(self):
        df = pd.DataFrame({
            "val": [1, None, 3, None, 5],
        })
        schema = detect_schema(df)
        stats = compute_stats(df, schema)
        assert "val" in stats
        assert stats["val"]["missing"] == 2
