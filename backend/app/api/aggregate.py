from fastapi import APIRouter, Query
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

router = APIRouter(prefix="/api/sentiment")

@router.get("/aggregate")
async def sentiment_aggregate(
         period: str = Query(..., pattern="^(minute|hour|day)$")
):
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("""
                SELECT
                    date_trunc(:period, analyzed_at) AS ts,
                    sentiment_label,
                    COUNT(*) AS count
                FROM sentiment_analysis
                GROUP BY ts, sentiment_label
                ORDER BY ts
            """),
            {"period": period}
        )

        rows = result.all()

    buckets = {}
    for ts, label, count in rows:
        ts = ts.isoformat()
        if ts not in buckets:
            buckets[ts] = {
                "timestamp": ts,
                "positive": 0,
                "negative": 0,
                "neutral": 0
            }
        buckets[ts][label] = count

    return {
        "period": period,
        "data": list(buckets.values())
    }

