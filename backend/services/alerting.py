
import os
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.api.websocket import manager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AlertService:
    """
    Monitors sentiment metrics and triggers alerts on anomalies
    """
    
    def __init__(self, db_session_maker):
        """
        Initialize with configuration from environment variables
        
        Loads:
        - ALERT_NEGATIVE_RATIO_THRESHOLD (default: 2.0)
        - ALERT_WINDOW_MINUTES (default: 5)
        - ALERT_MIN_POSTS (default: 10)
        """
        self.db_session_maker = db_session_maker
        self.ratio_threshold = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", "2.0"))
        self.window_minutes = int(os.getenv("ALERT_WINDOW_MINUTES", "5"))
        self.min_posts = int(os.getenv("ALERT_MIN_POSTS", "10"))
        self.check_interval = 60  # Check every minute
        self._running = False
        
    async def check_thresholds(self) -> Optional[dict]:
        """
        Check if current sentiment metrics exceed alert thresholds
        """
        async with self.db_session_maker() as session:
            # 1. Count positive/negative posts in last ALERT_WINDOW_MINUTES
            query = text("""
                SELECT 
                    COUNT(*) FILTER (WHERE sentiment_label = 'positive') as positive_count,
                    COUNT(*) FILTER (WHERE sentiment_label = 'negative') as negative_count,
                    COUNT(*) FILTER (WHERE sentiment_label = 'neutral') as neutral_count,
                    COUNT(*) as total_count
                FROM sentiment_analysis
                WHERE analyzed_at >= NOW() - INTERVAL ':minutes minutes'
            """)
            
            result = (await session.execute(
                query, 
                {"minutes": self.window_minutes}
            )).first()
            
            if not result or result.total_count < self.min_posts:
                return None
            
            # 3. Calculate ratio
            positive = result.positive_count
            negative = result.negative_count
            
            # Avoid division by zero
            if positive == 0:
                ratio = float(negative) if negative > 0 else 0.0
            else:
                ratio = negative / positive
            
            # 4. If ratio > threshold, trigger alert
            if ratio > self.ratio_threshold:
                return {
                    "alert_triggered": True,
                    "alert_type": "high_negative_ratio",
                    "threshold_value": self.ratio_threshold,
                    "actual_value": round(ratio, 2),
                    "window_start": (datetime.utcnow() - timedelta(minutes=self.window_minutes)).isoformat(),
                    "window_end": datetime.utcnow().isoformat(),
                    "post_count": result.total_count,
                    "details": {
                        "positive_count": result.positive_count,
                        "negative_count": result.negative_count,
                        "neutral_count": result.neutral_count,
                        "total_count": result.total_count
                    }
                }
            
            return None

    async def save_alert(self, alert_data: dict) -> int:
        """
        Save alert to database
        """
        async with self.db_session_maker() as session:
            query = text("""
                INSERT INTO sentiment_alerts (
                    alert_type, threshold_value, actual_value, 
                    window_start, window_end, post_count, details, triggered_at
                ) VALUES (
                    :alert_type, :threshold_value, :actual_value,
                    :window_start, :window_end, :post_count, :details, NOW()
                ) RETURNING id
            """)
            
            result = await session.execute(query, {
                "alert_type": alert_data["alert_type"],
                "threshold_value": alert_data["threshold_value"],
                "actual_value": alert_data["actual_value"],
                "window_start": datetime.fromisoformat(alert_data["window_start"]),
                "window_end": datetime.fromisoformat(alert_data["window_end"]),
                "post_count": alert_data["post_count"],
                "details": json.dumps(alert_data["details"])
            })
            
            await session.commit()
            alert_id = result.scalar()
            logger.warning(f"🚨 Alert Triggered: {alert_data['alert_type']} (Ratio: {alert_data['actual_value']})")
            return alert_id

    async def run_monitoring_loop(self):
        """
        Continuously monitor and trigger alerts
        """
        logger.info("Starting Alert Monitoring Service...")
        self._running = True
        
        while self._running:
            try:
                alert_data = await self.check_thresholds()
                
                if alert_data:
                    # Save to DB
                    await self.save_alert(alert_data)
                    
                    # Notify via WebSocket (optional but good for real-time)
                    # We can reuse the socket manager if accessible
                    # await manager.broadcast({"type": "alert", "data": alert_data})
                    
            except Exception as e:
                logger.error(f"Error in alert monitoring loop: {e}")
            
            await asyncio.sleep(self.check_interval)

    def stop(self):
        self._running = False
