import { useState, useCallback } from 'react';
import * as api from '../utils/api';

export function useDataset() {
  const [profile, setProfile] = useState(null);
  const [chartData, setChartData] = useState(null);
  const [tabularChartData, setTabularChartData] = useState(null);
  const [insights, setInsights] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [chartType, setChartType] = useState('line');
  const [selectedSeries, setSelectedSeries] = useState([]);
  const [indicators, setIndicators] = useState([]);
  const [timeframe, setTimeframe] = useState(null);
  const [compareMode, setCompareMode] = useState(false);

  const [tabularChartType, setTabularChartType] = useState('histogram');
  const [xCol, setXCol] = useState(null);
  const [yCol, setYCol] = useState(null);
  const [colorCol, setColorCol] = useState(null);
  const [agg, setAgg] = useState('mean');

  // LLM state
  const [llmSuggestions, setLlmSuggestions] = useState(null);
  const [llmInsights, setLlmInsights] = useState(null);
  const [llmChartInsights, setLlmChartInsights] = useState(null);
  const [llmLoading, setLlmLoading] = useState(false);

  const isTabular = profile?.schema?.dataset_type === 'tabular';

  const _fetchLLMData = useCallback(async (datasetId) => {
    setLlmLoading(true);
    try {
      const [suggestions, narrativeInsights] = await Promise.all([
        api.getLLMSuggestions(datasetId).catch(() => ({ suggestions: [] })),
        api.getLLMInsights(datasetId).catch(() => ({ narrative: '', findings: [] })),
      ]);
      setLlmSuggestions(suggestions.suggestions || []);
      setLlmInsights(narrativeInsights);
    } catch {
      // Non-critical — LLM is additive
    } finally {
      setLlmLoading(false);
    }
  }, []);

  const _fetchChartInsights = useCallback(async (datasetId, chartType, xCol, yCol, colorCol) => {
    try {
      const result = await api.getLLMChartInsights({
        dataset_id: datasetId,
        chart_type: chartType,
        x_col: xCol,
        y_col: yCol,
        color_col: colorCol,
      });
      setLlmChartInsights(result);
    } catch {
      // Non-critical
    }
  }, []);

  const upload = useCallback(async (file) => {
    setLoading(true);
    setError(null);
    setLlmSuggestions(null);
    setLlmInsights(null);
    setLlmChartInsights(null);
    try {
      const p = await api.uploadDataset(file);
      setProfile(p);

      if (p.schema.dataset_type === 'tabular') {
        const suggestions = p.tabular_profile?.suggested_charts || [];
        const first = suggestions[0];

        const defaultChart = first?.chart_type || 'histogram';
        const defaultX = first?.x_col || p.schema.value_columns[0] || p.schema.category_columns[0] || null;
        const defaultY = first?.y_col || null;
        const defaultColor = first?.color_col || p.schema.target_column || null;

        setTabularChartType(defaultChart);
        setXCol(defaultX);
        setYCol(defaultY);
        setColorCol(defaultColor);

        const [td, ins] = await Promise.all([
          api.getTabularChart({
            dataset_id: p.dataset_id,
            chart_type: defaultChart,
            x_col: defaultX,
            y_col: defaultY,
            color_col: defaultColor,
            agg: 'count',
          }),
          api.getInsights(p.dataset_id),
        ]);
        setTabularChartData(td);
        setChartData(null);
        setInsights(ins);

        // Fire LLM calls in background (non-blocking)
        _fetchLLMData(p.dataset_id);
        _fetchChartInsights(p.dataset_id, defaultChart, defaultX, defaultY, defaultColor);
      } else {
        const defaultSeries = p.schema.value_columns.slice(0, 1);
        setSelectedSeries(defaultSeries);
        const defaultType = p.schema.has_ohlc ? 'candlestick' : 'line';
        setChartType(defaultType);

        const [cd, ins] = await Promise.all([
          api.getChartData({
            dataset_id: p.dataset_id,
            chart_type: defaultType,
            series: defaultSeries,
            indicators: [],
          }),
          api.getInsights(p.dataset_id),
        ]);
        setChartData(cd);
        setTabularChartData(null);
        setInsights(ins);

        _fetchLLMData(p.dataset_id);
      }
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [_fetchLLMData, _fetchChartInsights]);

  const refreshChart = useCallback(async (overrides = {}) => {
    if (!profile) return;
    setLoading(true);
    try {
      const req = {
        dataset_id: profile.dataset_id,
        chart_type: overrides.chartType ?? chartType,
        series: overrides.series ?? selectedSeries,
        indicators: overrides.indicators ?? indicators,
        timeframe: overrides.timeframe ?? timeframe,
        compare_mode: overrides.compareMode ?? compareMode,
      };
      const cd = await api.getChartData(req);
      setChartData(cd);

      if (overrides.chartType !== undefined) setChartType(overrides.chartType);
      if (overrides.series !== undefined) setSelectedSeries(overrides.series);
      if (overrides.indicators !== undefined) setIndicators(overrides.indicators);
      if (overrides.timeframe !== undefined) setTimeframe(overrides.timeframe);
      if (overrides.compareMode !== undefined) setCompareMode(overrides.compareMode);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [profile, chartType, selectedSeries, indicators, timeframe, compareMode]);

  const refreshTabularChart = useCallback(async (overrides = {}) => {
    if (!profile) return;
    setLoading(true);
    setLlmChartInsights(null);
    try {
      const newType = overrides.chartType ?? tabularChartType;
      const newX = overrides.xCol !== undefined ? overrides.xCol : xCol;
      const newY = overrides.yCol !== undefined ? overrides.yCol : yCol;
      const newColor = overrides.colorCol !== undefined ? overrides.colorCol : colorCol;
      const newAgg = overrides.agg ?? agg;

      const td = await api.getTabularChart({
        dataset_id: profile.dataset_id,
        chart_type: newType,
        x_col: newX,
        y_col: newY,
        color_col: newColor,
        agg: newAgg,
      });
      setTabularChartData(td);

      setTabularChartType(newType);
      setXCol(newX);
      setYCol(newY);
      setColorCol(newColor);
      setAgg(newAgg);

      // Ask Gemini about this chart in background
      _fetchChartInsights(profile.dataset_id, newType, newX, newY, newColor);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [profile, tabularChartType, xCol, yCol, colorCol, agg, _fetchChartInsights]);

  const applySuggestion = useCallback(async (suggestion) => {
    if (!profile) return;
    await refreshTabularChart({
      chartType: suggestion.chart_type,
      xCol: suggestion.x_col || null,
      yCol: suggestion.y_col || null,
      colorCol: suggestion.color_col || null,
      agg: 'count',
    });
  }, [profile, refreshTabularChart]);

  return {
    profile, chartData, tabularChartData, insights, loading, error, isTabular,
    chartType, selectedSeries, indicators, timeframe, compareMode,
    tabularChartType, xCol, yCol, colorCol, agg,
    llmSuggestions, llmInsights, llmChartInsights, llmLoading,
    upload, refreshChart, refreshTabularChart, applySuggestion, setError,
  };
}
