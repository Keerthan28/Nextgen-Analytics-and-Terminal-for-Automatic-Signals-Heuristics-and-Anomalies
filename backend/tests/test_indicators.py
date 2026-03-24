import numpy as np
import pandas as pd
import pytest

from app.services.indicators import (
    simple_moving_average,
    exponential_moving_average,
    bollinger_bands,
    rsi,
    macd,
    rolling_volatility,
    drawdown,
    abnormal_volume,
    compute_indicator,
)


class TestSMA:
    def test_constant_series(self):
        s = pd.Series([10.0] * 20)
        result = simple_moving_average(s, 5)
        assert all(abs(v - 10.0) < 1e-9 for v in result)

    def test_window_size(self):
        s = pd.Series(range(1, 11), dtype=float)
        result = simple_moving_average(s, 3)
        assert abs(result.iloc[9] - 9.0) < 1e-9  # avg of 8, 9, 10

    def test_length_preserved(self):
        s = pd.Series(range(50), dtype=float)
        assert len(simple_moving_average(s, 20)) == 50


class TestEMA:
    def test_constant_series(self):
        s = pd.Series([5.0] * 20)
        result = exponential_moving_average(s, 10)
        assert all(abs(v - 5.0) < 1e-9 for v in result)

    def test_length_preserved(self):
        s = pd.Series(range(100), dtype=float)
        assert len(exponential_moving_average(s, 20)) == 100


class TestBollinger:
    def test_band_structure(self):
        s = pd.Series(np.random.randn(100).cumsum() + 100)
        bands = bollinger_bands(s, 20, 2.0)
        assert "upper" in bands
        assert "middle" in bands
        assert "lower" in bands
        assert all(bands["upper"] >= bands["middle"])
        assert all(bands["middle"] >= bands["lower"])


class TestRSI:
    def test_uptrend_high_rsi(self):
        s = pd.Series(range(1, 51), dtype=float)
        result = rsi(s, 14)
        assert result.iloc[-1] > 90

    def test_range(self):
        np.random.seed(1)
        s = pd.Series(np.random.randn(200).cumsum() + 100)
        result = rsi(s, 14).dropna()
        assert result.min() >= 0
        assert result.max() <= 100


class TestMACD:
    def test_keys(self):
        s = pd.Series(np.random.randn(100).cumsum() + 100)
        result = macd(s)
        assert "macd" in result
        assert "signal" in result
        assert "histogram" in result
        assert len(result["macd"]) == 100

    def test_histogram_is_difference(self):
        s = pd.Series(np.random.randn(100).cumsum() + 100)
        result = macd(s)
        diff = result["macd"] - result["signal"]
        np.testing.assert_array_almost_equal(result["histogram"], diff)


class TestVolatility:
    def test_positive(self):
        np.random.seed(0)
        s = pd.Series(np.random.randn(100).cumsum() + 100)
        vol = rolling_volatility(s, 20).dropna()
        assert (vol >= 0).all()


class TestDrawdown:
    def test_max_at_peak(self):
        s = pd.Series([100, 110, 105, 120, 90, 95])
        dd = drawdown(s)
        assert dd.iloc[0] == 0  # first value at cummax
        assert dd.min() == (90 - 120) / 120  # max drawdown from 120 to 90


class TestAbnormalVolume:
    def test_spike_detection(self):
        vol = pd.Series([100] * 50)
        vol.iloc[25] = 1000  # spike
        result = abnormal_volume(vol, 20, 2.0)
        assert result.iloc[25] == 1


class TestComputeIndicator:
    def test_sma_via_compute(self):
        df = pd.DataFrame({"close": np.arange(50, dtype=float)})
        result = compute_indicator(df, "close", "sma", {"window": 10})
        assert "sma" in result
        assert len(result["sma"]) == 50

    def test_unknown_indicator(self):
        df = pd.DataFrame({"close": [1, 2, 3]})
        result = compute_indicator(df, "close", "nonexistent")
        assert result == {}
