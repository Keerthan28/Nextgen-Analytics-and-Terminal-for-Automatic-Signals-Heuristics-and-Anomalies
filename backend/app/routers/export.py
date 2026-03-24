from __future__ import annotations
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.models.schemas import ExportRequest, ChartRequest
from app.services.data_processor import get_dataset, get_schema, prepare_chart_data, compute_stats
from app.services.insights import generate_insights
from app.services.export_service import export_chart_png, export_metrics_csv, export_report_html

router = APIRouter(prefix="/api/export", tags=["export"])


@router.post("/png")
async def export_png(req: ExportRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    chart_data = prepare_chart_data(df, schema)
    chart_type = req.chart_config.chart_type.value if req.chart_config else "line"

    try:
        img_bytes = export_chart_png(chart_data, chart_type)
    except Exception as e:
        raise HTTPException(500, f"PNG export failed: {e}")

    return Response(content=img_bytes, media_type="image/png", headers={
        "Content-Disposition": "attachment; filename=chart.png"
    })


@router.post("/csv")
async def export_csv(req: ExportRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    stats = compute_stats(df, schema)
    csv_bytes = export_metrics_csv(stats)

    return Response(content=csv_bytes, media_type="text/csv", headers={
        "Content-Disposition": "attachment; filename=metrics.csv"
    })


@router.post("/html")
async def export_html(req: ExportRequest):
    df = get_dataset(req.dataset_id)
    schema = get_schema(req.dataset_id)
    if df is None or schema is None:
        raise HTTPException(404, "Dataset not found")

    chart_data = prepare_chart_data(df, schema)
    chart_type = req.chart_config.chart_type.value if req.chart_config else "line"
    stats = compute_stats(df, schema)
    report = generate_insights(df, schema, req.dataset_id)

    html = export_report_html(
        chart_data, chart_type, stats,
        [f.model_dump() for f in report.top_findings],
        report.summary,
    )

    return Response(content=html, media_type="text/html", headers={
        "Content-Disposition": "attachment; filename=report.html"
    })
