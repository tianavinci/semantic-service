from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Text, Boolean, Integer
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, ENUM as PG_ENUM
from api.app.config import settings
from typing import AsyncGenerator
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
import logging

logger = logging.getLogger(__name__)

# Handle sslmode/ssl and timeout query params for asyncpg: asyncpg.connect expects
# proper python types (bool/number), but query params from the URL are strings.
# We'll remove these params from the URL and forward them via connect_args.
raw_db_url = settings.database_url or ""
connect_args: dict | None = None
try:
    parts = urlsplit(raw_db_url)
    if parts.query:
        qs = dict(parse_qsl(parts.query, keep_blank_values=True))
        # Extract known connect args we want to convert
        sslmode = qs.pop("sslmode", None)
        ssl = qs.pop("ssl", None)
        timeout = qs.pop("timeout", None)

        tmp_connect_args: dict = {}
        if sslmode is not None:
            # interpret common sslmode values
            val = sslmode.lower()
            if val in ("disable", "false", "0", "no"):
                tmp_connect_args["ssl"] = False
            elif val in ("require", "verify-ca", "verify-full", "true", "1", "yes"):
                tmp_connect_args["ssl"] = True
            else:
                # for values like 'prefer' or 'allow' do not force an ssl arg
                pass
        elif ssl is not None:
            if ssl.lower() in ("false", "0", "no"):
                tmp_connect_args["ssl"] = False
            elif ssl.lower() in ("true", "1", "yes"):
                tmp_connect_args["ssl"] = True
            # otherwise leave it out

        if timeout is not None:
            try:
                # accept integer or float
                if "." in timeout:
                    tmp_connect_args["timeout"] = float(timeout)
                else:
                    tmp_connect_args["timeout"] = int(timeout)
            except Exception:
                # ignore invalid timeout value and let asyncpg use its default
                logger.warning("Invalid timeout value in DATABASE_URL query params: %r", timeout)

        # Rebuild URL without the consumed query params
        new_query = urlencode(qs, doseq=True)
        parts = parts._replace(query=new_query)
        raw_db_url = urlunsplit(parts)

        connect_args = tmp_connect_args or None
except Exception as exc:
    # if anything goes wrong parsing, fall back to using raw_db_url without connect_args
    logger.exception("Failed to parse DATABASE_URL query params: %s", exc)
    connect_args = None

# Log sanitized connection info to help debugging (do NOT log credentials)
try:
    safe_url = raw_db_url
    # remove password if present
    if "@" in safe_url and "://" in safe_url:
        prefix, rest = safe_url.split("@", 1)
        if ":" in prefix:
            scheme_and_user = prefix.split("//", 1)[0]
            userinfo = prefix.split("//", 1)[1]
            if ":" in userinfo:
                user = userinfo.split(":")[0]
                safe_url = f"{scheme_and_user}//{user}:*****@{rest}"
    logger.info("Using DB URL: %s; connect_args keys: %s", safe_url, list(connect_args.keys()) if connect_args else None)
except Exception:
    # ignore any issues building safe_url
    pass

if connect_args:
    engine = create_async_engine(raw_db_url, pool_pre_ping=True, pool_size=10, max_overflow=20, connect_args=connect_args)
else:
    engine = create_async_engine(raw_db_url, pool_pre_ping=True, pool_size=10, max_overflow=20)

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
    created_by: Mapped[str] = mapped_column(String, nullable=False, default='System')
    updated_by: Mapped[str] = mapped_column(String, nullable=False, default='System')
    # Match DB: synonyms is TEXT[]; tags and metadata are JSONB
    synonyms: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    tags: Mapped[list[str]] = mapped_column(JSONB, default=list)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    meta: Mapped[dict] = mapped_column("metadata", JSONB, default=dict)

async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
