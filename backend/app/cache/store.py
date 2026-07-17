from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional

from app.config import CACHE_DIR, FEATURE_CACHE


class MultiLevelCache:
    """L1 in-process dict + L2 disk JSON. Keyed by stable hash."""

    def __init__(self, enabled: Optional[bool] = None, ttl_sec: int = 3600):
        self.enabled = FEATURE_CACHE if enabled is None else enabled
        self.ttl_sec = ttl_sec
        self._l1: dict[str, tuple[float, Any]] = {}
        self.dir = Path(CACHE_DIR)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.hits = 0
        self.misses = 0

    @staticmethod
    def make_key(namespace: str, payload: Any) -> str:
        raw = json.dumps({"ns": namespace, "p": payload}, ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        if not self.enabled:
            return None
        now = time.time()
        item = self._l1.get(key)
        if item and now - item[0] < self.ttl_sec:
            self.hits += 1
            return item[1]
        path = self.dir / f"{key}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if now - float(data.get("ts", 0)) < self.ttl_sec:
                    val = data.get("value")
                    self._l1[key] = (now, val)
                    self.hits += 1
                    return val
            except (json.JSONDecodeError, OSError, TypeError, ValueError):
                pass
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        now = time.time()
        self._l1[key] = (now, value)
        path = self.dir / f"{key}.json"
        try:
            path.write_text(
                json.dumps({"ts": now, "value": value}, ensure_ascii=False),
                encoding="utf-8",
            )
        except OSError:
            pass
