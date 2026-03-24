from __future__ import annotations
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.services.data_processor import get_dataset, get_schema
from app.services.clustering import compute_pca, suggest_k, compute_kmeans
from app.services.llm_service import suggest_clustering_columns

router = APIRouter(prefix="/api/clustering", tags=["clustering"])


class DatasetIdBody(BaseModel):
    dataset_id: str


class PCARequest(BaseModel):
    dataset_id: str
    n_components: Optional[int] = None
    feature_columns: Optional[list[str]] = None
    encoding_spec: Optional[dict[str, str]] = None


class KMeansRequest(BaseModel):
    dataset_id: str
    n_components: int = 5
    n_clusters: int = 3
    feature_columns: Optional[list[str]] = None
    encoding_spec: Optional[dict[str, str]] = None


async def _suggest_clustering_features(dataset_id: str) -> dict:
    df = get_dataset(dataset_id)
    schema = get_schema(dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found — re-upload the file if the server was restarted")
    try:
        return await suggest_clustering_columns(df, schema.model_dump())
    except RuntimeError as e:
        raise HTTPException(503, str(e))


@router.post("/suggest-features")
async def post_suggested_features(body: DatasetIdBody):
    """Prefer POST — same path style as /pca and /kmeans; avoids GET/proxy issues."""
    return await _suggest_clustering_features(body.dataset_id)


@router.get("/suggest-features/{dataset_id}")
async def get_suggested_features(dataset_id: str):
    return await _suggest_clustering_features(dataset_id)


@router.post("/pca")
async def run_pca(req: PCARequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    try:
        return compute_pca(df, schema, req.n_components, req.feature_columns, req.encoding_spec)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/suggest-k")
async def run_suggest_k(req: PCARequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    n = req.n_components or 5
    try:
        return suggest_k(df, schema, n_components=n, feature_columns=req.feature_columns, encoding_spec=req.encoding_spec)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/kmeans")
async def run_kmeans(req: KMeansRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")
    try:
        return compute_kmeans(df, schema, req.n_components, req.n_clusters, req.feature_columns, req.encoding_spec)
    except ValueError as e:
        raise HTTPException(400, str(e))
