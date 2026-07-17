"""Structured log summarization — compress tool observations."""

from __future__ import annotations

import json
import re
from collections import Counter
from typing import Any, Dict, List

from app import config


def summarize_logs(raw: Any, enabled: bool | None = None) -> str:
    use = config.FEATURE_SUMMARY if enabled is None else enabled
    if isinstance(raw, str):
        try:
            data = json.loads(raw)
        except Exception:
            text = raw
            if not use:
                return text
            return _summarize_text(text)
    else:
        data = raw

    if not use:
        return json.dumps(data, ensure_ascii=False)[:8000]

    if isinstance(data, dict) and "logs" in data:
        logs = data["logs"]
        meta = {k: v for k, v in data.items() if k != "logs"}
    elif isinstance(data, list):
        logs = data
        meta = {}
    else:
        return json.dumps(data, ensure_ascii=False)[:4000]

    levels = Counter(str(x.get("level", "?")).upper() for x in logs)
    services = Counter(str(x.get("service", "?")) for x in logs)
    # keep ERROR/WARN first, then truncate
    ranked = sorted(
        logs,
        key=lambda x: {"ERROR": 0, "WARN": 1, "WARNING": 1}.get(str(x.get("level", "")).upper(), 9),
    )
    samples = ranked[:12]
    error_msgs = []
    for x in ranked:
        if str(x.get("level", "")).upper() == "ERROR":
            error_msgs.append(str(x.get("msg", ""))[:160])
        if len(error_msgs) >= 5:
            break

    summary = {
        "meta": meta,
        "count": len(logs),
        "levels": dict(levels),
        "services": dict(services),
        "top_errors": error_msgs,
        "samples": samples,
        "note": "structured_summary_v1",
    }
    return json.dumps(summary, ensure_ascii=False)


def _summarize_text(text: str) -> str:
    lines = [ln for ln in text.splitlines() if ln.strip()]
    err = [ln for ln in lines if re.search(r"ERROR|Exception|timeout|fail", ln, re.I)]
    keep = (err[:8] or lines[:8])
    return json.dumps(
        {"count_lines": len(lines), "highlights": keep, "note": "structured_summary_text"},
        ensure_ascii=False,
    )
