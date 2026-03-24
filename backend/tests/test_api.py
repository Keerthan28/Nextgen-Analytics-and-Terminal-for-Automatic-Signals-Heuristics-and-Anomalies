import io
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


class TestHealth:
    def test_health_endpoint(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"


class TestUpload:
    def _csv_bytes(self, content: str) -> io.BytesIO:
        return io.BytesIO(content.encode())

    def test_upload_csv(self):
        csv = "date,price,volume\n2024-01-01,100,5000\n2024-01-02,101,6000\n2024-01-03,99,4500\n"
        r = client.post("/api/upload/", files={"file": ("test.csv", csv, "text/csv")})
        assert r.status_code == 200
        data = r.json()
        assert "dataset_id" in data
        assert data["schema"]["row_count"] == 3
        assert data["schema"]["datetime_column"] is not None

    def test_upload_empty(self):
        r = client.post("/api/upload/", files={"file": ("test.csv", b"", "text/csv")})
        assert r.status_code == 400

    def test_upload_bad_extension(self):
        r = client.post("/api/upload/", files={"file": ("test.pdf", b"hello", "application/pdf")})
        assert r.status_code == 400

    def test_upload_ohlcv(self):
        csv = "date,open,high,low,close,volume\n"
        csv += "2024-01-01,100,105,98,103,10000\n"
        csv += "2024-01-02,103,108,101,106,12000\n"
        csv += "2024-01-03,106,107,100,102,9000\n"
        r = client.post("/api/upload/", files={"file": ("stock.csv", csv, "text/csv")})
        assert r.status_code == 200
        data = r.json()
        assert data["schema"]["has_ohlc"] is True


class TestCharts:
    def _upload(self) -> str:
        csv = "date,close,volume\n"
        for i in range(30):
            csv += f"2024-01-{i+1:02d},{100+i},{5000+i*100}\n"
        r = client.post("/api/upload/", files={"file": ("data.csv", csv, "text/csv")})
        return r.json()["dataset_id"]

    def test_chart_data(self):
        did = self._upload()
        r = client.post("/api/charts/data", json={
            "dataset_id": did,
            "chart_type": "line",
            "series": ["close"],
            "indicators": [],
        })
        assert r.status_code == 200
        data = r.json()
        assert "x" in data
        assert "series" in data

    def test_chart_with_indicator(self):
        did = self._upload()
        r = client.post("/api/charts/data", json={
            "dataset_id": did,
            "chart_type": "line",
            "series": ["close"],
            "indicators": [{"indicator": "sma", "params": {"window": 5}}],
        })
        assert r.status_code == 200
        data = r.json()
        assert "indicators" in data
        assert any("sma" in k for k in data["indicators"])

    def test_invalid_dataset(self):
        r = client.post("/api/charts/data", json={
            "dataset_id": "nonexistent",
            "chart_type": "line",
        })
        assert r.status_code == 404


class TestAnalytics:
    def _upload(self) -> str:
        csv = "date,close,volume\n"
        for i in range(100):
            csv += f"2024-{(i//28)+1:02d}-{(i%28)+1:02d},{100+i*0.5},{5000+i*50}\n"
        r = client.post("/api/upload/", files={"file": ("data.csv", csv, "text/csv")})
        return r.json()["dataset_id"]

    def test_insights(self):
        did = self._upload()
        r = client.get(f"/api/analytics/insights/{did}")
        assert r.status_code == 200
        data = r.json()
        assert "top_findings" in data
        assert "summary" in data

    def test_stats(self):
        did = self._upload()
        r = client.get(f"/api/analytics/stats/{did}")
        assert r.status_code == 200
