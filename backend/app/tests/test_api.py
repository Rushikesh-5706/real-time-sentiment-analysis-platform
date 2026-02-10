import pytest
import datetime
from httpx import AsyncClient

# --- Health Check ---
@pytest.mark.asyncio
async def test_health_structure(client: AsyncClient):
    response = await client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert "services" in data
    assert "stats" in data
    assert "total_posts" in data["stats"]
    assert "database" in data["services"]

@pytest.mark.asyncio
async def test_health_services_status(client: AsyncClient):
    response = await client.get("/api/health")
    data = response.json()
    # Assuming test env DB is up or handled by fallback
    assert data["status"] in ["healthy", "unhealthy", "degraded"]

# --- Posts Endpoint ---
@pytest.mark.asyncio
async def test_get_posts_structure(client: AsyncClient):
    response = await client.get("/api/posts")
    data = response.json()
    assert "posts" in data
    assert "total" in data
    assert "limit" in data
    assert "offset" in data

@pytest.mark.asyncio
async def test_get_posts_pagination(client: AsyncClient):
    response = await client.get("/api/posts?limit=5&offset=0")
    data = response.json()
    assert data["limit"] == 5

@pytest.mark.asyncio
async def test_get_posts_validation_limit(client: AsyncClient):
    response = await client.get("/api/posts?limit=1000")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_get_posts_filter_source(client: AsyncClient):
    response = await client.get("/api/posts?source=twitter")
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_posts_filter_sentiment(client: AsyncClient):
    response = await client.get("/api/posts?sentiment=positive")
    assert response.status_code == 200

# --- Aggregate Endpoint ---
@pytest.mark.asyncio
async def test_aggregate_hourly_structure(client: AsyncClient):
    response = await client.get("/api/sentiment/aggregate?period=hour")
    data = response.json()
    assert "data" in data
    # If data exists, check fields
    if data["data"]:
        point = data["data"][0]
        assert "positive_count" in point
        assert "positive_percentage" in point
        assert "total_count" in point

@pytest.mark.asyncio
async def test_aggregate_summary_structure(client: AsyncClient):
    response = await client.get("/api/sentiment/aggregate?period=day")
    data = response.json()
    assert "summary" in data
    assert "total_posts" in data["summary"]

@pytest.mark.asyncio
async def test_aggregate_invalid_period(client: AsyncClient):
    response = await client.get("/api/sentiment/aggregate?period=year")
    assert response.status_code == 422

@pytest.mark.asyncio
async def test_aggregate_date_filtering(client: AsyncClient):
    # Just check it accepts params
    start = datetime.datetime.utcnow().isoformat()
    response = await client.get(f"/api/sentiment/aggregate?period=day&start_date={start}")
    assert response.status_code == 200

# --- Distribution Endpoint ---
@pytest.mark.asyncio
async def test_distribution_structure(client: AsyncClient):
    response = await client.get("/api/sentiment/distribution")
    data = response.json()
    assert "distribution" in data
    assert "percentages" in data
    assert "total" in data

@pytest.mark.asyncio
async def test_distribution_percentages_validity(client: AsyncClient):
    response = await client.get("/api/sentiment/distribution")
    data = response.json()
    pcts = data["percentages"]
    total_pct = pcts["positive"] + pcts["negative"] + pcts["neutral"]
    # Should be close to 100 or 0 if empty
    assert total_pct == 0 or abs(total_pct - 100) < 0.01

@pytest.mark.asyncio
async def test_distribution_hours_param(client: AsyncClient):
    response = await client.get("/api/sentiment/distribution?hours=48")
    assert response.status_code == 200
    assert response.json()["timeframe_hours"] == 48

@pytest.mark.asyncio
async def test_distribution_validation(client: AsyncClient):
    response = await client.get("/api/sentiment/distribution?hours=0")
    assert response.status_code == 422

# --- Websocket ---
from fastapi.testclient import TestClient
from app.api.main import app

def test_websocket_connect():
    client = TestClient(app)
    with client.websocket_connect("/ws/sentiment") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "connected"
        # Since logic loops, we might receive metrics immediately or after delay
        # Just creating connection is enough for this test
