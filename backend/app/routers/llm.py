from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.data_processor import get_dataset, get_schema, compute_stats
from app.services.llm_service import (
    suggest_charts,
    generate_narrative_insights,
    generate_chart_insights,
    get_token_usage,
    reset_token_usage,
)

router = APIRouter(prefix="/api/llm", tags=["llm"])


@router.get("/suggestions/{dataset_id}")
async def get_llm_suggestions(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    schema_dict = schema.model_dump()
    suggestions = await suggest_charts(df, schema_dict)
    return {"suggestions": suggestions}


@router.get("/insights/{dataset_id}")
async def get_llm_insights(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    stats = compute_stats(df, schema)
    schema_dict = schema.model_dump()
    result = await generate_narrative_insights(df, schema_dict, stats)
    return result


class ChartInsightRequest(BaseModel):
    dataset_id: str
    chart_type: str
    x_col: Optional[str] = None
    y_col: Optional[str] = None
    color_col: Optional[str] = None


@router.post("/chart-insights")
async def get_chart_insights(req: ChartInsightRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    schema_dict = schema.model_dump()
    result = await generate_chart_insights(
        df, schema_dict,
        chart_type=req.chart_type,
        x_col=req.x_col,
        y_col=req.y_col,
        color_col=req.color_col,
    )
    return result


@router.get("/token-usage")
async def token_usage():
    return get_token_usage()


@router.post("/reset-token-usage")
async def token_usage_reset():
    reset_token_usage()
    return {"status": "reset"}
