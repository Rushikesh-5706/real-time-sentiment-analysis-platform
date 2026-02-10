# backend/services/alerting.py
from datetime import datetime, timedelta
from sqlalchemy import text

class AlertService:
    def __init__(self, session_maker, redis_client):
        self.session_maker = session_maker

    async def check_thresholds(self):
        async with self.session_maker() as session:
            rows = (await session.execute(text("""
                SELECT sentiment_label, COUNT(*)
                FROM sentiment_analysis
                WHERE analyzed_at >= NOW() - INTERVAL '5 minutes'
                GROUP BY sentiment_label
            """))).all()

        counts = {k:v for k,v in rows}
        pos = counts.get("positive", 0)
        neg = counts.get("negative", 0)

        if pos == 0 or neg / max(pos,1) <= 2.0:
            return None

        return {
            "alert_type": "high_negative_ratio",
            "threshold": 2.0,
            "actual_value": neg / pos,
            "timestamp": datetime.utcnow().isoformat()
        }

    async def save_alert(self, alert):
        async with self.session_maker() as session:
            await session.execute(text("""
                INSERT INTO sentiment_alerts
                (alert_type, threshold_value, actual_value,
                 window_start, window_end, post_count, details)
                VALUES (:t, :th, :av, NOW()-INTERVAL '5 minutes', NOW(), 0, '{}')
            """), {
                "t": alert["alert_type"],
                "th": 2.0,
                "av": alert["actual_value"]
            })
            await session.commit()

