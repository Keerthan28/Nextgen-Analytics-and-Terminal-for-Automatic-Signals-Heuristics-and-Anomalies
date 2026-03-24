from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.services.data_processor import get_dataset, get_schema
from app.services.feature_encoding import build_encoded_dataframe, encoding_profile
from app.services.llm_service import suggest_encoding_config

router = APIRouter(prefix="/api/features", tags=["features"])


@router.get("/profile/{dataset_id}")
def get_encoding_profile(
    dataset_id: str,
    target: str | None = Query(None, description="Target column to exclude from features"),
):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    return encoding_profile(df, schema.model_dump(), target)


@router.get("/suggest-encodings/{dataset_id}")
async def get_suggested_encodings(
    dataset_id: str,
    target: str | None = Query(None),
):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    try:
        return await suggest_encoding_config(df, schema.model_dump(), target)
    except RuntimeError as e:
        raise HTTPException(503, str(e))


class EncodeRequest(BaseModel):
    dataset_id: str
    encoding_spec: dict[str, str]
    target: Optional[str] = None


@router.post("/encode")
def encode_dataset(body: EncodeRequest):
    df = get_dataset(body.dataset_id)
    schema = get_schema(body.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    try:
        encoded_df, summary = build_encoded_dataframe(
            df, schema.model_dump(), body.encoding_spec, body.target,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))

    preview_rows = 8
    preview = encoded_df.head(preview_rows)
    preview_data = []
    for _, row in preview.iterrows():
        preview_data.append({col: _safe_val(row[col]) for col in preview.columns})

    return {
        "rows": len(encoded_df),
        "columns": len(encoded_df.columns),
        "feature_names": encoded_df.columns.tolist(),
        "summary": summary,
        "preview": preview_data,
    }


def _safe_val(v):
    """JSON-safe scalar."""
    import math
    if v is None:
        return None
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    if isinstance(v, (int, float, bool, str)):
        return v
    return str(v)
