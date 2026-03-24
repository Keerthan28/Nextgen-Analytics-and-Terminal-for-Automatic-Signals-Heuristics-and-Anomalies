import numpy as np
import pandas as pd
import pytest

from app.models.schemas import DatasetSchema, ColumnMapping, ColumnRole
from app.services.insights import generate_insights


def _make_schema(cols, dt_col=None, value_cols=None, vol_col=None, has_ohlc=False):
    return DatasetSchema(
        columns=cols,
        row_count=0,
        datetime_column=dt_col,
        value_columns=value_cols or [],
        volume_column=vol_col,
        has_ohlc=has_ohlc,
    )


class TestInsightGeneration:
    def test_basic_return_insights(self):
        dates = pd.date_range("2024-01-01", periods=100)
        values = 100 + np.cumsum(np.random.normal(0.5, 1, 100))
        df = pd.DataFrame({"date": dates, "price": values})
        schema = _make_schema(
            [ColumnMapping(column_name="date", role=ColumnRole.DATETIME),
             ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            dt_col="date",
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test1")
        assert len(report.top_findings) > 0
        assert report.summary != ""

    def test_spike_detection(self):
        values = [100.0] * 50
        values[25] = 200.0  # 100% spike
        df = pd.DataFrame({"price": values})
        schema = _make_schema(
            [ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test_spike")
        titles = [f.title for f in report.top_findings]
        assert any("spike" in t.lower() for t in titles)

    def test_no_data(self):
        df = pd.DataFrame({"price": [1.0, 2.0]})
        schema = _make_schema(
            [ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test_nodata")
        assert "Not enough" in report.summary

    def test_no_numeric(self):
        df = pd.DataFrame({"text": ["a", "b", "c"]})
        schema = _make_schema(
            [ColumnMapping(column_name="text", role=ColumnRole.CATEGORY)],
        )
        report = generate_insights(df, schema, "test_no_numeric")
        assert "No numeric" in report.summary

    def test_rsi_overbought(self):
        values = list(range(1, 52))  # steady uptrend
        df = pd.DataFrame({"date": pd.date_range("2024-01-01", periods=51), "price": [float(v) for v in values]})
        schema = _make_schema(
            [ColumnMapping(column_name="date", role=ColumnRole.DATETIME),
             ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            dt_col="date",
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test_rsi", max_findings=10)
        titles = " ".join(f.title for f in report.top_findings)
        assert "RSI" in titles or "overbought" in titles.lower()

    def test_drawdown_detected(self):
        values = list(range(100, 150)) + list(range(150, 100, -1))
        df = pd.DataFrame({"price": [float(v) for v in values]})
        schema = _make_schema(
            [ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test_dd")
        titles = " ".join(f.title.lower() for f in report.top_findings)
        assert "drawdown" in titles

    def test_volume_surge(self):
        dates = pd.date_range("2024-01-01", periods=100)
        prices = 100 + np.cumsum(np.random.normal(0, 1, 100))
        volume = [1000.0] * 95 + [5000.0] * 5
        df = pd.DataFrame({"date": dates, "price": prices, "volume": volume})
        schema = _make_schema(
            [ColumnMapping(column_name="date", role=ColumnRole.DATETIME),
             ColumnMapping(column_name="price", role=ColumnRole.VALUE),
             ColumnMapping(column_name="volume", role=ColumnRole.VOLUME)],
            dt_col="date",
            value_cols=["price"],
            vol_col="volume",
        )
        report = generate_insights(df, schema, "test_vol")
        titles = " ".join(f.title.lower() for f in report.top_findings)
        assert "volume" in titles


class TestInsightTraceability:
    def test_all_findings_have_rule(self):
        dates = pd.date_range("2024-01-01", periods=100)
        values = 100 + np.cumsum(np.random.normal(0.5, 1, 100))
        df = pd.DataFrame({"date": dates, "price": values})
        schema = _make_schema(
            [ColumnMapping(column_name="date", role=ColumnRole.DATETIME),
             ColumnMapping(column_name="price", role=ColumnRole.VALUE)],
            dt_col="date",
            value_cols=["price"],
        )
        report = generate_insights(df, schema, "test_trace")
        for finding in report.top_findings:
            assert finding.rule != "", f"Finding '{finding.title}' has no rule"
