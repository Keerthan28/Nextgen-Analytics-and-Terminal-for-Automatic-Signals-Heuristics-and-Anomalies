from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum


class DatasetType(str, Enum):
    TIMESERIES = "timeseries"
    TABULAR = "tabular"


class ChartType(str, Enum):
    LINE = "line"
    OHLC = "ohlc"
    CANDLESTICK = "candlestick"
    HISTOGRAM = "histogram"
    BAR = "bar"
    SCATTER = "scatter"
    BOX = "box"
    HEATMAP = "heatmap"
    PIE = "pie"


class IndicatorType(str, Enum):
    SMA = "sma"
    EMA = "ema"
    BOLLINGER = "bollinger"
    RSI = "rsi"
    MACD = "macd"
    VOLATILITY = "volatility"
    DRAWDOWN = "drawdown"
    ABNORMAL_VOLUME = "abnormal_volume"


class ColumnRole(str, Enum):
    DATETIME = "datetime"
    OPEN = "open"
    HIGH = "high"
    LOW = "low"
    CLOSE = "close"
    VOLUME = "volume"
    VALUE = "value"
    CATEGORY = "category"
    IDENTIFIER = "identifier"
    GEO = "geo"
    IGNORE = "ignore"


class ColumnMapping(BaseModel):
    column_name: str
    role: ColumnRole


class DatasetSchema(BaseModel):
    columns: list[ColumnMapping]
    row_count: int
    dataset_type: DatasetType = DatasetType.TIMESERIES
    datetime_column: Optional[str] = None
    value_columns: list[str] = Field(default_factory=list)
    category_columns: list[str] = Field(default_factory=list)
    volume_column: Optional[str] = None
    target_column: Optional[str] = None
    has_ohlc: bool = False


class IndicatorConfig(BaseModel):
    indicator: IndicatorType
    params: dict = Field(default_factory=dict)


class ChartRequest(BaseModel):
    dataset_id: str
    chart_type: ChartType = ChartType.LINE
    series: list[str] = Field(default_factory=list)
    indicators: list[IndicatorConfig] = Field(default_factory=list)
    timeframe: Optional[str] = None
    compare_mode: bool = False
    annotations: list[dict] = Field(default_factory=list)


class TabularChartRequest(BaseModel):
    dataset_id: str
    chart_type: ChartType = ChartType.HISTOGRAM
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    color_col: Optional[str] = None
    agg: str = "count"


class InsightItem(BaseModel):
    title: str
    description: str
    severity: str = "info"
    metric: Optional[str] = None
    value: Optional[float] = None
    rule: str = ""
    timestamp: Optional[str] = None


class InsightReport(BaseModel):
    dataset_id: str
    top_findings: list[InsightItem]
    summary: str


class DatasetProfile(BaseModel):
    dataset_id: str
    schema: DatasetSchema
    preview: list[dict]
    stats: dict
    date_range: Optional[dict] = None
    tabular_profile: Optional[dict] = None


class ExportRequest(BaseModel):
    dataset_id: str
    format: str = "png"
    chart_config: Optional[ChartRequest] = None
