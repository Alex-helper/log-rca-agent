"""MCP client wrapper with summary + cache hooks."""

from __future__ import annotations

import json
from typing import Any, Optional

from app.cache.store import MultiLevelCache
from app.mcp.server import LogMcpServer
from app.otel.setup import get_tracer
from app.summary.structured import summarize_logs


class McpToolClient:
    def __init__(
        self,
        server: LogMcpServer,
        cache: Optional[MultiLevelCache] = None,
        summarize: bool = True,
    ):
        self.server = server
        self.cache = cache
        self.summarize = summarize
        self.tool_calls = 0
        self.tracer = get_tracer("mcp-client")

    def list_tools_openai(self) -> list[dict[str, Any]]:
        return self.server.openai_tools()

    def call(self, name: str, arguments: Optional[dict] = None) -> tuple[str, dict[str, Any]]:
        args = arguments or {}
        cache_payload = {"tool": name, "args": args, "summarize": self.summarize}
        if self.cache:
            hit = self.cache.get("mcp_tool", cache_payload)
            if hit is not None:
                return hit["text"], {"cached": True, "raw": hit.get("raw")}

        with self.tracer.start_as_current_span(f"mcp.call_tool.{name}") as span:
            span.set_attribute("mcp.tool", name)
            raw = self.server.call_tool(name, args)
            self.tool_calls += 1
            # Summarize log-heavy payloads
            result = raw.get("result", raw)
            if self.summarize and name in ("query_logs", "get_trace_logs", "aggregate_errors"):
                text = summarize_logs(result, enabled=True)
            else:
                text = json.dumps(raw, ensure_ascii=False)
            span.set_attribute("mcp.cached", False)

        if self.cache:
            self.cache.set("mcp_tool", cache_payload, {"text": text, "raw": raw})
        return text, {"cached": False, "raw": raw}
