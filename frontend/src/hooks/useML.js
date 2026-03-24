import { useState, useCallback, useEffect } from 'react';
import * as api from '../utils/api';

const CLASSIFICATION_MODELS = [
  { id: 'logistic_regression', name: 'Logistic Regression' },
  { id: 'random_forest', name: 'Random Forest' },
  { id: 'gradient_boosting', name: 'Gradient Boosting' },
];

const REGRESSION_MODELS = [
  { id: 'linear_regression', name: 'Linear Regression' },
  { id: 'ridge_regression', name: 'Ridge Regression' },
  { id: 'random_forest_regressor', name: 'Random Forest Regressor' },
  { id: 'gradient_boosting_regressor', name: 'Gradient Boosting Regressor' },
];

export { CLASSIFICATION_MODELS, REGRESSION_MODELS };

export function useML(datasetId, schema) {
  const [aiConfig, setAiConfig] = useState(null);
  const [aiLoading, setAiLoading] = useState(false);
  const [targetColumn, setTargetColumn] = useState(null);
  const [taskType, setTaskType] = useState('classification');
  const [excludeColumns, setExcludeColumns] = useState([]);
  const [selectedModelTypes, setSelectedModelTypes] = useState([]);

  const [encodingProfile, setEncodingProfile] = useState(null);
  const [encodingSpec, setEncodingSpec] = useState({});
  const [encodingReasons, setEncodingReasons] = useState({});
  const [encodingLoading, setEncodingLoading] = useState(false);

  const [encodingResult, setEncodingResult] = useState(null);
  const [encodingRunning, setEncodingRunning] = useState(false);

  const [preliminary, setPreliminary] = useState(null);
  const [mlResults, setMlResults] = useState(null);
  const [selectedModel, setSelectedModel] = useState(null);
  const [mlLoading, setMlLoading] = useState('');
  const [mlError, setMlError] = useState(null);

  useEffect(() => {
    setAiConfig(null);
    setAiLoading(false);
    setPreliminary(null);
    setMlResults(null);
    setSelectedModel(null);
    setMlError(null);
    setExcludeColumns([]);
    setEncodingProfile(null);
    setEncodingSpec({});
    setEncodingReasons({});
    setEncodingResult(null);

    if (schema?.target_column) {
      setTargetColumn(schema.target_column);
    } else {
      setTargetColumn(null);
    }
    setTaskType('classification');
    setSelectedModelTypes([]);
  }, [datasetId, schema]);

  useEffect(() => {
    if (!datasetId) return;
    let cancelled = false;
    api.getEncodingProfile(datasetId, targetColumn || null)
      .then((prof) => {
        if (cancelled || !prof?.columns) return;
        setEncodingProfile(prof);
        setEncodingSpec(Object.fromEntries(prof.columns.map((c) => [c.name, c.default_encoding])));
        setEncodingReasons({});
      })
      .catch(() => {
        if (!cancelled) {
          setEncodingProfile(null);
          setEncodingSpec({});
        }
      });
    return () => { cancelled = true; };
  }, [datasetId, targetColumn]);

  const fetchAIConfig = useCallback(async () => {
    if (!datasetId) return;
    setAiLoading(true);
    try {
      const config = await api.getMLSuggestConfig(datasetId);
      setAiConfig(config);
      if (config.target_column) setTargetColumn(config.target_column);
      if (config.task_type) setTaskType(config.task_type);
      if (config.exclude_columns?.length) setExcludeColumns(config.exclude_columns);
      if (config.recommended_models?.length) setSelectedModelTypes(config.recommended_models);
    } catch (e) {
      setMlError('AI config unavailable: ' + e.message);
    } finally {
      setAiLoading(false);
    }
  }, [datasetId]);

  const fetchEncodingAI = useCallback(async () => {
    if (!datasetId) return;
    setEncodingLoading(true);
    try {
      const res = await api.suggestEncodings(datasetId, targetColumn || null);
      if (res.encodings) setEncodingSpec(res.encodings);
      if (res.reasons) setEncodingReasons(res.reasons);
    } catch (e) {
      setMlError('Encoding suggestions failed: ' + e.message);
    } finally {
      setEncodingLoading(false);
    }
  }, [datasetId, targetColumn]);

  const setEncodingForColumn = useCallback((col, enc) => {
    setEncodingSpec((prev) => ({ ...prev, [col]: enc }));
  }, []);

  const reloadProfile = useCallback(async () => {
    if (!datasetId) return;
    try {
      const prof = await api.getEncodingProfile(datasetId, targetColumn || null);
      if (prof?.columns) {
        setEncodingProfile(prof);
        setEncodingSpec(Object.fromEntries(prof.columns.map((c) => [c.name, c.default_encoding])));
        setEncodingReasons({});
      }
    } catch {
      /* ignore — user will see the empty state */
    }
  }, [datasetId, targetColumn]);

  const encodeData = useCallback(async () => {
    if (!datasetId || !Object.keys(encodingSpec).length) return;
    setEncodingRunning(true);
    setMlError(null);
    try {
      const res = await api.encodeDataset(datasetId, encodingSpec, targetColumn || null);
      setEncodingResult(res);
    } catch (e) {
      setMlError('Encoding failed: ' + e.message);
    } finally {
      setEncodingRunning(false);
    }
  }, [datasetId, encodingSpec, targetColumn]);

  const runPreliminary = useCallback(async () => {
    if (!datasetId) return;
    setMlLoading('preliminary');
    setMlError(null);
    try {
      const res = await api.getPreliminaryAnalysis({
        dataset_id: datasetId,
        target_column: targetColumn,
        task_type: taskType,
        exclude_columns: excludeColumns,
      });
      setPreliminary(res);

      if (selectedModelTypes.length === 0 && res.available_models?.length) {
        setSelectedModelTypes(res.available_models);
      }
    } catch (e) {
      setMlError(e.message);
    } finally {
      setMlLoading('');
    }
  }, [datasetId, targetColumn, taskType, excludeColumns, selectedModelTypes]);

  const trainModels = useCallback(async () => {
    if (!datasetId || selectedModelTypes.length === 0) return;
    setMlLoading('training');
    setMlError(null);
    try {
      const res = await api.trainModels({
        dataset_id: datasetId,
        target_column: targetColumn,
        task_type: taskType,
        model_types: selectedModelTypes,
        exclude_columns: excludeColumns,
        encoding_spec: encodingSpec && Object.keys(encodingSpec).length ? encodingSpec : undefined,
      });
      setMlResults(res);
      setSelectedModel(res.best_model);
    } catch (e) {
      setMlError(e.message);
    } finally {
      setMlLoading('');
    }
  }, [datasetId, targetColumn, taskType, selectedModelTypes, excludeColumns, encodingSpec]);

  const toggleExcludeColumn = useCallback((col) => {
    setExcludeColumns((prev) =>
      prev.includes(col) ? prev.filter((c) => c !== col) : [...prev, col],
    );
    setPreliminary(null);
    setMlResults(null);
  }, []);

  const toggleModelType = useCallback((mt) => {
    setSelectedModelTypes((prev) =>
      prev.includes(mt) ? prev.filter((m) => m !== mt) : [...prev, mt],
    );
  }, []);

  const currentResult = mlResults?.models?.[selectedModel] || null;

  const availableModels = taskType === 'classification' ? CLASSIFICATION_MODELS : REGRESSION_MODELS;

  const rawColumns = [
    ...(schema?.value_columns || []),
    ...(schema?.category_columns || []),
  ].filter((c) => c !== targetColumn);

  const encodedFeatureNames = encodingResult?.feature_names?.filter(
    (n) => !n.startsWith('_target_'),
  ) || null;

  return {
    aiConfig, aiLoading, fetchAIConfig,
    targetColumn, setTargetColumn,
    taskType, setTaskType,
    excludeColumns, toggleExcludeColumn,
    selectedModelTypes, toggleModelType, setSelectedModelTypes,
    preliminary, mlResults, selectedModel, setSelectedModel,
    currentResult, mlLoading, mlError,
    runPreliminary, trainModels,
    availableModels,
    allColumns: rawColumns,
    encodedFeatureNames,
    encodingProfile, encodingSpec, encodingReasons, encodingLoading,
    fetchEncodingAI, setEncodingForColumn, reloadProfile,
    encodeData, encodingResult, encodingRunning,
  };
}
