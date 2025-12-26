import os
import asyncio
import json
from datetime import datetime, timezone
import redis
from transformers import pipeline
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

print("🟢 Worker booting...", flush=True)

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_NAME = os.getenv("REDIS_STREAM_NAME")
GROUP_NAME = os.getenv("REDIS_CONSUMER_GROUP")
CONSUMER_NAME = "worker-1"

DATABASE_URL = os.getenv("DATABASE_URL")

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

print("🟢 Loading sentiment model...", flush=True)
sentiment_model = pipeline(
    "sentiment-analysis",
    model=os.getenv("HUGGINGFACE_MODEL"),
)

print("🟢 Loading emotion model...", flush=True)
emotion_model = pipeline(
    "text-classification",
    model=os.getenv("EMOTION_MODEL"),
    top_k=None,
)

print("🟢 Models loaded", flush=True)

def init_consumer_group():
    try:
        redis_client.xgroup_create(
            STREAM_NAME, GROUP_NAME, id="0", mkstream=True
        )
        print("🟢 Consumer group created", flush=True)
    except redis.exceptions.ResponseError:
        print("🟡 Consumer group exists", flush=True)

def parse_datetime(value: str) -> datetime:
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt
async def check_and_trigger_alert(session: AsyncSession):
    threshold = float(os.getenv("ALERT_NEGATIVE_RATIO_THRESHOLD", 2.0))
    window_minutes = int(os.getenv("ALERT_WINDOW_MINUTES", 5))
    min_posts = int(os.getenv("ALERT_MIN_POSTS", 10))

    result = await session.execute(
        text("""
        SELECT
            COUNT(*) FILTER (WHERE sentiment_label = 'positive') AS positive,
            COUNT(*) FILTER (WHERE sentiment_label = 'negative') AS negative,
            COUNT(*) AS total
        FROM sentiment_analysis
        WHERE analyzed_at >= NOW() - INTERVAL ':window minutes'
        """).bindparams(window=window_minutes)
    )

    row = result.fetchone()
    if not row or row.total < min_posts or row.positive == 0:
        return

    ratio = row.negative / row.positive

    if ratio > threshold:
        await session.execute(
            text("""
            INSERT INTO sentiment_alerts
            (alert_type, threshold_value, actual_value,
             window_start, window_end, post_count, details)
            VALUES
            ('high_negative_ratio', :threshold, :actual,
             NOW() - INTERVAL ':window minutes', NOW(),
             :count,
             json_build_object(
                'positive', :positive,
                'negative', :negative
             ))
            """).bindparams(
                threshold=threshold,
                actual=ratio,
                window=window_minutes,
                count=row.total,
                positive=row.positive,
                negative=row.negative
            )
        )

        print("🚨 ALERT TRIGGERED", flush=True)

async def process_message(message_id, data):
    created_at = parse_datetime(data["created_at"])

    sentiment = sentiment_model(data["content"])[0]
    emotions = emotion_model(data["content"])[0]
    top_emotion = max(emotions, key=lambda x: x["score"])

    sentiment_label = sentiment["label"].lower()
    confidence_score = float(sentiment["score"])
    emotion_label = top_emotion["label"]

    async with AsyncSessionLocal() as session:
        async with session.begin():
            await session.execute(
                text("""
                INSERT INTO social_media_posts
                (post_id, source, content, author, created_at)
                VALUES (:post_id, :source, :content, :author, :created_at)
                ON CONFLICT (post_id) DO NOTHING
                """),
                {
                    "post_id": data["post_id"],
                    "source": data["source"],
                    "content": data["content"],
                    "author": data["author"],
                    "created_at": created_at,
                },
            )

            await session.execute(
                text("""
                INSERT INTO sentiment_analysis
                await check_and_trigger_alert(session)
                (post_id, model_name, sentiment_label, confidence_score, emotion)
                VALUES (:post_id, :model, :label, :confidence, :emotion)
                """),
                {
                    "post_id": data["post_id"],
                    "model": os.getenv("HUGGINGFACE_MODEL"),
                    "label": sentiment_label,
                    "confidence": confidence_score,
                    "emotion": emotion_label,
                },
            )

    # --- REAL-TIME PUB/SUB UPDATE ---
    update_payload = {
        "post_id": data["post_id"],
        "source": data["source"],
        "content": data["content"],
        "sentiment": sentiment_label,
        "confidence": confidence_score,
        "emotion": emotion_label,
        "timestamp": datetime.utcnow().isoformat()
    }
    redis_client.publish("sentiment_updates", json.dumps(update_payload))
    # --------------------------------

    redis_client.xack(STREAM_NAME, GROUP_NAME, message_id)
    print(f"✅ Processed {data['post_id']}", flush=True)

async def run():
    init_consumer_group()
    print("🚀 Worker running", flush=True)

    while True:
        messages = redis_client.xreadgroup(
            GROUP_NAME,
            CONSUMER_NAME,
            {STREAM_NAME: ">"},
            count=5,
            block=5000,
        )

        for _, entries in messages:
            for message_id, data in entries:
                try:
                    await process_message(message_id, data)
                except Exception as e:
                    print(f"❌ Fatal error: {e}", flush=True)

if __name__ == "__main__":
    asyncio.run(run())
