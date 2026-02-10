from app.api.aggregate import router as aggregate_router
from fastapi import APIRouter, Query
from datetime import datetime
from typing import Optional
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
import redis
import os
import json

router = APIRouter(prefix="/api")
router.include_router(aggregate_router)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))

def get_redis():
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

@router.get("/health")
async def health_check():
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            db_status = "connected"

            total_posts = (await session.execute(
                text("SELECT COUNT(*) FROM social_media_posts")
            )).scalar()

            total_analyses = (await session.execute(
                text("SELECT COUNT(*) FROM sentiment_analysis")
            )).scalar()

            recent_posts_1h = (await session.execute(
                text("""
                SELECT COUNT(*) FROM social_media_posts
                WHERE ingested_at >= NOW() - INTERVAL '1 hour'
                """)
            )).scalar()
    except Exception:
        db_status = "disconnected"
        total_posts = total_analyses = recent_posts_1h = 0

    try:
        r = get_redis()
        r.ping()
        redis_status = "connected"
    except Exception:
        redis_status = "disconnected"

    overall_status = (
        "healthy" if db_status == "connected" and redis_status == "connected"
        else "unhealthy"
    )

    return {
        "status": overall_status,
        "timestamp": datetime.utcnow().isoformat(),
        "services": {"database": db_status, "redis": redis_status},
        "stats": {
            "total_posts": total_posts,
            "total_analyses": total_analyses,
            "recent_posts_1h": recent_posts_1h,
        },
    }

@router.get("/posts")
async def get_posts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    source: Optional[str] = None,
    sentiment: Optional[str] = None,
):
    async with AsyncSessionLocal() as session:
        # Build query filters
        filters = []
        params = {"limit": limit, "offset": offset}
        
        if source:
            filters.append("p.source = :source")
            params["source"] = source
            
        if sentiment:
            filters.append("a.sentiment_label = :sentiment")
            params["sentiment"] = sentiment
            
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        # Get Posts
        query = f"""
            SELECT
              p.post_id, p.source, p.content, p.author, p.created_at,
              a.sentiment_label, a.confidence_score, a.emotion, a.model_name
            FROM social_media_posts p
            JOIN sentiment_analysis a ON a.post_id = p.post_id
            {where_clause}
            ORDER BY p.created_at DESC
            LIMIT :limit OFFSET :offset
            """
            
        rows = (await session.execute(text(query), params)).mappings().all()

        # Get Total Count
        count_query = f"""
            SELECT COUNT(*) 
            FROM social_media_posts p
            JOIN sentiment_analysis a ON a.post_id = p.post_id
            {where_clause}
        """
        total = (await session.execute(text(count_query), params)).scalar()

    return {
        "posts": [
            {
                "post_id": r["post_id"],
                "source": r["source"],
                "content": r["content"],
                "author": r["author"],
                "created_at": r["created_at"],
                "sentiment": {
                    "label": r["sentiment_label"],
                    "confidence": r["confidence_score"],
                    "emotion": r["emotion"],
                    "model_name": r["model_name"],
                },
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }

@router.get("/sentiment/distribution")
async def sentiment_distribution(hours: int = Query(24, ge=1, le=168)):
    async with AsyncSessionLocal() as session:
        rows = (await session.execute(
            text(f"""
            SELECT sentiment_label, COUNT(*)
            FROM sentiment_analysis
            WHERE analyzed_at >= NOW() - INTERVAL '{hours} hours'
            GROUP BY sentiment_label
            """)
        )).all()

    distribution = {"positive": 0, "negative": 0, "neutral": 0}
    for label, cnt in rows:
        distribution[label] = cnt

    total = sum(distribution.values())

    return {
        "timeframe_hours": hours,
        "distribution": distribution,
        "total": total,
        "percentages": {
            k: (v / total * 100) if total else 0
            for k, v in distribution.items()
        },
    }
