from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200

def test_posts():
    r = client.get("/api/posts")
    assert r.status_code == 200

def test_distribution():
    r = client.get("/api/sentiment/distribution")
    assert r.status_code == 200
