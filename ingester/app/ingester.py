import time
import json
import random
import uuid
import os
from datetime import datetime, timezone

import redis


REDIS_HOST = os.getenv("REDIS_HOST", "redis")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
STREAM_NAME = os.getenv("REDIS_STREAM_NAME", "social_posts_stream")

POSTS_PER_MINUTE = int(os.getenv("POSTS_PER_MINUTE", 60))
SLEEP_TIME = 60 / POSTS_PER_MINUTE


POSITIVE_TEMPLATES = [
    "I absolutely love {}!",
    "{} exceeded my expectations!",
    "Amazing experience with {}.",
]

NEGATIVE_TEMPLATES = [
    "Very disappointed with {}.",
    "Terrible experience using {}.",
    "I hate {}. Waste of money.",
]

NEUTRAL_TEMPLATES = [
    "Just tried {} today.",
    "Using {} for the first time.",
    "Received {} today.",
]

PRODUCTS = [
    "iPhone 16",
    "Tesla Model 3",
    "ChatGPT",
    "Netflix",
    "Amazon Prime",
]


def generate_post():
    sentiment_type = random.choices(
        ["positive", "neutral", "negative"],
        weights=[40, 30, 30],
        k=1,
    )[0]

    if sentiment_type == "positive":
        template = random.choice(POSITIVE_TEMPLATES)
    elif sentiment_type == "negative":
        template = random.choice(NEGATIVE_TEMPLATES)
    else:
        template = random.choice(NEUTRAL_TEMPLATES)

    product = random.choice(PRODUCTS)

    return {
        "post_id": f"post_{uuid.uuid4().hex}",
        "source": random.choice(["twitter", "reddit"]),
        "content": template.format(product),
        "author": f"user_{random.randint(1000, 9999)}",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }


def main():
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

    print("🚀 Ingester started, publishing to Redis Stream")

    while True:
        post = generate_post()
        try:
            r.xadd(STREAM_NAME, post)
            print(f"Published: {post['post_id']}")
        except redis.exceptions.RedisError as e:
            print(f"Redis error: {e}")

        time.sleep(SLEEP_TIME)


if __name__ == "__main__":
    main()

