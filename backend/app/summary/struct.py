from __future__ import annotations

import json
from typing import Any, Dict, List

from app.config import FEATURE_SUMMARY


def summarize_tool_result(tool: str, result: Any, enabled: bool | None = None) -> str:
    """
    结构化日志摘要：把工具原始 JSON 压成排障相关字段，降低回灌 Token。
    关闭时返回 pretty JSON 全文（基线）。
    """
    use = FEATURE_SUMMARY if enabled is None else enabled
    if not use:
        return json.dumps(result, ensure_ascii=False, indent=2)[:12000]

    if not isinstance(result, dict):
        return json.dumps(result, ensure_ascii=False)[:4000]

    if tool == "list_services":
        return json.dumps({
            "services": result.get("services", []),
            "count": result.get("count", 0),
        }, ensure_ascii=False)

    if tool == "aggregate_errors":
        return json.dumps({
            "by_service": result.get("by_service", {}),
            "top_samples": {
                k: v[:2] for k, v in (result.get("samples") or {}).items()
            },
        }, ensure_ascii=False)

    logs = result.get("logs") or []
    compact: List[Dict[str, Any]] = []
    for row in logs[:25]:
        if not isinstance(row, dict):
            continue
        compact.append({
            "ts": row.get("ts"),
            "service": row.get("service"),
            "level": row.get("level"),
            "trace_id": row.get("trace_id"),
            "msg": row.get("msg"),
        })

    summary = {
        "tool": tool,
        "count": result.get("count", len(compact)),
        "levels": _count_levels(compact),
        "services": sorted({c.get("service") for c in compact if c.get("service")}),
        "error_msgs": [c["msg"] for c in compact if str(c.get("level")).upper() == "ERROR"][:8],
        "lines": compact,
    }
    if "trace_id" in result:
        summary["trace_id"] = result.get("trace_id")
    if result.get("error"):
        summary["error"] = result["error"]
    return json.dumps(summary, ensure_ascii=False)


def _count_levels(rows: List[Dict[str, Any]]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for r in rows:
        lvl = str(r.get("level") or "?").upper()
        out[lvl] = out.get(lvl, 0) + 1
    return out
