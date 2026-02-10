import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.main import app
from app.core.database import Base
import os
from typing import AsyncGenerator, Generator

# Use an in-memory SQLite database for testing, or a separate test DB
# For simplicity in this env, we might use sqlite+aiosqlite:///:memory:
# But the app uses postgres specific features (date_trunc).
# So we must use the actual postgres DB but maybe a test database?
# The prompt says "zero manual configuration".
# We can use the existing DB but truncate tables?
# Be careful not to wipe production data if any.
# For this exercise, we will assume we can use the running postgres service.

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://sentiment_user:sentiment_password@postgres:5432/sentiment_db")

import pytest_asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def db_engine():
    engine = create_async_engine(DATABASE_URL, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()

@pytest_asyncio.fixture
async def db_session(db_engine):
    async_session = sessionmaker(db_engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        yield session
        await session.rollback()

@pytest_asyncio.fixture
async def client(db_session):
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c
