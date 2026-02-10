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
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
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
            
        if start_date:
            filters.append("p.created_at >= :start_date")
            params["start_date"] = start_date
        
        if end_date:
            filters.append("p.created_at <= :end_date")
            params["end_date"] = end_date
            
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

@router.post("/internal/broadcast")
async def internal_broadcast(post_data: dict):
    """
    Internal endpoint for worker to broadcast new analyzed posts to WebSocket clients.
    This is called by the worker service after saving analysis results.
    """
    try:
        from app.api.websocket import broadcast_new_post
        await broadcast_new_post(post_data)
        return {"status": "ok", "broadcasted": post_data['post_id']}
    except Exception as e:
        # Logger is not defined here, using print for now or we should import logger
        print(f"Broadcast error: {e}")
        return {"status": "error", "message": str(e)}

@router.get("/alerts")
async def get_alerts(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    alert_type: Optional[str] = None
):
    """
    Retrieve triggered sentiment alerts with pagination.
    
    Returns recent alerts that were triggered when sentiment thresholds were exceeded.
    """
    async with AsyncSessionLocal() as session:
        filters = []
        params = {"limit": limit, "offset": offset}
        
        if alert_type:
            filters.append("alert_type = :alert_type")
            params["alert_type"] = alert_type
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        # Get alerts
        query = f"""
            SELECT 
                id, alert_type, threshold_value, actual_value,
                window_start, window_end, post_count, triggered_at, details
            FROM sentiment_alerts
            {where_clause}
            ORDER BY triggered_at DESC
            LIMIT :limit OFFSET :offset
        """
        
        rows = (await session.execute(text(query), params)).mappings().all()
        
        # Get total count
        count_query = f"SELECT COUNT(*) FROM sentiment_alerts {where_clause}"
        total = (await session.execute(text(count_query), params)).scalar()
    
    return {
        "alerts": [
            {
                "id": r["id"],
                "alert_type": r["alert_type"],
                "threshold_value": r["threshold_value"],
                "actual_value": r["actual_value"],
                "window_start": r["window_start"],
                "window_end": r["window_end"],
                "post_count": r["post_count"],
                "triggered_at": r["triggered_at"],
                "details": r["details"]
            }
            for r in rows
        ],
        "total": total,
        "limit": limit,
        "offset": offset
    }

@router.get("/metrics")
async def get_metrics():
    """
    System metrics for monitoring and observability.
    """
    async with AsyncSessionLocal() as session:
        # Total counts
        total_posts = (await session.execute(
            text("SELECT COUNT(*) FROM social_media_posts")
        )).scalar()
        
        total_analyses = (await session.execute(
            text("SELECT COUNT(*) FROM sentiment_analysis")
        )).scalar()
        
        total_alerts = (await session.execute(
            text("SELECT COUNT(*) FROM sentiment_alerts")
        )).scalar()
        
        # Processing metrics (last hour)
        last_hour_stats = (await session.execute(text("""
            SELECT 
                COUNT(*) as total,
                AVG(confidence_score) as avg_confidence,
                COUNT(*) FILTER (WHERE sentiment_label = 'positive') as positive,
                COUNT(*) FILTER (WHERE sentiment_label = 'negative') as negative,
                COUNT(*) FILTER (WHERE sentiment_label = 'neutral') as neutral
            FROM sentiment_analysis
            WHERE analyzed_at >= NOW() - INTERVAL '1 hour'
        """))).first()
        
        # Model usage stats
        model_usage = (await session.execute(text("""
            SELECT model_name, COUNT(*) as count
            FROM sentiment_analysis
            GROUP BY model_name
        """))).all()
    
    return {
        "timestamp": datetime.utcnow().isoformat(),
        "totals": {
            "posts": total_posts,
            "analyses": total_analyses,
            "alerts": total_alerts
        },
        "last_hour": {
            "total_processed": last_hour_stats.total,
            "avg_confidence": float(last_hour_stats.avg_confidence or 0),
            "sentiment_breakdown": {
                "positive": last_hour_stats.positive,
                "negative": last_hour_stats.negative,
                "neutral": last_hour_stats.neutral
            }
        },
        "models": [
            {"name": m.model_name, "usage_count": m.count}
            for m in model_usage
        ]
    }
