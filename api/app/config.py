from pydantic import BaseModel
import os

class Settings(BaseModel):
    # Use localhost as the default for local development. When running in Docker-compose
    # the `DATABASE_URL` environment variable is set to use the service name `db`,
    # which will override this default.
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://lextr_user:Mygooru1028%24@localhost:5433/lextr",
    )
    redis_url: str | None = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    default_namespace: str = os.getenv("SEMANTIC_NAMESPACE_DEFAULT", "default")
    semantic_version: str = os.getenv("SEMANTIC_VERSION", "v0.1.0")
    enable_cache: bool = os.getenv("ENABLE_CACHE", "true").lower() == "true"
    cache_ttl_seconds: int = int(os.getenv("CACHE_TTL_SECONDS", "86400"))
    max_batch: int = int(os.getenv("MAX_BATCH", "5000"))
    readiness_delay_sec: int = int(os.getenv("READINESS_DELAY_SEC", "0"))

settings = Settings()
