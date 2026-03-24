from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.models.schemas import ChartRequest, TabularChartRequest, IndicatorType
from app.services.data_processor import (
    get_dataset, get_schema, prepare_chart_data, prepare_tabular_chart,
)
from app.services.indicators import compute_indicator

router = APIRouter(prefix="/api/charts", tags=["charts"])


@router.post("/data")
async def get_chart_data(req: ChartRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found. Upload first.")

    series_cols = req.series if req.series else None
    chart_data = prepare_chart_data(df, schema, series_cols, req.timeframe)

    indicator_data = {}
    for ic in req.indicators:
        primary_col = _pick_indicator_col(schema, req.series)
        result = compute_indicator(
            df, primary_col, ic.indicator.value, ic.params,
            volume_col=schema.volume_column,
        )
        for k, v in result.items():
            indicator_data[f"{ic.indicator.value}_{k}"] = v

    chart_data["indicators"] = indicator_data
    chart_data["chart_type"] = req.chart_type.value

    return chart_data


@router.post("/tabular")
async def get_tabular_chart(req: TabularChartRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found. Upload first.")

    result = prepare_tabular_chart(
        df, schema,
        chart_type=req.chart_type.value,
        x_col=req.x_col,
        y_col=req.y_col,
        color_col=req.color_col,
        agg=req.agg,
    )
    return result


def _pick_indicator_col(schema, series_list):
    if series_list:
        return series_list[0]
    from app.models.schemas import ColumnRole
    for m in schema.columns:
        if m.role == ColumnRole.CLOSE:
            return m.column_name
    return schema.value_columns[0] if schema.value_columns else ""
