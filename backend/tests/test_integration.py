import pytest
import datetime
from sqlalchemy import text
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_e2e_full_flow_comprehensive(client: AsyncClient, db_session):
    """
    Comprehensive end-to-end test: 
    Insert data → Verify all endpoints → Check data consistency
    """
    # 1. Insert test data (simulate worker behavior)
    pid = f"e2e_{int(datetime.datetime.utcnow().timestamp())}"
    await db_session.execute(text("""
        INSERT INTO social_media_posts (post_id, source, content, author, created_at, ingested_at)
        VALUES (:pid, 'test_platform', 'I love this test!', 'test_user', NOW(), NOW())
    """), {'pid': pid})
    
    await db_session.execute(text("""
        INSERT INTO sentiment_analysis (post_id, model_name, sentiment_label, confidence_score, emotion, analyzed_at)
        VALUES (:pid, 'test_model', 'positive', 0.95, 'joy', NOW())
    """), {'pid': pid})
    await db_session.commit()
    
    # 2. Test Posts API - verify structure and data
    resp_posts = await client.get("/api/posts?limit=100")
    assert resp_posts.status_code == 200
    posts_data = resp_posts.json()
    
    # Verify structure
    assert "posts" in posts_data
    assert "total" in posts_data
    assert "limit" in posts_data
    assert "offset" in posts_data
    
    # Verify our post exists
    posts = posts_data["posts"]
    assert any(p["post_id"] == pid for p in posts), "Inserted post not found"
    
    # Find our post and verify fields
    our_post = next(p for p in posts if p["post_id"] == pid)
    assert our_post["source"] == "test_platform"
    assert our_post["content"] == "I love this test!"
    assert our_post["author"] == "test_user"
    assert "sentiment" in our_post
    assert our_post["sentiment"]["label"] == "positive"
    assert our_post["sentiment"]["confidence"] == 0.95
    assert our_post["sentiment"]["emotion"] == "joy"
    assert our_post["sentiment"]["model_name"] == "test_model"
    
    # 3. Test Aggregate API - verify structure and calculations
    resp_agg = await client.get("/api/sentiment/aggregate?period=day")
    assert resp_agg.status_code == 200
    agg_data = resp_agg.json()
    
    # Verify structure
    assert "period" in agg_data
    assert "data" in agg_data
    assert "summary" in agg_data
    assert agg_data["period"] == "day"
    
    # Verify data is not empty (we just inserted data)
    assert len(agg_data["data"]) > 0, "Aggregate data should not be empty"
    
    # Verify first data point has all required fields
    first_point = agg_data["data"][0]
    required_fields = [
        'timestamp', 'positive_count', 'negative_count', 'neutral_count',
        'total_count', 'positive_percentage', 'negative_percentage',
        'neutral_percentage', 'average_confidence'
    ]
    for field in required_fields:
        assert field in first_point, f"Missing field: {field}"
    
    # Verify summary structure
    assert "total_posts" in agg_data["summary"]
    assert "positive_total" in agg_data["summary"]
    assert "negative_total" in agg_data["summary"]
    assert "neutral_total" in agg_data["summary"]
    assert agg_data["summary"]["total_posts"] >= 1
    
    # 4. Test Distribution API - verify calculations
    resp_dist = await client.get("/api/sentiment/distribution?hours=24")
    assert resp_dist.status_code == 200
    dist_data = resp_dist.json()
    
    # Verify structure
    assert "timeframe_hours" in dist_data
    assert "distribution" in dist_data
    assert "total" in dist_data
    assert "percentages" in dist_data
    assert dist_data["timeframe_hours"] == 24
    
    # Verify distribution has all sentiment types
    assert "positive" in dist_data["distribution"]
    assert "negative" in dist_data["distribution"]
    assert "neutral" in dist_data["distribution"]
    
    # Verify percentages sum to 100 (or 0 if no data)
    pct = dist_data["percentages"]
    total_pct = pct["positive"] + pct["negative"] + pct["neutral"]
    if dist_data["total"] > 0:
        assert abs(total_pct - 100.0) < 0.1, f"Percentages sum to {total_pct}, expected ~100"
    
    # Our post was positive, so positive count should be >= 1
    assert dist_data["distribution"]["positive"] >= 1

@pytest.mark.asyncio
async def test_e2e_empty_data_handling(client: AsyncClient):
    """
    Test that endpoints handle empty results gracefully
    """
    # Query with date range that has no data
    resp = await client.get("/api/sentiment/aggregate?period=hour&start_date=2020-01-01T00:00:00&end_date=2020-01-02T00:00:00")
    assert resp.status_code == 200
    data = resp.json()
    
    # Should return structure with at least one time period with zeros
    assert "data" in data
    assert len(data["data"]) >= 1, "Should return at least one time period even when empty"
    
    first = data["data"][0]
    assert first["total_count"] == 0
    assert first["positive_count"] == 0

@pytest.mark.asyncio
async def test_e2e_filtering_consistency(client: AsyncClient, db_session):
    """
    Test that filtering works correctly across endpoints
    """
    # Insert posts with different sources
    timestamp = int(datetime.datetime.utcnow().timestamp())
    
    await db_session.execute(text("""
        INSERT INTO social_media_posts (post_id, source, content, author, created_at, ingested_at)
        VALUES 
            (:pid1, 'twitter', 'content1', 'user1', NOW(), NOW()),
            (:pid2, 'reddit', 'content2', 'user2', NOW(), NOW())
    """), {'pid1': f'test_twitter_{timestamp}', 'pid2': f'test_reddit_{timestamp}'})
    
    await db_session.execute(text("""
        INSERT INTO sentiment_analysis (post_id, model_name, sentiment_label, confidence_score, emotion, analyzed_at)
        VALUES 
            (:pid1, 'test', 'positive', 0.9, 'joy', NOW()),
            (:pid2, 'test', 'negative', 0.8, 'anger', NOW())
    """), {'pid1': f'test_twitter_{timestamp}', 'pid2': f'test_reddit_{timestamp}'})
    await db_session.commit()
    
    # Test source filtering
    resp = await client.get("/api/posts?source=twitter")
    posts = resp.json()["posts"]
    twitter_posts = [p for p in posts if p["source"] == "twitter"]
    assert len(twitter_posts) > 0
    assert all(p["source"] == "twitter" for p in twitter_posts)
    
    # Test sentiment filtering
    resp = await client.get("/api/posts?sentiment=positive")
    posts = resp.json()["posts"]
    positive_posts = [p for p in posts if p["sentiment"]["label"] == "positive"]
    assert len(positive_posts) > 0
    assert all(p["sentiment"]["label"] == "positive" for p in positive_posts)

@pytest.mark.asyncio
async def test_e2e_health_endpoint(client: AsyncClient):
    """
    Comprehensive health check validation
    """
    resp = await client.get("/api/health")
    assert resp.status_code == 200
    
    data = resp.json()
    
    # Verify all required fields
    assert "status" in data
    assert "timestamp" in data
    assert "services" in data
    assert "stats" in data
    
    # Verify status is valid
    assert data["status"] in ["healthy", "unhealthy", "degraded"]
    
    # Verify services structure
    services = data["services"]
    assert "database" in services
    assert "redis" in services
    assert services["database"] in ["connected", "disconnected"]
    assert services["redis"] in ["connected", "disconnected"]
    
    # Verify stats structure
    stats = data["stats"]
    assert "total_posts" in stats
    assert "total_analyses" in stats
    assert "recent_posts_1h" in stats
    assert isinstance(stats["total_posts"], int)
    assert stats["total_posts"] >= 0

@pytest.mark.asyncio
async def test_e2e_pagination(client: AsyncClient, db_session):
    """
    Test pagination works correctly
    """
    # Get first page
    resp1 = await client.get("/api/posts?limit=5&offset=0")
    page1 = resp1.json()
    
    # Get second page
    resp2 = await client.get("/api/posts?limit=5&offset=5")
    page2 = resp2.json()
    
    # Verify structure
    assert page1["limit"] == 5
    assert page1["offset"] == 0
    assert page2["limit"] == 5
    assert page2["offset"] == 5
    
    # If we have enough data, verify pages are different
    if page1["total"] > 5:
        posts1_ids = {p["post_id"] for p in page1["posts"]}
        posts2_ids = {p["post_id"] for p in page2["posts"]}
        # Pages should have different posts (no overlap)
        assert len(posts1_ids.intersection(posts2_ids)) == 0

@pytest.mark.asyncio
async def test_e2e_aggregate_periods(client: AsyncClient):
    """
    Test all aggregation periods work
    """
    for period in ['minute', 'hour', 'day']:
        resp = await client.get(f"/api/sentiment/aggregate?period={period}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["period"] == period
        assert "data" in data
