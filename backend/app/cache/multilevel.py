"""L1 process memory + L2 disk JSON cache."""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any, Optional, Tuple

from app import config


class MultiLevelCache:
    def __init__(self, enabled: Optional[bool] = None):
        self.enabled = config.FEATURE_CACHE if enabled is None else enabled
        self.l1: dict[str, Tuple[float, Any]] = {}
        self.dir = Path(config.CACHE_DIR)
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
        item = self.l1.get(key)
        if item and now - item[0] < config.CACHE_TTL_SEC:
            self.hits += 1
            return item[1]
        path = self.dir / f"{key}.json"
        if path.exists():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                if now - data.get("ts", 0) < config.CACHE_TTL_SEC:
                    val = data.get("value")
                    self.l1[key] = (data["ts"], val)
                    self.hits += 1
                    return val
            except Exception:
                pass
        self.misses += 1
        return None

    def set(self, key: str, value: Any) -> None:
        if not self.enabled:
            return
        ts = time.time()
        self.l1[key] = (ts, value)
        path = self.dir / f"{key}.json"
        path.write_text(
            json.dumps({"ts": ts, "value": value}, ensure_ascii=False),
            encoding="utf-8",
        )
