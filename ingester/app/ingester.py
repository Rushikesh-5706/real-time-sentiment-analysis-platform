import os
import time
import json
import random
from datetime import datetime, timezone
import redis

REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_NAME = os.getenv("REDIS_STREAM_NAME", "social_posts_stream")
RATE = int(os.getenv("INGESTER_RATE_SECONDS", 5))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    decode_responses=True
)

positive = [
    "I absolutely love {}.",
    "{} exceeded my expectations!",
    "Amazing experience with {}."
]
negative = [
    "Very disappointed with {}.",
    "Terrible experience using {}.",
    "I hate {}."
]
neutral = [
    "Just tried {}.",
    "Using {} for the first time.",
    "Received {} today."
]

products = [
    "Netflix",
    "Amazon Prime",
    "Tesla Model 3",
    "ChatGPT",
    "iPhone 16"
]

def generate_post():
    sentiment_type = random.choices(
        ["positive", "negative", "neutral"],
        weights=[40, 30, 30]
    )[0]

    product = random.choice(products)

    if sentiment_type == "positive":
        content = random.choice(positive).format(product)
    elif sentiment_type == "negative":
        content = random.choice(negative).format(product)
    else:
        content = random.choice(neutral).format(product)

    return {
        "post_id": f"live_{int(time.time() * 1000)}",
        "source": random.choice(["twitter", "reddit"]),
        "content": content,
        "author": f"user{random.randint(1,100)}",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

print("🚀 Ingester started")

while True:
    try:
        post = generate_post()
        redis_client.xadd(STREAM_NAME, post_data)
        print("📤 Published:", post["post_id"], flush=True)
        time.sleep(RATE)
    except Exception as e:
        print("❌ Ingester error:", e, flush=True)
        time.sleep(5)

