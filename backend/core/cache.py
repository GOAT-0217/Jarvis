import json
import os
from typing import Any, Optional

import redis


class RedisCache:
    def __init__(self):
        self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
        self.key_prefix = os.getenv("REDIS_KEY_PREFIX", "supermew")
        self.default_ttl = int(os.getenv("REDIS_CACHE_TTL_SECONDS", "300"))
        self._client = None

    def _get_client(self):
        """该方法实现Redis客户端的懒加载"""
        if self._client is None:
            self._client = redis.Redis.from_url(self.redis_url, decode_responses=True)
        return self._client

    def _key(self, key: str) -> str:
        """生成Redis缓存键。"""
        return f"{self.key_prefix}:{key}"

    def get_json(self, key: str) -> Optional[Any]:
        """从Redis获取指定键的值:实现了安全的JSON数据读取，确保在数据缺失或出错时程序不会崩溃"""
        try:
            value = self._get_client().get(self._key(key))
            if not value:
                return None
            return json.loads(value)
        except Exception:
            return None

    def set_json(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """将任意值序列化为JSON字符串，并存入Redis。"""
        try:
            payload = json.dumps(value, ensure_ascii=False)
            self._get_client().setex(self._key(key), ttl or self.default_ttl, payload)
        except Exception:
            return

    def delete(self, key: str) -> None:
        """从Redis缓存中删除指定键。"""
        try:
            self._get_client().delete(self._key(key))
        except Exception:
            return

    def delete_pattern(self, pattern: str) -> None:
        """用于批量删除匹配指定模式的Redis键"""
        try:
            full_pattern = self._key(pattern)
            keys = self._get_client().keys(full_pattern)
            if keys:
                self._get_client().delete(*keys)
        except Exception:
            return


cache = RedisCache()
