from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Dict, List, Optional

from app.cache import MultiLevelCache
from app.config import AGENT_MAX_STEPS, FEATURE_CACHE, FEATURE_SUMMARY, PROMPTS_DIR
from app.llm import DeepSeekClient, LLMError
from app.mcp import get_registry
from app.otel.tracing import span
from app.summary import summarize_tool_result


ALLOWED_TOOLS = {"list_services", "query_logs", "get_trace_logs", "aggregate_errors"}


@dataclass
class RunResult:
    report: Dict[str, Any]
    steps: List[Dict[str, Any]] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)


def _extract_json(text: str) -> Optional[Dict[str, Any]]:
    text = (text or "").strip()
    if not text:
        return None
    try:
        obj = json.loads(text)
        if isinstance(obj, dict):
            return obj
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{[\s\S]*\}", text)
    if not m:
        return None
    try:
        obj = json.loads(m.group(0))
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        return None


class RcaAgent:
    def __init__(
        self,
        llm: Optional[DeepSeekClient] = None,
        use_summary: Optional[bool] = None,
        use_cache: Optional[bool] = None,
        max_steps: Optional[int] = None,
    ):
        self.llm = llm or DeepSeekClient()
        self.use_summary = FEATURE_SUMMARY if use_summary is None else use_summary
        self.use_cache = FEATURE_CACHE if use_cache is None else use_cache
        self.max_steps = max_steps or AGENT_MAX_STEPS
        self.registry = get_registry()
        self.cache = MultiLevelCache(enabled=self.use_cache)
        self.system = (PROMPTS_DIR / "system.txt").read_text(encoding="utf-8")

    async def run_stream(self, alert: Dict[str, Any]) -> AsyncIterator[Dict[str, Any]]:
        t0 = time.time()
        prompt_tokens = 0
        completion_tokens = 0
        tool_calls = 0
        steps: List[Dict[str, Any]] = []

        with span("agent.rca.run"):
            history: List[Dict[str, str]] = [
                {"role": "system", "content": self.system},
                {
                    "role": "user",
                    "content": (
                        "请对以下告警做根因定位。先用工具取证，再输出 final report。\n"
                        f"ALERT_JSON:\n{json.dumps(alert, ensure_ascii=False)}"
                    ),
                },
            ]

            report: Optional[Dict[str, Any]] = None
            try:
                for step_i in range(self.max_steps):
                    content, usage = await self.llm.chat(history, temperature=0.15, max_tokens=1200)
                    prompt_tokens += usage.get("prompt_tokens", 0)
                    completion_tokens += usage.get("completion_tokens", 0)

                    obj = _extract_json(content)
                    if not obj:
                        err = {
                            "type": "error",
                            "content": f"模型输出无法解析为 JSON：{content[:300]}",
                        }
                        steps.append(err)
                        yield {"event": "trace", "data": err}
                        break

                    typ = (obj.get("type") or "").lower()
                    thought = obj.get("thought") or ""
                    if thought:
                        ev = {"type": "thought", "content": thought, "step": step_i + 1}
                        steps.append(ev)
                        yield {"event": "trace", "data": ev}

                    if typ == "final":
                        report = obj.get("report") if isinstance(obj.get("report"), dict) else obj
                        report = self._normalize_report(report)
                        break

                    if typ != "action":
                        err = {"type": "error", "content": f"未知 type: {typ}"}
                        steps.append(err)
                        yield {"event": "trace", "data": err}
                        break

                    tool = (obj.get("tool") or "").strip()
                    arguments = obj.get("arguments") if isinstance(obj.get("arguments"), dict) else {}
                    if tool not in ALLOWED_TOOLS:
                        obs = {"error": f"工具不在白名单: {tool}", "allowed": sorted(ALLOWED_TOOLS)}
                        obs_text = json.dumps(obs, ensure_ascii=False)
                    else:
                        act = {
                            "type": "action",
                            "content": f"{tool}({json.dumps(arguments, ensure_ascii=False)})",
                            "tool": tool,
                            "step": step_i + 1,
                        }
                        steps.append(act)
                        yield {"event": "trace", "data": act}

                        cache_key = self.cache.make_key("mcp", {"tool": tool, "args": arguments})
                        cached = self.cache.get(cache_key)
                        if cached is not None:
                            raw = cached
                            from_cache = True
                        else:
                            raw = self.registry.call_tool(tool, arguments)
                            self.cache.set(cache_key, raw)
                            tool_calls += 1
                            from_cache = False

                        obs_text = summarize_tool_result(tool, raw, enabled=self.use_summary)
                        if from_cache:
                            obs_text = "[cache_hit]\n" + obs_text

                    obs_ev = {
                        "type": "observation",
                        "content": obs_text[:6000],
                        "tool": tool,
                        "step": step_i + 1,
                    }
                    steps.append(obs_ev)
                    yield {"event": "trace", "data": obs_ev}

                    history.append({"role": "assistant", "content": json.dumps(obj, ensure_ascii=False)})
                    history.append({
                        "role": "user",
                        "content": f"Observation from {tool}:\n{obs_text}\n继续。若证据足够请输出 type=final。",
                    })
                else:
                    # max steps without final
                    report = self._fallback_report(alert, steps, "达到最大步数，基于已有 observation 汇总")

            except LLMError as e:
                yield {"event": "error", "data": {"message": str(e)}}
                metrics = self._metrics(t0, prompt_tokens, completion_tokens, tool_calls)
                yield {"event": "metrics", "data": metrics}
                yield {"event": "done", "data": {}}
                return

            if report is None:
                report = self._fallback_report(alert, steps, "未能解析 final，使用兜底报告")

            metrics = self._metrics(t0, prompt_tokens, completion_tokens, tool_calls)
            yield {"event": "report", "data": report}
            yield {"event": "metrics", "data": metrics}
            yield {"event": "done", "data": {}}

    def _metrics(self, t0: float, pt: int, ct: int, tool_calls: int) -> Dict[str, Any]:
        return {
            "latency_ms": int((time.time() - t0) * 1000),
            "prompt_tokens": pt,
            "completion_tokens": ct,
            "tool_calls": tool_calls,
            "cache_hits": self.cache.hits,
            "feature_summary": self.use_summary,
            "feature_cache": self.use_cache,
            "model": self.llm.model,
        }

    def _normalize_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "root_cause": str(report.get("root_cause") or "证据不足，未能定位"),
            "evidence": list(report.get("evidence") or [])[:12],
            "blast_radius": str(report.get("blast_radius") or "未知"),
            "remediation": list(report.get("remediation") or [])[:12],
            "confidence_note": str(report.get("confidence_note") or "低：证据有限"),
        }

    def _fallback_report(self, alert: Dict[str, Any], steps: List[Dict[str, Any]], note: str) -> Dict[str, Any]:
        obs = [s.get("content", "") for s in steps if s.get("type") == "observation"]
        evidence = [o[:200] for o in obs[-3:]] or ["无工具观测"]
        return {
            "root_cause": f"假设 / 证据不足：{note}。告警：{alert.get('message', '')}",
            "evidence": evidence,
            "blast_radius": f"可能影响服务：{alert.get('service', 'unknown')} 及其上游调用链",
            "remediation": [
                "核对相关 trace 的 ERROR 日志",
                "检查依赖中间件连通性与超时配置",
                "必要时对故障服务限流并回滚最近变更",
            ],
            "confidence_note": f"低：{note}",
        }

    async def run(self, alert: Dict[str, Any]) -> RunResult:
        report: Dict[str, Any] = {}
        steps: List[Dict[str, Any]] = []
        metrics: Dict[str, Any] = {}
        async for ev in self.run_stream(alert):
            if ev["event"] == "trace":
                steps.append(ev["data"])
            elif ev["event"] == "report":
                report = ev["data"]
            elif ev["event"] == "metrics":
                metrics = ev["data"]
            elif ev["event"] == "error":
                raise LLMError(ev["data"].get("message", "unknown"))
        return RunResult(report=report, steps=steps, metrics=metrics)
