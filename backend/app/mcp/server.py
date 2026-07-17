"""In-process MCP-style log tool server (tools/list + tools/call)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app import config
from app.otel import get_tracer

TOOL_SPECS = [
    {
        "name": "list_services",
        "description": "List microservice names that have local log fixtures.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "query_logs",
        "description": "Query logs by service and optional keyword / level filter.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "keyword": {"type": "string"},
                "level": {"type": "string"},
                "limit": {"type": "integer", "default": 30},
            },
            "required": ["service"],
        },
    },
    {
        "name": "get_trace_logs",
        "description": "Fetch all log lines for a trace_id across services.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace_id": {"type": "string"},
                "limit": {"type": "integer", "default": 50},
            },
            "required": ["trace_id"],
        },
    },
    {
        "name": "aggregate_errors",
        "description": "Aggregate ERROR/WARN counts by service and message signature.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service": {"type": "string"},
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
]


class MCPLogServer:
    """Local MCP tool host backed by JSONL fixtures."""

    def __init__(self, log_dir: Optional[Path] = None):
        self.log_dir = Path(log_dir or config.LOG_FIXTURE_DIR)
        self._logs: List[dict] = []
        self._load()

    def _load(self) -> None:
        self._logs = []
        if not self.log_dir.exists():
            return
        for path in sorted(self.log_dir.glob("*.jsonl")):
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                try:
                    self._logs.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    def list_tools(self) -> List[dict]:
        return TOOL_SPECS

    def call_tool(self, name: str, arguments: Optional[dict] = None) -> dict:
        tracer = get_tracer()
        args = arguments or {}
        with tracer.start_as_current_span(f"mcp.tool.{name}") as span:
            span.set_attribute("mcp.tool", name)
            span.set_attribute("mcp.args", json.dumps(args, ensure_ascii=False)[:500])
            if name == "list_services":
                result = self._list_services()
            elif name == "query_logs":
                result = self._query_logs(args)
            elif name == "get_trace_logs":
                result = self._get_trace_logs(args)
            elif name == "aggregate_errors":
                result = self._aggregate_errors(args)
            else:
                result = {"error": f"unknown tool: {name}"}
            return result

    def _list_services(self) -> dict:
        services = sorted({str(x.get("service")) for x in self._logs if x.get("service")})
        return {"services": services, "log_count": len(self._logs)}

    def _query_logs(self, args: dict) -> dict:
        service = str(args.get("service", "")).strip()
        keyword = str(args.get("keyword", "")).strip().lower()
        level = str(args.get("level", "")).strip().upper()
        limit = int(args.get("limit") or 30)
        rows = []
        for row in self._logs:
            if service and str(row.get("service")) != service:
                continue
            if level and str(row.get("level", "")).upper() != level:
                continue
            msg = str(row.get("msg", "")).lower()
            if keyword and keyword not in msg and keyword not in str(row.get("trace_id", "")).lower():
                continue
            rows.append(row)
            if len(rows) >= limit:
                break
        return {"service": service, "count": len(rows), "logs": rows}

    def _get_trace_logs(self, args: dict) -> dict:
        tid = str(args.get("trace_id", "")).strip()
        limit = int(args.get("limit") or 50)
        rows = [r for r in self._logs if str(r.get("trace_id", "")) == tid][:limit]
        return {"trace_id": tid, "count": len(rows), "logs": rows}

    def _aggregate_errors(self, args: dict) -> dict:
        service = str(args.get("service", "")).strip()
        limit = int(args.get("limit") or 20)
        from collections import Counter

        c = Counter()
        for row in self._logs:
            if service and str(row.get("service")) != service:
                continue
            if str(row.get("level", "")).upper() not in ("ERROR", "WARN", "WARNING", "FATAL"):
                continue
            key = f"{row.get('service')}|{row.get('msg', '')[:100]}"
            c[key] += 1
        items = [
            {"signature": k, "count": v}
            for k, v in c.most_common(limit)
        ]
        return {"service": service or "*", "items": items}
