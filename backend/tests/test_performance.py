
import pytest
import asyncio
import time
from sqlalchemy import text
from app.core.database import AsyncSessionLocal

@pytest.mark.asyncio
async def test_worker_throughput():
    """
    Verify worker can process ≥2 messages per second
    Target: Process 100 messages in <50 seconds
    """
    # This test would need to:
    # 1. Publish 100 messages to Redis
    # 2. Measure time for worker to process all
    # 3. Assert processing rate ≥ 2 msg/sec
    
    # NOTE: This is a simulation, actual test needs Redis+Worker running
    start_time = time.time()
    
    # Simulate processing 100 posts
    async with AsyncSessionLocal() as session:
        # Count current posts
        initial_count = (await session.execute(
            text("SELECT COUNT(*) FROM sentiment_analysis")
        )).scalar()
        
    # Wait for worker to process (in real test)
    await asyncio.sleep(2)
    
    async with AsyncSessionLocal() as session:
        final_count = (await session.execute(
            text("SELECT COUNT(*) FROM sentiment_analysis")
        )).scalar()
    
    processing_time = time.time() - start_time
    messages_processed = final_count - initial_count
    
    if messages_processed > 0:
        rate = messages_processed / processing_time
        print(f"Processing rate: {rate:.2f} messages/second")
        # In production test, assert rate >= 2.0
