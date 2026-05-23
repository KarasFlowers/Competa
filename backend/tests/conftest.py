"""Shared test fixtures — in-memory DB + async client."""

import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Force mock LLM in all tests (before importing app/settings)
os.environ["LLM_MODE"] = "mock"

from app.db.session import get_session
from app.main import app
from app.models.database import Base

# In-memory SQLite for tests
TEST_ENGINE = create_async_engine("sqlite+aiosqlite://", echo=False)
TestSession = async_sessionmaker(TEST_ENGINE, class_=AsyncSession, expire_on_commit=False)


@pytest.fixture(autouse=True)
async def setup_db():
    """Create tables before each test, drop after."""
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with TEST_ENGINE.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def _override_get_session():
    async with TestSession() as session:
        yield session


# Override the DB dependency for all tests
app.dependency_overrides[get_session] = _override_get_session


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def session():
    async with TestSession() as s:
        yield s
