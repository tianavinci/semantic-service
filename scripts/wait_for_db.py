"""Wait-for-DB script: tries to connect to the DATABASE_URL using asyncpg
and, on success, execs the provided command (usually uvicorn).

Usage (in Dockerfile/CMD):
  CMD ["python", "scripts/wait_for_db.py", "uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "2"]

The script looks at the env var DATABASE_URL (default defined in api/app/config.py).
It will retry until `timeout` seconds elapse (default 60). It can optionally use
an environment-provided fallback host IP (DOCKER_HOST_IP) to substitute for
hosts like `host.docker.internal` when DNS resolution inside the container fails.
"""

import os
import sys
import asyncio
import logging
from urllib.parse import urlparse, urlunparse

import asyncpg

logging.basicConfig(level=os.getenv("WAIT_LOG_LEVEL", "INFO"))
logger = logging.getLogger("wait_for_db")

DB_URL = os.getenv("DATABASE_URL")
TIMEOUT = int(os.getenv("DB_WAIT_TIMEOUT", "60"))
INTERVAL = float(os.getenv("DB_WAIT_INTERVAL", "1"))
FALLBACK_IP = os.getenv("DOCKER_HOST_IP")


async def try_connect(db_url: str):
    try:
        # Normalize DSN for asyncpg: asyncpg expects schemes like 'postgresql://'
        # but callers may pass 'postgresql+asyncpg://' (SQLAlchemy style). Strip the
        # '+asyncpg' suffix and remove query params to avoid asyncpg parsing issues.
        from urllib.parse import urlsplit, urlunsplit

        parts = urlsplit(db_url)
        scheme = parts.scheme.split("+", 1)[0]
        # rebuild without query to avoid passing unknown params to asyncpg
        normalized = urlunsplit((scheme, parts.netloc, parts.path or "", "", ""))

        conn = await asyncpg.connect(dsn=normalized)
        await conn.close()
        return True
    except Exception as exc:
        logger.debug("DB connect failed for %s: %s", db_url, exc)
        return False


def replace_host_in_dsn(dsn: str, new_host: str) -> str:
    """Return a DSN with the hostname replaced by new_host, preserving port and auth."""
    parsed = urlparse(dsn)
    # parsed.netloc can be user:pass@host:port or host:port
    # Build new netloc with same userinfo and port
    userinfo = ""
    if parsed.username:
        userinfo = parsed.username
        if parsed.password:
            userinfo += f":{parsed.password}"
        userinfo += "@"
    port = f":{parsed.port}" if parsed.port else ""
    new_netloc = f"{userinfo}{new_host}{port}"
    new_parsed = parsed._replace(netloc=new_netloc)
    return urlunparse(new_parsed)


async def wait_for_db(db_url: str, timeout: int, interval: float):
    logger.info("Waiting for DB at %s (timeout=%ss)...", db_url, timeout)
    deadline = asyncio.get_event_loop().time() + timeout
    tried_fallback = False
    while True:
        ok = await try_connect(db_url)
        if ok:
            logger.info("DB is available (using %s)", db_url)
            return True

        # If we have a fallback IP and haven't tried it yet, attempt once
        if FALLBACK_IP and not tried_fallback:
            try:
                fallback_dsn = replace_host_in_dsn(db_url, FALLBACK_IP)
                logger.info("Attempting fallback DB host %s -> %s", FALLBACK_IP, fallback_dsn)
                tried_fallback = True
                ok2 = await try_connect(fallback_dsn)
                if ok2:
                    logger.info("DB is available (using fallback host %s)", FALLBACK_IP)
                    return True
                else:
                    logger.warning("Fallback host %s did not accept connection", FALLBACK_IP)
            except Exception as exc:
                logger.debug("Fallback attempt failed: %s", exc)

        if asyncio.get_event_loop().time() > deadline:
            logger.error("Timed out waiting for DB after %s seconds", timeout)
            return False
        await asyncio.sleep(interval)


def main():
    if not DB_URL:
        # try to import default from app config
        try:
            from api.app.config import settings

            db = settings.database_url
        except Exception:
            db = None
    else:
        db = DB_URL

    if not db:
        logger.error("No DATABASE_URL provided via env or config; exiting")
        sys.exit(1)

    # command to execute after DB is ready
    cmd = sys.argv[1:]
    if not cmd:
        logger.error("No command provided to execute after DB readiness; exiting")
        sys.exit(1)

    ok = asyncio.run(wait_for_db(db, TIMEOUT, INTERVAL))
    if not ok:
        logger.error("DB did not become ready; exiting")
        sys.exit(2)

    # exec the command
    logger.info("Executing: %s", cmd)
    os.execvp(cmd[0], cmd)


if __name__ == '__main__':
    main()
