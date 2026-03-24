# VEDA — Visual Engine for Data Analytics

A dark-theme, terminal-inspired charting workspace that accepts uploaded CSV/Excel datasets and renders interactive financial-style charts with automatic insights, AI-powered ML training, PCA/K-Means clustering, and feature encoding.

## Features

- **File Upload** — Drop CSV or Excel files; auto-detects schema, datetime columns, OHLC, and volume
- **Chart Types** — Line, OHLC, and Candlestick rendering with Plotly.js
- **Volume Panel** — Color-coded volume bars synced to the price chart
- **Indicators** — SMA, EMA, Bollinger Bands, RSI, MACD, Rolling Volatility, Drawdown, Abnormal Volume
- **Insight Engine** — Auto-generated findings: returns, spikes/drops, MA crossovers, RSI extremes, volatility alerts
- **AI-Powered Insights** — Gemini integration for chart suggestions, narrative insights, and ML configuration
- **ML Training** — Classification & Regression with multiple algorithms, auto leakage detection, metrics & feature importance
- **PCA + K-Means Clustering** — AI-driven feature selection, scree plots, silhouette analysis, cluster visualization
- **Feature Encoding** — Per-column encoding (binary, one-hot, label, frequency, target) with AI suggestions and live preview
- **Comparison Mode** — Normalize multiple series to percent change for overlay comparison
- **Timeframe Shortcuts** — 1D, 5D, 1M, 3M, 6M, YTD, 1Y, Max
- **Export** — PNG chart, CSV metrics, and full HTML report
- **Dark Terminal Theme** — Bloomberg-inspired design with JetBrains Mono typography

## Architecture

```
├── backend/          FastAPI service
│   ├── app/
│   │   ├── main.py           Application entry point
│   │   ├── models/schemas.py Pydantic models
│   │   ├── routers/          API endpoints (upload, charts, analytics, export, ml, clustering, features)
│   │   └── services/         Data processing, indicators, insights, ML, clustering, encoding, LLM
│   └── tests/                Unit + integration tests
├── frontend/         React + Vite + Plotly.js
│   └── src/
│       ├── components/       TopBar, Sidebar, Charts, Insights, ML, Clustering, Encoding panels
│       ├── hooks/            useDataset, useML, useClustering state management
│       ├── styles/           CSS + theme constants
│       └── utils/            API client, formatters
└── sample_data/      4 sample datasets for testing
```

## Quick Start

### Prerequisites
- Python 3.10+
- Node.js 18+
- Gemini API key (set as `GEMINI_API_KEY` in `backend/.env`)

### Run Everything

```bash
chmod +x start.sh
./start.sh
```

### Or Start Services Individually

**Backend:**
```bash
cd backend
pip3 install -r requirements.txt
echo "GEMINI_API_KEY=your_key_here" > .env
python3 -m uvicorn app.main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173** in your browser.

## Running Tests

```bash
cd backend
python3 -m pytest tests/ -v
```

## Sample Datasets

| File | Description |
|---|---|
| `stock_ohlcv.csv` | 252-day simulated stock with OHLCV, injected spike + drop |
| `macro_monthly.csv` | 10-year monthly macro indicators (GDP, CPI, unemployment, Fed rate) |
| `business_kpi.csv` | 365-day business KPI (revenue, users, conversion rate) |
| `messy_data.csv` | Mixed date formats, missing values, duplicates — robustness test |

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `POST` | `/api/upload/` | Upload CSV/Excel file |
| `PUT` | `/api/upload/{id}/schema` | Update column mappings |
| `POST` | `/api/charts/data` | Get chart data with indicators |
| `GET` | `/api/analytics/insights/{id}` | Get auto-generated insights |
| `GET` | `/api/analytics/stats/{id}` | Get column statistics |
| `POST` | `/api/ml/train` | Train ML models |
| `GET` | `/api/ml/suggest-config/{id}` | AI-suggested ML configuration |
| `POST` | `/api/clustering/pca` | Run PCA analysis |
| `POST` | `/api/clustering/kmeans` | Run K-Means clustering |
| `GET` | `/api/features/profile/{id}` | Get encoding profile |
| `POST` | `/api/features/encode` | Apply feature encodings |
| `POST` | `/api/export/png` | Export chart as PNG |
| `POST` | `/api/export/csv` | Export metrics as CSV |
| `POST` | `/api/export/html` | Export full HTML report |
| `GET` | `/api/health` | Health check |

## Tech Stack

- **Backend:** FastAPI, pandas, NumPy, SciPy, scikit-learn, Plotly (server-side), Google Gemini AI
- **Frontend:** React 18, Vite, Plotly.js, react-dropzone, Lucide icons
- **Testing:** pytest, FastAPI TestClient
