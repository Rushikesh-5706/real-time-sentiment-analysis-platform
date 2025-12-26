from datetime import datetime, timedelta
from sqlalchemy import select, func
from app.core.database import AsyncSessionLocal
from app.models.models import SocialMediaPost, SentimentAnalysis

async def seed_demo_data():
    async with AsyncSessionLocal() as session:
        # Check if already seeded
        existing = await session.execute(
            select(func.count()).select_from(SocialMediaPost)
        )
        if existing.scalar() > 0:
            return  # ✅ already seeded, do nothing

        now = datetime.utcnow()

        # ---------------- INSERT POSTS FIRST ----------------
        posts = [
            SocialMediaPost(
                post_id="post_1",
                source="twitter",
                content="Amazing experience with Netflix.",
                author="user1",
                created_at=now - timedelta(hours=3),
            ),
            SocialMediaPost(
                post_id="post_2",
                source="twitter",
                content="Terrible experience using Amazon Prime.",
                author="user2",
                created_at=now - timedelta(hours=2),
            ),
            SocialMediaPost(
                post_id="post_3",
                source="reddit",
                content="I absolutely love Tesla Model 3.",
                author="user3",
                created_at=now - timedelta(hours=1),
            ),
            SocialMediaPost(
                post_id="post_4",
                source="reddit",
                content="Very disappointed with Tesla Model 3.",
                author="user4",
                created_at=now - timedelta(minutes=30),
            ),
        ]

        session.add_all(posts)
        await session.commit()  # ✅ CRITICAL

        # ---------------- INSERT ANALYSIS SECOND ----------------
        analyses = [
            SentimentAnalysis(
                post_id="post_1",
                model_name="demo-seed",
                sentiment_label="positive",
                confidence_score=0.9,
                emotion="joy",
            ),
            SentimentAnalysis(
                post_id="post_2",
                model_name="demo-seed",
                sentiment_label="negative",
                confidence_score=0.9,
                emotion="anger",
            ),
            SentimentAnalysis(
                post_id="post_3",
                model_name="demo-seed",
                sentiment_label="positive",
                confidence_score=0.9,
                emotion="joy",
            ),
            SentimentAnalysis(
                post_id="post_4",
                model_name="demo-seed",
                sentiment_label="negative",
                confidence_score=0.9,
                emotion="anger",
            ),
        ]

        session.add_all(analyses)
        await session.commit()

