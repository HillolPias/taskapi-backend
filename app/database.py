from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

connect_args = {"ssl": "require"} if "neon.tech" in settings.database_url else {}

engine = create_async_engine(
    settings.database_url, echo=True, connect_args=connect_args
)

SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with SessionLocal() as session:
        yield session
