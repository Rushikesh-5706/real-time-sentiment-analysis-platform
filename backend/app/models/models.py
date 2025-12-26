from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    Float,
    ForeignKey,
    Index,
    JSON,
)
from sqlalchemy.sql import func
from app.core.database import Base


class SocialMediaPost(Base):
    __tablename__ = "social_media_posts"

    id = Column(Integer, primary_key=True, index=True)
    post_id = Column(String(255), unique=True, index=True, nullable=False)
    source = Column(String(50), index=True, nullable=False)
    content = Column(Text, nullable=False)
    author = Column(String(255))
    created_at = Column(DateTime, nullable=False)
    ingested_at = Column(DateTime, server_default=func.now())


class SentimentAnalysis(Base):
    __tablename__ = "sentiment_analysis"

    id = Column(Integer, primary_key=True)
    post_id = Column(
        String(255),
        ForeignKey("social_media_posts.post_id", ondelete="CASCADE"),
        nullable=False,
    )
    model_name = Column(String(100), nullable=False)
    sentiment_label = Column(String(20), nullable=False)
    confidence_score = Column(Float, nullable=False)
    emotion = Column(String(50))
    analyzed_at = Column(DateTime, server_default=func.now(), index=True)


class SentimentAlert(Base):
    __tablename__ = "sentiment_alerts"

    id = Column(Integer, primary_key=True)
    alert_type = Column(String(50), nullable=False)
    threshold_value = Column(Float, nullable=False)
    actual_value = Column(Float, nullable=False)
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    post_count = Column(Integer, nullable=False)
    triggered_at = Column(DateTime, server_default=func.now(), index=True)
    details = Column(JSON)


