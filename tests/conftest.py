import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.main import app
from app.database import Base, get_db
from app.config import settings

test_engine = create_async_engine(settings.test_database_url, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(test_engine, expire_on_commit=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Runs once before any tests start: creates all tables in the test database.
    Runs once after all tests finish: drops them again, leaving no trace."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def clean_tables():
    """Runs before EVERY individual test: wipes all data so each test
    starts from a completely empty, predictable database."""
    async with test_engine.begin() as conn:
        await conn.execute(text("TRUNCATE tasks, projects RESTART IDENTITY CASCADE"))
    yield


@pytest_asyncio.fixture
async def client():
    """Gives each test a fake HTTP client wired to your real FastAPI app,
    but talking to the TEST database instead of your real one."""

    async def override_get_db():
        async with TestSessionLocal() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()
