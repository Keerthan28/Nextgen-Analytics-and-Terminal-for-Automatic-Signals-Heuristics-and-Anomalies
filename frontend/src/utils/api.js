const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const body = await res.text();
    throw new Error(`API ${res.status}: ${body}`);
  }
  const contentType = res.headers.get('content-type') || '';
  if (contentType.includes('json')) return res.json();
  if (contentType.includes('html') || contentType.includes('text')) return res.text();
  return res.blob();
}

export async function uploadDataset(file) {
  const form = new FormData();
  form.append('file', file);
  return request('/upload/', { method: 'POST', body: form });
}

export async function updateSchema(datasetId, mappings) {
  return request(`/upload/${datasetId}/schema`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mappings),
  });
}

export async function getChartData(chartRequest) {
  return request('/charts/data', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chartRequest),
  });
}

export async function getTabularChart(tabularRequest) {
  return request('/charts/tabular', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(tabularRequest),
  });
}

export async function getInsights(datasetId) {
  return request(`/analytics/insights/${datasetId}`);
}

export async function getStats(datasetId) {
  return request(`/analytics/stats/${datasetId}`);
}

export async function exportPNG(datasetId, chartConfig = null) {
  const res = await fetch(`${BASE}/export/png`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, format: 'png', chart_config: chartConfig }),
  });
  if (!res.ok) throw new Error('Export failed');
  return res.blob();
}

export async function exportCSV(datasetId) {
  const res = await fetch(`${BASE}/export/csv`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, format: 'csv' }),
  });
  if (!res.ok) throw new Error('Export failed');
  return res.blob();
}

export async function exportHTML(datasetId) {
  const res = await fetch(`${BASE}/export/html`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId, format: 'html' }),
  });
  if (!res.ok) throw new Error('Export failed');
  return res.blob();
}

export async function getLLMSuggestions(datasetId) {
  return request(`/llm/suggestions/${datasetId}`);
}

export async function getLLMInsights(datasetId) {
  return request(`/llm/insights/${datasetId}`);
}

export async function getLLMChartInsights(chartInsightReq) {
  return request('/llm/chart-insights', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(chartInsightReq),
  });
}

export async function suggestClusteringFeatures(datasetId) {
  if (!datasetId) {
    throw new Error('No dataset loaded — upload a file first');
  }
  return request('/clustering/suggest-features', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ dataset_id: datasetId }),
  });
}

function clusteringBody(datasetId, nComponents, nClusters, featureColumns, encodingSpec) {
  const body = { dataset_id: datasetId };
  if (nComponents != null) body.n_components = nComponents;
  if (nClusters != null) body.n_clusters = nClusters;
  if (featureColumns?.length) body.feature_columns = featureColumns;
  if (encodingSpec != null && typeof encodingSpec === 'object') {
    body.encoding_spec = encodingSpec;
  }
  return body;
}

export async function runPCA(datasetId, nComponents = null, featureColumns = null, encodingSpec = null) {
  return request('/clustering/pca', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clusteringBody(datasetId, nComponents, null, featureColumns, encodingSpec)),
  });
}

export async function suggestK(datasetId, nComponents = 5, featureColumns = null, encodingSpec = null) {
  return request('/clustering/suggest-k', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clusteringBody(datasetId, nComponents, null, featureColumns, encodingSpec)),
  });
}

export async function runKMeans(datasetId, nComponents = 5, nClusters = 3, featureColumns = null, encodingSpec = null) {
  return request('/clustering/kmeans', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clusteringBody(datasetId, nComponents, nClusters, featureColumns, encodingSpec)),
  });
}

export async function getEncodingProfile(datasetId, targetColumn = null) {
  const q = targetColumn ? `?target=${encodeURIComponent(targetColumn)}` : '';
  return request(`/features/profile/${datasetId}${q}`);
}

export async function suggestEncodings(datasetId, targetColumn = null) {
  const q = targetColumn ? `?target=${encodeURIComponent(targetColumn)}` : '';
  return request(`/features/suggest-encodings/${datasetId}${q}`);
}

export async function encodeDataset(datasetId, encodingSpec, targetColumn = null) {
  return request('/features/encode', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      dataset_id: datasetId,
      encoding_spec: encodingSpec,
      target: targetColumn || null,
    }),
  });
}

export async function getPreliminaryAnalysis(config) {
  return request('/ml/preliminary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
}

export async function getMLSuggestConfig(datasetId) {
  return request(`/ml/suggest-config/${datasetId}`);
}

export async function trainModels(config) {
  return request('/ml/train', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
}

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
