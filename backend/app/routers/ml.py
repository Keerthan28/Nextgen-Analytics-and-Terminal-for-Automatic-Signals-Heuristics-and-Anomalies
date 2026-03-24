from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.data_processor import get_dataset, get_schema
from app.services.ml_service import preliminary_analysis, train_selected_models
from app.services.llm_service import suggest_ml_config

router = APIRouter(prefix="/api/ml", tags=["ml"])


class PreliminaryRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    dataset_id: str
    target_column: Optional[str] = None
    task_type: Optional[str] = None
    exclude_columns: list[str] = []


@router.post("/preliminary")
async def run_preliminary(req: PreliminaryRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    return preliminary_analysis(
        df, schema,
        target_override=req.target_column,
        task_type_override=req.task_type,
        exclude_cols=req.exclude_columns or None,
    )


@router.get("/preliminary/{dataset_id}")
async def run_preliminary_get(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    return preliminary_analysis(df, schema)


@router.get("/suggest-config/{dataset_id}")
async def get_ml_config(dataset_id: str):
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    config = await suggest_ml_config(df, schema.model_dump())
    return config


class TrainRequest(BaseModel):
    model_config = {"protected_namespaces": ()}
    dataset_id: str
    target_column: Optional[str] = None
    task_type: Optional[str] = None
    model_types: list[str] = []
    include_columns: Optional[list[str]] = None
    exclude_columns: list[str] = []
    encoding_spec: Optional[dict[str, str]] = None


@router.post("/train")
async def run_train(req: TrainRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    try:
        return train_selected_models(
            df, schema,
            model_types=req.model_types,
            target=req.target_column,
            task_type=req.task_type,
            include_cols=req.include_columns,
            exclude_cols=req.exclude_columns or None,
            encoding_spec=req.encoding_spec,
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
