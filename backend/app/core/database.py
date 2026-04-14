"""SQLAlchemy async database setup.

Targets Supabase (PostgreSQL) in production via DATABASE_URL env var.
Supabase connection strings use the pooler (port 5432) or the direct
connection (port 5432 with ?sslmode=require).

Connection pool tuning for Railway:
  - Free tier Railway containers have limited RAM — keep pool_size small.
  - Supabase free tier allows up to 50 concurrent connections.
  - pool_size=5, max_overflow=10 keeps us well within limits.
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.core.config import settings

# Supabase/PostgreSQL requires SSL in production.
# asyncpg will negotiate TLS automatically when the server requires it.
_connect_args = {}
if "supabase.co" in settings.DATABASE_URL:
    _connect_args = {"ssl": "require"}

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.ENVIRONMENT == "development",
    pool_size=5,          # Conservative for Railway free tier
    max_overflow=10,
    pool_pre_ping=True,   # Detect stale connections (important for Supabase)
    connect_args=_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def init_db():
    """Create all tables on startup.

    In production, use `alembic upgrade head` in a one-off Railway job instead of
    calling this function — it is kept here for local dev convenience.
    """
    async with engine.begin() as conn:
        from app.models import user, account, job, outreach, agent  # noqa
        await conn.run_sync(Base.metadata.create_all)

    # Initialize pgvector schema (resume_embeddings table + extension)
    from app.core.chroma_client import init_vector_schema
    await init_vector_schema()
