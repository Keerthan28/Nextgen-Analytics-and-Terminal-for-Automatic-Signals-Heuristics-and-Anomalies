import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import upload, charts, analytics, export, llm, clustering, ml, features

env_file = Path(__file__).resolve().parent.parent / ".env"
if env_file.exists():
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())

app = FastAPI(
    title="VEDA - Visual Engine for Data Analytics",
    version="2.0.0",
    description="Terminal-inspired charting workspace with Gemini AI-powered insights",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router)
app.include_router(charts.router)
app.include_router(analytics.router)
app.include_router(export.router)
app.include_router(llm.router)
app.include_router(clustering.router)
app.include_router(ml.router)
app.include_router(features.router)


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "VEDA", "ai": bool(os.getenv("GEMINI_API_KEY"))}
