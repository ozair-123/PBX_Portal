"""Database session manager with async SQLAlchemy support."""

import os
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is not set")

# Convert postgresql:// to postgresql+asyncpg:// for async support
# If using psycopg2-binary, use postgresql+psycopg2://
if DATABASE_URL.startswith("postgresql://"):
    # For sync operations (Alembic migrations), keep as-is
    # For async operations, we'll use asyncpg
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
else:
    ASYNC_DATABASE_URL = DATABASE_URL

# Note: Since we're using psycopg2-binary per requirements.txt, we'll actually use sync sessions
# For true async, would need asyncpg. Let's keep it simple with sync sessions for MVP.

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Create sync engine (works with psycopg2-binary)
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10
)

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)


def get_db():
    """Dependency for FastAPI to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
