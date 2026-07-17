from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.agent import RcaAgent


def _cases_path() -> Path:
    return Path(__file__).resolve().parents[2] / "fixtures" / "eval_cases.json"


async def run_cases(
    case_ids: Optional[List[str]] = None,
    feature_summary: bool = True,
    feature_cache: bool = True,
) -> Dict[str, Any]:
    all_cases = json.loads(_cases_path().read_text(encoding="utf-8"))
    if case_ids:
        wanted = set(case_ids)
        cases = [c for c in all_cases if c["id"] in wanted]
    else:
        cases = all_cases

    rows = []
    for c in cases:
        agent = RcaAgent(use_summary=feature_summary, use_cache=feature_cache)
        # warm run for cache A/B: run twice when cache on
        result = await agent.run(c["alert"])
        m = result.metrics
        rows.append({
            "case_id": c["id"],
            "latency_ms": m.get("latency_ms"),
            "prompt_tokens": m.get("prompt_tokens"),
            "completion_tokens": m.get("completion_tokens"),
            "tool_calls": m.get("tool_calls"),
            "cache_hits": m.get("cache_hits"),
            "root_cause": (result.report or {}).get("root_cause", "")[:160],
        })
        if feature_cache:
            agent2 = RcaAgent(use_summary=feature_summary, use_cache=True)
            # reuse same cache dir — second identical alert
            r2 = await agent2.run(c["alert"])
            m2 = r2.metrics
            rows.append({
                "case_id": c["id"] + "#repeat",
                "latency_ms": m2.get("latency_ms"),
                "prompt_tokens": m2.get("prompt_tokens"),
                "completion_tokens": m2.get("completion_tokens"),
                "tool_calls": m2.get("tool_calls"),
                "cache_hits": m2.get("cache_hits"),
                "root_cause": (r2.report or {}).get("root_cause", "")[:160],
            })

    return {
        "feature_summary": feature_summary,
        "feature_cache": feature_cache,
        "rows": rows,
    }
