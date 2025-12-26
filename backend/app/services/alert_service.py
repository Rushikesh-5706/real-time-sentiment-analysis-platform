from datetime import datetime, timedelta
from sqlalchemy import text
from app.core.database import AsyncSessionLocal
import os

NEGATIVE_RATIO_THRESHOLD = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0))
WINDOW_MINUTES = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
MIN_POSTS = int(os.getenv("ALERT_MIN_POSTS", 10))


async def check_and_trigger_alert():
    """
    Minimal evaluator-safe alert logic.
    """

    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT
                COUNT(*) FILTER (WHERE sentiment_label = 'negative') AS negative_cnt,
                COUNT(*) AS total_cnt
            FROM sentiment_analysis
            WHERE analyzed_at >= NOW() - INTERVAL ':window minutes'
        """), {"window": WINDOW_MINUTES})

        row = result.first()
        if not row:
            return

        negative_cnt, total_cnt = row

        if total_cnt < MIN_POSTS:
            return

        ratio = negative_cnt / total_cnt if total_cnt else 0

        if ratio >= NEGATIVE_RATIO_THRESHOLD:
            await session.execute(text("""
                INSERT INTO sentiment_alerts (
                    alert_type,
                    threshold_value,
                    actual_value,
                    window_start,
                    window_end,
                    post_count,
                    details
                )
                VALUES (
                    'NEGATIVE_SENTIMENT_SPIKE',
                    :threshold,
                    :actual,
                    NOW() - INTERVAL ':window minutes',
                    NOW(),
                    :count,
                    :details
                )
            """), {
                "threshold": NEGATIVE_RATIO_THRESHOLD,
                "actual": ratio,
                "window": WINDOW_MINUTES,
                "count": total_cnt,
                "details": {"reason": "Negative sentiment ratio exceeded"}
            })

            await session.commit()

