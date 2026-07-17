"""
MCP-style tool registry for log RCA.

Tools expose JSON Schema descriptors compatible with MCP tool listing,
and execute in-process against fixture logs (local MCP server transport).
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.config import FIXTURES_LOGS
from app.otel.tracing import span


ToolHandler = Callable[[Dict[str, Any]], Any]


class MCPToolRegistry:
    def __init__(self, logs_dir: Optional[Path] = None):
        self.logs_dir = Path(logs_dir or FIXTURES_LOGS)
        self._entries: Dict[str, Dict[str, Any]] = {}
        self._register_defaults()

    def _register(self, name: str, description: str, schema: Dict[str, Any], handler: ToolHandler):
        self._entries[name] = {
            "name": name,
            "description": description,
            "inputSchema": schema,
            "handler": handler,
        }

    def list_tools(self) -> List[Dict[str, Any]]:
        """MCP tools/list shape (without handler)."""
        out = []
        for name, e in self._entries.items():
            out.append({
                "name": e["name"],
                "description": e["description"],
                "inputSchema": e["inputSchema"],
            })
        return out

    def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        if name not in self._entries:
            raise ValueError(f"Unknown MCP tool: {name}")
        args = arguments or {}
        with span(f"mcp.tool.{name}", {"mcp.tool": name}):
            return self._entries[name]["handler"](args)

    # ── data helpers ──────────────────────────────────────────
    def _load_all(self) -> List[Dict[str, Any]]:
        rows: List[Dict[str, Any]] = []
        if not self.logs_dir.exists():
            return rows
        for p in sorted(self.logs_dir.glob("*.jsonl")):
            for line in p.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    rows.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
        return rows

    def _register_defaults(self):
        self._register(
            "list_services",
            "List microservice names present in the log corpus.",
            {"type": "object", "properties": {}, "additionalProperties": False},
            self._list_services,
        )
        self._register(
            "query_logs",
            "Query logs by service / level / keyword / time substring.",
            {
                "type": "object",
                "properties": {
                    "service": {"type": "string"},
                    "level": {"type": "string"},
                    "keyword": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
            self._query_logs,
        )
        self._register(
            "get_trace_logs",
            "Fetch all log lines for a trace_id across services.",
            {
                "type": "object",
                "properties": {
                    "trace_id": {"type": "string"},
                    "limit": {"type": "integer", "default": 50},
                },
                "required": ["trace_id"],
            },
            self._get_trace_logs,
        )
        self._register(
            "aggregate_errors",
            "Aggregate ERROR/WARN counts by service (optional keyword filter).",
            {
                "type": "object",
                "properties": {
                    "keyword": {"type": "string"},
                },
            },
            self._aggregate_errors,
        )

    def _list_services(self, args: Dict[str, Any]) -> Dict[str, Any]:
        services = sorted({r.get("service", "") for r in self._load_all() if r.get("service")})
        return {"services": services, "count": len(services)}

    def _query_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        service = (args.get("service") or "").strip()
        level = (args.get("level") or "").strip().upper()
        keyword = (args.get("keyword") or "").strip().lower()
        limit = int(args.get("limit") or 20)
        limit = max(1, min(limit, 100))
        hits = []
        for r in self._load_all():
            if service and r.get("service") != service:
                continue
            if level and str(r.get("level", "")).upper() != level:
                continue
            blob = json.dumps(r, ensure_ascii=False).lower()
            if keyword and keyword not in blob:
                continue
            hits.append(r)
            if len(hits) >= limit:
                break
        return {"count": len(hits), "logs": hits}

    def _get_trace_logs(self, args: Dict[str, Any]) -> Dict[str, Any]:
        tid = (args.get("trace_id") or "").strip()
        if not tid:
            return {"error": "trace_id required", "logs": []}
        limit = int(args.get("limit") or 50)
        hits = [r for r in self._load_all() if r.get("trace_id") == tid][:limit]
        return {"trace_id": tid, "count": len(hits), "logs": hits}

    def _aggregate_errors(self, args: Dict[str, Any]) -> Dict[str, Any]:
        keyword = (args.get("keyword") or "").strip().lower()
        counts: Dict[str, Dict[str, int]] = {}
        samples: Dict[str, List[str]] = {}
        for r in self._load_all():
            lvl = str(r.get("level", "")).upper()
            if lvl not in ("ERROR", "WARN"):
                continue
            msg = str(r.get("msg", ""))
            if keyword and keyword not in json.dumps(r, ensure_ascii=False).lower():
                continue
            svc = r.get("service") or "unknown"
            bucket = counts.setdefault(svc, {"ERROR": 0, "WARN": 0})
            bucket[lvl] = bucket.get(lvl, 0) + 1
            samples.setdefault(svc, [])
            if len(samples[svc]) < 3:
                samples[svc].append(msg)
        return {"by_service": counts, "samples": samples}


_registry: Optional[MCPToolRegistry] = None


def get_registry() -> MCPToolRegistry:
    global _registry
    if _registry is None:
        _registry = MCPToolRegistry()
    return _registry
