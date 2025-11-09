import json, asyncio
import logging
from redis.asyncio import Redis
# redis exceptions location may differ across redis-py versions; try both
try:
    from redis import exceptions as redis_exceptions
except Exception:
    from redis.asyncio import exceptions as redis_exceptions
from api.app.config import settings

log = logging.getLogger(__name__)

def _k_phys(ns, ent, phys): return f"attr:by_phys:{ns}:{ent}:{phys}"
def _k_logi(ns, ent, logi): return f"attr:by_logi:{ns}:{ent}:{logi}"

class Cache:
    def __init__(self):
        self.enabled = settings.enable_cache and settings.redis_url is not None
        self.ttl = settings.cache_ttl_seconds
        self.redis: Redis | None = None
        if self.enabled:
            try:
                self.redis = Redis.from_url(settings.redis_url)
            except Exception as e:
                log.warning("Failed to create Redis client: %s", e)
                self.redis = None

    async def get_phys(self, ns, ent, phys):
        if not self.redis: return None
        try:
            raw = await self.redis.get(_k_phys(ns, ent, phys))
            return json.loads(raw) if raw else None
        except redis_exceptions.ConnectionError as e:
            log.warning("Redis connection error on get_phys: %s", e)
            return None
        except Exception as e:
            log.exception("Redis get_phys unexpected error: %s", e)
            return None

    async def get_logi(self, ns, ent, logi):
        if not self.redis: return None
        try:
            raw = await self.redis.get(_k_logi(ns, ent, logi))
            return json.loads(raw) if raw else None
        except redis_exceptions.ConnectionError as e:
            log.warning("Redis connection error on get_logi: %s", e)
            return None
        except Exception as e:
            log.exception("Redis get_logi unexpected error: %s", e)
            return None

    async def set_both(self, payload):
        if not self.redis: return
        ns, ent = payload["namespace"], payload["entity"]
        phys, logi = payload["physical_name"], payload["logical_name"]
        raw = json.dumps(payload)
        try:
            await asyncio.gather(
                self.redis.set(_k_phys(ns, ent, phys), raw, ex=self.ttl),
                self.redis.set(_k_logi(ns, ent, logi), raw, ex=self.ttl)
            )
        except redis_exceptions.ConnectionError as e:
            # Don't let cache failures break the request path
            log.warning("Redis connection error on set_both: %s", e)
        except Exception as e:
            log.exception("Unexpected error writing to Redis cache: %s", e)

    async def invalidate(self, ns, ent, phys, logi):
        if not self.redis: return
        try:
            await self.redis.delete(_k_phys(ns, ent, phys))
            await self.redis.delete(_k_logi(ns, ent, logi))
        except redis_exceptions.ConnectionError as e:
            log.warning("Redis connection error on invalidate: %s", e)
        except Exception as e:
            log.exception("Unexpected error deleting Redis keys: %s", e)

cache = Cache()
