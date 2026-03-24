import { useState, useCallback, useEffect, useMemo } from 'react';
import * as api from '../utils/api';

export function useClustering(datasetId, schema, encodingSpec = {}) {
  const numericCols = useMemo(
    () => (schema?.value_columns ? [...schema.value_columns] : []),
    [schema?.value_columns],
  );
  const categoryCols = useMemo(() => {
    const t = schema?.target_column;
    return (schema?.category_columns || []).filter((c) => c !== t);
  }, [schema?.category_columns, schema?.target_column]);

  const columnOrder = useMemo(
    () => [...numericCols, ...categoryCols.filter((c) => !numericCols.includes(c))],
    [numericCols, categoryCols],
  );

  const [selectedFeatureColumns, setSelectedFeatureColumns] = useState([]);
  const [aiClustering, setAiClustering] = useState(null);
  const [aiClusteringLoading, setAiClusteringLoading] = useState(false);

  const [pcaResult, setPcaResult] = useState(null);
  const [kSuggestion, setKSuggestion] = useState(null);
  const [kmeansResult, setKmeansResult] = useState(null);
  const [nComponents, setNComponents] = useState(5);
  const [nClusters, setNClusters] = useState(3);
  const [clusterLoading, setClusterLoading] = useState('');
  const [clusterError, setClusterError] = useState(null);
  const [clusterView, setClusterView] = useState('scree');

  useEffect(() => {
    if (numericCols.length) setSelectedFeatureColumns([...numericCols]);
    else if (categoryCols.length) setSelectedFeatureColumns([categoryCols[0]]);
    else setSelectedFeatureColumns([]);
    setAiClustering(null);
  }, [datasetId, numericCols.join('|'), categoryCols.join('|')]);

  useEffect(() => {
    setPcaResult(null);
    setKSuggestion(null);
    setKmeansResult(null);
    setClusterError(null);
    setClusterView('scree');
  }, [datasetId]);

  const fetchClusteringFeaturesAI = useCallback(async () => {
    if (!datasetId) {
      setClusterError('No dataset loaded — upload a file first.');
      return;
    }
    setAiClusteringLoading(true);
    setClusterError(null);
    try {
      const res = await api.suggestClusteringFeatures(datasetId);
      setAiClustering(res);
      if (res.feature_columns?.length) {
        const allowed = new Set(numericCols);
        const picked = res.feature_columns.filter((c) => allowed.has(c));
        if (picked.length) setSelectedFeatureColumns(picked);
      }
    } catch (e) {
      setClusterError(e.message);
    } finally {
      setAiClusteringLoading(false);
    }
  }, [datasetId, numericCols]);

  const toggleFeatureColumn = useCallback(
    (col) => {
      setSelectedFeatureColumns((prev) => {
        const set = new Set(prev);
        if (set.has(col)) {
          if (set.size <= 1) return prev;
          set.delete(col);
        } else {
          set.add(col);
        }
        return columnOrder.filter((c) => set.has(c));
      });
      setPcaResult(null);
      setKSuggestion(null);
      setKmeansResult(null);
    },
    [columnOrder],
  );

  const encodingForRequest = useCallback(() => {
    const hasCat = selectedFeatureColumns.some((c) => categoryCols.includes(c));
    if (!hasCat) return undefined;
    const spec = {};
    for (const c of selectedFeatureColumns) {
      if (encodingSpec[c] != null) spec[c] = encodingSpec[c];
    }
    return spec;
  }, [selectedFeatureColumns, categoryCols, encodingSpec]);

  const runPCAAnalysis = useCallback(async () => {
    if (!datasetId || selectedFeatureColumns.length === 0) return;
    setClusterLoading('pca');
    setClusterError(null);
    try {
      const cols = selectedFeatureColumns;
      const enc = encodingForRequest();
      const res = await api.runPCA(datasetId, null, cols, enc === undefined ? null : enc);
      setPcaResult(res);
      setNComponents(res.suggested_components || 5);

      const kRes = await api.suggestK(datasetId, res.suggested_components || 5, cols, enc === undefined ? null : enc);
      setKSuggestion(kRes);
      setNClusters(kRes.suggested_k || 3);
      setClusterView('scree');
    } catch (e) {
      setClusterError(e.message);
    } finally {
      setClusterLoading('');
    }
  }, [datasetId, selectedFeatureColumns, encodingForRequest]);

  const resetClustering = useCallback(() => {
    setPcaResult(null);
    setKSuggestion(null);
    setKmeansResult(null);
    setClusterView('scree');
    setClusterError(null);
  }, []);

  const runKMeansAnalysis = useCallback(async () => {
    if (!datasetId || selectedFeatureColumns.length === 0) return;
    setClusterLoading('kmeans');
    setClusterError(null);
    try {
      const cols = selectedFeatureColumns;
      const enc = encodingForRequest();
      const res = await api.runKMeans(datasetId, nComponents, nClusters, cols, enc === undefined ? null : enc);
      setKmeansResult(res);
      setClusterView('clusters');
    } catch (e) {
      setClusterError(e.message);
    } finally {
      setClusterLoading('');
    }
  }, [datasetId, nComponents, nClusters, selectedFeatureColumns, encodingForRequest]);

  return {
    numericCols,
    categoryCols,
    columnOrder,
    selectedFeatureColumns,
    toggleFeatureColumn,
    aiClustering,
    aiClusteringLoading,
    fetchClusteringFeaturesAI,
    pcaResult,
    kSuggestion,
    kmeansResult,
    nComponents,
    setNComponents,
    nClusters,
    setNClusters,
    clusterLoading,
    clusterError,
    clusterView,
    setClusterView,
    runPCAAnalysis,
    runKMeansAnalysis,
    resetClustering,
  };
}
