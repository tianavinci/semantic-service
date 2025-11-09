from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, Integer, JSON
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, ENUM as PG_ENUM
from api.app.config import settings
from typing import AsyncGenerator

engine = create_async_engine(settings.database_url, pool_pre_ping=True, pool_size=10, max_overflow=20)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase): ...
class Attribute(Base):
    __tablename__ = "attribute"
    __table_args__ = {"schema": "meta"}
    id: Mapped[int] = mapped_column(primary_key=True)
    namespace: Mapped[str] = mapped_column(String)
    entity: Mapped[str] = mapped_column(String)
    # Map to Postgres enum type `meta.attr_category` explicitly using dialect ENUM with schema
    category: Mapped[str] = mapped_column(
        PG_ENUM('entity', 'component', 'rule', 'measure', 'other', name='attr_category', schema='meta', create_type=False)
    )
    logical_name: Mapped[str] = mapped_column(Text)
    physical_name: Mapped[str] = mapped_column(Text)
    data_type: Mapped[str] = mapped_column(String)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_system: Mapped[str | None] = mapped_column(String, nullable=True)
    owner: Mapped[str | None] = mapped_column(String, nullable=True)
    # Match DB: synonyms is TEXT[]; tags and metadata are JSONB
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
