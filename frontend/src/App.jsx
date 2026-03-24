import { useRef, useCallback, useState } from 'react';
import { useDataset } from './hooks/useDataset';
import { useClustering } from './hooks/useClustering';
import { useML } from './hooks/useML';
import TopBar from './components/TopBar';
import UploadZone from './components/UploadZone';
import Sidebar from './components/Sidebar';
import ChartToolbar from './components/ChartToolbar';
import PriceChart from './components/PriceChart';
import VolumeChart from './components/VolumeChart';
import SubChart from './components/SubChart';
import InsightsPanel from './components/InsightsPanel';
import DataPreview from './components/DataPreview';
import TabularChart from './components/TabularChart';
import TabularToolbar from './components/TabularToolbar';
import TabularSidebar from './components/TabularSidebar';
import ClusteringControls from './components/ClusteringControls';
import ClusteringCharts from './components/ClusteringCharts';
import MLControls from './components/MLControls';
import MLEncodingPanel from './components/MLEncodingPanel';
import MLCharts from './components/MLCharts';
import * as api from './utils/api';

const SUB_CHART_INDICATORS = ['rsi', 'macd', 'volatility', 'drawdown'];

export default function App() {
  const {
    profile, chartData, tabularChartData, insights, loading, error, isTabular,
    chartType, selectedSeries, indicators, timeframe, compareMode,
    tabularChartType, xCol, yCol, colorCol, agg,
    llmSuggestions, llmInsights, llmChartInsights, llmLoading,
    upload, refreshChart, refreshTabularChart, applySuggestion, setError,
  } = useDataset();

  const ml = useML(profile?.dataset_id, profile?.schema);
  const clustering = useClustering(profile?.dataset_id, profile?.schema, ml.encodingSpec);

  const fileInputRef = useRef(null);
  const [rightPanel, setRightPanel] = useState('insights');
  const [mainView, setMainView] = useState('charts');

  const handleUploadClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      upload(file);
      setMainView('charts');
      setRightPanel('insights');
    }
    e.target.value = '';
  }, [upload]);

  const handleExport = useCallback(async (format) => {
    if (!profile) return;
    try {
      let blob;
      let filename;
      switch (format) {
        case 'png':
          blob = await api.exportPNG(profile.dataset_id);
          filename = 'natasha_chart.png';
          break;
        case 'csv':
          blob = await api.exportCSV(profile.dataset_id);
          filename = 'natasha_metrics.csv';
          break;
        case 'html':
          blob = await api.exportHTML(profile.dataset_id);
          filename = 'natasha_report.html';
          break;
        default: return;
      }
      api.downloadBlob(blob, filename);
    } catch (e) {
      setError(`Export failed: ${e.message}`);
    }
  }, [profile, setError]);

  const activeSubCharts = indicators
    .map(i => i.indicator)
    .filter(id => SUB_CHART_INDICATORS.includes(id));

  const hasData = !!profile;
  const numericCols = profile?.schema?.value_columns || [];
  const categoryCols = profile?.schema?.category_columns || [];
  const allCols = [...categoryCols, ...numericCols];

  return (
    <>
      <input
        ref={fileInputRef}
        type="file"
        accept=".csv,.xlsx,.xls"
        style={{ display: 'none' }}
        onChange={handleFileSelect}
      />

      <div className={`app-layout ${hasData ? '' : 'no-data'}`}>
        <TopBar
          profile={profile}
          onUploadClick={handleUploadClick}
          onExport={handleExport}
        />

        {!hasData ? (
          <div className="main-area">
            <UploadZone onFile={upload} loading={loading} />
          </div>
        ) : isTabular ? (
          <>
            <TabularSidebar
              profile={profile}
              llmSuggestions={llmSuggestions}
              llmLoading={llmLoading}
              onSuggestionClick={(s) => { setMainView('charts'); applySuggestion(s); }}
            />

            <div className="main-area">
              {/* Main view toggle */}
              <div className="toolbar" style={{ gap: 4, padding: '4px 12px' }}>
                <ViewTab active={mainView === 'charts'} onClick={() => setMainView('charts')}>Charts</ViewTab>
                <ViewTab active={mainView === 'clustering'} onClick={() => setMainView('clustering')} accent="var(--cyan)">Clustering</ViewTab>
                <ViewTab active={mainView === 'ml'} onClick={() => setMainView('ml')} accent="var(--purple)">ML Models</ViewTab>
                <div className="spacer" />
                {mainView === 'charts' && (
                  <TabularToolbar
                    chartType={tabularChartType}
                    xCol={xCol} yCol={yCol} colorCol={colorCol} agg={agg}
                    numericCols={numericCols} categoryCols={categoryCols} allCols={allCols}
                    onChartTypeChange={(t) => refreshTabularChart({ chartType: t })}
                    onXColChange={(c) => refreshTabularChart({ xCol: c })}
                    onYColChange={(c) => refreshTabularChart({ yCol: c })}
                    onColorColChange={(c) => refreshTabularChart({ colorCol: c })}
                    onAggChange={(a) => refreshTabularChart({ agg: a })}
                    inline
                  />
                )}
              </div>

              {loading && (
                <div className="loading">
                  <div className="spinner" />
                  <span className="mono" style={{ fontSize: 11 }}>Rendering...</span>
                </div>
              )}

              {mainView === 'charts' && (
                <>
                  <TabularChart chartData={tabularChartData} />
                  <DataPreview profile={profile} />
                </>
              )}

              {mainView === 'clustering' && (
                <ClusteringCharts
                  clusterView={clustering.clusterView}
                  pcaResult={clustering.pcaResult}
                  kSuggestion={clustering.kSuggestion}
                  kmeansResult={clustering.kmeansResult}
                />
              )}

              {mainView === 'ml' && (
                <MLCharts mlResults={ml.mlResults} currentResult={ml.currentResult} />
              )}
            </div>

            {/* Right panel */}
            <div className="right-panel" style={{ display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>
              <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', flexShrink: 0 }}>
                <PanelTab active={rightPanel === 'insights'} onClick={() => setRightPanel('insights')} accent="var(--accent)">Insights</PanelTab>
                <PanelTab active={rightPanel === 'clustering'} onClick={() => setRightPanel('clustering')} accent="var(--cyan)">Clustering</PanelTab>
                <PanelTab active={rightPanel === 'ml'} onClick={() => setRightPanel('ml')} accent="var(--purple)">ML</PanelTab>
                <PanelTab active={rightPanel === 'encoding'} onClick={() => setRightPanel('encoding')} accent="var(--orange)">Encoding</PanelTab>
              </div>
              <div style={{ flex: 1, overflow: 'auto' }}>
                {rightPanel === 'insights' && (
                  <InsightsPanel
                    insights={insights}
                    llmInsights={llmInsights}
                    llmChartInsights={llmChartInsights}
                    llmLoading={llmLoading}
                  />
                )}
                {rightPanel === 'clustering' && (
                  <ClusteringControls {...clustering} onOpenEncodingTab={() => setRightPanel('encoding')} />
                )}
                {rightPanel === 'ml' && (
                  <MLControls {...ml} onOpenEncodingTab={() => setRightPanel('encoding')} />
                )}
                {rightPanel === 'encoding' && (
                  <MLEncodingPanel
                    encodingProfile={ml.encodingProfile}
                    encodingSpec={ml.encodingSpec}
                    encodingReasons={ml.encodingReasons}
                    encodingLoading={ml.encodingLoading}
                    fetchEncodingAI={ml.fetchEncodingAI}
                    setEncodingForColumn={ml.setEncodingForColumn}
                    targetColumn={ml.targetColumn}
                    reloadProfile={ml.reloadProfile}
                    encodeData={ml.encodeData}
                    encodingResult={ml.encodingResult}
                    encodingRunning={ml.encodingRunning}
                  />
                )}
              </div>
            </div>
          </>
        ) : (
          <>
            <Sidebar
              profile={profile}
              selectedSeries={selectedSeries}
              indicators={indicators}
              onSeriesChange={(s) => refreshChart({ series: s })}
              onIndicatorChange={(ind) => refreshChart({ indicators: ind })}
            />

            <div className="main-area">
              <ChartToolbar
                chartType={chartType}
                timeframe={timeframe}
                hasOHLC={profile.schema.has_ohlc}
                compareMode={compareMode}
                onChartTypeChange={(t) => refreshChart({ chartType: t })}
                onTimeframeChange={(tf) => refreshChart({ timeframe: tf })}
                onCompareModeToggle={() => refreshChart({ compareMode: !compareMode })}
              />

              {loading && (
                <div className="loading">
                  <div className="spinner" />
                  <span className="mono" style={{ fontSize: 11 }}>Refreshing...</span>
                </div>
              )}

              <PriceChart chartData={chartData} chartType={chartType} compareMode={compareMode} />
              <VolumeChart chartData={chartData} />

              {activeSubCharts.map(key => (
                <SubChart key={key} chartData={chartData} indicatorKey={key} title={key.toUpperCase()} />
              ))}

              <DataPreview profile={profile} />
            </div>

            <InsightsPanel
              insights={insights}
              llmInsights={llmInsights}
              llmChartInsights={null}
              llmLoading={llmLoading}
            />
          </>
        )}
      </div>

      {error && (
        <div style={{
          position: 'fixed', bottom: 20, left: '50%', transform: 'translateX(-50%)',
          background: 'var(--red)', color: '#fff', padding: '10px 20px',
          borderRadius: 8, fontSize: 12, zIndex: 100, maxWidth: 500,
          fontFamily: "'JetBrains Mono', monospace",
          cursor: 'pointer',
        }} onClick={() => setError(null)}>
          {error}
        </div>
      )}
    </>
  );
}


const VIEW_COLORS = {
  'var(--accent)': 'rgba(88, 166, 255, 0.15)',
  'var(--cyan)': 'rgba(57, 210, 192, 0.15)',
  'var(--purple)': 'rgba(188, 140, 255, 0.15)',
};

function ViewTab({ active, onClick, children, accent = 'var(--accent)' }) {
  return (
    <button onClick={onClick} style={{
      padding: '5px 14px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
      border: `1px solid ${active ? accent : 'var(--border)'}`,
      background: active ? (VIEW_COLORS[accent] || 'rgba(88,166,255,0.15)') : 'transparent',
      color: active ? accent : 'var(--text-muted)',
      borderRadius: 6, transition: 'all 0.15s',
    }}>{children}</button>
  );
}

function PanelTab({ active, onClick, children, accent = 'var(--accent)' }) {
  return (
    <button onClick={onClick} style={{
      flex: 1, padding: '7px 4px', fontSize: 9, fontWeight: 600, cursor: 'pointer',
      border: 'none', borderBottom: active ? `2px solid ${accent}` : '2px solid transparent',
      background: 'transparent',
      color: active ? accent : 'var(--text-muted)',
    }}>{children}</button>
  );
}
