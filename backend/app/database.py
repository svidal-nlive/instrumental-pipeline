from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os
from app.models import Base  # Import Base from models and re-export it

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/pipeline_db")

# Create the asynchronous database engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session maker
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency function for FastAPI
async def get_db():
    async with SessionLocal() as session:
        yield session
