from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "healthy"
    assert r.json()["service"] == "manufacturing-quality-investigation-agent"


def test_readiness():
    r = client.get("/readiness")
    assert r.status_code == 200
    assert r.json()["status"] == "ready"
    assert r.json()["checks"]["database"] == "ready"
