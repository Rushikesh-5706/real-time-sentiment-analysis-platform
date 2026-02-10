import os
import time
import json
import random
from datetime import datetime, timezone
import redis
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DataIngester:
    def __init__(self, redis_client, stream_name: str, posts_per_minute: int = 60):
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.posts_per_minute = posts_per_minute
        self.sleep_interval = 60.0 / posts_per_minute
        
        self.positive_templates = [
            "I absolutely love {product}!",
            "{product} exceeded my expectations!",
            "Amazing experience with {product}",
            "Best purchase ever! {product} is fantastic",
            "{product} is simply outstanding"
        ]
        
        self.negative_templates = [
            "Very disappointed with {product}",
            "Terrible experience with {product}",
            "Would not recommend {product}",
            "I hate {product}. Waste of money",
            "{product} is awful and not worth it"
        ]
        
        self.neutral_templates = [
            "Just tried {product}",
            "Received {product} today",
            "Using {product} for the first time",
            "{product} arrived as expected",
            "Checking out {product} now"
        ]
        
        self.products = [
            "iPhone 16", "Tesla Model 3", "ChatGPT", "Netflix", 
            "Amazon Prime", "PlayStation 5", "AirPods Pro",
            "MacBook Pro", "Samsung Galaxy", "Google Pixel"
        ]
        
        self.sources = ["reddit", "twitter", "facebook", "instagram"]
        
    def generate_post(self) -> dict:
        sentiment_type = random.choices(
            ["positive", "negative", "neutral"],
            weights=[40, 30, 30]
        )[0]
        
        product = random.choice(self.products)
        
        if sentiment_type == "positive":
            content = random.choice(self.positive_templates).format(product=product)
        elif sentiment_type == "negative":
            content = random.choice(self.negative_templates).format(product=product)
        else:
            content = random.choice(self.neutral_templates).format(product=product)
        
        return {
            'post_id': f'post_{int(time.time() * 1000000)}',
            'source': random.choice(self.sources),
            'content': content,
            'author': f'user{random.randint(1000, 9999)}',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
    
    async def publish_post(self, post: dict) -> bool:
        try:
            message_id = self.redis_client.xadd(self.stream_name, post)
            logger.info(f"Published post {post['post_id']} with message_id {message_id}")
            return True
        except redis.exceptions.ConnectionError as e:
            logger.error(f"Redis connection error: {e}")
            return False
        except Exception as e:
            logger.error(f"Error publishing post: {e}")
            return False
    
    async def start(self, duration_seconds: int = None):
        logger.info(f"Starting ingester - {self.posts_per_minute} posts/minute")
        start_time = time.time()
        post_count = 0
        
        try:
            while True:
                if duration_seconds and (time.time() - start_time) >= duration_seconds:
                    logger.info(f"Duration limit reached. Published {post_count} posts")
                    break
                
                post = self.generate_post()
                success = await self.publish_post(post)
                
                if success:
                    post_count += 1
                    if post_count % 10 == 0:
                        logger.info(f"Published {post_count} posts")
                
                time.sleep(self.sleep_interval)
                
        except KeyboardInterrupt:
            logger.info(f"Ingester stopped. Total posts published: {post_count}")
        except Exception as e:
            logger.error(f"Fatal error in ingester: {e}")

if __name__ == "__main__":
    import asyncio
    
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    STREAM_NAME = os.getenv("REDIS_STREAM_NAME", "social_posts_stream")
    POSTS_PER_MINUTE = int(os.getenv("POSTS_PER_MINUTE", 60))
    
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True,
        socket_connect_timeout=5,
        socket_timeout=5
    )
    
    for attempt in range(30):
        try:
            redis_client.ping()
            logger.info("Connected to Redis")
            break
        except:
            logger.info(f"Waiting for Redis... (attempt {attempt + 1}/30)")
            time.sleep(2)
    else:
        logger.error("Could not connect to Redis after 30 attempts")
        exit(1)
    
    ingester = DataIngester(redis_client, STREAM_NAME, POSTS_PER_MINUTE)
    asyncio.run(ingester.start())
