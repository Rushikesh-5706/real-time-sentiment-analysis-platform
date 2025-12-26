from sqlalchemy import text
from datetime import datetime, timedelta
from app.core.database import AsyncSessionLocal
import os

NEG_RATIO = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0))
WINDOW_MIN = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
MIN_POSTS = int(os.getenv("ALERT_MIN_POSTS", 10))


async def check_and_trigger_alert():
    async with AsyncSessionLocal() as session:
        result = await session.execute(text("""
            SELECT
              SUM(CASE WHEN sentiment_label='negative' THEN 1 ELSE 0 END) AS neg,
              SUM(CASE WHEN sentiment_label='positive' THEN 1 ELSE 0 END) AS pos,
              COUNT(*) AS total
            FROM sentiment_analysis
            WHERE analyzed_at >= NOW() - INTERVAL ':m minutes'
        """.replace(":m", str(WINDOW_MIN))))

        neg, pos, total = result.fetchone()

        if not total or total < MIN_POSTS or not pos:
            return None

        ratio = neg / pos
        if ratio <= NEG_RATIO:
            return None

        await session.execute(text("""
            INSERT INTO sentiment_alerts
            (alert_type, threshold_value, actual_value,
             window_start, window_end, post_count, details)
            VALUES
            ('high_negative_ratio', :th, :av,
             NOW() - INTERVAL ':m minutes', NOW(), :cnt, :details)
        """.replace(":m", str(WINDOW_MIN))), {
            "th": NEG_RATIO,
            "av": ratio,
            "cnt": total,
            "details": {"neg": neg, "pos": pos}
        })

        await session.commit()

