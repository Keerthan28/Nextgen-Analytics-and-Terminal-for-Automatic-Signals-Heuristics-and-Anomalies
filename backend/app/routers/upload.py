from __future__ import annotations
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.models.schemas import DatasetProfile, DatasetSchema, DatasetType, ColumnMapping
from app.services.data_processor import (
    load_file,
    detect_schema,
    get_dataset,
    get_schema,
    set_schema,
    compute_stats,
    build_tabular_profile,
)

router = APIRouter(prefix="/api/upload", tags=["upload"])


@router.post("/", response_model=DatasetProfile)
async def upload_dataset(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(400, "No file provided")

    allowed = (".csv", ".xlsx", ".xls")
    if not any(file.filename.lower().endswith(ext) for ext in allowed):
        raise HTTPException(400, f"Unsupported file type. Allowed: {', '.join(allowed)}")

    content = await file.read()
    if len(content) == 0:
        raise HTTPException(400, "Empty file")

    try:
        dataset_id, df = load_file(file.filename, content)
    except ValueError as e:
        raise HTTPException(422, str(e))

    schema = detect_schema(df)
    set_schema(dataset_id, schema)
    stats = compute_stats(df, schema)

    preview = df.head(10).fillna("").to_dict(orient="records")

    date_range = None
    if schema.datetime_column and schema.datetime_column in df.columns:
        import pandas as pd
        dts = pd.to_datetime(df[schema.datetime_column], errors="coerce").dropna()
        if len(dts):
            date_range = {"start": str(dts.min()), "end": str(dts.max())}

    tabular_profile = None
    if schema.dataset_type == DatasetType.TABULAR:
        tabular_profile = build_tabular_profile(df, schema)

    return DatasetProfile(
        dataset_id=dataset_id,
        schema=schema,
        preview=preview,
        stats=stats,
        date_range=date_range,
        tabular_profile=tabular_profile,
    )


@router.put("/{dataset_id}/schema")
async def update_schema(dataset_id: str, mappings: list[ColumnMapping]):
    df = get_dataset(dataset_id)
    if df is None:
        raise HTTPException(404, "Dataset not found")

    value_cols = []
    category_cols = []
    dt_col = None
    vol_col = None
    ohlc = {"open": False, "high": False, "low": False, "close": False}

    for m in mappings:
        if m.column_name not in df.columns:
            raise HTTPException(400, f"Column '{m.column_name}' not in dataset")
        if m.role.value == "datetime":
            dt_col = m.column_name
        elif m.role.value in ("close", "value"):
            value_cols.append(m.column_name)
        elif m.role.value == "volume":
            vol_col = m.column_name
        elif m.role.value == "category":
            category_cols.append(m.column_name)
        elif m.role.value in ohlc:
            ohlc[m.role.value] = True

    schema = DatasetSchema(
        columns=mappings,
        row_count=len(df),
        datetime_column=dt_col,
        value_columns=value_cols,
        category_columns=category_cols,
        volume_column=vol_col,
        has_ohlc=all(ohlc.values()),
    )
    set_schema(dataset_id, schema)
    return {"status": "ok", "schema": schema}
