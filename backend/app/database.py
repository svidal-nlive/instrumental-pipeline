from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import os

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@db:5432/pipeline_db")

# Create the database engine
engine = create_async_engine(DATABASE_URL, echo=True)

# Async session maker
SessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

# Dependency function
async def get_db():
    async with SessionLocal() as session:
        yield session
