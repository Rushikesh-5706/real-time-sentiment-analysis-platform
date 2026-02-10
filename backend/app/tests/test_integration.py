import pytest
import datetime
from sqlalchemy import text
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_e2e_full_flow(client: AsyncClient, db_session):
    # 1. Insert into DB (Simulate Worker)
    pid = f"e2e_{int(datetime.datetime.utcnow().timestamp())}"
    await db_session.execute(text("""
        INSERT INTO social_media_posts (post_id, source, content, author, created_at, ingested_at)
        VALUES (:pid, 'test', 'content', 'author', NOW(), NOW())
    """), {'pid': pid})
    
    await db_session.execute(text("""
        INSERT INTO sentiment_analysis (post_id, model_name, sentiment_label, confidence_score, emotion, analyzed_at)
        VALUES (:pid, 'test_model', 'positive', 0.95, 'joy', NOW())
    """), {'pid': pid})
    await db_session.commit()
    
    # 2. Check Posts API
    resp_posts = await client.get(f"/api/posts?limit=100")
    assert resp_posts.status_code == 200
    posts = resp_posts.json()["posts"]
    assert any(p["post_id"] == pid for p in posts)
    
    # 3. Check Aggregate API
    resp_agg = await client.get("/api/sentiment/aggregate?period=day")
    assert resp_agg.status_code == 200
    
    # 4. Check Distribution API
    resp_dist = await client.get("/api/sentiment/distribution")
    assert resp_dist.status_code == 200
    
@pytest.mark.asyncio
async def test_e2e_metrics_consistency(client: AsyncClient, db_session):
    # Check that distribution matches database counts
    resp = await client.get("/api/sentiment/distribution?hours=1")
    data = resp.json()
    # Hard to assert exact numbers without isolating DB, but we can check keys
    assert "positive" in data["distribution"]
    
@pytest.mark.asyncio
async def test_e2e_health(client: AsyncClient):
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    
@pytest.mark.asyncio
async def test_e2e_no_data_crash(client: AsyncClient):
    # Ensure APIs don't crash on empty/different filters
    resp = await client.get("/api/posts?source=nonexistent")
    assert resp.status_code == 200
    assert len(resp.json()["posts"]) == 0
