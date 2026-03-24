from __future__ import annotations
from fastapi import APIRouter, HTTPException

from app.models.schemas import InsightReport, DatasetType
from app.services.data_processor import get_dataset, get_schema, compute_stats
from app.services.insights import generate_insights
from app.services.tabular_insights import generate_tabular_insights

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/insights/{dataset_id}", response_model=InsightReport)
async def get_insights(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    if schema.dataset_type == DatasetType.TABULAR:
        return generate_tabular_insights(df, schema, dataset_id)
    return generate_insights(df, schema, dataset_id)


@router.get("/stats/{dataset_id}")
async def get_stats(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    return compute_stats(df, schema)
