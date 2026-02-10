import os
import sys
import time
import asyncio
import json
import redis
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
import logging
import httpx

sys.path.append('/app/backend')
from services.sentiment_analyzer import SentimentAnalyzer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ADD before class definition (line 18):
shutdown_event = asyncio.Event()

def handle_shutdown(signum, frame):
    """Handle SIGTERM and SIGINT gracefully"""
    logger.info(f"Received signal {signum}, initiating graceful shutdown...")
    shutdown_event.set()

import signal
signal.signal(signal.SIGTERM, handle_shutdown)
signal.signal(signal.SIGINT, handle_shutdown)

class SentimentWorker:
    def __init__(self, redis_client, db_engine, stream_name: str, consumer_group: str):
        self.redis_client = redis_client
        self.stream_name = stream_name
        self.consumer_group = consumer_group
        self.consumer_name = f"worker_{os.getpid()}"
        
        self.async_session = sessionmaker(
            db_engine,
            class_=AsyncSession,
            expire_on_commit=False
        )
        
        self.local_analyzer = SentimentAnalyzer(model_type='local')
        
        try:
            self.external_analyzer = SentimentAnalyzer(model_type='external')
        except ValueError:
            logger.warning("No external LLM API key - using local only")
            self.external_analyzer = None
        
        self.processed_count = 0
        self.error_count = 0
        
        self._create_consumer_group()
    
    def _create_consumer_group(self):
        try:
            self.redis_client.xgroup_create(
                self.stream_name,
                self.consumer_group,
                id='0',
                mkstream=True
            )
            logger.info(f"Created consumer group: {self.consumer_group}")
        except redis.exceptions.ResponseError as e:
            if 'BUSYGROUP' in str(e):
                logger.info(f"Consumer group {self.consumer_group} already exists")
            else:
                raise
    
    async def process_message(self, message_id: str, message_data: dict) -> bool:
        try:
            required_fields = ['post_id', 'source', 'content', 'author', 'created_at']
            if not all(field in message_data for field in required_fields):
                logger.warning(f"Invalid message data: {message_data}")
                self.redis_client.xack(self.stream_name, self.consumer_group, message_id)
                return False
            
            # Parse ISO timestamp to datetime object for PostgreSQL
            # Remove timezone info to match TIMESTAMP WITHOUT TIME ZONE column
            from datetime import datetime as dt
            created_at_str = message_data['created_at']
            created_at_dt = dt.fromisoformat(created_at_str.replace('Z', '+00:00')).replace(tzinfo=None)
            
            content = message_data['content']
            
            # Use LOCAL models ONLY for reliable processing
            # External API is unreliable and causes processing failures
            try:
                sentiment_result = await self.local_analyzer.analyze_sentiment(content)
                emotion_result = await self.local_analyzer.analyze_emotion(content)
            except Exception as e:
                logger.error(f"Analysis failed for {message_data['post_id']}: {e}")
                # Use neutral fallback if even local model fails
                sentiment_result = {
                    'sentiment_label': 'neutral',
                    'confidence_score': 0.5,
                    'model_name': 'fallback'
                }
                emotion_result = {
                    'emotion': 'neutral',
                    'confidence_score': 0.5,
                    'model_name': 'fallback'
                }
            
            async with self.async_session() as session:
                await session.execute(
                    text("""
                        INSERT INTO social_media_posts (post_id, source, content, author, created_at, ingested_at)
                        VALUES (:post_id, :source, :content, :author, :created_at, NOW())
                        ON CONFLICT (post_id) DO UPDATE SET ingested_at = NOW()
                    """),
                    {
                        'post_id': message_data['post_id'],
                        'source': message_data['source'],
                        'content': message_data['content'],
                        'author': message_data['author'],
                        'created_at': created_at_dt  # Use parsed datetime
                    }
                )
                
                await session.execute(
                    text("""
                        INSERT INTO sentiment_analysis (
                            post_id, model_name, sentiment_label, 
                            confidence_score, emotion, analyzed_at
                        )
                        VALUES (:post_id, :model_name, :sentiment_label, 
                                :confidence_score, :emotion, NOW())
                    """),
                    {
                        'post_id': message_data['post_id'],
                        'model_name': sentiment_result['model_name'],
                        'sentiment_label': sentiment_result['sentiment_label'],
                        'confidence_score': sentiment_result['confidence_score'],
                        'emotion': emotion_result['emotion']
                    }
                )
                
                await session.commit()
            
            # Broadcast new post to WebSocket clients
            try:
                async with httpx.AsyncClient(timeout=2.0) as http_client:
                    await http_client.post(
                        'http://backend:8000/api/internal/broadcast',
                        json={
                            'post_id': message_data['post_id'],
                            'content': message_data['content'],
                            'source': message_data['source'],
                            'sentiment_label': sentiment_result['sentiment_label'],
                            'confidence_score': sentiment_result['confidence_score'],
                            'emotion': emotion_result['emotion']
                        }
                    )
                    logger.debug(f"Broadcasted post {message_data['post_id']}")
            except Exception as broadcast_error:
                # Don't fail processing if broadcast fails
                logger.warning(f"Broadcast failed: {broadcast_error}")
            
            self.redis_client.xack(self.stream_name, self.consumer_group, message_id)
            
            self.processed_count += 1
            if self.processed_count % 10 == 0:
                logger.info(f"Processed {self.processed_count} messages")
            
            return True
            
        except Exception as e:
            logger.error(f"Error processing message {message_id}: {e}")
            self.error_count += 1
            return False
    
    async def run(self, batch_size: int = 10, block_ms: int = 5000):
        logger.info(f"Worker {self.consumer_name} started")
        
        try:
            while not shutdown_event.is_set():
                try:
                    messages = self.redis_client.xreadgroup(
                        self.consumer_group,
                        self.consumer_name,
                        {self.stream_name: '>'},
                        count=batch_size,
                        block=block_ms
                    )
                    
                    if not messages:
                        continue
                    
                    tasks = []
                    for stream_name, stream_messages in messages:
                        for message_id, message_data in stream_messages:
                            tasks.append(self.process_message(message_id, message_data))
                    
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                        
                except redis.exceptions.ConnectionError as e:
                    logger.error(f"Redis connection error: {e}")
                    await asyncio.sleep(5)
                    continue
                    
        except KeyboardInterrupt:
            logger.info(f"Worker stopped")

if __name__ == "__main__":
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    STREAM_NAME = os.getenv("REDIS_STREAM_NAME", "social_posts_stream")
    CONSUMER_GROUP = os.getenv("REDIS_CONSUMER_GROUP", "sentiment_workers")
    
    DATABASE_URL = os.getenv("DATABASE_URL")
    if not DATABASE_URL:
        logger.error("DATABASE_URL environment variable required")
        exit(1)
    
    redis_client = redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        decode_responses=True
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
        logger.error("Could not connect to Redis")
        exit(1)
    
    db_engine = create_async_engine(DATABASE_URL, echo=False)
    
    worker = SentimentWorker(redis_client, db_engine, STREAM_NAME, CONSUMER_GROUP)
    asyncio.run(worker.run())
